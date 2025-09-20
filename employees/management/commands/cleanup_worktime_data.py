"""
Management команда для очистки старых данных рабочего времени
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import datetime, date, timedelta

from employees.models import WorkSession, WorkDaySummary, WorkTimeAuditLog, SKUDEvent


class Command(BaseCommand):
    help = 'Очистка старых данных рабочего времени'

    def add_arguments(self, parser):
        parser.add_argument(
            '--older-than-days',
            type=int,
            default=365,
            help='Удалить данные старше указанного количества дней (по умолчанию 365)',
        )
        parser.add_argument(
            '--keep-audit-logs',
            action='store_true',
            help='Сохранить записи аудита (по умолчанию удаляются)',
        )
        parser.add_argument(
            '--keep-skud-events',
            action='store_true',
            help='Сохранить события СКУД (по умолчанию удаляются)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет удалено без выполнения',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Подробный вывод процесса',
        )

    def handle(self, *args, **options):
        self.verbosity = options['verbose']
        older_than_days = options['older_than_days']
        keep_audit_logs = options['keep_audit_logs']
        keep_skud_events = options['keep_skud_events']
        dry_run = options['dry_run']

        # Вычисляем дату отсечения
        cutoff_date = date.today() - timedelta(days=older_than_days)

        self.stdout.write(
            self.style.SUCCESS(f'🧹 Очистка данных старше {cutoff_date} ({older_than_days} дней)')
        )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  РЕЖИМ ПРОСМОТРА - данные не будут удалены'))

        # Статистика для удаления
        stats = {
            'sessions': 0,
            'summaries': 0,
            'audit_logs': 0,
            'skud_events': 0
        }

        try:
            # Подсчитываем данные для удаления
            self.stdout.write('\n📊 Подсчёт данных для удаления...')
            
            # Рабочие сессии
            sessions_to_delete = WorkSession.objects.filter(date__lt=cutoff_date)
            stats['sessions'] = sessions_to_delete.count()
            
            # Сводки дней
            summaries_to_delete = WorkDaySummary.objects.filter(date__lt=cutoff_date)
            stats['summaries'] = summaries_to_delete.count()
            
            # Записи аудита
            if not keep_audit_logs:
                audit_logs_to_delete = WorkTimeAuditLog.objects.filter(date__lt=cutoff_date)
                stats['audit_logs'] = audit_logs_to_delete.count()
            
            # События СКУД
            if not keep_skud_events:
                skud_events_to_delete = SKUDEvent.objects.filter(event_time__date__lt=cutoff_date)
                stats['skud_events'] = skud_events_to_delete.count()

            # Выводим статистику
            self.stdout.write(f'📅 Рабочих сессий: {stats["sessions"]}')
            self.stdout.write(f'📊 Сводок дней: {stats["summaries"]}')
            
            if not keep_audit_logs:
                self.stdout.write(f'📝 Записей аудита: {stats["audit_logs"]}')
            else:
                self.stdout.write('📝 Записи аудита: сохраняются')
            
            if not keep_skud_events:
                self.stdout.write(f'🔔 Событий СКУД: {stats["skud_events"]}')
            else:
                self.stdout.write('🔔 События СКУД: сохраняются')

            total_to_delete = sum(stats.values())
            
            if total_to_delete == 0:
                self.stdout.write(self.style.SUCCESS('\n✅ Нет данных для удаления'))
                return

            self.stdout.write(f'\n🗑️  Всего записей для удаления: {total_to_delete}')

            # Запрашиваем подтверждение
            if not dry_run:
                confirm = input('\n❓ Продолжить удаление? (yes/no): ')
                if confirm.lower() not in ['yes', 'y', 'да', 'д']:
                    self.stdout.write(self.style.WARNING('❌ Операция отменена'))
                    return

            # Выполняем удаление
            if not dry_run:
                self.stdout.write('\n🗑️  Начинаем удаление...')
                
                with transaction.atomic():
                    # Удаляем рабочие сессии
                    if stats['sessions'] > 0:
                        if self.verbosity:
                            self.stdout.write('   Удаление рабочих сессий...')
                        deleted_sessions = sessions_to_delete.delete()[0]
                        self.stdout.write(f'   ✅ Удалено сессий: {deleted_sessions}')
                    
                    # Удаляем сводки дней
                    if stats['summaries'] > 0:
                        if self.verbosity:
                            self.stdout.write('   Удаление сводок дней...')
                        deleted_summaries = summaries_to_delete.delete()[0]
                        self.stdout.write(f'   ✅ Удалено сводок: {deleted_summaries}')
                    
                    # Удаляем записи аудита
                    if not keep_audit_logs and stats['audit_logs'] > 0:
                        if self.verbosity:
                            self.stdout.write('   Удаление записей аудита...')
                        deleted_audit = audit_logs_to_delete.delete()[0]
                        self.stdout.write(f'   ✅ Удалено записей аудита: {deleted_audit}')
                    
                    # Удаляем события СКУД
                    if not keep_skud_events and stats['skud_events'] > 0:
                        if self.verbosity:
                            self.stdout.write('   Удаление событий СКУД...')
                        deleted_events = skud_events_to_delete.delete()[0]
                        self.stdout.write(f'   ✅ Удалено событий СКУД: {deleted_events}')

                self.stdout.write(self.style.SUCCESS('\n🎉 Очистка завершена успешно!'))
            else:
                self.stdout.write(self.style.WARNING('\n⚠️  РЕЖИМ ПРОСМОТРА - данные не удалены'))

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n⚠️  Остановлено пользователем'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Критическая ошибка: {str(e)}'))
            raise

        # Рекомендации
        self.stdout.write('\n💡 Рекомендации:')
        
        if older_than_days > 730:  # Больше 2 лет
            self.stdout.write('   - Рассмотрите возможность архивирования данных вместо удаления')
        
        if not keep_skud_events:
            self.stdout.write('   - События СКУД удалены - восстановление невозможно')
        
        if not keep_audit_logs:
            self.stdout.write('   - Записи аудита удалены - история изменений потеряна')
        
        self.stdout.write(f'   - Для автоматической очистки настройте cron задачу с периодом {older_than_days} дней')

        # Создаём запись аудита о очистке
        if not dry_run and total_to_delete > 0:
            try:
                from employees.models import Employee
                
                # Создаём системную запись аудита
                WorkTimeAuditLog.objects.create(
                    employee=None,  # Системная операция
                    date=date.today(),
                    action='bulk_import',  # Используем существующий тип
                    description=f'Очистка данных старше {cutoff_date}. Удалено: '
                              f'{stats["sessions"]} сессий, {stats["summaries"]} сводок, '
                              f'{stats["audit_logs"]} записей аудита, {stats["skud_events"]} событий СКУД',
                    reason=f'Management команда cleanup_worktime_data (--older-than-days={older_than_days})',
                    changed_by=None
                )
                
                self.stdout.write('📝 Создана запись аудита об очистке')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️  Не удалось создать запись аудита: {e}'))
