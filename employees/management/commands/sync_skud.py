"""
Команда Django для синхронизации данных с системой СКУД
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import date, timedelta
from employees.models import Employee
from employees.skud_integration import get_skud_integration


class Command(BaseCommand):
    help = 'Синхронизация данных рабочего времени с системой СКУД'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Дата для синхронизации в формате YYYY-MM-DD (по умолчанию - сегодня)',
        )
        parser.add_argument(
            '--employee-id',
            type=str,
            help='Табельный номер сотрудника для синхронизации (если не указан - все сотрудники)',
        )
        parser.add_argument(
            '--days-back',
            type=int,
            default=0,
            help='Количество дней назад для синхронизации (по умолчанию - 0, только указанная дата)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительная синхронизация (перезаписать существующие записи)',
        )

    def handle(self, *args, **options):
        # Определяем дату синхронизации
        if options['date']:
            try:
                sync_date = date.fromisoformat(options['date'])
            except ValueError:
                raise CommandError('Неверный формат даты. Используйте YYYY-MM-DD')
        else:
            sync_date = timezone.now().date()

        # Получаем экземпляр интеграции с СКУД
        skud = get_skud_integration()

        self.stdout.write(
            self.style.SUCCESS(f'Начинаем синхронизацию с СКУД на дату: {sync_date}')
        )

        # Определяем диапазон дат
        end_date = sync_date
        start_date = sync_date - timedelta(days=options['days_back'])

        if options['days_back'] > 0:
            self.stdout.write(f'Синхронизация за период: {start_date} - {end_date}')

        # Синхронизация конкретного сотрудника или всех
        if options['employee_id']:
            try:
                employee = Employee.objects.get(employee_id=options['employee_id'])
                self.sync_employee(skud, employee, start_date, end_date, options['force'])
            except Employee.DoesNotExist:
                raise CommandError(f'Сотрудник с табельным номером {options["employee_id"]} не найден')
        else:
            # Синхронизация всех активных сотрудников
            self.sync_all_employees(skud, start_date, end_date, options['force'])

        self.stdout.write(
            self.style.SUCCESS('Синхронизация завершена')
        )

    def sync_employee(self, skud, employee, start_date, end_date, force=False):
        """Синхронизация одного сотрудника"""
        self.stdout.write(f'Синхронизация сотрудника: {employee.full_name} ({employee.employee_id})')

        current_date = start_date
        synced_records = 0

        while current_date <= end_date:
            try:
                records_count = skud.sync_work_time_records(employee, current_date)
                synced_records += records_count
                
                if records_count > 0:
                    self.stdout.write(f'  {current_date}: {records_count} записей')
                else:
                    self.stdout.write(f'  {current_date}: нет данных')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  {current_date}: ошибка - {str(e)}')
                )

            current_date += timedelta(days=1)

        self.stdout.write(
            self.style.SUCCESS(f'Сотрудник {employee.full_name}: {synced_records} записей синхронизировано')
        )

    def sync_all_employees(self, skud, start_date, end_date, force=False):
        """Синхронизация всех активных сотрудников"""
        active_employees = Employee.objects.filter(is_active=True)
        total_employees = active_employees.count()

        self.stdout.write(f'Найдено активных сотрудников: {total_employees}')

        if total_employees == 0:
            self.stdout.write(self.style.WARNING('Нет активных сотрудников для синхронизации'))
            return

        # Подтверждение для большого количества сотрудников
        if total_employees > 10:
            confirm = input(f'Выполнить синхронизацию для {total_employees} сотрудников? (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write('Синхронизация отменена')
                return

        results = skud.sync_all_employees(start_date)

        self.stdout.write(
            self.style.SUCCESS(
                f'Результаты синхронизации:\n'
                f'  Всего сотрудников: {results["total_employees"]}\n'
                f'  Синхронизировано: {results["synced_employees"]}\n'
                f'  Всего записей: {results["total_records"]}'
            )
        )

        if results['errors']:
            self.stdout.write(self.style.WARNING('Ошибки при синхронизации:'))
            for error in results['errors']:
                self.stdout.write(f'  {error["employee_id"]}: {error["error"]}')
