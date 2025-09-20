"""
Management команда для получения статистики системы учёта рабочего времени
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, date, timedelta

from employees.models import (
    Employee, SKUDEvent, WorkSession, WorkDaySummary, 
    WorkTimeAuditLog, SKUDDevice
)


class Command(BaseCommand):
    help = 'Статистика системы учёта рабочего времени'

    def add_arguments(self, parser):
        parser.add_argument(
            '--period-days',
            type=int,
            default=30,
            help='Период для статистики в днях (по умолчанию 30)',
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Подробная статистика с разбивкой по отделам',
        )
        parser.add_argument(
            '--export-csv',
            type=str,
            help='Экспорт статистики в CSV файл',
        )

    def handle(self, *args, **options):
        period_days = options['period_days']
        detailed = options['detailed']
        export_csv = options['export_csv']

        # Вычисляем период
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)

        self.stdout.write(
            self.style.SUCCESS(f'📊 Статистика системы учёта рабочего времени')
        )
        self.stdout.write(f'📅 Период: {start_date} - {end_date} ({period_days} дней)')
        self.stdout.write('='*60)

        # Общая статистика системы
        self.stdout.write('\n🏢 ОБЩАЯ СТАТИСТИКА СИСТЕМЫ')
        self.stdout.write('-'*40)

        # Сотрудники
        total_employees = Employee.objects.filter(is_active=True).count()
        inactive_employees = Employee.objects.filter(is_active=False).count()
        
        self.stdout.write(f'👥 Всего сотрудников: {total_employees + inactive_employees}')
        self.stdout.write(f'   ✅ Активных: {total_employees}')
        self.stdout.write(f'   ❌ Неактивных: {inactive_employees}')

        # Устройства СКУД
        total_devices = SKUDDevice.objects.count()
        active_devices = SKUDDevice.objects.filter(is_active=True).count()
        
        self.stdout.write(f'\n🔧 Устройства СКУД: {total_devices}')
        self.stdout.write(f'   ✅ Активных: {active_devices}')
        self.stdout.write(f'   ❌ Неактивных: {total_devices - active_devices}')

        # События СКУД
        total_events = SKUDEvent.objects.count()
        events_in_period = SKUDEvent.objects.filter(
            event_time__date__gte=start_date,
            event_time__date__lte=end_date
        ).count()
        unprocessed_events = SKUDEvent.objects.filter(is_processed=False).count()

        self.stdout.write(f'\n🔔 События СКУД: {total_events}')
        self.stdout.write(f'   📅 За период: {events_in_period}')
        self.stdout.write(f'   ⏳ Не обработано: {unprocessed_events}')

        # Рабочие сессии
        total_sessions = WorkSession.objects.count()
        sessions_in_period = WorkSession.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).count()
        open_sessions = WorkSession.objects.filter(status='open').count()

        self.stdout.write(f'\n⏰ Рабочие сессии: {total_sessions}')
        self.stdout.write(f'   📅 За период: {sessions_in_period}')
        self.stdout.write(f'   🔓 Открытых: {open_sessions}')

        # Сводки дней
        total_summaries = WorkDaySummary.objects.count()
        summaries_in_period = WorkDaySummary.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).count()

        self.stdout.write(f'\n📊 Сводки дней: {total_summaries}')
        self.stdout.write(f'   📅 За период: {summaries_in_period}')

        # Статистика за период
        self.stdout.write(f'\n📈 СТАТИСТИКА ЗА ПЕРИОД ({period_days} дней)')
        self.stdout.write('-'*40)

        # События по типам
        event_types = SKUDEvent.objects.filter(
            event_time__date__gte=start_date,
            event_time__date__lte=end_date
        ).values('event_type').annotate(count=Count('id'))

        self.stdout.write('\n🔔 События по типам:')
        for event_type in event_types:
            type_name = {
                'entry': 'Вход',
                'exit': 'Выход',
                'denied': 'Отказ',
                'alarm': 'Тревога'
            }.get(event_type['event_type'], event_type['event_type'])
            self.stdout.write(f'   {type_name}: {event_type["count"]}')

        # Статусы сводок
        summary_statuses = WorkDaySummary.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).values('status').annotate(count=Count('id'))

        self.stdout.write('\n📊 Статусы дней:')
        for status in summary_statuses:
            status_name = {
                'present': 'Присутствовал',
                'absent': 'Отсутствовал',
                'excused': 'Уважительная причина',
                'partial': 'Частично присутствовал',
                'problem': 'Проблема'
            }.get(status['status'], status['status'])
            self.stdout.write(f'   {status_name}: {status["count"]}')

        # Общее время работы
        total_hours = WorkDaySummary.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(total=Sum('total_seconds_in_office'))['total'] or 0

        expected_hours = WorkDaySummary.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(total=Sum('expected_seconds'))['total'] or 0

        self.stdout.write(f'\n⏱️  Время работы:')
        self.stdout.write(f'   📊 Отработано: {total_hours / 3600:.1f} часов')
        self.stdout.write(f'   📋 Ожидаемо: {expected_hours / 3600:.1f} часов')
        
        if expected_hours > 0:
            efficiency = (total_hours / expected_hours) * 100
            self.stdout.write(f'   📈 Эффективность: {efficiency:.1f}%')

        # Среднее время работы
        avg_hours = WorkDaySummary.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(avg=Avg('total_seconds_in_office'))['avg'] or 0

        self.stdout.write(f'   📊 Среднее время в день: {avg_hours / 3600:.1f} часов')

        # Проблемные дни
        problem_days = WorkDaySummary.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).filter(
            Q(has_missing_exit=True) | Q(has_manual_corrections=True)
        ).count()

        self.stdout.write(f'   ⚠️  Проблемных дней: {problem_days}')

        # Подробная статистика по отделам
        if detailed:
            self.stdout.write(f'\n🏢 ПОДРОБНАЯ СТАТИСТИКА ПО ОТДЕЛАМ')
            self.stdout.write('-'*40)

            dept_stats = WorkDaySummary.objects.filter(
                date__gte=start_date,
                date__lte=end_date,
                employee__department__isnull=False
            ).values(
                'employee__department__name'
            ).annotate(
                employees=Count('employee', distinct=True),
                days=Count('id'),
                total_hours=Sum('total_seconds_in_office'),
                expected_hours=Sum('expected_seconds'),
                problem_days=Count('id', filter=Q(has_missing_exit=True) | Q(has_manual_corrections=True))
            ).order_by('-total_hours')

            for dept in dept_stats:
                dept_name = dept['employee__department__name']
                employees = dept['employees']
                days = dept['days']
                total_hours = dept['total_hours'] / 3600 if dept['total_hours'] else 0
                expected_hours = dept['expected_hours'] / 3600 if dept['expected_hours'] else 0
                problem_days = dept['problem_days']
                
                efficiency = (total_hours / expected_hours * 100) if expected_hours > 0 else 0
                
                self.stdout.write(f'\n📋 {dept_name}:')
                self.stdout.write(f'   👥 Сотрудников: {employees}')
                self.stdout.write(f'   📅 Дней: {days}')
                self.stdout.write(f'   ⏱️  Отработано: {total_hours:.1f}ч')
                self.stdout.write(f'   📊 Ожидаемо: {expected_hours:.1f}ч')
                self.stdout.write(f'   📈 Эффективность: {efficiency:.1f}%')
                self.stdout.write(f'   ⚠️  Проблемных дней: {problem_days}')

        # Активность системы
        self.stdout.write(f'\n🔔 АКТИВНОСТЬ СИСТЕМЫ')
        self.stdout.write('-'*40)

        # События по дням
        events_by_day = SKUDEvent.objects.filter(
            event_time__date__gte=start_date,
            event_time__date__lte=end_date
        ).extra(
            select={'day': 'date(event_time)'}
        ).values('day').annotate(count=Count('id')).order_by('-count')[:10]

        self.stdout.write('\n📅 Топ дней по активности:')
        for day_stat in events_by_day:
            self.stdout.write(f'   {day_stat["day"]}: {day_stat["count"]} событий')

        # Записи аудита
        audit_logs = WorkTimeAuditLog.objects.filter(
            changed_at__date__gte=start_date,
            changed_at__date__lte=end_date
        ).count()

        self.stdout.write(f'\n📝 Записей аудита за период: {audit_logs}')

        # Рекомендации
        self.stdout.write(f'\n💡 РЕКОМЕНДАЦИИ')
        self.stdout.write('-'*40)

        if unprocessed_events > 0:
            self.stdout.write(f'⚠️  Есть {unprocessed_events} необработанных событий')
            self.stdout.write('   Запустите: python manage.py process_skud_events')

        if open_sessions > 0:
            self.stdout.write(f'⚠️  Есть {open_sessions} открытых сессий')
            self.stdout.write('   Проверьте незакрытые сессии в админке')

        if problem_days > 0:
            self.stdout.write(f'⚠️  Есть {problem_days} проблемных дней')
            self.stdout.write('   Проверьте данные в админке или через API')

        if efficiency < 80 and total_hours > 0:
            self.stdout.write(f'⚠️  Низкая эффективность работы: {efficiency:.1f}%')
            self.stdout.write('   Проверьте корректность данных')

        # Экспорт в CSV
        if export_csv:
            self.export_to_csv(export_csv, start_date, end_date, dept_stats if detailed else None)

        self.stdout.write(f'\n✅ Статистика готова!')

    def export_to_csv(self, filename, start_date, end_date, dept_stats=None):
        """Экспорт статистики в CSV файл"""
        import csv
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Заголовок
                writer.writerow(['Статистика системы учёта рабочего времени'])
                writer.writerow([f'Период: {start_date} - {end_date}'])
                writer.writerow([])
                
                # Общая статистика
                writer.writerow(['Общая статистика'])
                writer.writerow(['Параметр', 'Значение'])
                
                total_employees = Employee.objects.filter(is_active=True).count()
                writer.writerow(['Активных сотрудников', total_employees])
                
                total_events = SKUDEvent.objects.filter(
                    event_time__date__gte=start_date,
                    event_time__date__lte=end_date
                ).count()
                writer.writerow(['Событий за период', total_events])
                
                total_sessions = WorkSession.objects.filter(
                    date__gte=start_date,
                    date__lte=end_date
                ).count()
                writer.writerow(['Сессий за период', total_sessions])
                
                total_summaries = WorkDaySummary.objects.filter(
                    date__gte=start_date,
                    date__lte=end_date
                ).count()
                writer.writerow(['Сводок за период', total_summaries])
                
                if dept_stats:
                    writer.writerow([])
                    writer.writerow(['Статистика по отделам'])
                    writer.writerow(['Отдел', 'Сотрудников', 'Дней', 'Часов', 'Эффективность%'])
                    
                    for dept in dept_stats:
                        dept_name = dept['employee__department__name']
                        employees = dept['employees']
                        days = dept['days']
                        total_hours = dept['total_hours'] / 3600 if dept['total_hours'] else 0
                        expected_hours = dept['expected_hours'] / 3600 if dept['expected_hours'] else 0
                        efficiency = (total_hours / expected_hours * 100) if expected_hours > 0 else 0
                        
                        writer.writerow([dept_name, employees, days, f'{total_hours:.1f}', f'{efficiency:.1f}'])
                
                self.stdout.write(f'📄 Статистика экспортирована в: {filename}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Ошибка экспорта: {e}'))
