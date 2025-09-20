"""
Management команда для пересчёта исторических данных рабочего времени
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import datetime, date, timedelta
import sys

from employees.models import Employee, SKUDEvent, WorkSession, WorkDaySummary, WorkTimeAuditLog
from employees.work_time_processor import WorkTimeProcessor


class Command(BaseCommand):
    help = 'Пересчёт рабочих сессий и сводок для исторических данных'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from-date',
            type=str,
            required=True,
            help='Начальная дата периода в формате YYYY-MM-DD',
        )
        parser.add_argument(
            '--to-date',
            type=str,
            required=True,
            help='Конечная дата периода в формате YYYY-MM-DD',
        )
        parser.add_argument(
            '--employee-id',
            type=str,
            help='ID конкретного сотрудника для обработки',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Размер пакета для обработки (по умолчанию 100)',
        )
        parser.add_argument(
            '--force-rebuild',
            action='store_true',
            help='Принудительное пересоздание существующих данных',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет сделано без выполнения изменений',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Подробный вывод процесса',
        )

    def handle(self, *args, **options):
        self.verbosity = options['verbose']
        
        # Парсим даты
        try:
            from_date = datetime.strptime(options['from_date'], '%Y-%m-%d').date()
            to_date = datetime.strptime(options['to_date'], '%Y-%m-%d').date()
        except ValueError:
            raise CommandError('Неверный формат даты. Используйте YYYY-MM-DD')

        if from_date > to_date:
            raise CommandError('Начальная дата не может быть позже конечной')

        if from_date > date.today():
            raise CommandError('Начальная дата не может быть в будущем')

        # Получаем сотрудников для обработки
        if options['employee_id']:
            try:
                employees = [Employee.objects.get(id=options['employee_id'])]
            except Employee.DoesNotExist:
                raise CommandError(f'Сотрудник с ID {options["employee_id"]} не найден')
        else:
            employees = Employee.objects.filter(is_active=True)

        if not employees:
            raise CommandError('Нет активных сотрудников для обработки')

        batch_size = options['batch_size']
        force_rebuild = options['force_rebuild']
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.SUCCESS(
                f'🚀 Начинаем пересчёт данных с {from_date} по {to_date}'
            )
        )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  РЕЖИМ ПРОСМОТРА - изменения не будут сохранены'))

        # Подсчитываем общий объём работы
        total_days = (to_date - from_date).days + 1
        total_employees = len(employees)
        total_operations = total_days * total_employees

        self.stdout.write(f'📊 Объём работы: {total_operations} операций ({total_days} дней × {total_employees} сотрудников)')

        # Создаём процессор
        processor = WorkTimeProcessor()

        # Статистика
        stats = {
            'processed_employees': 0,
            'processed_days': 0,
            'created_sessions': 0,
            'created_summaries': 0,
            'updated_sessions': 0,
            'updated_summaries': 0,
            'deleted_sessions': 0,
            'deleted_summaries': 0,
            'errors': 0,
            'skipped': 0
        }

        try:
            # Обрабатываем каждого сотрудника
            for i, employee in enumerate(employees, 1):
                self.stdout.write(
                    f'\n👤 [{i}/{total_employees}] Обработка: {employee.full_name} ({employee.employee_id})'
                )
                
                # Обрабатываем каждый день
                current_date = from_date
                while current_date <= to_date:
                    try:
                        if self.verbosity:
                            self.stdout.write(f'   📅 {current_date}', ending='')

                        # Проверяем наличие данных для пересчёта
                        existing_sessions = WorkSession.objects.filter(
                            employee=employee, date=current_date
                        ).count()
                        
                        existing_summaries = WorkDaySummary.objects.filter(
                            employee=employee, date=current_date
                        ).count()

                        # Если данные существуют и не принудительный пересчёт
                        if existing_sessions > 0 or existing_summaries > 0:
                            if not force_rebuild:
                                if self.verbosity:
                                    self.stdout.write(f' - пропуск (данные существуют)', ending='')
                                stats['skipped'] += 1
                                current_date += timedelta(days=1)
                                continue
                            else:
                                # Удаляем существующие данные
                                if not dry_run:
                                    deleted_sessions = WorkSession.objects.filter(
                                        employee=employee, date=current_date
                                    ).delete()[0]
                                    
                                    deleted_summaries = WorkDaySummary.objects.filter(
                                        employee=employee, date=current_date
                                    ).delete()[0]
                                    
                                    stats['deleted_sessions'] += deleted_sessions
                                    stats['deleted_summaries'] += deleted_summaries

                                if self.verbosity:
                                    self.stdout.write(f' - пересоздание', ending='')

                        # Проверяем наличие событий СКУД
                        skud_events = SKUDEvent.objects.filter(
                            employee=employee,
                            event_time__date=current_date
                        ).exists()

                        if not skud_events:
                            if self.verbosity:
                                self.stdout.write(f' - нет событий', ending='')
                            stats['skipped'] += 1
                            current_date += timedelta(days=1)
                            continue

                        # Обрабатываем данные
                        if not dry_run:
                            with transaction.atomic():
                                success = processor.process_skud_events_for_employee(
                                    employee, current_date
                                )
                                
                                if success:
                                    # Подсчитываем созданные данные
                                    new_sessions = WorkSession.objects.filter(
                                        employee=employee, date=current_date
                                    ).count()
                                    
                                    new_summaries = WorkDaySummary.objects.filter(
                                        employee=employee, date=current_date
                                    ).count()
                                    
                                    stats['created_sessions'] += new_sessions
                                    stats['created_summaries'] += new_summaries
                                    
                                    if self.verbosity:
                                        self.stdout.write(f' - ✅ создано {new_sessions} сессий, {new_summaries} сводок', ending='')
                                else:
                                    stats['errors'] += 1
                                    if self.verbosity:
                                        self.stdout.write(f' - ❌ ошибка', ending='')
                        else:
                            if self.verbosity:
                                self.stdout.write(f' - будет обработан', ending='')

                        stats['processed_days'] += 1

                    except Exception as e:
                        stats['errors'] += 1
                        if self.verbosity:
                            self.stdout.write(f' - ❌ ошибка: {str(e)}', ending='')
                        else:
                            self.stdout.write(f'   ❌ Ошибка {current_date}: {str(e)}')

                    current_date += timedelta(days=1)
                    if self.verbosity:
                        self.stdout.write()  # Новая строка

                stats['processed_employees'] += 1

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n⚠️  Остановлено пользователем'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Критическая ошибка: {str(e)}'))
            raise

        # Выводим финальную статистику
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 ИТОГОВАЯ СТАТИСТИКА'))
        self.stdout.write('='*60)
        
        self.stdout.write(f'👥 Обработано сотрудников: {stats["processed_employees"]}/{total_employees}')
        self.stdout.write(f'📅 Обработано дней: {stats["processed_days"]}/{total_operations}')
        self.stdout.write(f'⏭️  Пропущено: {stats["skipped"]}')
        self.stdout.write(f'❌ Ошибок: {stats["errors"]}')
        
        if not dry_run:
            self.stdout.write(f'✅ Создано сессий: {stats["created_sessions"]}')
            self.stdout.write(f'✅ Создано сводок: {stats["created_summaries"]}')
            self.stdout.write(f'🗑️  Удалено сессий: {stats["deleted_sessions"]}')
            self.stdout.write(f'🗑️  Удалено сводок: {stats["deleted_summaries"]}')

        # Создаём запись аудита
        if not dry_run and stats['processed_days'] > 0:
            try:
                # Создаём системную запись аудита
                audit_description = f"Пересчёт данных с {from_date} по {to_date}. "
                audit_description += f"Обработано: {stats['processed_days']} дней, "
                audit_description += f"Создано: {stats['created_sessions']} сессий, "
                audit_description += f"{stats['created_summaries']} сводок"

                WorkTimeAuditLog.objects.create(
                    employee=employees[0] if len(employees) == 1 else None,
                    date=from_date,
                    action='reprocess_day',
                    description=audit_description,
                    reason='Management команда worktime_rebuild',
                    changed_by=None  # Системная операция
                )
                
                self.stdout.write(self.style.SUCCESS('📝 Создана запись аудита'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️  Не удалось создать запись аудита: {e}'))

        if stats['errors'] == 0:
            self.stdout.write(self.style.SUCCESS('\n🎉 Пересчёт завершён успешно!'))
        else:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Пересчёт завершён с {stats["errors"]} ошибками'))

        # Рекомендации
        if stats['skipped'] > 0:
            self.stdout.write('\n💡 Совет: Используйте --force-rebuild для пересчёта существующих данных')
        
        if stats['errors'] > 0:
            self.stdout.write('\n💡 Совет: Проверьте логи ошибок и исправьте проблемные данные')
