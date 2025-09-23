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
    from django.db.models import Count, Q, Sum
    from datetime import datetime, timedelta
    
    today = timezone.now().date()
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Основные метрики
    total_employees = Employee.objects.filter(is_active=True).count()
    active_employees = Employee.objects.filter(is_active=True).count()  # Все активные сотрудники
    
    # Сотрудники в отпуске сегодня
    on_vacation = Employee.objects.filter(
        is_active=True,
        vacations__start_date__lte=today,
        vacations__end_date__gte=today,
        vacations__status__in=['approved', 'taken']
    ).distinct().count()
    
    # Общая сумма зарплат (пока заглушка, так как нет поля salary)
    total_salaries = 0  # TODO: добавить поле salary в модель Employee
    
    # Сотрудники по полу
    gender_stats = Employee.objects.filter(is_active=True).values('gender').annotate(count=Count('id'))
    male_count = next((item['count'] for item in gender_stats if item['gender'] == 'M'), 0)
    female_count = next((item['count'] for item in gender_stats if item['gender'] == 'F'), 0)
    
    # Получаем параметры фильтрации
    sort_by = request.GET.get('sort', 'time')  # time, name, status
    sort_order = request.GET.get('order', 'asc')  # asc, desc
    
    # Список сотрудников с временем прихода за сегодня
    today_attendance = []
    work_sessions_today = WorkSession.objects.filter(
        date=today,
        employee__is_active=True
    ).select_related('employee').order_by('start_time')
    
    for session in work_sessions_today:
        arrival_time = session.start_time.time()
        is_late = arrival_time > datetime.strptime('09:00', '%H:%M').time()
        
        status = 'on_time' if not is_late else 'late'
        if arrival_time.hour >= 12:  # Если пришел после 12, считаем не пришел
            status = 'absent'
        
        today_attendance.append({
            'employee': session.employee,
            'arrival_time': arrival_time,
            'status': status,
            'is_present': True
        })
    
    # Сотрудники, которые не пришли сегодня
    present_employee_ids = [att['employee'].id for att in today_attendance]
    absent_employees = Employee.objects.filter(
        is_active=True
    ).exclude(id__in=present_employee_ids)
    
    for emp in absent_employees:
        today_attendance.append({
            'employee': emp,
            'arrival_time': None,
            'status': 'absent',
            'is_present': False
        })
    
    
    # Сортируем по выбранному параметру
    if sort_by == 'name':
        today_attendance.sort(key=lambda x: x['employee'].full_name, reverse=(sort_order == 'desc'))
    elif sort_by == 'status':
        status_order = {'on_time': 0, 'late': 1, 'absent': 2}
        today_attendance.sort(key=lambda x: status_order.get(x['status'], 3), reverse=(sort_order == 'desc'))
    else:  # sort_by == 'time'
        today_attendance.sort(key=lambda x: x['arrival_time'] or datetime.max.time(), reverse=(sort_order == 'desc'))
    
    # Все именинники (сегодня и все остальные)
    all_birthdays = []
    
    # Получаем всех активных сотрудников
    all_employees = Employee.objects.filter(is_active=True).select_related('department', 'division')
    
    for emp in all_employees:
        this_year_birthday = emp.birth_date.replace(year=today.year)
        
        # Если день рождения уже прошел в этом году, берем следующий год
        if this_year_birthday < today:
            next_year_birthday = emp.birth_date.replace(year=today.year + 1)
            days_until = (next_year_birthday - today).days
            birthday_date = next_year_birthday
            is_today = False
        else:
            days_until = (this_year_birthday - today).days
            birthday_date = this_year_birthday
            is_today = (days_until == 0)
        
        all_birthdays.append({
            'employee': emp,
            'days_until': days_until,
            'birthday_date': birthday_date,
            'is_today': is_today
        })
    
    # Сортируем по количеству дней до дня рождения
    all_birthdays.sort(key=lambda x: x['days_until'])
    
    context = {
        'total_employees': total_employees,
        'active_employees': active_employees,
        'on_vacation': on_vacation,
        'total_salaries': total_salaries,
        'male_count': male_count,
        'female_count': female_count,
        'today_attendance': today_attendance,
        'birthdays': all_birthdays,
        'today': today,
        'sort_by': sort_by,
        'sort_order': sort_order,
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
    """Список сотрудников с поиском и фильтрацией"""
    from django.db.models import Q
    
    # Базовый queryset
    employees = Employee.objects.filter(is_active=True).select_related('department', 'division')
    
    # Поиск по ФИО
    search_query = request.GET.get('search', '').strip()
    if search_query:
        employees = employees.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(middle_name__icontains=search_query)
        )
    
    # Фильтр по отделу
    department_id = request.GET.get('department')
    if department_id:
        employees = employees.filter(department_id=department_id)
    
    # Фильтр по должности
    position = request.GET.get('position')
    if position:
        employees = employees.filter(position=position)
    
    # Фильтр по статусу
    status = request.GET.get('status')
    if status == 'active':
        employees = employees.filter(is_active=True)
    elif status == 'inactive':
        employees = employees.filter(is_active=False)
    
    # Сортировка
    sort_by = request.GET.get('sort', 'last_name')
    sort_order = request.GET.get('order', 'asc')
    
    if sort_order == 'desc':
        sort_by = f'-{sort_by}'
    
    employees = employees.order_by(sort_by)
    
    # Количество записей на странице
    per_page = int(request.GET.get('per_page', 20))
    per_page = min(per_page, 100)  # Максимум 100 записей
    
    # Пагинация
    paginator = Paginator(employees, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Данные для фильтров
    departments = Employee.objects.filter(
        is_active=True,
        department__isnull=False
    ).values_list('department__id', 'department__name').distinct().order_by('department__name')
    
    positions = Employee.POSITION_CHOICES
    
    context = {
        'page_obj': page_obj,
        'employees': page_obj,
        'departments': departments,
        'positions': positions,
        'search_query': search_query,
        'current_filters': {
            'department': department_id,
            'position': position,
            'status': status,
        }
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


def login_view(request):
    """Страница входа в систему"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.first_name or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Неверные учетные данные')
    
    return render(request, 'employees/login.html')


def logout_view(request):
    """Выход из системы"""
    logout(request)
    messages.info(request, 'Вы вышли из системы')
    return redirect('login_view')


def profile_view(request):
    """Профиль пользователя"""
    return render(request, 'employees/profile.html')