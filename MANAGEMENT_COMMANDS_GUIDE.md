# Руководство по Management командам системы учёта рабочего времени

## Обзор

Система включает 5 management команд для управления данными рабочего времени:

1. **`worktime_stats`** - Статистика и мониторинг системы
2. **`process_skud_events`** - Массовая обработка событий СКУД
3. **`worktime_rebuild`** - Пересчёт исторических данных
4. **`cleanup_worktime_data`** - Очистка старых данных
5. **`process_work_time`** - Ежедневная обработка (базовая)

---

## 1. worktime_stats - Статистика системы

### Назначение
Получение подробной статистики о работе системы учёта рабочего времени.

### Использование
```bash
python manage.py worktime_stats [опции]
```

### Параметры
- `--period-days N` - Период для статистики в днях (по умолчанию 30)
- `--detailed` - Подробная статистика с разбивкой по отделам
- `--export-csv FILE` - Экспорт статистики в CSV файл

### Примеры
```bash
# Базовая статистика за последние 30 дней
python manage.py worktime_stats

# Подробная статистика за неделю
python manage.py worktime_stats --period-days=7 --detailed

# Экспорт в CSV
python manage.py worktime_stats --detailed --export-csv=report.csv
```

### Вывод включает
- Общую статистику системы (сотрудники, устройства, события)
- Статистику за период (события по типам, статусы дней)
- Время работы и эффективность
- Подробную статистику по отделам (с --detailed)
- Рекомендации по устранению проблем

---

## 2. process_skud_events - Массовая обработка событий

### Назначение
Массовая обработка необработанных событий СКУД для создания рабочих сессий и сводок.

### Использование
```bash
python manage.py process_skud_events [опции]
```

### Параметры
- `--batch-size N` - Размер пакета для обработки (по умолчанию 1000)
- `--from-date DATE` - Начальная дата (YYYY-MM-DD)
- `--to-date DATE` - Конечная дата (YYYY-MM-DD)
- `--employee-id ID` - ID конкретного сотрудника
- `--device-id ID` - ID конкретного устройства
- `--force-process` - Принудительная обработка уже обработанных событий
- `--dry-run` - Показать что будет обработано без выполнения
- `--verbose` - Подробный вывод

### Примеры
```bash
# Обработка всех необработанных событий
python manage.py process_skud_events

# Обработка событий за период
python manage.py process_skud_events --from-date=2025-01-01 --to-date=2025-09-19

# Обработка для конкретного сотрудника
python manage.py process_skud_events --employee-id=123 --verbose

# Просмотр что будет обработано
python manage.py process_skud_events --dry-run
```

### Особенности
- Группирует события по сотрудникам и датам
- Обрабатывает данные пакетами для оптимизации
- Создаёт записи аудита
- Поддерживает прерывание (Ctrl+C)

---

## 3. worktime_rebuild - Пересчёт исторических данных

### Назначение
Пересчёт рабочих сессий и сводок для исторических данных с возможностью принудительного пересоздания.

### Использование
```bash
python manage.py worktime_rebuild --from-date=DATE --to-date=DATE [опции]
```

### Параметры
- `--from-date DATE` - Начальная дата (обязательно)
- `--to-date DATE` - Конечная дата (обязательно)
- `--employee-id ID` - ID конкретного сотрудника
- `--batch-size N` - Размер пакета (по умолчанию 100)
- `--force-rebuild` - Принудительное пересоздание существующих данных
- `--dry-run` - Показать что будет сделано без выполнения
- `--verbose` - Подробный вывод

### Примеры
```bash
# Пересчёт данных за месяц
python manage.py worktime_rebuild --from-date=2025-08-01 --to-date=2025-08-31

# Принудительный пересчёт с пересозданием
python manage.py worktime_rebuild --from-date=2025-01-01 --to-date=2025-09-19 --force-rebuild

# Просмотр плана пересчёта
python manage.py worktime_rebuild --from-date=2025-09-01 --to-date=2025-09-19 --dry-run

# Пересчёт для конкретного сотрудника
python manage.py worktime_rebuild --from-date=2025-09-01 --to-date=2025-09-19 --employee-id=123
```

### Особенности
- Удаляет существующие данные при --force-rebuild
- Создаёт записи аудита
- Обрабатывает данные по дням и сотрудникам
- Показывает детальную статистику

---

## 4. cleanup_worktime_data - Очистка старых данных

### Назначение
Очистка старых данных для освобождения места в базе данных.

### Использование
```bash
python manage.py cleanup_worktime_data [опции]
```

### Параметры
- `--older-than-days N` - Удалить данные старше N дней (по умолчанию 365)
- `--keep-audit-logs` - Сохранить записи аудита
- `--keep-skud-events` - Сохранить события СКУД
- `--dry-run` - Показать что будет удалено без выполнения
- `--verbose` - Подробный вывод

### Примеры
```bash
# Очистка данных старше года
python manage.py cleanup_worktime_data --older-than-days=365

# Очистка с сохранением событий СКУД
python manage.py cleanup_worktime_data --keep-skud-events

# Просмотр что будет удалено
python manage.py cleanup_worktime_data --older-than-days=730 --dry-run

# Агрессивная очистка (старше 6 месяцев)
python manage.py cleanup_worktime_data --older-than-days=180 --verbose
```

### Особенности
- Запрашивает подтверждение перед удалением
- Создаёт записи аудита об очистке
- Поддерживает селективное сохранение данных
- Показывает детальную статистику удаления

---

## 5. process_work_time - Ежедневная обработка (базовая)

### Назначение
Базовая команда для ежедневной обработки событий СКУД.

### Использование
```bash
python manage.py process_work_time [опции]
```

### Параметры
- `--employee-id ID` - ID сотрудника для обработки
- `--date DATE` - Дата для обработки (по умолчанию сегодня)
- `--from-date DATE` - Начальная дата периода
- `--to-date DATE` - Конечная дата периода
- `--reprocess` - Пересчитать уже обработанные данные

### Примеры
```bash
# Обработка на сегодня
python manage.py process_work_time

# Обработка конкретной даты
python manage.py process_work_time --date=2025-09-19

# Обработка периода
python manage.py process_work_time --from-date=2025-09-01 --to-date=2025-09-19

# Обработка для конкретного сотрудника
python manage.py process_work_time --employee-id=123 --date=2025-09-19
```

---

## Рекомендации по использованию

### Ежедневные задачи
```bash
# 1. Обработка новых событий
python manage.py process_skud_events --batch-size=500

# 2. Проверка статистики
python manage.py worktime_stats --period-days=7
```

### Еженедельные задачи
```bash
# 1. Детальная статистика
python manage.py worktime_stats --detailed --export-csv=weekly_report.csv

# 2. Обработка накопившихся событий
python manage.py process_skud_events --from-date=2025-09-13 --to-date=2025-09-19
```

### Ежемесячные задачи
```bash
# 1. Пересчёт данных за месяц
python manage.py worktime_rebuild --from-date=2025-08-01 --to-date=2025-08-31

# 2. Очистка старых данных
python manage.py cleanup_worktime_data --older-than-days=365 --dry-run
```

### Настройка автоматизации (Cron)

```bash
# Ежедневно в 02:00 - обработка событий
0 2 * * * cd /path/to/project && python manage.py process_skud_events

# Еженедельно в воскресенье в 03:00 - очистка старых данных
0 3 * * 0 cd /path/to/project && python manage.py cleanup_worktime_data --older-than-days=365

# Ежемесячно 1 числа в 04:00 - пересчёт за прошлый месяц
0 4 1 * * cd /path/to/project && python manage.py worktime_rebuild --from-date=$(date -d "last month" +%Y-%m-01) --to-date=$(date -d "last day of last month" +%Y-%m-%d)
```

### Мониторинг и диагностика

```bash
# Проверка состояния системы
python manage.py worktime_stats --detailed

# Поиск проблемных данных
python manage.py worktime_stats --period-days=30 | grep "⚠️"

# Обработка накопившихся событий
python manage.py process_skud_events --dry-run
```

---

## Безопасность и производительность

### Рекомендации
- Всегда используйте `--dry-run` для больших операций
- Делайте резервные копии перед массовыми операциями
- Настройте мониторинг выполнения команд
- Используйте `--batch-size` для оптимизации памяти

### Ограничения
- Команды блокируют базу данных во время выполнения
- Большие периоды могут занимать много времени
- Рекомендуется запускать в нерабочее время

### Логирование
- Все команды выводят подробную статистику
- Создаются записи аудита для важных операций
- Используйте `--verbose` для детального логирования
