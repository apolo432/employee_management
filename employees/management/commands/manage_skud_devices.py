"""
Команда Django для управления СКУД устройствами
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime, timedelta
from employees.models import SKUDDevice, SKUDEvent, Employee
from employees.skud_device_communication import SKUDDeviceCommunicator, SKUDEventProcessor


class Command(BaseCommand):
    help = 'Управление СКУД устройствами'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Действие для выполнения')
        
        # Команда добавления устройства
        add_parser = subparsers.add_parser('add', help='Добавить новое СКУД устройство')
        add_parser.add_argument('--name', required=True, help='Название устройства')
        add_parser.add_argument('--ip', required=True, help='IP адрес устройства')
        add_parser.add_argument('--port', type=int, default=80, help='Порт устройства')
        add_parser.add_argument('--serial', required=True, help='Серийный номер устройства')
        add_parser.add_argument('--type', choices=['turnstile', 'reader', 'controller', 'gate', 'door', 'other'],
                              default='turnstile', help='Тип устройства')
        add_parser.add_argument('--location', help='Местоположение устройства')
        add_parser.add_argument('--description', help='Описание устройства')
        
        # Команда тестирования устройств
        test_parser = subparsers.add_parser('test', help='Тестировать СКУД устройства')
        test_parser.add_argument('--device-id', help='ID конкретного устройства')
        test_parser.add_argument('--all', action='store_true', help='Тестировать все устройства')
        
        # Команда синхронизации времени
        sync_parser = subparsers.add_parser('sync-time', help='Синхронизировать время устройств')
        sync_parser.add_argument('--device-id', help='ID конкретного устройства')
        sync_parser.add_argument('--all', action='store_true', help='Синхронизировать все устройства')
        
        # Команда получения статуса
        status_parser = subparsers.add_parser('status', help='Получить статус устройств')
        status_parser.add_argument('--device-id', help='ID конкретного устройства')
        
        # Команда обработки событий
        process_parser = subparsers.add_parser('process-events', help='Обработать необработанные события')
        process_parser.add_argument('--hours', type=int, default=24, help='Количество часов назад для обработки')
        
        # Команда генерации отчета
        report_parser = subparsers.add_parser('report', help='Генерировать отчет по событиям')
        report_parser.add_argument('--date', help='Дата для отчета (YYYY-MM-DD)')
        report_parser.add_argument('--device-id', help='ID конкретного устройства')
        report_parser.add_argument('--format', choices=['table', 'json'], default='table', help='Формат отчета')

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'add':
            self.add_device(options)
        elif action == 'test':
            self.test_devices(options)
        elif action == 'sync-time':
            self.sync_time(options)
        elif action == 'status':
            self.get_status(options)
        elif action == 'process-events':
            self.process_events(options)
        elif action == 'report':
            self.generate_report(options)
        else:
            self.stdout.write(self.style.ERROR('Неизвестное действие. Используйте --help для справки.'))

    def add_device(self, options):
        """Добавление нового СКУД устройства"""
        try:
            # Проверяем, не существует ли уже устройство с таким IP
            if SKUDDevice.objects.filter(ip_address=options['ip']).exists():
                raise CommandError(f'Устройство с IP {options["ip"]} уже существует')
            
            # Проверяем, не существует ли уже устройство с таким серийным номером
            if SKUDDevice.objects.filter(serial_number=options['serial']).exists():
                raise CommandError(f'Устройство с серийным номером {options["serial"]} уже существует')
            
            device = SKUDDevice.objects.create(
                name=options['name'],
                ip_address=options['ip'],
                port=options['port'],
                serial_number=options['serial'],
                device_type=options['type'],
                location=options.get('location', ''),
                description=options.get('description', '')
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Устройство "{device.name}" успешно добавлено (ID: {device.id})')
            )
            
            # Тестируем соединение
            communicator = SKUDDeviceCommunicator()
            is_online, message = communicator.test_device_connection(device)
            
            if is_online:
                self.stdout.write(self.style.SUCCESS(f'Соединение с устройством установлено: {message}'))
            else:
                self.stdout.write(self.style.WARNING(f'Не удалось установить соединение: {message}'))
                
        except Exception as e:
            raise CommandError(f'Ошибка при добавлении устройства: {str(e)}')

    def test_devices(self, options):
        """Тестирование СКУД устройств"""
        communicator = SKUDDeviceCommunicator()
        
        if options.get('device_id'):
            try:
                device = SKUDDevice.objects.get(id=options['device_id'])
                devices = [device]
            except SKUDDevice.DoesNotExist:
                raise CommandError(f'Устройство с ID {options["device_id"]} не найдено')
        elif options.get('all'):
            devices = SKUDDevice.objects.filter(is_active=True)
        else:
            devices = SKUDDevice.objects.filter(is_active=True)[:5]  # По умолчанию тестируем первые 5
        
        if not devices:
            self.stdout.write(self.style.WARNING('Нет активных устройств для тестирования'))
            return
        
        self.stdout.write(f'Тестирование {len(devices)} устройств...')
        
        for device in devices:
            self.stdout.write(f'\nТестирование: {device.name} ({device.ip_address})')
            
            is_online, message = communicator.test_device_connection(device)
            
            if is_online:
                self.stdout.write(self.style.SUCCESS(f'  ✓ {message}'))
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ {message}'))
            
            # Обновляем время последней связи
            device.last_communication = timezone.now()
            device.save(update_fields=['last_communication'])

    def sync_time(self, options):
        """Синхронизация времени устройств"""
        communicator = SKUDDeviceCommunicator()
        
        if options.get('device_id'):
            try:
                device = SKUDDevice.objects.get(id=options['device_id'])
                devices = [device]
            except SKUDDevice.DoesNotExist:
                raise CommandError(f'Устройство с ID {options["device_id"]} не найдено')
        elif options.get('all'):
            devices = SKUDDevice.objects.filter(is_active=True)
        else:
            devices = SKUDDevice.objects.filter(is_active=True)
        
        if not devices:
            self.stdout.write(self.style.WARNING('Нет активных устройств для синхронизации'))
            return
        
        self.stdout.write(f'Синхронизация времени для {len(devices)} устройств...')
        
        for device in devices:
            self.stdout.write(f'Синхронизация: {device.name} ({device.ip_address})')
            
            success = communicator.sync_device_time(device)
            
            if success:
                self.stdout.write(self.style.SUCCESS('  ✓ Время синхронизировано'))
            else:
                self.stdout.write(self.style.ERROR('  ✗ Ошибка синхронизации времени'))

    def get_status(self, options):
        """Получение статуса устройств"""
        communicator = SKUDDeviceCommunicator()
        
        if options.get('device_id'):
            try:
                device = SKUDDevice.objects.get(id=options['device_id'])
                devices = [device]
            except SKUDDevice.DoesNotExist:
                raise CommandError(f'Устройство с ID {options["device_id"]} не найдено')
        else:
            devices = SKUDDevice.objects.all()
        
        if not devices:
            self.stdout.write(self.style.WARNING('Нет устройств в системе'))
            return
        
        # Получаем общий статус здоровья
        health_status = communicator.check_all_devices_health()
        
        self.stdout.write('\n' + '='*100)
        self.stdout.write(f"{'Устройство':<25} {'IP':<15} {'Статус':<12} {'Связь':<8} {'Последняя связь':<20}")
        self.stdout.write('='*100)
        
        for device in devices:
            device_health = health_status.get(device.ip_address, {})
            is_online = device_health.get('is_online', False)
            last_comm = device.last_communication.strftime('%Y-%m-%d %H:%M:%S') if device.last_communication else 'Никогда'
            
            self.stdout.write(
                f"{device.name:<25} "
                f"{device.ip_address:<15} "
                f"{device.get_status_display():<12} "
                f"{'✓' if is_online else '✗':<8} "
                f"{last_comm:<20}"
            )
        
        self.stdout.write('='*100)
        
        # Общая статистика
        total_devices = len(devices)
        online_devices = sum(1 for status in health_status.values() if status['is_online'])
        
        self.stdout.write(f'\nОбщая статистика:')
        self.stdout.write(f'Всего устройств: {total_devices}')
        self.stdout.write(f'Онлайн: {online_devices}')
        self.stdout.write(f'Офлайн: {total_devices - online_devices}')

    def process_events(self, options):
        """Обработка необработанных событий"""
        processor = SKUDEventProcessor()
        
        self.stdout.write('Обработка необработанных событий...')
        
        processed_count = processor.process_unprocessed_events()
        
        self.stdout.write(
            self.style.SUCCESS(f'Обработано событий: {processed_count}')
        )
        
        # Показываем статистику необработанных событий
        unprocessed_count = SKUDEvent.objects.filter(is_processed=False).count()
        if unprocessed_count > 0:
            self.stdout.write(
                self.style.WARNING(f'Осталось необработанных событий: {unprocessed_count}')
            )

    def generate_report(self, options):
        """Генерация отчета по событиям"""
        processor = SKUDEventProcessor()
        
        # Определяем дату для отчета
        if options.get('date'):
            try:
                report_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Неверный формат даты. Используйте YYYY-MM-DD')
        else:
            report_date = timezone.now().date()
        
        # Фильтр по устройству
        device_filter = {}
        if options.get('device_id'):
            device_filter['device_id'] = options['device_id']
        
        self.stdout.write(f'Генерация отчета за {report_date}...')
        
        # Получаем события за дату
        events = SKUDEvent.objects.filter(
            event_time__date=report_date,
            **device_filter
        ).select_related('device', 'employee')
        
        if options['format'] == 'json':
            self.output_json_report(events, report_date)
        else:
            self.output_table_report(events, report_date)

    def output_table_report(self, events, report_date):
        """Вывод отчета в виде таблицы"""
        self.stdout.write('\n' + '='*120)
        self.stdout.write(f"ОТЧЕТ ПО СОБЫТИЯМ СКУД за {report_date}")
        self.stdout.write('='*120)
        
        # Общая статистика
        total_events = events.count()
        entry_events = events.filter(event_type='entry').count()
        exit_events = events.filter(event_type='exit').count()
        denied_events = events.filter(event_type='denied').count()
        alarm_events = events.filter(event_type='alarm').count()
        
        self.stdout.write(f'Всего событий: {total_events}')
        self.stdout.write(f'Входы: {entry_events}')
        self.stdout.write(f'Выходы: {exit_events}')
        self.stdout.write(f'Отказы: {denied_events}')
        self.stdout.write(f'Тревоги: {alarm_events}')
        self.stdout.write('-'*120)
        
        # Детали событий
        if events.exists():
            self.stdout.write(f"{'Время':<20} {'Устройство':<20} {'Сотрудник':<30} {'Тип':<10} {'Карта':<15}")
            self.stdout.write('-'*120)
            
            for event in events[:50]:  # Показываем первые 50 событий
                employee_name = event.employee.full_name if event.employee else 'Неизвестный'
                event_time = event.event_time.strftime('%H:%M:%S')
                
                self.stdout.write(
                    f"{event_time:<20} "
                    f"{event.device.name:<20} "
                    f"{employee_name:<30} "
                    f"{event.get_event_type_display():<10} "
                    f"{event.card_number:<15}"
                )
            
            if total_events > 50:
                self.stdout.write(f'... и еще {total_events - 50} событий')
        else:
            self.stdout.write('Событий не найдено')

    def output_json_report(self, events, report_date):
        """Вывод отчета в формате JSON"""
        import json
        
        report_data = {
            'date': report_date.isoformat(),
            'total_events': events.count(),
            'events': []
        }
        
        for event in events:
            report_data['events'].append({
                'id': str(event.id),
                'device_name': event.device.name,
                'device_ip': event.device.ip_address,
                'employee_name': event.employee.full_name if event.employee else None,
                'employee_id': event.employee.employee_id if event.employee else None,
                'event_type': event.event_type,
                'event_time': event.event_time.isoformat(),
                'card_number': event.card_number
            })
        
        json_output = json.dumps(report_data, ensure_ascii=False, indent=2)
        self.stdout.write(json_output)
