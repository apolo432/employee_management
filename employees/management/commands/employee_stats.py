"""
Команда Django для генерации статистики по сотрудникам
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import date, timedelta
from employees.models import Employee
from employees.skud_integration import get_skud_integration


class Command(BaseCommand):
    help = 'Генерация статистики по сотрудникам'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            type=str,
            help='Начальная дата в формате YYYY-MM-DD (по умолчанию - начало месяца)',
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='Конечная дата в формате YYYY-MM-DD (по умолчанию - сегодня)',
        )
        parser.add_argument(
            '--employee-id',
            type=str,
            help='Табельный номер сотрудника (если не указан - все сотрудники)',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['table', 'json', 'csv'],
            default='table',
            help='Формат вывода (table, json, csv)',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Файл для сохранения результатов',
        )

    def handle(self, *args, **options):
        # Определяем период
        if options['start_date']:
            try:
                start_date = date.fromisoformat(options['start_date'])
            except ValueError:
                raise CommandError('Неверный формат начальной даты. Используйте YYYY-MM-DD')
        else:
            # Начало текущего месяца
            today = timezone.now().date()
            start_date = today.replace(day=1)

        if options['end_date']:
            try:
                end_date = date.fromisoformat(options['end_date'])
            except ValueError:
                raise CommandError('Неверный формат конечной даты. Используйте YYYY-MM-DD')
        else:
            end_date = timezone.now().date()

        self.stdout.write(f'Статистика за период: {start_date} - {end_date}')

        # Получаем экземпляр интеграции с СКУД
        skud = get_skud_integration()

        # Генерируем статистику
        if options['employee_id']:
            try:
                employee = Employee.objects.get(employee_id=options['employee_id'])
                stats = [skud.get_employee_statistics(employee, start_date, end_date)]
            except Employee.DoesNotExist:
                raise CommandError(f'Сотрудник с табельным номером {options["employee_id"]} не найден')
        else:
            # Статистика для всех активных сотрудников
            active_employees = Employee.objects.filter(is_active=True)
            stats = []
            
            for employee in active_employees:
                try:
                    employee_stats = skud.get_employee_statistics(employee, start_date, end_date)
                    stats.append(employee_stats)
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Ошибка при получении статистики для {employee.full_name}: {str(e)}')
                    )

        # Выводим результаты
        self.output_results(stats, options['format'], options['output'])

    def output_results(self, stats, format_type, output_file):
        """Вывод результатов в указанном формате"""
        
        if format_type == 'table':
            self.output_table(stats)
        elif format_type == 'json':
            self.output_json(stats)
        elif format_type == 'csv':
            self.output_csv(stats)

        if output_file:
            self.save_to_file(stats, format_type, output_file)

    def output_table(self, stats):
        """Вывод в виде таблицы"""
        if not stats:
            self.stdout.write(self.style.WARNING('Нет данных для отображения'))
            return

        # Заголовок таблицы
        self.stdout.write('\n' + '='*120)
        self.stdout.write(f"{'Сотрудник':<30} {'Период':<20} {'Дней':<6} {'Присут.':<8} {'Отсут.':<8} {'Часов':<8} {'Среднее':<8} {'Посещ.':<8}")
        self.stdout.write('='*120)

        for stat in stats:
            self.stdout.write(
                f"{stat['employee']:<30} "
                f"{stat['period']:<20} "
                f"{stat['total_days']:<6} "
                f"{stat['present_days']:<8} "
                f"{stat['absent_days']:<8} "
                f"{stat['total_hours']:<8} "
                f"{stat['avg_hours_per_day']:<8} "
                f"{stat['attendance_rate']:<8}%"
            )

        self.stdout.write('='*120)

        # Общая статистика
        if len(stats) > 1:
            total_employees = len(stats)
            avg_attendance = sum(s['attendance_rate'] for s in stats) / total_employees
            avg_hours = sum(s['total_hours'] for s in stats) / total_employees

            self.stdout.write(f'\nОбщая статистика:')
            self.stdout.write(f'Всего сотрудников: {total_employees}')
            self.stdout.write(f'Средняя посещаемость: {avg_attendance:.2f}%')
            self.stdout.write(f'Среднее количество часов: {avg_hours:.2f}')

    def output_json(self, stats):
        """Вывод в формате JSON"""
        import json
        json_output = json.dumps(stats, ensure_ascii=False, indent=2)
        self.stdout.write(json_output)

    def output_csv(self, stats):
        """Вывод в формате CSV"""
        import csv
        import io
        
        output = io.StringIO()
        if stats:
            fieldnames = stats[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(stats)
        
        self.stdout.write(output.getvalue())

    def save_to_file(self, stats, format_type, filename):
        """Сохранение результатов в файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                if format_type == 'json':
                    import json
                    json.dump(stats, f, ensure_ascii=False, indent=2)
                elif format_type == 'csv':
                    import csv
                    if stats:
                        fieldnames = stats[0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(stats)
                else:  # table
                    f.write('Статистика сотрудников\n')
                    f.write('='*50 + '\n')
                    for stat in stats:
                        f.write(f"Сотрудник: {stat['employee']}\n")
                        f.write(f"Период: {stat['period']}\n")
                        f.write(f"Всего дней: {stat['total_days']}\n")
                        f.write(f"Присутствовал: {stat['present_days']}\n")
                        f.write(f"Отсутствовал: {stat['absent_days']}\n")
                        f.write(f"Общее время: {stat['total_hours']} часов\n")
                        f.write(f"Среднее в день: {stat['avg_hours_per_day']} часов\n")
                        f.write(f"Процент посещаемости: {stat['attendance_rate']}%\n")
                        f.write('-'*50 + '\n')

            self.stdout.write(
                self.style.SUCCESS(f'Результаты сохранены в файл: {filename}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при сохранении файла: {str(e)}')
            )
