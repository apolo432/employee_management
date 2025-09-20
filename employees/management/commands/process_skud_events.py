"""
Management команда для массовой обработки событий СКУД
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import datetime, date, timedelta
from collections import defaultdict

from employees.models import Employee, SKUDEvent, WorkSession, WorkDaySummary
from employees.work_time_processor import WorkTimeProcessor


class Command(BaseCommand):
    help = 'Массовая обработка необработанных событий СКУД'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Размер пакета для обработки (по умолчанию 1000)',
        )
        parser.add_argument(
            '--from-date',
            type=str,
            help='Начальная дата для обработки в формате YYYY-MM-DD',
        )
        parser.add_argument(
            '--to-date',
            type=str,
            help='Конечная дата для обработки в формате YYYY-MM-DD',
        )
        parser.add_argument(
            '--employee-id',
            type=str,
            help='ID конкретного сотрудника для обработки',
        )
        parser.add_argument(
            '--device-id',
            type=str,
            help='ID конкретного устройства для обработки',
        )
        parser.add_argument(
            '--force-process',
            action='store_true',
            help='Принудительная обработка уже обработанных событий',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет обработано без выполнения изменений',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Подробный вывод процесса',
        )

    def handle(self, *args, **options):
        self.verbosity = options['verbose']
        batch_size = options['batch_size']
        force_process = options['force_process']
        dry_run = options['dry_run']

        # Парсим даты если указаны
        from_date = None
        to_date = None
        
        if options['from_date']:
            try:
                from_date = datetime.strptime(options['from_date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Неверный формат начальной даты. Используйте YYYY-MM-DD')

        if options['to_date']:
            try:
                to_date = datetime.strptime(options['to_date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Неверный формат конечной даты. Используйте YYYY-MM-DD')

        if from_date and to_date and from_date > to_date:
            raise CommandError('Начальная дата не может быть позже конечной')

        self.stdout.write(
            self.style.SUCCESS('🚀 Начинаем массовую обработку событий СКУД')
        )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  РЕЖИМ ПРОСМОТРА - изменения не будут сохранены'))

        # Строим запрос для событий
        events_query = SKUDEvent.objects.all()
        
        if not force_process:
            events_query = events_query.filter(is_processed=False)
        
        if from_date:
            events_query = events_query.filter(event_time__date__gte=from_date)
        
        if to_date:
            events_query = events_query.filter(event_time__date__lte=to_date)
        
        if options['employee_id']:
            try:
                employee = Employee.objects.get(id=options['employee_id'])
                events_query = events_query.filter(employee=employee)
                self.stdout.write(f'👤 Обработка событий для: {employee.full_name}')
            except Employee.DoesNotExist:
                raise CommandError(f'Сотрудник с ID {options["employee_id"]} не найден')
        
        if options['device_id']:
            events_query = events_query.filter(device_id=options['device_id'])

        total_events = events_query.count()
        
        if total_events == 0:
            self.stdout.write(self.style.WARNING('⚠️  Нет событий для обработки'))
            return

        self.stdout.write(f'📊 Найдено событий для обработки: {total_events}')

        # Создаём процессор
        processor = WorkTimeProcessor()

        # Статистика
        stats = {
            'processed_events': 0,
            'processed_employees': 0,
            'processed_days': 0,
            'created_sessions': 0,
            'created_summaries': 0,
            'errors': 0,
            'skipped': 0
        }

        # Группируем события по сотрудникам и датам
        events_by_employee_date = defaultdict(list)
        
        self.stdout.write('📋 Группировка событий...')
        
        for event in events_query.select_related('employee').iterator(chunk_size=batch_size):
            if event.employee is None:
                self.stdout.write(f'⚠️  Событие {event.id} без сотрудника, пропускаем')
                continue
                
            event_date = event.event_time.date()
            key = (event.employee.id, event_date)
            events_by_employee_date[key].append(event)

        total_groups = len(events_by_employee_date)
        self.stdout.write(f'📊 Сгруппировано в {total_groups} групп (сотрудник + дата)')

        # Обрабатываем каждую группу
        processed_employees = set()
        processed_days = set()
        
        try:
            for i, ((employee_id, event_date), events) in enumerate(events_by_employee_date.items(), 1):
                try:
                    employee = events[0].employee
                    
                    if self.verbosity:
                        self.stdout.write(
                            f'[{i}/{total_groups}] 👤 {employee.full_name} - 📅 {event_date} ({len(events)} событий)',
                            ending=''
                        )

                    # Обрабатываем события для этого сотрудника и даты
                    if not dry_run:
                        with transaction.atomic():
                            success = processor.process_skud_events_for_employee(employee, event_date)
                            
                            if success:
                                # Помечаем события как обработанные
                                event_ids = [event.id for event in events]
                                SKUDEvent.objects.filter(id__in=event_ids).update(is_processed=True)
                    else:
                        # В режиме dry-run просто имитируем успешную обработку
                        success = True
                    
                    if success:
                        stats['processed_events'] += len(events)
                        processed_employees.add(employee_id)
                        processed_days.add((employee_id, event_date))
                        
                        # Подсчитываем созданные данные
                        new_sessions = WorkSession.objects.filter(
                            employee=employee, date=event_date
                        ).count()
                        
                        new_summaries = WorkDaySummary.objects.filter(
                            employee=employee, date=event_date
                        ).count()
                        
                        stats['created_sessions'] += new_sessions
                        stats['created_summaries'] += new_summaries
                        
                        if self.verbosity:
                            self.stdout.write(f' - ✅ {len(events)} событий, {new_sessions} сессий, {new_summaries} сводок')
                        else:
                            if i % 10 == 0 or i == total_groups:
                                self.stdout.write(f'   Обработано: {i}/{total_groups} групп')
                    else:
                        stats['errors'] += 1
                        if self.verbosity:
                            self.stdout.write(f' - ❌ ошибка обработки')

                except Exception as e:
                    stats['errors'] += 1
                    if self.verbosity:
                        self.stdout.write(f' - ❌ ошибка: {str(e)}')
                    else:
                        self.stdout.write(f'   ❌ Ошибка в группе {i}: {str(e)}')

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n⚠️  Остановлено пользователем'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Критическая ошибка: {str(e)}'))
            raise

        # Выводим финальную статистику
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 ИТОГОВАЯ СТАТИСТИКА'))
        self.stdout.write('='*60)
        
        self.stdout.write(f'📋 Обработано событий: {stats["processed_events"]}/{total_events}')
        self.stdout.write(f'👥 Затронуто сотрудников: {len(processed_employees)}')
        self.stdout.write(f'📅 Затронуто дней: {len(processed_days)}')
        self.stdout.write(f'✅ Создано сессий: {stats["created_sessions"]}')
        self.stdout.write(f'✅ Создано сводок: {stats["created_summaries"]}')
        self.stdout.write(f'❌ Ошибок: {stats["errors"]}')

        if stats['errors'] == 0:
            self.stdout.write(self.style.SUCCESS('\n🎉 Обработка завершена успешно!'))
        else:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Обработка завершена с {stats["errors"]} ошибками'))

        # Рекомендации
        if stats['processed_events'] < total_events:
            self.stdout.write(f'\n💡 Совет: {total_events - stats["processed_events"]} событий не обработано')
        
        if stats['errors'] > 0:
            self.stdout.write('\n💡 Совет: Проверьте логи ошибок для исправления проблемных данных')
