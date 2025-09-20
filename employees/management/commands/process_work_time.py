"""
Management команда для обработки рабочего времени
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime, date, timedelta

from employees.models import Employee, SKUDEvent
from employees.work_time_processor import WorkTimeProcessor


class Command(BaseCommand):
    help = 'Обработка событий СКУД и формирование рабочих сессий'

    def add_arguments(self, parser):
        parser.add_argument(
            '--employee-id',
            type=str,
            help='ID сотрудника для обработки (если не указан, обрабатываются все)',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Дата для обработки в формате YYYY-MM-DD (по умолчанию сегодня)',
        )
        parser.add_argument(
            '--from-date',
            type=str,
            help='Начальная дата периода в формате YYYY-MM-DD',
        )
        parser.add_argument(
            '--to-date',
            type=str,
            help='Конечная дата периода в формате YYYY-MM-DD',
        )
        parser.add_argument(
            '--reprocess',
            action='store_true',
            help='Пересчитать уже обработанные данные',
        )

    def handle(self, *args, **options):
        processor = WorkTimeProcessor()
        
        # Определяем дату или период
        if options['from_date'] and options['to_date']:
            # Обработка периода
            start_date = datetime.strptime(options['from_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(options['to_date'], '%Y-%m-%d').date()
            self.stdout.write(f'Обработка периода: {start_date} - {end_date}')
            
            if options['employee_id']:
                # Обработка конкретного сотрудника за период
                try:
                    employee = Employee.objects.get(id=options['employee_id'])
                    processed_days = processor.reprocess_employee_period(employee, start_date, end_date)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Обработано {processed_days} дней для {employee.full_name}'
                        )
                    )
                except Employee.DoesNotExist:
                    raise CommandError(f'Сотрудник с ID {options["employee_id"]} не найден')
            else:
                # Обработка всех сотрудников за период
                current_date = start_date
                total_processed = 0
                while current_date <= end_date:
                    results = processor.reprocess_all_employees_day(current_date)
                    total_processed += results['processed']
                    if results['errors'] > 0:
                        self.stdout.write(
                            self.style.WARNING(f'Ошибки на {current_date}: {results["errors"]}')
                        )
                    current_date += timedelta(days=1)
                
                self.stdout.write(
                    self.style.SUCCESS(f'Обработано {total_processed} записей за период')
                )
        
        else:
            # Обработка одной даты
            if options['date']:
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            else:
                target_date = timezone.now().date()
            
            self.stdout.write(f'Обработка даты: {target_date}')
            
            if options['employee_id']:
                # Обработка конкретного сотрудника
                try:
                    employee = Employee.objects.get(id=options['employee_id'])
                    
                    # Проверяем наличие событий
                    events_count = SKUDEvent.objects.filter(
                        employee=employee,
                        event_time__date=target_date
                    ).count()
                    
                    self.stdout.write(f'Найдено {events_count} событий для {employee.full_name}')
                    
                    if processor.process_skud_events_for_employee(employee, target_date):
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Успешно обработаны данные для {employee.full_name}'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Ошибка обработки данных для {employee.full_name}'
                            )
                        )
                        
                except Employee.DoesNotExist:
                    raise CommandError(f'Сотрудник с ID {options["employee_id"]} не найден')
            else:
                # Обработка всех сотрудников
                results = processor.reprocess_all_employees_day(target_date)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Обработано: {results["processed"]}, Ошибок: {results["errors"]}'
                    )
                )
        
        # Показываем статистику
        self._show_statistics()

    def _show_statistics(self):
        """Показать статистику по обработанным данным"""
        from employees.models import WorkSession, WorkDaySummary
        
        total_sessions = WorkSession.objects.count()
        total_summaries = WorkDaySummary.objects.count()
        
        open_sessions = WorkSession.objects.filter(status='open').count()
        problem_summaries = WorkDaySummary.objects.filter(status='problem').count()
        
        self.stdout.write('\n--- Статистика ---')
        self.stdout.write(f'Всего сессий: {total_sessions}')
        self.stdout.write(f'Открытых сессий: {open_sessions}')
        self.stdout.write(f'Всего сводок: {total_summaries}')
        self.stdout.write(f'Сводок с проблемами: {problem_summaries}')
        
        if open_sessions > 0:
            self.stdout.write(
                self.style.WARNING(f'Внимание: {open_sessions} открытых сессий требуют проверки')
            )
