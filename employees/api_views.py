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
    DepartmentWorkTimeStatsSerializer, ReprocessWorkTimeSerializer
)
from .work_time_processor import WorkTimeProcessor


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
