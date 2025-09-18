# Система управления сотрудниками

    Django-приложение для управления сотрудниками с интеграцией системы СКУД (Система Контроля и Управления Доступом).

## Описание

Система позволяет:
- Управлять организационной структурой (Организация > Департамент > Отдел > Сотрудник)
- Вносить данные о сотрудниках (ФИО, фото, дата рождения, контакты)
- Отслеживать отпуска и командировки
- Интегрироваться с системой СКУД для автоматического учета рабочего времени
- Генерировать отчеты по посещаемости и рабочему времени

## Структура проекта

```
employee_management/
├── employees/                 # Основное приложение
│   ├── models.py             # Модели данных
│   ├── admin.py              # Админ-интерфейс
│   ├── skud_integration.py   # Интеграция с СКУД
│   └── management/           # Django команды
│       └── commands/
│           ├── sync_skud.py  # Синхронизация с СКУД
│           └── employee_stats.py # Статистика сотрудников
├── employee_management/     # Настройки проекта
└── requirements.txt         # Зависимости
```

## Установка и настройка

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка базы данных

```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Создание суперпользователя

```bash
python manage.py createsuperuser
```

### 4. Запуск сервера

```bash
python manage.py runserver
```

Админ-панель будет доступна по адресу: http://127.0.0.1:8000/admin/

## Модели данных

### Organization (Организация)
- Название, описание, адрес
- Контактная информация (телефон, email)

### Department (Департамент)
- Принадлежность к организации
- Руководитель департамента
- Описание

### Division (Отдел)
- Принадлежность к департаменту
- Руководитель отдела
- Описание

### Employee (Сотрудник)
- Личные данные: ФИО, фото, дата рождения, пол
- Контакты: телефон, email
- Рабочая информация: должность, табельный номер
- Принадлежность к организации/департаменту/отделу
- Статус (активный/неактивный)

### Vacation (Отпуск)
- Сотрудник, даты отпуска
- Количество дней, статус
- Причина отпуска

### BusinessTrip (Командировка)
- Сотрудник, место назначения
- Даты командировки, цель
- Статус командировки

### WorkTimeRecord (Запись рабочего времени)
- Сотрудник, дата
- Время прихода/ухода
- Автоматический расчет общего времени
- Интеграция с СКУД

## Интеграция с СКУД

Система поддерживает два типа интеграции с СКУД:

### 1. Прямая интеграция через IP-адреса (НОВОЕ!)

Система может принимать данные напрямую от СКУД устройств через IP-адреса. Устройства отправляют данные на сервер, который автоматически обрабатывает события и создает записи рабочего времени.

#### Быстрый старт:
1. Создайте миграции: `python manage.py makemigrations employees && python manage.py migrate`
2. Добавьте СКУД устройство: `python manage.py manage_skud_devices add --name "Турникет" --ip "192.168.1.100" --serial "SKUD001"`
3. Настройте устройство для отправки данных на `http://YOUR_SERVER:8000/api/skud/event/`
4. Тестируйте: `python test_skud_integration.py`

#### Основные возможности:
- Прямое общение с СКУД устройствами через IP
- Автоматическая обработка событий прохода
- Создание записей рабочего времени
- Мониторинг состояния устройств
- API для приема данных от устройств
- Команды управления через CLI
- Админ-интерфейс для управления

#### API Endpoints:
- `POST /api/skud/event/` - Прием событий от устройств
- `GET /api/skud/status/` - Статус системы СКУД
- `GET /api/skud/health/` - Проверка здоровья системы
- `GET /api/skud/test/` - Тестовый endpoint

### 2. Интеграция через API (существующая)

В файле `employees/skud_integration.py` настройте параметры:

```python
SKUD_SETTINGS = {
    'API_URL': 'http://your-skud-system.com/api',
    'API_KEY': 'your-api-key',
    'USE_MOCK': False,  # Установите False для реальной интеграции
}
```

### Команды для работы с СКУД

#### Управление СКУД устройствами (НОВОЕ!)

```bash
# Добавить новое устройство
python manage.py manage_skud_devices add --name "Турникет" --ip "192.168.1.100" --serial "SKUD001"

# Тестировать устройства
python manage.py manage_skud_devices test --all

# Синхронизировать время устройств
python manage.py manage_skud_devices sync-time --all

# Получить статус устройств
python manage.py manage_skud_devices status

# Обработать необработанные события
python manage.py manage_skud_devices process-events

# Генерация отчета
python manage.py manage_skud_devices report --date 2024-01-15
```

#### Синхронизация данных (существующая)

```bash
# Синхронизация всех сотрудников на сегодня
python manage.py sync_skud

# Синхронизация конкретного сотрудника
python manage.py sync_skud --employee-id EMP001

# Синхронизация за период
python manage.py sync_skud --date 2024-01-15 --days-back 7

# Принудительная синхронизация
python manage.py sync_skud --force
```

#### Генерация статистики

```bash
# Статистика за текущий месяц
python manage.py employee_stats

# Статистика за период
python manage.py employee_stats --start-date 2024-01-01 --end-date 2024-01-31

# Статистика конкретного сотрудника
python manage.py employee_stats --employee-id EMP001

# Экспорт в файл
python manage.py employee_stats --format csv --output stats.csv
```

## Использование админ-панели

1. Войдите в админ-панель: http://127.0.0.1:8000/admin/
2. Создайте организацию
3. Добавьте департаменты
4. Создайте отделы
5. Добавьте сотрудников
6. Управляйте отпусками и командировками
7. Просматривайте записи рабочего времени

## API для интеграции с СКУД

### Получение логов доступа

```python
from employees.skud_integration import get_skud_integration

skud = get_skud_integration()
logs = skud.get_employee_access_logs('EMP001', start_date, end_date)
```

### Синхронизация рабочего времени

```python
from employees.models import Employee

employee = Employee.objects.get(employee_id='EMP001')
records_count = skud.sync_work_time_records(employee, date.today())
```

### Получение статистики

```python
stats = skud.get_employee_statistics(employee, start_date, end_date)
print(f"Посещаемость: {stats['attendance_rate']}%")
print(f"Общее время: {stats['total_hours']} часов")
```

## Настройки для продакшена

1. Измените `SECRET_KEY` в `settings.py`
2. Установите `DEBUG = False`
3. Настройте базу данных PostgreSQL
4. Добавьте настройки для статических файлов
5. Настройте интеграцию с реальной системой СКУД

## Разработка

### Добавление новых полей

1. Измените модели в `employees/models.py`
2. Создайте миграцию: `python manage.py makemigrations`
3. Примените миграцию: `python manage.py migrate`

### Расширение интеграции с СКУД

1. Модифицируйте класс `SKUDIntegration` в `employees/skud_integration.py`
2. Добавьте новые методы для работы с API СКУД
3. Обновите команды управления при необходимости

## Новые файлы и компоненты

### Модели данных
- `employees/models.py` - Добавлены модели `SKUDDevice` и `SKUDEvent`

### API и коммуникация
- `employees/skud_device_communication.py` - Классы для общения с СКУД устройствами
- `employees/skud_api.py` - API endpoints для приема данных от устройств
- `employees/urls.py` - URL маршруты для API

### Управление и команды
- `employees/management/commands/manage_skud_devices.py` - Команды управления СКУД устройствами
- `employees/admin.py` - Обновленный админ-интерфейс

### Документация и тесты
- `SKUD_INTEGRATION_GUIDE.md` - Подробное руководство по интеграции
- `skud_device_config_example.py` - Пример конфигурации СКУД устройства
- `test_skud_integration.py` - Тестовый скрипт для проверки интеграции

## Быстрый тест системы

После настройки системы можно запустить тестовый скрипт:

```bash
python test_skud_integration.py
```

Скрипт проверит:
- Соединение с сервером
- API endpoints
- Отправку и получение событий
- Симуляцию рабочего дня
