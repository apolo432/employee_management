# 🔧 Developer Checklist

## ✅ Проверка логики СКУД системы

### 1. **Запуск сервера**
```bash
python manage.py runserver 8000
```

### 2. **Тест главной страницы**
- Открой: `http://127.0.0.1:8000/`
- Время загрузки: < 1 сек ✅
- Статистика отображается ✅

### 3. **Тест устройств**
```bash
# Проверка через API
curl -X GET "http://127.0.0.1:8000/test-device/414ad182-3ab8-432e-be21-66b7879a714e/"

# Ожидаемый результат:
{"success": true, "message": "Тестовое устройство: соединение установлено (имитация)"}
```

### 4. **Тест через фронтенд**
- На главной странице нажми "Проверить" в секции "Устройства"
- Должно показать: "Статус устройств обновлен" ✅

### 5. **Проверка кэширования**
```bash
# Первый запрос (создает кэш)
curl -X GET "http://127.0.0.1:8000/api/status/"

# Второй запрос (из кэша)
curl -X GET "http://127.0.0.1:8000/api/status/"

# Должен быть быстрее
```

### 6. **Тест отправки события**
```bash
curl -X POST "http://127.0.0.1:8000/api/skud/event/" \
  -H "Content-Type: application/json" \
  -d '{
    "card_number": "12345",
    "event_type": "entry",
    "timestamp": "2025-09-18T10:00:00"
  }'

# Ожидаемый результат: 201 Created
```

### 7. **Проверка базы данных**
```bash
python manage.py shell -c "
from employees.models import SKUDDevice, SKUDEvent
print(f'Устройств: {SKUDDevice.objects.count()}')
print(f'Событий: {SKUDEvent.objects.count()}')
print(f'Активных устройств: {SKUDDevice.objects.filter(status=\"active\").count()}')
"
```

## 🎯 Критерии успеха

- ✅ Главная страница загружается < 1 сек
- ✅ Тестовые устройства показывают "онлайн"
- ✅ API возвращает корректные JSON ответы
- ✅ Кэширование работает (второй запрос быстрее)
- ✅ События создаются в БД
- ✅ Нет ошибок в логах сервера

## 🚨 Если что-то не работает

1. **Проверь логи сервера** - нет ли ошибок 500
2. **Очисти кэш**: `python manage.py shell -c "from django.core.cache import cache; cache.clear()"`
3. **Перезапусти сервер**: Ctrl+C → `python manage.py runserver 8000`
4. **Проверь БД**: `python manage.py shell -c "from employees.models import *; print('OK')"`
