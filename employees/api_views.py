"""
API Views для системы учёта рабочего времени
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal

from .models import (
    Employee, WorkSession, WorkDaySummary, WorkTimeAuditLog,
    SKUDEvent, SKUDDevice
)
from .serializers import (
    EmployeeSerializer, WorkSessionSerializer, WorkDaySummarySerializer,
    WorkTimeAuditLogSerializer, SKUDEventSerializer, SKUDDeviceSerializer,
    WorkSessionCreateSerializer, EmployeeWorkTimeStatsSerializer,
    DepartmentWorkTimeStatsSerializer, ReprocessWorkTimeSerializer,
    BirthdayEmployeeSerializer, PINFLSyncSerializer, PINFLSyncResponseSerializer
)
from .work_time_processor import WorkTimeProcessor
from .pinfl_api import pinfl_client


class WorkSessionViewSet(viewsets.ModelViewSet):
    """ViewSet для рабочих сессий"""
    
    queryset = WorkSession.objects.all()
    serializer_class = WorkSessionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'date', 'status', 'is_open']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_id']
    ordering_fields = ['date', 'start_time', 'end_time', 'duration_seconds']
    ordering = ['-date', '-start_time']
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return WorkSessionCreateSerializer
        return WorkSessionSerializer
    
    def get_permissions(self):
        """Права доступа"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Фильтрация queryset в зависимости от прав пользователя"""
        queryset = super().get_queryset().select_related('employee', 'corrected_by')
        
        # Если пользователь не админ, показываем только его собственные сессии
        if not self.request.user.is_staff:
            # Предполагаем, что у пользователя есть связанный Employee
            try:
                employee = Employee.objects.get(user=self.request.user)
                queryset = queryset.filter(employee=employee)
            except Employee.DoesNotExist:
                queryset = queryset.none()
        
        return queryset
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def close_open_sessions(self, request):
        """Закрытие открытых сессий"""
        employee_id = request.data.get('employee_id')
        date_str = request.data.get('date')
        reason = request.data.get('reason', 'Закрыто через API')
        
        queryset = self.get_queryset().filter(status='open')
        
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        if date_str:
            queryset = queryset.filter(date=date_str)
        
        closed_count = 0
        for session in queryset:
            session.end_time = timezone.now()
            session.status = 'closed_manual'
            session.manual_reason = reason
            session.corrected_by = request.user
            session.save()
            closed_count += 1
        
        return Response({
            'message': f'Закрыто {closed_count} открытых сессий',
            'closed_count': closed_count
        })
    
    @action(detail=False, methods=['get'])
    def employee_sessions(self, request):
        """Получение сессий конкретного сотрудника"""
        employee_id = request.query_params.get('employee_id')
        if not employee_id:
            return Response(
                {'error': 'employee_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(employee_id=employee_id)
        
        # Фильтрация по датам
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        if from_date:
            queryset = queryset.filter(date__gte=from_date)
        if to_date:
            queryset = queryset.filter(date__lte=to_date)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class WorkDaySummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для сводок рабочих дней (только чтение)"""
    
    queryset = WorkDaySummary.objects.all()
    serializer_class = WorkDaySummarySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'date', 'status', 'has_missing_exit', 'has_manual_corrections']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_id']
    ordering_fields = ['date', 'total_seconds_in_office', 'expected_seconds']
    ordering = ['-date']
    
    def get_queryset(self):
        """Фильтрация queryset в зависимости от прав пользователя"""
        queryset = super().get_queryset().select_related('employee')
        
        # Если пользователь не админ, показываем только его собственные сводки
        if not self.request.user.is_staff:
            try:
                employee = Employee.objects.get(user=self.request.user)
                queryset = queryset.filter(employee=employee)
            except Employee.DoesNotExist:
                queryset = queryset.none()
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def employee_summary(self, request):
        """Получение сводки конкретного сотрудника за период"""
        employee_id = request.query_params.get('employee_id')
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        if not employee_id or not from_date or not to_date:
            return Response(
                {'error': 'employee_id, from_date, to_date are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            employee_id=employee_id,
            date__gte=from_date,
            date__lte=to_date
        )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def department_stats(self, request):
        """Статистика по отделу"""
        department_id = request.query_params.get('department_id')
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        if not department_id or not from_date or not to_date:
            return Response(
                {'error': 'department_id, from_date, to_date are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем сотрудников отдела
        employees = Employee.objects.filter(
            department_id=department_id,
            is_active=True
        )
        
        # Получаем сводки за период
        summaries = self.get_queryset().filter(
            employee__department_id=department_id,
            date__gte=from_date_obj,
            date__lte=to_date_obj
        )
        
        # Рассчитываем статистику
        total_employees = employees.count()
        total_days = (to_date_obj - from_date_obj).days + 1
        total_hours_worked = sum(s.total_hours for s in summaries)
        total_hours_expected = sum(s.expected_hours for s in summaries)
        problem_days_count = summaries.filter(
            Q(has_missing_exit=True) | Q(has_manual_corrections=True)
        ).count()
        
        stats = {
            'department_name': employees.first().department.name if employees.exists() else 'Unknown',
            'period_start': from_date_obj,
            'period_end': to_date_obj,
            'total_employees': total_employees,
            'total_days': total_days,
            'total_hours_worked': total_hours_worked,
            'total_hours_expected': total_hours_expected,
            'average_hours_per_employee': total_hours_worked / total_employees if total_employees > 0 else 0,
            'work_efficiency_percent': (total_hours_worked / total_hours_expected * 100) if total_hours_expected > 0 else 0,
            'problem_days_count': problem_days_count
        }
        
        serializer = DepartmentWorkTimeStatsSerializer(stats)
        return Response(serializer.data)


class EmployeeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для сотрудников (только чтение)"""
    
    queryset = Employee.objects.filter(is_active=True)
    serializer_class = EmployeeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['department', 'division', 'position', 'work_fraction']
    search_fields = ['first_name', 'last_name', 'employee_id', 'email']
    ordering_fields = ['last_name', 'first_name', 'hire_date', 'work_fraction']
    ordering = ['last_name', 'first_name']
    
    @action(detail=True, methods=['get'])
    def work_time_stats(self, request, pk=None):
        """Статистика рабочего времени сотрудника"""
        employee = self.get_object()
        
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        if not from_date or not to_date:
            return Response(
                {'error': 'from_date and to_date are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем сводки за период
        summaries = WorkDaySummary.objects.filter(
            employee=employee,
            date__gte=from_date_obj,
            date__lte=to_date_obj
        )
        
        # Рассчитываем статистику
        total_days = (to_date_obj - from_date_obj).days + 1
        present_days = summaries.filter(status='present').count()
        absent_days = summaries.filter(status='absent').count()
        excused_days = summaries.filter(status='excused').count()
        problem_days = summaries.filter(status='problem').count()
        
        total_hours_worked = sum(s.total_hours for s in summaries)
        total_hours_expected = sum(s.expected_hours for s in summaries)
        total_overtime_hours = sum(s.overtime_hours for s in summaries)
        total_underwork_hours = sum(s.underwork_hours for s in summaries)
        
        average_hours_per_day = total_hours_worked / total_days if total_days > 0 else 0
        work_efficiency_percent = (total_hours_worked / total_hours_expected * 100) if total_hours_expected > 0 else 0
        
        stats = {
            'employee': employee,
            'period_start': from_date_obj,
            'period_end': to_date_obj,
            'total_days': total_days,
            'present_days': present_days,
            'absent_days': absent_days,
            'excused_days': excused_days,
            'problem_days': problem_days,
            'total_hours_worked': total_hours_worked,
            'total_hours_expected': total_hours_expected,
            'total_overtime_hours': total_overtime_hours,
            'total_underwork_hours': total_underwork_hours,
            'average_hours_per_day': average_hours_per_day,
            'work_efficiency_percent': work_efficiency_percent
        }
        
        serializer = EmployeeWorkTimeStatsSerializer(stats)
        return Response(serializer.data)


class WorkTimeProcessorViewSet(viewsets.ViewSet):
    """ViewSet для управления обработкой рабочего времени"""
    
    permission_classes = [permissions.IsAdminUser]
    
    @action(detail=False, methods=['post'])
    def reprocess(self, request):
        """Пересчёт рабочего времени"""
        serializer = ReprocessWorkTimeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        processor = WorkTimeProcessor()
        
        try:
            if data.get('employee_id') and data.get('date'):
                # Пересчёт конкретного сотрудника на конкретную дату
                employee = Employee.objects.get(id=data['employee_id'])
                success = processor.process_skud_events_for_employee(employee, data['date'])
                
                if success:
                    return Response({'message': 'Данные успешно пересчитаны'})
                else:
                    return Response(
                        {'error': 'Ошибка при пересчёте данных'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            elif data.get('employee_id') and data.get('from_date') and data.get('to_date'):
                # Пересчёт сотрудника за период
                employee = Employee.objects.get(id=data['employee_id'])
                processed_days = processor.reprocess_employee_period(
                    employee, data['from_date'], data['to_date']
                )
                
                return Response({
                    'message': f'Пересчитано {processed_days} дней',
                    'processed_days': processed_days
                })
            
            elif data.get('date'):
                # Пересчёт всех сотрудников на дату
                results = processor.reprocess_all_employees_day(data['date'])
                
                return Response({
                    'message': f'Обработано: {results["processed"]}, Ошибок: {results["errors"]}',
                    'processed': results['processed'],
                    'errors': results['errors']
                })
            
            elif data.get('from_date') and data.get('to_date'):
                # Пересчёт всех сотрудников за период
                current_date = data['from_date']
                total_processed = 0
                total_errors = 0
                
                while current_date <= data['to_date']:
                    results = processor.reprocess_all_employees_day(current_date)
                    total_processed += results['processed']
                    total_errors += results['errors']
                    current_date += timedelta(days=1)
                
                return Response({
                    'message': f'Обработано: {total_processed}, Ошибок: {total_errors}',
                    'processed': total_processed,
                    'errors': total_errors
                })
            
            else:
                return Response(
                    {'error': 'Недостаточно параметров для пересчёта'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Employee.DoesNotExist:
            return Response(
                {'error': 'Сотрудник не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Ошибка при пересчёте: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WorkTimeAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для аудита изменений (только чтение)"""
    
    queryset = WorkTimeAuditLog.objects.all()
    serializer_class = WorkTimeAuditLogSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'action', 'changed_by']
    search_fields = ['employee__first_name', 'employee__last_name', 'description']
    ordering_fields = ['changed_at', 'date']
    ordering = ['-changed_at']
    
    def get_queryset(self):
        """Фильтрация queryset в зависимости от прав пользователя"""
        queryset = super().get_queryset().select_related('employee', 'changed_by')
        
        # Если пользователь не админ, показываем только его собственные записи аудита
        if not self.request.user.is_staff:
            try:
                employee = Employee.objects.get(user=self.request.user)
                queryset = queryset.filter(employee=employee)
            except Employee.DoesNotExist:
                queryset = queryset.none()
        
        return queryset


class SKUDEventViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для событий СКУД (только чтение)"""
    
    queryset = SKUDEvent.objects.all()
    serializer_class = SKUDEventSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['device', 'employee', 'event_type', 'is_processed']
    search_fields = ['employee__first_name', 'employee__last_name', 'card_number']
    ordering_fields = ['event_time', 'created_at']
    ordering = ['-event_time']
    
    def get_queryset(self):
        """Фильтрация queryset в зависимости от прав пользователя"""
        queryset = super().get_queryset().select_related('device', 'employee')
        
        # Если пользователь не админ, показываем только его собственные события
        if not self.request.user.is_staff:
            try:
                employee = Employee.objects.get(user=self.request.user)
                queryset = queryset.filter(employee=employee)
            except Employee.DoesNotExist:
                queryset = queryset.none()
        
        return queryset


class SKUDDeviceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для СКУД устройств (только чтение)"""
    
    queryset = SKUDDevice.objects.all()
    serializer_class = SKUDDeviceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['device_type', 'status', 'is_active']
    search_fields = ['name', 'serial_number', 'ip_address', 'location']
    ordering_fields = ['name', 'ip_address', 'created_at']
    ordering = ['name']


class BirthdayViewSet(viewsets.ViewSet):
    """ViewSet для получения именинников"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def today_birthdays(self, request):
        """Получить именинников на сегодня"""
        today = timezone.now().date()
        
        # Получаем сотрудников с днем рождения сегодня
        birthday_employees = Employee.objects.filter(
            is_active=True,
            birth_date__month=today.month,
            birth_date__day=today.day
        ).select_related('department', 'division')
        
        serializer = BirthdayEmployeeSerializer(birthday_employees, many=True)
        
        return Response({
            'today_birthdays': serializer.data,
            'count': birthday_employees.count(),
            'date': today
        })
    
    @action(detail=False, methods=['get'])
    def upcoming_birthdays(self, request):
        """Получить ближайшие дни рождения (максимум 2 сотрудника)"""
        today = timezone.now().date()
        limit = int(request.query_params.get('limit', 2))
        
        # Получаем всех активных сотрудников
        employees = Employee.objects.filter(is_active=True).select_related('department', 'division')
        
        # Создаем список с информацией о днях рождения
        birthday_info = []
        for employee in employees:
            this_year_birthday = employee.birth_date.replace(year=today.year)
            
            # Если день рождения уже прошел в этом году, считаем до следующего года
            if this_year_birthday < today:
                next_year_birthday = employee.birth_date.replace(year=today.year + 1)
                days_until = (next_year_birthday - today).days
                birthday_date = next_year_birthday
            else:
                days_until = (this_year_birthday - today).days
                birthday_date = this_year_birthday
            
            birthday_info.append({
                'employee': employee,
                'days_until': days_until,
                'birthday_date': birthday_date
            })
        
        # Сортируем по количеству дней до дня рождения
        birthday_info.sort(key=lambda x: x['days_until'])
        
        # Берем только ближайшие
        upcoming = birthday_info[:limit]
        
        # Сериализуем данные
        serializer = BirthdayEmployeeSerializer([item['employee'] for item in upcoming], many=True)
        
        # Добавляем информацию о днях до дня рождения
        result_data = []
        for i, item in enumerate(upcoming):
            data = serializer.data[i]
            data['days_until_birthday'] = item['days_until']
            data['birthday_date'] = item['birthday_date']
            result_data.append(data)
        
        return Response({
            'upcoming_birthdays': result_data,
            'count': len(result_data),
            'today': today
        })
    
    @action(detail=False, methods=['get'])
    def birthday_widget_data(self, request):
        """Получить данные для виджета дня рождения"""
        today = timezone.now().date()
        
        # Именинники сегодня фильтруем только по правам доступа
        today_birthdays = Employee.objects.filter(
            is_active=True,
            birth_date__month=today.month,
            birth_date__day=today.day
        ).select_related('department', 'division')
        
        # Ближайшие дни рождения (максимум 2)
        employees = Employee.objects.filter(is_active=True).select_related('department', 'division')
        
        birthday_info = []
        for employee in employees:
            this_year_birthday = employee.birth_date.replace(year=today.year)
            
            if this_year_birthday < today:
                next_year_birthday = employee.birth_date.replace(year=today.year + 1)
                days_until = (next_year_birthday - today).days
                birthday_date = next_year_birthday
            else:
                days_until = (this_year_birthday - today).days
                birthday_date = this_year_birthday
            
            # Пропускаем тех, у кого день рождения сегодня (они уже в today_birthdays)
            if days_until > 0:
                birthday_info.append({
                    'employee': employee,
                    'days_until': days_until,
                    'birthday_date': birthday_date
                })
        
        # Сортируем и берем ближайшие
        birthday_info.sort(key=lambda x: x['days_until'])
        upcoming_birthdays = birthday_info[:2]
        
        # Сериализуем данные
        today_serializer = BirthdayEmployeeSerializer(today_birthdays, many=True)
        upcoming_serializer = BirthdayEmployeeSerializer([item['employee'] for item in upcoming_birthdays], many=True)
        
        # Формируем результат
        result = {
            'has_today_birthdays': today_birthdays.exists(),
            'today_birthdays': today_serializer.data,
            'upcoming_birthdays': [],
            'today': today
        }
        
        # Добавляем информацию о ближайших днях рождения
        for i, item in enumerate(upcoming_birthdays):
            data = upcoming_serializer.data[i]
            data['days_until_birthday'] = item['days_until']
            data['birthday_date'] = item['birthday_date']
            result['upcoming_birthdays'].append(data)
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def analytics_summary(self, request):
        """Получить краткую сводку аналитики сотрудников"""
        from django.db.models import Count
        from collections import defaultdict
        
        today = timezone.now().date()
        
        # Основные метрики
        total_employees = Employee.objects.filter(is_active=True).count()
        
        # Половой состав
        gender_stats = Employee.objects.filter(is_active=True).values('gender').annotate(count=Count('id'))
        gender_data = {
            'male': next((item['count'] for item in gender_stats if item['gender'] == 'M'), 0),
            'female': next((item['count'] for item in gender_stats if item['gender'] == 'F'), 0)
        }
        
        # Возрастная структура
        employees = Employee.objects.filter(is_active=True)
        ages = [emp.age for emp in employees]
        avg_age = sum(ages) / len(ages) if ages else 0
        
        # Именинники сегодня
        today_birthdays = Employee.objects.filter(
            is_active=True,
            birth_date__month=today.month,
            birth_date__day=today.day
        ).select_related('department', 'division')
        
        # Ближайшие дни рождения
        upcoming_birthdays = []
        for emp in Employee.objects.filter(is_active=True).select_related('department', 'division'):
            this_year_birthday = emp.birth_date.replace(year=today.year)
            if this_year_birthday < today:
                next_year_birthday = emp.birth_date.replace(year=today.year + 1)
                days_until = (next_year_birthday - today).days
            else:
                days_until = (this_year_birthday - today).days
            
            if 0 < days_until <= 7:
                upcoming_birthdays.append({
                    'employee': emp,
                    'days_until': days_until
                })
        
        upcoming_birthdays.sort(key=lambda x: x['days_until'])
        upcoming_birthdays = upcoming_birthdays[:3]  # Топ 3 ближайших
        
        # Текучесть за последние 6 месяцев
        six_months_ago = today - timedelta(days=180)
        terminated_employees = Employee.objects.filter(
            is_active=False,
            termination_date__gte=six_months_ago
        ).count()
        
        turnover_rate = (terminated_employees / total_employees * 100) if total_employees > 0 else 0
        
        # Новые сотрудники за последние 6 месяцев
        new_employees = Employee.objects.filter(
            is_active=True,
            hire_date__gte=six_months_ago
        ).count()
        
        result = {
            'total_employees': total_employees,
            'gender_data': gender_data,
            'avg_age': round(avg_age, 1),
            'today_birthdays': BirthdayEmployeeSerializer(today_birthdays, many=True).data,
            'upcoming_birthdays': [
                {
                    'employee': BirthdayEmployeeSerializer(item['employee']).data,
                    'days_until': item['days_until']
                } for item in upcoming_birthdays
            ],
            'turnover_rate': round(turnover_rate, 1),
            'new_employees': new_employees,
            'today': today
        }
        
        return Response(result)


class PINFLSyncViewSet(viewsets.ViewSet):
    """ViewSet для синхронизации PINFL с SKUD API"""
    
    permission_classes = [permissions.IsAdminUser]
    
    @action(detail=False, methods=['post'])
    def sync_employee(self, request):
        """Синхронизация PINFL конкретного сотрудника"""
        serializer = PINFLSyncSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            employee = Employee.objects.get(id=data['employee_id'])
        except Employee.DoesNotExist:
            return Response(
                {'error': 'Сотрудник не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Валидация PINFL
        is_valid, error_message = pinfl_client.validate_pinfl_format(data['pinfl'])
        if not is_valid:
            return Response(
                {'error': error_message}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем уникальность PINFL
        existing_employee = Employee.objects.filter(pinfl=data['pinfl']).exclude(id=employee.id).first()
        if existing_employee:
            return Response(
                {'error': f'PINFL {data["pinfl"]} уже используется сотрудником {existing_employee.full_name}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Выполняем синхронизацию
        result = pinfl_client.sync_employee_pinfl(
            employee=employee,
            pinfl=data['pinfl'],
            date=data['date']
        )
        
        response_serializer = PINFLSyncResponseSerializer(result)
        
        if result['success']:
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(response_serializer.data, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_sync(self, request):
        """Массовая синхронизация PINFL для нескольких сотрудников"""
        employees_data = request.data.get('employees', [])
        
        if not employees_data:
            return Response(
                {'error': 'Список сотрудников не может быть пустым'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        success_count = 0
        error_count = 0
        
        for emp_data in employees_data:
            serializer = PINFLSyncSerializer(data=emp_data)
            if not serializer.is_valid():
                results.append({
                    'employee_id': emp_data.get('employee_id'),
                    'success': False,
                    'error': 'Неверные данные: ' + str(serializer.errors)
                })
                error_count += 1
                continue
            
            data = serializer.validated_data
            
            try:
                employee = Employee.objects.get(id=data['employee_id'])
            except Employee.DoesNotExist:
                results.append({
                    'employee_id': str(data['employee_id']),
                    'success': False,
                    'error': 'Сотрудник не найден'
                })
                error_count += 1
                continue
            
            # Валидация PINFL
            is_valid, error_message = pinfl_client.validate_pinfl_format(data['pinfl'])
            if not is_valid:
                results.append({
                    'employee_id': str(data['employee_id']),
                    'success': False,
                    'error': error_message
                })
                error_count += 1
                continue
            
            # Проверяем уникальность PINFL
            existing_employee = Employee.objects.filter(pinfl=data['pinfl']).exclude(id=employee.id).first()
            if existing_employee:
                results.append({
                    'employee_id': str(data['employee_id']),
                    'success': False,
                    'error': f'PINFL {data["pinfl"]} уже используется'
                })
                error_count += 1
                continue
            
            # Выполняем синхронизацию
            result = pinfl_client.sync_employee_pinfl(
                employee=employee,
                pinfl=data['pinfl'],
                date=data['date']
            )
            
            results.append(result)
            if result['success']:
                success_count += 1
            else:
                error_count += 1
        
        return Response({
            'message': f'Обработано: {len(employees_data)}, Успешно: {success_count}, Ошибок: {error_count}',
            'total_processed': len(employees_data),
            'success_count': success_count,
            'error_count': error_count,
            'results': results
        })
    
    @action(detail=False, methods=['get'])
    def test_connection(self, request):
        """Тестирование подключения к SKUD API"""
        result = pinfl_client.test_connection()
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    @action(detail=False, methods=['get'])
    def employees_without_pinfl(self, request):
        """Получение списка сотрудников без PINFL"""
        employees = Employee.objects.filter(
            is_active=True,
            pinfl__isnull=True
        ).select_related('department', 'division')
        
        serializer = EmployeeSerializer(employees, many=True)
        
        return Response({
            'employees': serializer.data,
            'count': employees.count()
        })
    
    @action(detail=False, methods=['get'])
    def employees_with_pinfl(self, request):
        """Получение списка сотрудников с PINFL"""
        employees = Employee.objects.filter(
            is_active=True,
            pinfl__isnull=False
        ).select_related('department', 'division')
        
        serializer = EmployeeSerializer(employees, many=True)
        
        return Response({
            'employees': serializer.data,
            'count': employees.count()
        })
