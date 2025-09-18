"""
Модуль для прямого общения с СКУД устройствами через IP-адреса
"""

import socket
import requests
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.utils import timezone as django_timezone
from .models import SKUDDevice, SKUDEvent, Employee, WorkTimeRecord

logger = logging.getLogger(__name__)


class SKUDDeviceCommunicator:
    """Класс для общения с СКУД устройствами через IP"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.logger = logger
    
    def test_device_connection(self, device: SKUDDevice) -> Tuple[bool, str]:
        """
        Тестирование соединения с СКУД устройством
        
        Args:
            device: Объект СКУД устройства
            
        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        try:
            # Специальная логика для тестовых устройств
            if (device.serial_number.startswith('TEST') or 
                device.serial_number == 'LOCAL001'):
                # Для тестовых устройств имитируем успешное соединение
                import random
                # 90% вероятность успеха для тестовых устройств
                if random.random() < 0.9:
                    device.last_communication = django_timezone.now()
                    device.status = 'active'
                    device.save(update_fields=['last_communication', 'status'])
                    return True, "Тестовое устройство: соединение установлено (имитация)"
                else:
                    device.status = 'error'
                    device.save(update_fields=['status'])
                    return False, "Тестовое устройство: ошибка соединения (имитация)"
            
            # Для локальных IP адресов (127.0.0.1, localhost)
            if device.ip_address in ['127.0.0.1', 'localhost', '::1']:
                device.last_communication = django_timezone.now()
                device.status = 'active'
                device.save(update_fields=['last_communication', 'status'])
                return True, "Локальное устройство: соединение установлено"
            
            # Реальная проверка для внешних устройств
            # Попробуем HTTP соединение
            if self._test_http_connection(device):
                device.last_communication = django_timezone.now()
                device.status = 'active'
                device.save(update_fields=['last_communication', 'status'])
                return True, "HTTP соединение успешно"
            
            # Попробуем TCP соединение
            if self._test_tcp_connection(device):
                device.last_communication = django_timezone.now()
                device.status = 'active'
                device.save(update_fields=['last_communication', 'status'])
                return True, "TCP соединение успешно"
            
            # Если ничего не сработало
            device.status = 'error'
            device.save(update_fields=['status'])
            return False, "Не удалось установить соединение"
            
        except Exception as e:
            self.logger.error(f"Ошибка при тестировании устройства {device.name}: {e}")
            device.status = 'error'
            device.save(update_fields=['status'])
            return False, f"Ошибка: {str(e)}"
    
    def _test_http_connection(self, device: SKUDDevice) -> bool:
        """Тестирование HTTP соединения"""
        try:
            url = f"http://{device.ip_address}:{device.port}"
            response = requests.get(url, timeout=self.timeout)
            return response.status_code < 500
        except:
            return False
    
    def _test_tcp_connection(self, device: SKUDDevice) -> bool:
        """Тестирование TCP соединения"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((device.ip_address, device.port))
            sock.close()
            return result == 0
        except:
            return False
    
    def send_command_to_device(self, device: SKUDDevice, command: Dict) -> Tuple[bool, str]:
        """
        Отправка команды на СКУД устройство
        
        Args:
            device: Объект СКУД устройства
            command: Команда для отправки
            
        Returns:
            Tuple[bool, str]: (успех, ответ)
        """
        try:
            url = f"http://{device.ip_address}:{device.port}/api/command"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'EmployeeManagement/1.0'
            }
            
            response = requests.post(
                url, 
                json=command, 
                headers=headers, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                # Обновляем время последней связи
                device.last_communication = django_timezone.now()
                device.save(update_fields=['last_communication'])
                
                return True, response.text
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            self.logger.error(f"Ошибка отправки команды на {device.name}: {e}")
            return False, str(e)
    
    def get_device_status(self, device: SKUDDevice) -> Dict:
        """
        Получение статуса СКУД устройства
        
        Args:
            device: Объект СКУД устройства
            
        Returns:
            Dict: Статус устройства
        """
        try:
            url = f"http://{device.ip_address}:{device.port}/api/status"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                device.last_communication = django_timezone.now()
                device.save(update_fields=['last_communication'])
                return response.json()
            else:
                return {'error': f"HTTP {response.status_code}"}
                
        except Exception as e:
            self.logger.error(f"Ошибка получения статуса {device.name}: {e}")
            return {'error': str(e)}
    
    def sync_device_time(self, device: SKUDDevice) -> bool:
        """
        Синхронизация времени устройства с сервером
        
        Args:
            device: Объект СКУД устройства
            
        Returns:
            bool: Успех операции
        """
        command = {
            'action': 'sync_time',
            'server_time': django_timezone.now().isoformat()
        }
        
        success, response = self.send_command_to_device(device, command)
        return success
    
    def process_device_event(self, device_ip: str, event_data: Dict) -> SKUDEvent:
        """
        Обработка события от СКУД устройства
        
        Args:
            device_ip: IP адрес устройства
            event_data: Данные события
            
        Returns:
            SKUDEvent: Созданное событие
        """
        try:
            # Находим устройство по IP
            device = SKUDDevice.objects.get(ip_address=device_ip)
            
            # Парсим данные события
            card_number = event_data.get('card_number', '')
            event_type = self._determine_event_type(event_data)
            event_time = self._parse_event_time(event_data.get('timestamp'))
            
            # Ищем сотрудника по номеру карты
            employee = self._find_employee_by_card(card_number)
            
            # Создаем событие
            skud_event = SKUDEvent.objects.create(
                device=device,
                employee=employee,
                card_number=card_number,
                event_type=event_type,
                event_time=event_time,
                raw_data=json.dumps(event_data, ensure_ascii=False)
            )
            
            # Обрабатываем событие для рабочего времени
            self._process_event_for_work_time(skud_event)
            
            self.logger.info(f"Создано событие СКУД: {skud_event}")
            return skud_event
            
        except SKUDDevice.DoesNotExist:
            self.logger.error(f"Устройство с IP {device_ip} не найдено")
            raise ValueError(f"Устройство с IP {device_ip} не найдено")
        except Exception as e:
            self.logger.error(f"Ошибка обработки события: {e}")
            raise
    
    def _determine_event_type(self, event_data: Dict) -> str:
        """Определение типа события"""
        event_type = event_data.get('event_type', '').lower()
        
        if event_type in ['entry', 'in', 'вход']:
            return 'entry'
        elif event_type in ['exit', 'out', 'выход']:
            return 'exit'
        elif event_type in ['denied', 'refused', 'отказ']:
            return 'denied'
        elif event_type in ['alarm', 'alert', 'тревога']:
            return 'alarm'
        else:
            # Попробуем определить по другим полям
            if 'direction' in event_data:
                direction = event_data['direction'].lower()
                if direction in ['in', 'вход']:
                    return 'entry'
                elif direction in ['out', 'выход']:
                    return 'exit'
            
            return 'entry'  # По умолчанию считаем входом
    
    def _parse_event_time(self, timestamp: str) -> datetime:
        """Парсинг времени события"""
        if not timestamp:
            return django_timezone.now()
        
        try:
            # Пробуем разные форматы времени
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S%z'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp, fmt)
                    if dt.tzinfo is None:
                        dt = django_timezone.make_aware(dt)
                    return dt
                except ValueError:
                    continue
            
            # Если не удалось распарсить, используем текущее время
            return django_timezone.now()
            
        except Exception:
            return django_timezone.now()
    
    def _find_employee_by_card(self, card_number: str) -> Optional[Employee]:
        """Поиск сотрудника по номеру карты"""
        if not card_number:
            return None
        
        # Пока что используем employee_id как номер карты
        # В будущем можно добавить отдельное поле card_number в модель Employee
        try:
            return Employee.objects.get(employee_id=card_number)
        except Employee.DoesNotExist:
            return None
    
    def _process_event_for_work_time(self, event: SKUDEvent):
        """Обработка события для записи рабочего времени"""
        if not event.employee:
            return
        
        event_date = event.event_time.date()
        
        # Получаем или создаем запись рабочего времени
        work_record, created = WorkTimeRecord.objects.get_or_create(
            employee=event.employee,
            date=event_date,
            defaults={}
        )
        
        event_time = event.event_time.time()
        
        # Обновляем время в зависимости от типа события
        if event.event_type == 'entry':
            work_record.arrival_time = event_time
            work_record.arrival_event = event
            work_record.notes = f"Вход через {event.device.name}"
        elif event.event_type == 'exit':
            work_record.departure_time = event_time
            work_record.departure_event = event
            if work_record.notes:
                work_record.notes += f"; Выход через {event.device.name}"
            else:
                work_record.notes = f"Выход через {event.device.name}"
        
        work_record.save()
        event.is_processed = True
        event.save(update_fields=['is_processed'])
    
    def get_device_events(self, device: SKUDDevice, hours: int = 24) -> List[SKUDEvent]:
        """
        Получение событий устройства за последние часы
        
        Args:
            device: Объект СКУД устройства
            hours: Количество часов для получения событий
            
        Returns:
            List[SKUDEvent]: Список событий
        """
        since_time = django_timezone.now() - django_timezone.timedelta(hours=hours)
        
        return SKUDEvent.objects.filter(
            device=device,
            event_time__gte=since_time
        ).order_by('-event_time')
    
    def check_all_devices_health(self) -> Dict[str, Dict]:
        """
        Проверка состояния всех активных устройств
        
        Returns:
            Dict[str, Dict]: Результаты проверки для каждого устройства
        """
        devices = SKUDDevice.objects.filter(is_active=True)
        results = {}
        
        for device in devices:
            try:
                is_online, message = self.test_device_connection(device)
                
                # Обновляем статус устройства
                if is_online and device.status == 'error':
                    device.status = 'active'
                    device.save(update_fields=['status'])
                elif not is_online and device.status == 'active':
                    device.status = 'error'
                    device.save(update_fields=['status'])
                
                results[device.ip_address] = {
                    'device_name': device.name,
                    'is_online': is_online,
                    'message': message,
                    'status': device.status
                }
                
            except Exception as e:
                results[device.ip_address] = {
                    'device_name': device.name,
                    'is_online': False,
                    'message': f"Ошибка: {str(e)}",
                    'status': 'error'
                }
        
        return results


class SKUDEventProcessor:
    """Класс для обработки событий СКУД"""
    
    def __init__(self):
        self.logger = logger
    
    def process_unprocessed_events(self) -> int:
        """
        Обработка необработанных событий СКУД
        
        Returns:
            int: Количество обработанных событий
        """
        unprocessed_events = SKUDEvent.objects.filter(is_processed=False)
        processed_count = 0
        
        for event in unprocessed_events:
            try:
                self._process_single_event(event)
                processed_count += 1
            except Exception as e:
                self.logger.error(f"Ошибка обработки события {event.id}: {e}")
        
        return processed_count
    
    def _process_single_event(self, event: SKUDEvent):
        """Обработка одного события"""
        if not event.employee:
            self.logger.warning(f"Событие {event.id} без привязанного сотрудника")
            event.is_processed = True
            event.save(update_fields=['is_processed'])
            return
        
        # Логика обработки события (уже реализована в SKUDDeviceCommunicator)
        communicator = SKUDDeviceCommunicator()
        communicator._process_event_for_work_time(event)
    
    def generate_daily_report(self, date: datetime.date) -> Dict:
        """
        Генерация ежедневного отчета по событиям СКУД
        
        Args:
            date: Дата для отчета
            
        Returns:
            Dict: Отчет
        """
        events = SKUDEvent.objects.filter(
            event_time__date=date
        ).select_related('device', 'employee')
        
        report = {
            'date': date.isoformat(),
            'total_events': events.count(),
            'entry_events': events.filter(event_type='entry').count(),
            'exit_events': events.filter(event_type='exit').count(),
            'denied_events': events.filter(event_type='denied').count(),
            'alarm_events': events.filter(event_type='alarm').count(),
            'devices': {},
            'employees': {}
        }
        
        # Статистика по устройствам
        for device in SKUDDevice.objects.all():
            device_events = events.filter(device=device)
            report['devices'][device.name] = {
                'total': device_events.count(),
                'entry': device_events.filter(event_type='entry').count(),
                'exit': device_events.filter(event_type='exit').count()
            }
        
        # Статистика по сотрудникам
        employee_events = events.filter(employee__isnull=False)
        for event in employee_events:
            employee_name = event.employee.full_name
            if employee_name not in report['employees']:
                report['employees'][employee_name] = {
                    'total': 0,
                    'entry': 0,
                    'exit': 0
                }
            
            report['employees'][employee_name]['total'] += 1
            if event.event_type == 'entry':
                report['employees'][employee_name]['entry'] += 1
            elif event.event_type == 'exit':
                report['employees'][employee_name]['exit'] += 1
        
        return report
