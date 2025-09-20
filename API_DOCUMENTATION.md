# REST API Документация - Система учёта рабочего времени

## Общая информация

Базовый URL: `http://localhost:8000/api/worktime/`

### Аутентификация
- **Session Authentication** - для веб-интерфейса
- **Token Authentication** - для внешних интеграций
- Получить токен: `POST /api/auth/token/` с логином/паролем

### Права доступа
- **Обычные пользователи**: видят только свои данные
- **Администраторы**: полный доступ ко всем данным

### Общие возможности
- **Фильтрация**: `?field=value`
- **Поиск**: `?search=query`
- **Сортировка**: `?ordering=field` или `?ordering=-field`
- **Пагинация**: автоматическая (20 записей на страницу)

---

## Endpoints

### 1. Рабочие сессии (`/sessions/`)

#### GET `/sessions/` - Список сессий
**Фильтры:**
- `employee` - ID сотрудника
- `date` - Дата сессии
- `status` - Статус (auto, manual, open, closed_manual)
- `is_open` - Открытые сессии (true/false)

**Пример:**
```bash
GET /api/worktime/sessions/?employee=123&date=2025-09-19&status=open
```

#### GET `/sessions/{id}/` - Детали сессии
**Ответ:**
```json
{
  "id": "uuid",
  "employee": "uuid",
  "employee_name": "Иванов Иван Иванович",
  "date": "2025-09-19",
  "start_time": "2025-09-19T09:00:00Z",
  "end_time": "2025-09-19T17:00:00Z",
  "duration_seconds": 28800,
  "duration_hours": 8.0,
  "status": "auto",
  "status_display": "Автоматическая",
  "is_open": false,
  "manual_reason": "",
  "corrected_by": null,
  "created_at": "2025-09-19T09:00:00Z"
}
```

#### POST `/sessions/` - Создание сессии (только админ)
**Тело запроса:**
```json
{
  "employee": "uuid",
  "date": "2025-09-19",
  "start_time": "2025-09-19T09:00:00Z",
  "end_time": "2025-09-19T17:00:00Z",
  "status": "manual",
  "manual_reason": "Причина создания"
}
```

#### POST `/sessions/close_open_sessions/` - Закрытие открытых сессий (админ)
**Тело запроса:**
```json
{
  "employee_id": "uuid",
  "date": "2025-09-19",
  "reason": "Закрыто через API"
}
```

#### GET `/sessions/employee_sessions/` - Сессии сотрудника
**Параметры:**
- `employee_id` - ID сотрудника (обязательный)
- `from_date` - Дата начала периода
- `to_date` - Дата окончания периода

---

### 2. Сводки рабочих дней (`/summaries/`)

#### GET `/summaries/` - Список сводок
**Фильтры:**
- `employee` - ID сотрудника
- `date` - Дата
- `status` - Статус (present, absent, excused, partial, problem)
- `has_missing_exit` - Есть незакрытые сессии
- `has_manual_corrections` - Есть ручные корректировки

#### GET `/summaries/{id}/` - Детали сводки
**Ответ:**
```json
{
  "id": "uuid",
  "employee": "uuid",
  "employee_name": "Иванов Иван Иванович",
  "date": "2025-09-19",
  "first_entry": "2025-09-19T09:00:00Z",
  "last_exit": "2025-09-19T17:00:00Z",
  "total_seconds_in_office": 28800,
  "total_hours": 8.0,
  "expected_seconds": 28800,
  "expected_hours": 8.0,
  "overtime_seconds": 0,
  "overtime_hours": 0,
  "underwork_seconds": 0,
  "underwork_hours": 0,
  "sessions_count": 1,
  "status": "present",
  "status_display": "Присутствовал",
  "has_missing_exit": false,
  "has_manual_corrections": false
}
```

#### GET `/summaries/employee_summary/` - Сводка сотрудника за период
**Параметры:**
- `employee_id` - ID сотрудника (обязательный)
- `from_date` - Дата начала (обязательный)
- `to_date` - Дата окончания (обязательный)

#### GET `/summaries/department_stats/` - Статистика отдела
**Параметры:**
- `department_id` - ID отдела (обязательный)
- `from_date` - Дата начала (обязательный)
- `to_date` - Дата окончания (обязательный)

**Ответ:**
```json
{
  "department_name": "IT отдел",
  "period_start": "2025-09-01",
  "period_end": "2025-09-30",
  "total_employees": 10,
  "total_days": 30,
  "total_hours_worked": 1600.0,
  "total_hours_expected": 1600.0,
  "average_hours_per_employee": 160.0,
  "work_efficiency_percent": 100.0,
  "problem_days_count": 2
}
```

---

### 3. Сотрудники (`/employees/`)

#### GET `/employees/` - Список сотрудников
**Фильтры:**
- `department` - ID отдела
- `division` - ID подразделения
- `position` - Должность
- `work_fraction` - Ставка работы

#### GET `/employees/{id}/` - Детали сотрудника
**Ответ:**
```json
{
  "id": "uuid",
  "last_name": "Иванов",
  "first_name": "Иван",
  "middle_name": "Иванович",
  "full_name": "Иванов Иван Иванович",
  "birth_date": "1990-01-01",
  "age": 35,
  "gender": "M",
  "phone": "+7900123456",
  "email": "ivan@example.com",
  "organization": "uuid",
  "department": "uuid",
  "department_name": "IT отдел",
  "division": "uuid",
  "division_name": "Разработка",
  "position": "specialist",
  "employee_id": "EMP001",
  "hire_date": "2020-01-01",
  "termination_date": null,
  "is_active": true,
  "work_fraction": "1.00",
  "daily_hours": "8.00",
  "created_at": "2020-01-01T00:00:00Z"
}
```

#### GET `/employees/{id}/work_time_stats/` - Статистика рабочего времени
**Параметры:**
- `from_date` - Дата начала (обязательный)
- `to_date` - Дата окончания (обязательный)

**Ответ:**
```json
{
  "employee": {...},
  "period_start": "2025-09-01",
  "period_end": "2025-09-30",
  "total_days": 30,
  "present_days": 25,
  "absent_days": 2,
  "excused_days": 3,
  "problem_days": 0,
  "total_hours_worked": 200.0,
  "total_hours_expected": 200.0,
  "total_overtime_hours": 5.0,
  "total_underwork_hours": 0.0,
  "average_hours_per_day": 8.0,
  "work_efficiency_percent": 100.0
}
```

---

### 4. Обработка данных (`/processor/`)

#### POST `/processor/reprocess/` - Пересчёт данных (админ)
**Варианты использования:**

1. **Пересчёт конкретного сотрудника на дату:**
```json
{
  "employee_id": "uuid",
  "date": "2025-09-19"
}
```

2. **Пересчёт сотрудника за период:**
```json
{
  "employee_id": "uuid",
  "from_date": "2025-09-01",
  "to_date": "2025-09-30"
}
```

3. **Пересчёт всех сотрудников на дату:**
```json
{
  "date": "2025-09-19"
}
```

4. **Пересчёт всех сотрудников за период:**
```json
{
  "from_date": "2025-09-01",
  "to_date": "2025-09-30"
}
```

---

### 5. Аудит изменений (`/audit-logs/`)

#### GET `/audit-logs/` - История изменений
**Фильтры:**
- `employee` - ID сотрудника
- `action` - Тип действия
- `changed_by` - Кто изменил

**Ответ:**
```json
{
  "id": "uuid",
  "employee": "uuid",
  "employee_name": "Иванов Иван Иванович",
  "date": "2025-09-19",
  "action": "edit_session",
  "action_display": "Редактирование сессии",
  "description": "Изменено время окончания сессии",
  "old_value": {"end_time": "2025-09-19T16:00:00Z"},
  "new_value": {"end_time": "2025-09-19T17:00:00Z"},
  "reason": "Исправление времени ухода",
  "changed_by": "uuid",
  "changed_by_name": "admin",
  "changed_at": "2025-09-19T18:00:00Z"
}
```

---

### 6. События СКУД (`/skud-events/`)

#### GET `/skud-events/` - Список событий
**Фильтры:**
- `device` - ID устройства
- `employee` - ID сотрудника
- `event_type` - Тип события (entry, exit, denied, alarm)
- `is_processed` - Обработано (true/false)

---

### 7. Устройства СКУД (`/skud-devices/`)

#### GET `/skud-devices/` - Список устройств
**Фильтры:**
- `device_type` - Тип устройства
- `status` - Статус
- `is_active` - Активно (true/false)

---

## Примеры использования

### Получение статистики сотрудника за месяц
```bash
curl -H "Authorization: Token your_token_here" \
     "http://localhost:8000/api/worktime/employees/123/work_time_stats/?from_date=2025-09-01&to_date=2025-09-30"
```

### Закрытие открытых сессий
```bash
curl -X POST \
     -H "Authorization: Token your_token_here" \
     -H "Content-Type: application/json" \
     -d '{"employee_id": "123", "reason": "Закрыто через API"}' \
     "http://localhost:8000/api/worktime/sessions/close_open_sessions/"
```

### Пересчёт данных за период
```bash
curl -X POST \
     -H "Authorization: Token your_token_here" \
     -H "Content-Type: application/json" \
     -d '{"from_date": "2025-09-01", "to_date": "2025-09-30"}' \
     "http://localhost:8000/api/worktime/processor/reprocess/"
```

---

## Коды ошибок

- `400 Bad Request` - Неверные параметры запроса
- `401 Unauthorized` - Требуется аутентификация
- `403 Forbidden` - Недостаточно прав
- `404 Not Found` - Ресурс не найден
- `500 Internal Server Error` - Внутренняя ошибка сервера

---

## Примечания

1. Все даты передаются в формате ISO 8601: `YYYY-MM-DD` или `YYYY-MM-DDTHH:MM:SSZ`
2. UUID поля должны передаваться как строки
3. Decimal поля (ставки, часы) передаются как строки
4. Булевы поля передаются как `true`/`false`
5. Все ответы содержат пагинацию при необходимости
6. Поиск работает по полям, указанным в `search_fields` каждого ViewSet
