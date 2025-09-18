"""
API endpoints для приема данных от СКУД устройств
"""

import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import SKUDDevice, SKUDEvent, Employee
from .skud_device_communication import SKUDDeviceCommunicator, SKUDEventProcessor

logger = logging.getLogger(__name__)


class SKUDAPIView(View):
    """Базовый класс для API СКУД"""
    
    def dispatch(self, request, *args, **kwargs):
        # Логирование всех запросов
        client_ip = self.get_client_ip(request)
        logger.info(f"СКУД API запрос от {client_ip}: {request.method} {request.path}")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_client_ip(self, request):
        """Получение IP адреса клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@method_decorator(csrf_exempt, name='dispatch')
class SKUDEventEndpoint(SKUDAPIView):
    """
    Endpoint для приема событий от СКУД устройств
    POST /api/skud/event/
    """
    
    def get(self, request):
        """Информация о том, как использовать API"""
        return JsonResponse({
            'status': 'info',
            'message': 'СКУД Event API',
            'usage': 'Отправляйте POST запросы с данными события',
            'format': {
                'card_number': 'string',
                'event_type': 'entry|exit|denied|alarm',
                'timestamp': 'ISO datetime'
            },
            'example': {
                'card_number': '12345',
                'event_type': 'entry',
                'timestamp': '2025-09-18T10:00:00'
            }
        })
    
    def post(self, request):
        try:
            # Получаем IP адрес отправителя
            client_ip = self.get_client_ip(request)
            
            # Парсим данные
            try:
                if request.content_type == 'application/json':
                    data = json.loads(request.body)
                else:
                    # Пробуем парсить как обычный текст
                    data = json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"Ошибка парсинга JSON от {client_ip}: {e}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Неверный формат JSON'
                }, status=400)
            
            # Проверяем наличие обязательных полей
            required_fields = ['card_number', 'event_type']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Отсутствует обязательное поле: {field}'
                    }, status=400)
            
            # Добавляем IP адрес отправителя в данные
            data['device_ip'] = client_ip
            
            # Обрабатываем событие
            communicator = SKUDDeviceCommunicator()
            skud_event = communicator.process_device_event(client_ip, data)
            
            logger.info(f"Обработано событие СКУД: {skud_event}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Событие успешно обработано',
                'event_id': str(skud_event.id),
                'employee_found': skud_event.employee is not None
            })
            
        except SKUDDevice.DoesNotExist:
            logger.error(f"Устройство с IP {client_ip} не найдено в системе")
            return JsonResponse({
                'status': 'error',
                'message': 'Устройство не зарегистрировано в системе'
            }, status=404)
            
        except Exception as e:
            logger.error(f"Ошибка обработки события от {client_ip}: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Внутренняя ошибка сервера'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SKUDStatusEndpoint(SKUDAPIView):
    """
    Endpoint для получения статуса системы СКУД
    GET /api/skud/status/
    """
    
    def get(self, request):
        try:
            communicator = SKUDDeviceCommunicator()
            health_status = communicator.check_all_devices_health()
            
            # Общая статистика
            total_devices = SKUDDevice.objects.filter(is_active=True).count()
            online_devices = sum(1 for status in health_status.values() if status['is_online'])
            
            return JsonResponse({
                'status': 'success',
                'server_time': timezone.now().isoformat(),
                'total_devices': total_devices,
                'online_devices': online_devices,
                'devices': health_status
            })
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса СКУД: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Ошибка получения статуса'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SKUDDeviceInfoEndpoint(SKUDAPIView):
    """
    Endpoint для получения информации о конкретном устройстве
    GET /api/skud/device/{device_id}/
    """
    
    @require_http_methods(["GET"])
    def get(self, request, device_id):
        try:
            device = SKUDDevice.objects.get(id=device_id)
            
            # Получаем последние события
            recent_events = SKUDEvent.objects.filter(
                device=device
            ).order_by('-event_time')[:10]
            
            events_data = []
            for event in recent_events:
                events_data.append({
                    'id': str(event.id),
                    'employee_name': event.employee.full_name if event.employee else 'Неизвестный',
                    'event_type': event.event_type,
                    'event_time': event.event_time.isoformat(),
                    'card_number': event.card_number
                })
            
            return JsonResponse({
                'status': 'success',
                'device': {
                    'id': str(device.id),
                    'name': device.name,
                    'device_type': device.device_type,
                    'serial_number': device.serial_number,
                    'ip_address': device.ip_address,
                    'port': device.port,
                    'location': device.location,
                    'status': device.status,
                    'is_active': device.is_active,
                    'last_communication': device.last_communication.isoformat() if device.last_communication else None
                },
                'recent_events': events_data
            })
            
        except SKUDDevice.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Устройство не найдено'
            }, status=404)
            
        except Exception as e:
            logger.error(f"Ошибка получения информации об устройстве {device_id}: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Ошибка получения информации об устройстве'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SKUDEventsEndpoint(SKUDAPIView):
    """
    Endpoint для получения событий СКУД
    GET /api/skud/events/
    """
    
    @require_http_methods(["GET"])
    def get(self, request):
        try:
            # Параметры фильтрации
            device_id = request.GET.get('device_id')
            employee_id = request.GET.get('employee_id')
            event_type = request.GET.get('event_type')
            hours = int(request.GET.get('hours', 24))
            
            # Базовый запрос
            events = SKUDEvent.objects.select_related('device', 'employee')
            
            # Фильтры
            if device_id:
                events = events.filter(device_id=device_id)
            
            if employee_id:
                events = events.filter(employee__employee_id=employee_id)
            
            if event_type:
                events = events.filter(event_type=event_type)
            
            # Фильтр по времени
            since_time = timezone.now() - timezone.timedelta(hours=hours)
            events = events.filter(event_time__gte=since_time)
            
            # Ограничиваем количество результатов
            limit = int(request.GET.get('limit', 100))
            events = events[:limit]
            
            # Формируем ответ
            events_data = []
            for event in events:
                events_data.append({
                    'id': str(event.id),
                    'device_name': event.device.name,
                    'device_ip': event.device.ip_address,
                    'employee_name': event.employee.full_name if event.employee else None,
                    'employee_id': event.employee.employee_id if event.employee else None,
                    'card_number': event.card_number,
                    'event_type': event.event_type,
                    'event_time': event.event_time.isoformat(),
                    'is_processed': event.is_processed
                })
            
            return JsonResponse({
                'status': 'success',
                'events': events_data,
                'total_count': len(events_data)
            })
            
        except Exception as e:
            logger.error(f"Ошибка получения событий СКУД: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Ошибка получения событий'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SKUDHealthCheckEndpoint(SKUDAPIView):
    """
    Endpoint для проверки здоровья системы
    GET /api/skud/health/
    """
    
    def get(self, request):
        try:
            processor = SKUDEventProcessor()
            
            # Проверяем необработанные события
            unprocessed_count = SKUDEvent.objects.filter(is_processed=False).count()
            
            # Проверяем устройства
            communicator = SKUDDeviceCommunicator()
            device_health = communicator.check_all_devices_health()
            
            # Общий статус
            total_devices = len(device_health)
            online_devices = sum(1 for status in device_health.values() if status['is_online'])
            
            health_status = 'healthy'
            if unprocessed_count > 100:  # Много необработанных событий
                health_status = 'warning'
            if online_devices == 0 and total_devices > 0:  # Нет онлайн устройств
                health_status = 'critical'
            
            return JsonResponse({
                'status': 'success',
                'health': {
                    'overall_status': health_status,
                    'server_time': timezone.now().isoformat(),
                    'unprocessed_events': unprocessed_count,
                    'total_devices': total_devices,
                    'online_devices': online_devices,
                    'device_health': device_health
                }
            })
            
        except Exception as e:
            logger.error(f"Ошибка проверки здоровья системы: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Ошибка проверки здоровья системы'
            }, status=500)


@csrf_exempt
def skud_test_endpoint(request):
    """
    Простой тестовый endpoint для проверки связи
    GET/POST /api/skud/test/
    """
    if request.method == 'GET':
        return JsonResponse({
            'status': 'success',
            'message': 'СКУД API работает',
            'server_time': timezone.now().isoformat(),
            'client_ip': request.META.get('REMOTE_ADDR')
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            return JsonResponse({
                'status': 'success',
                'message': 'Тестовые данные получены',
                'received_data': data,
                'server_time': timezone.now().isoformat(),
                'client_ip': request.META.get('REMOTE_ADDR')
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Неверный формат JSON'
            }, status=400)
    
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Метод не поддерживается'
        }, status=405)
