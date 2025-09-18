"""
Простые views для веб-интерфейса тестирования СКУД интеграции
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json

from .models import SKUDDevice, SKUDEvent, Employee
from .skud_device_communication import SKUDDeviceCommunicator, SKUDEventProcessor


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
    # Оптимизированный запрос с select_related для будущих расширений
    devices = SKUDDevice.objects.all().order_by('name')
    
    # Пагинация
    paginator = Paginator(devices, 12)  # Увеличили до 12 для лучшего отображения
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'devices': page_obj,
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
