"""
Тестовый скрипт для проверки интеграции с СКУД системой
"""

import requests
import json
import time
from datetime import datetime, timedelta
import random

# Настройки тестирования
SERVER_URL = "http://localhost:8000"
API_BASE = f"{SERVER_URL}/api/skud"

# Тестовые данные
TEST_EMPLOYEES = [
    {"employee_id": "EMP001", "name": "Иванов Иван Иванович"},
    {"employee_id": "EMP002", "name": "Петров Петр Петрович"},
    {"employee_id": "EMP003", "name": "Сидоров Сидор Сидорович"},
    {"employee_id": "EMP004", "name": "Козлова Анна Сергеевна"},
    {"employee_id": "EMP005", "name": "Смирнова Елена Владимировна"},
]

TEST_DEVICES = [
    {"ip": "192.168.1.100", "name": "Турникет главный вход", "serial": "SKUD001"},
    {"ip": "192.168.1.101", "name": "Считыватель офис", "serial": "SKUD002"},
    {"ip": "192.168.1.102", "name": "Контроллер склад", "serial": "SKUD003"},
]


def test_server_connection():
    """Тест соединения с сервером"""
    print("🔍 Тестирование соединения с сервером...")
    
    try:
        response = requests.get(f"{API_BASE}/test/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Сервер доступен: {data['message']}")
            print(f"   Время сервера: {data['server_time']}")
            return True
        else:
            print(f"❌ Ошибка сервера: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка соединения: {e}")
        return False


def test_health_check():
    """Тест проверки здоровья системы"""
    print("\n🏥 Тестирование проверки здоровья системы...")
    
    try:
        response = requests.get(f"{API_BASE}/health/")
        if response.status_code == 200:
            data = response.json()
            health = data['health']
            print(f"✅ Общий статус: {health['overall_status']}")
            print(f"   Устройств всего: {health['total_devices']}")
            print(f"   Устройств онлайн: {health['online_devices']}")
            print(f"   Необработанных событий: {health['unprocessed_events']}")
            return True
        else:
            print(f"❌ Ошибка проверки здоровья: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка соединения: {e}")
        return False


def test_event_sending():
    """Тест отправки событий"""
    print("\n📤 Тестирование отправки событий...")
    
    success_count = 0
    total_count = 0
    
    for device in TEST_DEVICES:
        for employee in TEST_EMPLOYEES:
            # Случайный тип события
            event_type = random.choice(['entry', 'exit'])
            
            # Время события (в пределах последних 24 часов)
            event_time = datetime.now() - timedelta(
                hours=random.randint(0, 24),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            
            event_data = {
                "card_number": employee["employee_id"],
                "event_type": event_type,
                "timestamp": event_time.isoformat(),
                "device_info": {
                    "serial_number": device["serial"],
                    "model": "TestDevice-1000",
                    "firmware": "1.0.0",
                    "location": device["name"]
                }
            }
            
            try:
                # Имитируем запрос от устройства по его IP
                headers = {'X-Forwarded-For': device["ip"]}
                
                response = requests.post(
                    f"{API_BASE}/event/",
                    json=event_data,
                    headers=headers,
                    timeout=5
                )
                
                total_count += 1
                
                if response.status_code == 200:
                    result = response.json()
                    if result['status'] == 'success':
                        print(f"✅ {employee['name']} - {event_type} через {device['name']}")
                        success_count += 1
                    else:
                        print(f"⚠️  {employee['name']} - ошибка: {result['message']}")
                else:
                    print(f"❌ {employee['name']} - HTTP ошибка: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ {employee['name']} - ошибка соединения: {e}")
                total_count += 1
    
    print(f"\n📊 Результаты отправки событий:")
    print(f"   Успешно отправлено: {success_count}/{total_count}")
    print(f"   Процент успеха: {(success_count/total_count)*100:.1f}%")
    
    return success_count > 0


def test_events_retrieval():
    """Тест получения событий"""
    print("\n📥 Тестирование получения событий...")
    
    try:
        # Получаем события за последние 24 часа
        response = requests.get(f"{API_BASE}/events/?hours=24")
        
        if response.status_code == 200:
            data = response.json()
            events = data['events']
            print(f"✅ Получено событий: {len(events)}")
            
            if events:
                print("   Последние события:")
                for event in events[:5]:  # Показываем первые 5
                    print(f"   - {event['event_time']} | {event['employee_name']} | {event['event_type']} | {event['device_name']}")
            
            return True
        else:
            print(f"❌ Ошибка получения событий: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка соединения: {e}")
        return False


def test_status_endpoint():
    """Тест endpoint статуса"""
    print("\n📊 Тестирование endpoint статуса...")
    
    try:
        response = requests.get(f"{API_BASE}/status/")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Статус получен")
            print(f"   Время сервера: {data['server_time']}")
            print(f"   Устройств всего: {data['total_devices']}")
            print(f"   Устройств онлайн: {data['online_devices']}")
            
            if data['devices']:
                print("   Статус устройств:")
                for ip, device_status in data['devices'].items():
                    status_icon = "✅" if device_status['is_online'] else "❌"
                    print(f"   {status_icon} {device_status['device_name']} ({ip})")
            
            return True
        else:
            print(f"❌ Ошибка получения статуса: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка соединения: {e}")
        return False


def simulate_workday():
    """Симуляция рабочего дня"""
    print("\n🏢 Симуляция рабочего дня...")
    
    # Время начала и окончания рабочего дня
    work_start = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    work_end = datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)
    
    events_sent = 0
    
    for employee in TEST_EMPLOYEES:
        # Время прихода (8:00-9:30)
        arrival_time = work_start + timedelta(
            minutes=random.randint(0, 90)
        )
        
        # Время ухода (17:00-18:30)
        departure_time = work_end + timedelta(
            minutes=random.randint(-60, 30)
        )
        
        # Выбираем случайное устройство
        device = random.choice(TEST_DEVICES)
        
        # Событие прихода
        arrival_event = {
            "card_number": employee["employee_id"],
            "event_type": "entry",
            "timestamp": arrival_time.isoformat(),
            "device_info": {
                "serial_number": device["serial"],
                "model": "TestDevice-1000",
                "firmware": "1.0.0",
                "location": device["name"]
            }
        }
        
        # Событие ухода
        departure_event = {
            "card_number": employee["employee_id"],
            "event_type": "exit",
            "timestamp": departure_time.isoformat(),
            "device_info": {
                "serial_number": device["serial"],
                "model": "TestDevice-1000",
                "firmware": "1.0.0",
                "location": device["name"]
            }
        }
        
        # Отправляем события
        headers = {'X-Forwarded-For': device["ip"]}
        
        try:
            # Приход
            response = requests.post(
                f"{API_BASE}/event/",
                json=arrival_event,
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                events_sent += 1
            
            # Уход
            response = requests.post(
                f"{API_BASE}/event/",
                json=departure_event,
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                events_sent += 1
                
            print(f"✅ {employee['name']}: {arrival_time.strftime('%H:%M')} - {departure_time.strftime('%H:%M')}")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ {employee['name']}: ошибка отправки - {e}")
    
    print(f"\n📊 Симуляция завершена: отправлено {events_sent} событий")
    return events_sent > 0


def main():
    """Основная функция тестирования"""
    print("🧪 ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ С СКУД СИСТЕМОЙ")
    print("=" * 50)
    
    tests = [
        ("Соединение с сервером", test_server_connection),
        ("Проверка здоровья", test_health_check),
        ("Отправка событий", test_event_sending),
        ("Получение событий", test_events_retrieval),
        ("Endpoint статуса", test_status_endpoint),
        ("Симуляция рабочего дня", simulate_workday),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Ошибка в тесте '{test_name}': {e}")
            results.append((test_name, False))
    
    # Итоговый отчет
    print("\n" + "=" * 50)
    print("📋 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Результат: {passed}/{len(results)} тестов пройдено")
    
    if passed == len(results):
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        print("⚠️  Некоторые тесты провалены. Проверьте настройки системы.")


if __name__ == "__main__":
    main()
