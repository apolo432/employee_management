"""
Пример конфигурации для СКУД устройства
Этот файл показывает, как настроить СКУД устройство для отправки данных на сервер
"""

# Пример конфигурации СКУД устройства
SKUD_DEVICE_CONFIG = {
    # Настройки сервера
    'server': {
        'ip': '192.168.1.50',  # IP адрес Django сервера
        'port': 8000,          # Порт Django сервера
        'api_url': 'http://192.168.1.50:8000/api/skud/event/',
        'timeout': 10,         # Таймаут соединения в секундах
    },
    
    # Настройки устройства
    'device': {
        'serial_number': 'SKUD001',
        'model': 'Turnstile-2000',
        'firmware_version': '1.2.3',
        'location': 'Главный вход',
    },
    
    # Настройки связи
    'communication': {
        'retry_attempts': 3,    # Количество попыток повторной отправки
        'retry_delay': 5,       # Задержка между попытками в секундах
        'heartbeat_interval': 60,  # Интервал отправки heartbeat в секундах
        'batch_size': 10,       # Размер батча для групповой отправки
    },
    
    # Настройки данных
    'data': {
        'include_timestamp': True,
        'include_device_info': True,
        'compress_data': False,
        'encryption': False,
    }
}

# Пример функции отправки события на сервер
def send_event_to_server(card_number, event_type, timestamp=None):
    """
    Функция для отправки события от СКУД устройства на сервер
    
    Args:
        card_number: Номер карты/кода сотрудника
        event_type: Тип события ('entry', 'exit', 'denied', 'alarm')
        timestamp: Время события (если не указано, используется текущее время)
    """
    import requests
    import json
    from datetime import datetime
    
    # Подготавливаем данные
    event_data = {
        'card_number': card_number,
        'event_type': event_type,
        'timestamp': timestamp or datetime.now().isoformat(),
        'device_info': {
            'serial_number': SKUD_DEVICE_CONFIG['device']['serial_number'],
            'model': SKUD_DEVICE_CONFIG['device']['model'],
            'firmware': SKUD_DEVICE_CONFIG['device']['firmware_version'],
            'location': SKUD_DEVICE_CONFIG['device']['location']
        }
    }
    
    # Отправляем данные на сервер
    try:
        response = requests.post(
            SKUD_DEVICE_CONFIG['server']['api_url'],
            json=event_data,
            timeout=SKUD_DEVICE_CONFIG['server']['timeout']
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['status'] == 'success':
                print(f"Событие успешно отправлено: {card_number} - {event_type}")
                return True
            else:
                print(f"Ошибка сервера: {result['message']}")
                return False
        else:
            print(f"HTTP ошибка: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Ошибка соединения: {e}")
        return False

# Пример использования
if __name__ == "__main__":
    # Отправляем событие входа
    send_event_to_server("EMP001", "entry")
    
    # Отправляем событие выхода
    send_event_to_server("EMP001", "exit")
    
    # Отправляем событие отказа в доступе
    send_event_to_server("EMP002", "denied")

# Пример JSON данных, которые должны отправляться от СКУД устройства
EXAMPLE_EVENT_DATA = {
    "card_number": "EMP001",
    "event_type": "entry",
    "timestamp": "2024-01-15T09:30:00",
    "direction": "in",
    "device_info": {
        "serial_number": "SKUD001",
        "model": "Turnstile-2000",
        "firmware": "1.2.3",
        "location": "Главный вход"
    }
}

# Пример конфигурации для разных типов СКУД устройств

# Турникет
TURNSTILE_CONFIG = {
    'device_type': 'turnstile',
    'supported_events': ['entry', 'exit'],
    'card_types': ['rfid', 'nfc', 'barcode'],
    'anti_passback': True,  # Запрет повторного прохода
    'alarm_on_tailgating': True,  # Тревога при проходе "в хвост"
}

# Считыватель карт
READER_CONFIG = {
    'device_type': 'reader',
    'supported_events': ['entry', 'exit', 'denied'],
    'card_types': ['rfid', 'nfc', 'magnetic'],
    'pin_entry': True,  # Поддержка PIN кода
    'biometric': False,  # Биометрическая аутентификация
}

# Контроллер доступа
CONTROLLER_CONFIG = {
    'device_type': 'controller',
    'supported_events': ['entry', 'exit', 'denied', 'alarm'],
    'card_types': ['rfid', 'nfc', 'magnetic', 'proximity'],
    'multi_reader': True,  # Поддержка нескольких считывателей
    'relay_control': True,  # Управление реле
    'alarm_inputs': 4,     # Количество входов тревоги
}

# Пример настройки устройства для автоматической отправки данных
AUTO_SEND_CONFIG = {
    'enable_auto_send': True,
    'send_immediately': True,  # Отправлять сразу или батчами
    'max_batch_size': 10,
    'batch_timeout': 30,  # Таймаут для батча в секундах
    'retry_failed': True,
    'max_retries': 3,
}

# Пример обработки ошибок
ERROR_HANDLING_CONFIG = {
    'log_errors': True,
    'store_failed_events': True,  # Сохранять неудачные события локально
    'max_stored_events': 1000,
    'auto_retry_failed': True,
    'retry_interval': 300,  # Интервал повторных попыток в секундах
}
