"""
Простые views для веб-интерфейса тестирования СКУД интеграции
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta, date
from django.db.models import Q
import json

from .models import SKUDDevice, SKUDEvent, Employee, WorkDaySummary, WorkSession
from .skud_device_communication import SKUDDeviceCommunicator, SKUDEventProcessor
from .reports import WorkTimeReportGenerator


def dashboard(request):
    """Главная страница с обзором системы"""
    # Получаем кэшированные данные
    from .cache_utils import get_cached_dashboard_data
    
    cached_data = get_cached_dashboard_data()
    
    # Список устройств для отображения (без проверки соединения)
    devices = SKUDDevice.objects.filter(is_active=True).order_by('name')
    
    context = {
        'device_stats': cached_data['device_stats'],
        'event_stats': cached_data['event_stats'],
        'recent_events': cached_data['recent_events'],
        'devices': devices,
        'today': timezone.now().date(),
    }
    
    return render(request, 'employees/dashboard.html', context)


def devices_list(request):
    """Список СКУД устройств"""
    # Фильтр по статусу активности
    show_inactive = request.GET.get('show_inactive', 'false').lower() == 'true'
    
    # Оптимизированный запрос с select_related для будущих расширений
    if show_inactive:
        devices = SKUDDevice.objects.all().order_by('-is_active', 'name')
    else:
        devices = SKUDDevice.objects.filter(is_active=True).order_by('name')
    
    # Пагинация
    paginator = Paginator(devices, 12)  # Увеличили до 12 для лучшего отображения
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'devices': page_obj,
        'show_inactive': show_inactive,
    }
    
    return render(request, 'employees/devices_list.html', context)


def device_detail(request, device_id):
    """Детальная информация об устройстве"""
    try:
        device = SKUDDevice.objects.get(id=device_id)
        
        # Последние события устройства
        events = SKUDEvent.objects.filter(device=device).order_by('-event_time')[:20]
        
        # Статистика за последние 7 дней
        week_ago = timezone.now() - timedelta(days=7)
        week_events = SKUDEvent.objects.filter(
            device=device,
            event_time__gte=week_ago
        )
        
        context = {
            'device': device,
            'events': events,
            'week_events_count': week_events.count(),
            'entry_count': week_events.filter(event_type='entry').count(),
            'exit_count': week_events.filter(event_type='exit').count(),
        }
        
        return render(request, 'employees/device_detail.html', context)
        
    except SKUDDevice.DoesNotExist:
        messages.error(request, 'Устройство не найдено')
        return redirect('devices_list')


def events_list(request):
    """Список событий СКУД"""
    # Оптимизированный запрос с select_related
    events = SKUDEvent.objects.select_related('device', 'employee').order_by('-event_time')
    
    # Фильтры
    device_id = request.GET.get('device')
    event_type = request.GET.get('type')
    hours = int(request.GET.get('hours', 24))
    
    if device_id:
        events = events.filter(device_id=device_id)
    if event_type:
        events = events.filter(event_type=event_type)
    
    # Фильтр по времени
    since_time = timezone.now() - timedelta(hours=hours)
    events = events.filter(event_time__gte=since_time)
    
    # Пагинация
    paginator = Paginator(events, 25)  # Увеличили для лучшей производительности
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Оптимизированные данные для фильтров - только активные устройства
    devices = SKUDDevice.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'events': page_obj,
        'devices': devices,
        'current_device': device_id,
        'current_type': event_type,
        'current_hours': hours,
    }
    
    return render(request, 'employees/events_list.html', context)


def test_device(request, device_id):
    """Тестирование устройства"""
    try:
        device = SKUDDevice.objects.get(id=device_id)
        communicator = SKUDDeviceCommunicator()
        
        is_online, message = communicator.test_device_connection(device)
        
        return JsonResponse({
            'success': is_online,
            'message': message,
            'device_name': device.name
        })
        
    except SKUDDevice.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Устройство не найдено'
        })


def add_device(request):
    """Добавление нового устройства"""
    if request.method == 'POST':
        name = request.POST.get('name')
        ip_address = request.POST.get('ip_address')
        port = int(request.POST.get('port', 80))
        serial_number = request.POST.get('serial_number')
        device_type = request.POST.get('device_type')
        location = request.POST.get('location', '')
        description = request.POST.get('description', '')
        
        try:
            device = SKUDDevice.objects.create(
                name=name,
                ip_address=ip_address,
                port=port,
                serial_number=serial_number,
                device_type=device_type,
                location=location,
                description=description
            )
            
            messages.success(request, f'Устройство "{device.name}" успешно добавлено')
            return redirect('device_detail', device_id=device.id)
            
        except Exception as e:
            messages.error(request, f'Ошибка при добавлении устройства: {str(e)}')
    
    return render(request, 'employees/add_device.html')


def send_test_event(request):
    """Отправка тестового события"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Получаем IP адрес клиента
            client_ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
            
            # Обрабатываем событие
            communicator = SKUDDeviceCommunicator()
            skud_event = communicator.process_device_event(client_ip, data)
            
            return JsonResponse({
                'success': True,
                'message': 'Событие успешно обработано',
                'event_id': str(skud_event.id),
                'employee_found': skud_event.employee is not None
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Ошибка: {str(e)}'
            })
    
    return render(request, 'employees/send_test_event.html')


def api_status(request):
    """API статус системы"""
    from .cache_utils import SKUDCache
    
    try:
        # Проверяем кэш
        cached_status = SKUDCache.get_api_status()
        
        if cached_status:
            return JsonResponse(cached_status)
        
        # Если кэш пустой, генерируем данные (БЕЗ проверки устройств!)
        from django.db.models import Count, Q
        
        device_stats = SKUDDevice.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True))
        )
        
        event_stats = SKUDEvent.objects.aggregate(
            total=Count('id'),
            today=Count('id', filter=Q(event_time__date=timezone.now().date()))
        )
        
        status_data = {
            'status': 'success',
            'total_devices': device_stats['total'],
            'active_devices': device_stats['active'],
            'total_events': event_stats['total'],
            'today_events': event_stats['today'],
            'server_time': timezone.now().isoformat(),
            'devices': {}  # Пустой объект устройств - проверка по запросу
        }
        
        # Кэшируем результат
        SKUDCache.set_api_status(status_data)
        
        return JsonResponse(status_data)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'server_time': timezone.now().isoformat()
        }, status=500)


def check_devices_health(request):
    """AJAX endpoint для проверки статуса устройств"""
    if request.method == 'POST':
        communicator = SKUDDeviceCommunicator()
        results = communicator.check_all_devices_health()
        
        return JsonResponse({
            'status': 'success',
            'devices': results,
            'timestamp': timezone.now().isoformat()
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Only POST requests allowed'
    }, status=405)


def quick_test(request):
    """Быстрый тест системы"""
    if request.method == 'POST':
        # Тестируем все устройства
        communicator = SKUDDeviceCommunicator()
        results = communicator.check_all_devices_health()
        
        return JsonResponse({
            'success': True,
            'results': results
        })
    
    return render(request, 'employees/quick_test.html')


def employees_list(request):
    """Список сотрудников"""
    employees = Employee.objects.filter(is_active=True).order_by('last_name', 'first_name')
    
    # Пагинация
    paginator = Paginator(employees, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'employees': page_obj,
    }
    
    return render(request, 'employees/employees_list.html', context)


def employee_events(request, employee_id):
    """События конкретного сотрудника"""
    try:
        employee = Employee.objects.get(id=employee_id)
        
        # События за последние 30 дней
        month_ago = timezone.now() - timedelta(days=30)
        events = SKUDEvent.objects.filter(
            employee=employee,
            event_time__gte=month_ago
        ).order_by('-event_time')
        
        context = {
            'employee': employee,
            'events': events,
        }
        
        return render(request, 'employees/employee_events.html', context)
        
    except Employee.DoesNotExist:
        messages.error(request, 'Сотрудник не найден')
        return redirect('employees_list')


def delete_device(request, device_id):
    """Удаление СКУД устройства"""
    try:
        device = SKUDDevice.objects.get(id=device_id)
        
        if request.method == 'POST':
            # Проверяем, есть ли связанные события
            events_count = SKUDEvent.objects.filter(device=device).count()
            
            if events_count > 0:
                messages.warning(
                    request, 
                    f'Нельзя удалить устройство "{device.name}" - у него есть {events_count} связанных событий. '
                    'Сначала удалите все события или деактивируйте устройство.'
                )
                return redirect('device_detail', device_id=device.id)
            
            # Удаляем устройство
            device_name = device.name
            device.delete()
            
            messages.success(request, f'Устройство "{device_name}" успешно удалено')
            return redirect('devices_list')
        
        # GET запрос - показываем страницу подтверждения
        context = {
            'device': device,
        }
        return render(request, 'employees/delete_device.html', context)
        
    except SKUDDevice.DoesNotExist:
        messages.error(request, 'Устройство не найдено')
        return redirect('devices_list')


def deactivate_device(request, device_id):
    """Деактивация СКУД устройства (мягкое удаление)"""
    try:
        device = SKUDDevice.objects.get(id=device_id)
        
        if request.method == 'POST':
            # Деактивируем устройство вместо удаления
            device.is_active = False
            device.status = 'inactive'
            device.save()
            
            messages.success(request, f'Устройство "{device.name}" деактивировано')
            return redirect('device_detail', device_id=device.id)
        
        # GET запрос - показываем страницу подтверждения
        context = {
            'device': device,
        }
        return render(request, 'employees/deactivate_device.html', context)
        
    except SKUDDevice.DoesNotExist:
        messages.error(request, 'Устройство не найдено')
        return redirect('devices_list')


def activate_device(request, device_id):
    """Активация СКУД устройства"""
    try:
        device = SKUDDevice.objects.get(id=device_id)
        
        if request.method == 'POST':
            # Активируем устройство
            device.is_active = True
            device.status = 'active'
            device.save()
            
            messages.success(request, f'Устройство "{device.name}" активировано')
            return redirect('device_detail', device_id=device.id)
        
        # GET запрос - показываем страницу подтверждения
        context = {
            'device': device,
        }
        return render(request, 'employees/activate_device.html', context)
        
    except SKUDDevice.DoesNotExist:
        messages.error(request, 'Устройство не найдено')
        return redirect('devices_list')


# =============================================================================
# Views для системы отчётов
# =============================================================================

def reports_dashboard(request):
    """Главная страница системы отчётов"""
    from django.db.models import Count, Sum
    from datetime import date
    
    # Статистика за текущий месяц
    today = date.today()
    month_start = today.replace(day=1)
    
    # Общая статистика
    total_employees = Employee.objects.filter(is_active=True).count()
    total_summaries = WorkDaySummary.objects.filter(date__gte=month_start).count()
    total_sessions = WorkSession.objects.filter(date__gte=month_start).count()
    
    # Статистика по статусам
    status_stats = WorkDaySummary.objects.filter(
        date__gte=month_start
    ).values('status').annotate(count=Count('id'))
    
    # Статистика по отделам
    department_stats = WorkDaySummary.objects.filter(
        date__gte=month_start,
        employee__department__isnull=False
    ).values(
        'employee__department__name'
    ).annotate(
        employees=Count('employee', distinct=True),
        days=Count('id'),
        total_hours=Sum('total_seconds_in_office')
    ).order_by('-total_hours')
    
    # Русские названия месяцев
    months_ru = {
        1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
        5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
        9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
    }
    
    context = {
        'total_employees': total_employees,
        'total_summaries': total_summaries,
        'total_sessions': total_sessions,
        'status_stats': status_stats,
        'department_stats': department_stats,
        'current_month': f"{months_ru[today.month]} {today.year}"
    }
    
    return render(request, 'employees/reports_dashboard.html', context)


def monthly_report(request):
    """Страница месячного отчёта"""
    from django.db.models import Q
    
    if request.method == 'POST':
        year = int(request.POST.get('year'))
        month = int(request.POST.get('month'))
        department_id = request.POST.get('department_id') or None
        employee_id = request.POST.get('employee_id') or None
        format_type = request.POST.get('format', 'xlsx')
        
        generator = WorkTimeReportGenerator()
        
        if format_type == 'csv':
            return generator.generate_monthly_report_csv(year, month, department_id, employee_id)
        else:
            return generator.generate_monthly_report_xlsx(year, month, department_id, employee_id)
    
    # GET запрос - показываем форму
    from datetime import date
    
    # Получаем доступные годы и месяцы
    years = range(date.today().year - 2, date.today().year + 1)
    months = [(i, f'{i:02d}') for i in range(1, 13)]
    
    # Получаем отделы для фильтрации
    departments = Employee.objects.filter(
        is_active=True,
        department__isnull=False
    ).values_list('department__id', 'department__name').distinct().order_by('department__name')
    
    # Получаем сотрудников для фильтрации
    employees = Employee.objects.filter(is_active=True).order_by('last_name', 'first_name')
    
    context = {
        'years': years,
        'months': months,
        'departments': departments,
        'employees': employees,
        'current_year': date.today().year,
        'current_month': date.today().month
    }
    
    return render(request, 'employees/monthly_report.html', context)


def employee_report(request):
    """Страница отчёта по сотруднику"""
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            generator = WorkTimeReportGenerator()
            return generator.generate_employee_detailed_report(employee_id, start_date, end_date)
            
        except ValueError:
            messages.error(request, 'Неверный формат даты')
        except Exception as e:
            messages.error(request, f'Ошибка при генерации отчёта: {str(e)}')
    
    # GET запрос - показываем форму
    employees = Employee.objects.filter(is_active=True).order_by('last_name', 'first_name')
    
    context = {
        'employees': employees
    }
    
    return render(request, 'employees/employee_report.html', context)


def department_report(request):
    """Страница отчёта по отделу"""
    if request.method == 'POST':
        department_id = request.POST.get('department_id')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            generator = WorkTimeReportGenerator()
            return generator.generate_department_statistics_report(department_id, start_date, end_date)
            
        except ValueError:
            messages.error(request, 'Неверный формат даты')
        except Exception as e:
            messages.error(request, f'Ошибка при генерации отчёта: {str(e)}')
    
    # GET запрос - показываем форму
    departments = Employee.objects.filter(
        is_active=True,
        department__isnull=False
    ).values_list('department__id', 'department__name').distinct().order_by('department__name')
    
    context = {
        'departments': departments
    }
    
    return render(request, 'employees/department_report.html', context)


def work_time_summaries(request):
    """Страница просмотра сводок рабочего времени"""
    from django.db.models import Q
    
    # Параметры фильтрации
    employee_id = request.GET.get('employee_id')
    department_id = request.GET.get('department_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    
    # Базовый queryset
    queryset = WorkDaySummary.objects.select_related(
        'employee', 'employee__department', 'employee__division'
    ).order_by('-date', 'employee__last_name')
    
    # Применяем фильтры
    if employee_id:
        queryset = queryset.filter(employee_id=employee_id)
    
    if department_id:
        queryset = queryset.filter(employee__department_id=department_id)
    
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
    
    if status:
        queryset = queryset.filter(status=status)
    
    # Пагинация
    paginator = Paginator(queryset, 50)
    page_number = request.GET.get('page')
    summaries = paginator.get_page(page_number)
    
    # Данные для фильтров
    employees = Employee.objects.filter(is_active=True).order_by('last_name', 'first_name')
    departments = Employee.objects.filter(
        is_active=True,
        department__isnull=False
    ).values_list('department__id', 'department__name').distinct().order_by('department__name')
    
    status_choices = WorkDaySummary.SUMMARY_STATUS_CHOICES
    
    context = {
        'summaries': summaries,
        'employees': employees,
        'departments': departments,
        'status_choices': status_choices,
        'current_filters': {
            'employee_id': employee_id,
            'department_id': department_id,
            'start_date': start_date,
            'end_date': end_date,
            'status': status
        }
    }
    
    return render(request, 'employees/work_time_summaries.html', context)


def work_sessions(request):
    """Страница просмотра рабочих сессий"""
    from django.db.models import Q
    
    # Параметры фильтрации
    employee_id = request.GET.get('employee_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    is_open = request.GET.get('is_open')
    
    # Базовый queryset
    queryset = WorkSession.objects.select_related(
        'employee', 'corrected_by'
    ).order_by('-date', '-start_time')
    
    # Применяем фильтры
    if employee_id:
        queryset = queryset.filter(employee_id=employee_id)
    
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
    
    if status:
        queryset = queryset.filter(status=status)
    
    if is_open == 'true':
        queryset = queryset.filter(status='open')
    elif is_open == 'false':
        queryset = queryset.exclude(status='open')
    
    # Пагинация
    paginator = Paginator(queryset, 50)
    page_number = request.GET.get('page')
    sessions = paginator.get_page(page_number)
    
    # Данные для фильтров
    employees = Employee.objects.filter(is_active=True).order_by('last_name', 'first_name')
    status_choices = WorkSession.SESSION_STATUS_CHOICES
    
    context = {
        'sessions': sessions,
        'employees': employees,
        'status_choices': status_choices,
        'current_filters': {
            'employee_id': employee_id,
            'start_date': start_date,
            'end_date': end_date,
            'status': status,
            'is_open': is_open
        }
    }
    
    return render(request, 'employees/work_sessions.html', context)


# =============================================================================
# Views для аутентификации (временная система логина)
# =============================================================================

def login_view(request):
    """Страница входа в систему"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.first_name or user.username}!')
            
            # Перенаправляем на страницу, с которой пришли, или на главную
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            messages.error(request, 'Неверный логин или пароль')
    
    context = {
        'next': request.GET.get('next', '/')
    }
    return render(request, 'employees/login.html', context)


def logout_view(request):
    """Выход из системы"""
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы')
    return redirect('login_view')


@login_required
def profile_view(request):
    """Профиль пользователя"""
    user = request.user
    
    # Получаем связанного сотрудника, если есть
    try:
        employee = Employee.objects.get(user=user)
        employee_data = {
            'full_name': employee.full_name,
            'employee_id': employee.employee_id,
            'department': employee.department.name if employee.department else 'Не указан',
            'position': employee.get_position_display(),
            'work_fraction': f"{employee.work_fraction * 100:.0f}%",
            'daily_hours': employee.daily_hours
        }
    except Employee.DoesNotExist:
        employee_data = None
    
    # Статистика за текущий месяц
    today = date.today()
    month_start = today.replace(day=1)
    
    if employee_data:
        summaries = WorkDaySummary.objects.filter(
            employee__user=user,
            date__gte=month_start
        )
        
        total_hours = sum(s.total_hours for s in summaries)
        expected_hours = sum(s.expected_hours for s in summaries)
        overtime_hours = sum(s.overtime_hours for s in summaries)
        
        work_stats = {
            'total_days': summaries.count(),
            'present_days': summaries.filter(status='present').count(),
            'absent_days': summaries.filter(status='absent').count(),
            'excused_days': summaries.filter(status='excused').count(),
            'total_hours': total_hours,
            'expected_hours': expected_hours,
            'overtime_hours': overtime_hours,
            'underwork_hours': max(0, expected_hours - total_hours) if expected_hours > total_hours else 0,
            'problem_days': summaries.filter(
                Q(has_missing_exit=True) | Q(has_manual_corrections=True)
            ).count()
        }
    else:
        work_stats = None
    
    context = {
        'user': user,
        'employee_data': employee_data,
        'work_stats': work_stats
    }
    
    return render(request, 'employees/profile.html', context)