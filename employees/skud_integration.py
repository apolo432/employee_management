"""
Модуль для интеграции с системой СКУД (Система Контроля и Управления Доступом)
"""

import requests
import json
from datetime import datetime, date, time
from typing import List, Dict, Optional
from django.conf import settings
from django.utils import timezone
from .models import Employee, WorkTimeRecord


class SKUDIntegration:
    """Класс для интеграции с системой СКУД"""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def get_employee_access_logs(self, employee_id: str, start_date: date, end_date: date) -> List[Dict]:
        """
        Получение логов доступа сотрудника за период
        
        Args:
            employee_id: ID сотрудника в системе СКУД
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            Список записей доступа
        """
        url = f"{self.api_url}/access-logs"
        params = {
            'employee_id': employee_id,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get('data', [])
        except requests.RequestException as e:
            print(f"Ошибка при получении логов доступа: {e}")
            return []
    
    def sync_work_time_records(self, employee: Employee, sync_date: date = None) -> int:
        """
        Синхронизация записей рабочего времени с СКУД
        
        Args:
            employee: Объект сотрудника
            sync_date: Дата для синхронизации (по умолчанию - сегодня)
            
        Returns:
            Количество обновленных записей
        """
        if sync_date is None:
            sync_date = timezone.now().date()
        
        # Получаем логи доступа из СКУД
        access_logs = self.get_employee_access_logs(
            employee.employee_id, 
            sync_date, 
            sync_date
        )
        
        updated_count = 0
        
        for log in access_logs:
            # Парсим время из лога
            arrival_time = self._parse_time(log.get('arrival_time'))
            departure_time = self._parse_time(log.get('departure_time'))
            
            if arrival_time or departure_time:
                # Создаем или обновляем запись рабочего времени
                work_record, created = WorkTimeRecord.objects.get_or_create(
                    employee=employee,
                    date=sync_date,
                    defaults={
                        'arrival_time': arrival_time,
                        'departure_time': departure_time,
                        'notes': f"Синхронизировано с СКУД: {log.get('device_name', 'Неизвестное устройство')}"
                    }
                )
                
                if not created:
                    # Обновляем существующую запись
                    work_record.arrival_time = arrival_time or work_record.arrival_time
                    work_record.departure_time = departure_time or work_record.departure_time
                    work_record.notes = f"Обновлено из СКУД: {log.get('device_name', 'Неизвестное устройство')}"
                    work_record.save()
                
                updated_count += 1
        
        return updated_count
    
    def sync_all_employees(self, sync_date: date = None) -> Dict[str, int]:
        """
        Синхронизация всех активных сотрудников
        
        Args:
            sync_date: Дата для синхронизации (по умолчанию - сегодня)
            
        Returns:
            Словарь с результатами синхронизации
        """
        if sync_date is None:
            sync_date = timezone.now().date()
        
        active_employees = Employee.objects.filter(is_active=True)
        results = {
            'total_employees': active_employees.count(),
            'synced_employees': 0,
            'total_records': 0,
            'errors': []
        }
        
        for employee in active_employees:
            try:
                records_count = self.sync_work_time_records(employee, sync_date)
                if records_count > 0:
                    results['synced_employees'] += 1
                    results['total_records'] += records_count
            except Exception as e:
                results['errors'].append({
                    'employee_id': employee.employee_id,
                    'error': str(e)
                })
        
        return results
    
    def get_employee_statistics(self, employee: Employee, start_date: date, end_date: date) -> Dict:
        """
        Получение статистики по сотруднику за период
        
        Args:
            employee: Объект сотрудника
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            Словарь со статистикой
        """
        records = WorkTimeRecord.objects.filter(
            employee=employee,
            date__range=[start_date, end_date]
        ).order_by('date')
        
        total_days = (end_date - start_date).days + 1
        present_days = records.filter(is_present=True).count()
        absent_days = total_days - present_days
        
        total_hours = sum(record.total_hours or 0 for record in records if record.total_hours)
        avg_hours_per_day = total_hours / present_days if present_days > 0 else 0
        
        return {
            'employee': employee.full_name,
            'period': f"{start_date} - {end_date}",
            'total_days': total_days,
            'present_days': present_days,
            'absent_days': absent_days,
            'total_hours': round(total_hours, 2),
            'avg_hours_per_day': round(avg_hours_per_day, 2),
            'attendance_rate': round((present_days / total_days) * 100, 2) if total_days > 0 else 0
        }
    
    def _parse_time(self, time_str: str) -> Optional[time]:
        """
        Парсинг времени из строки
        
        Args:
            time_str: Строка с временем
            
        Returns:
            Объект time или None
        """
        if not time_str:
            return None
        
        try:
            # Пробуем разные форматы времени
            formats = ['%H:%M:%S', '%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(time_str, fmt)
                    return dt.time()
                except ValueError:
                    continue
            
            return None
        except Exception:
            return None


class SKUDMockIntegration(SKUDIntegration):
    """
    Мок-класс для тестирования интеграции с СКУД
    Использует фиктивные данные вместо реального API
    """
    
    def get_employee_access_logs(self, employee_id: str, start_date: date, end_date: date) -> List[Dict]:
        """Мок-данные для тестирования"""
        import random
        from datetime import timedelta
        
        logs = []
        current_date = start_date
        
        while current_date <= end_date:
            # Генерируем случайные данные для тестирования
            if random.choice([True, False]):  # 50% вероятность присутствия
                arrival_hour = random.randint(8, 10)
                arrival_minute = random.randint(0, 59)
                departure_hour = random.randint(17, 19)
                departure_minute = random.randint(0, 59)
                
                logs.append({
                    'employee_id': employee_id,
                    'date': current_date.isoformat(),
                    'arrival_time': f"{arrival_hour:02d}:{arrival_minute:02d}:00",
                    'departure_time': f"{departure_hour:02d}:{departure_minute:02d}:00",
                    'device_name': f"Терминал {random.randint(1, 5)}"
                })
            
            current_date += timedelta(days=1)
        
        return logs


# Настройки интеграции (можно вынести в settings.py)
SKUD_SETTINGS = {
    'API_URL': getattr(settings, 'SKUD_API_URL', 'http://localhost:8000/api/skud'),
    'API_KEY': getattr(settings, 'SKUD_API_KEY', 'test-api-key'),
    'USE_MOCK': getattr(settings, 'SKUD_USE_MOCK', True),  # Для разработки
}


def get_skud_integration() -> SKUDIntegration:
    """
    Фабричная функция для получения экземпляра интеграции с СКУД
    
    Returns:
        Экземпляр класса интеграции
    """
    if SKUD_SETTINGS['USE_MOCK']:
        return SKUDMockIntegration(
            SKUD_SETTINGS['API_URL'],
            SKUD_SETTINGS['API_KEY']
        )
    else:
        return SKUDIntegration(
            SKUD_SETTINGS['API_URL'],
            SKUD_SETTINGS['API_KEY']
        )
