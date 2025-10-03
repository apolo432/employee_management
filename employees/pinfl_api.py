"""
API интеграция с SKUD PINFL сервисом
"""

import requests
import logging
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class PINFLAPIClient:
    """Клиент для работы с SKUD PINFL API"""
    
    def __init__(self):
        self.base_url = "https://apiskud.miit.uz/site/pinfl"
        self.login = "api-pinfl"
        self.password = "5+ihav9&3&W)(RNz"
        self.timeout = 30  # секунд
    
    def sync_employee_pinfl(self, employee, pinfl, date=None):
        """
        Синхронизация PINFL сотрудника с SKUD API
        
        Args:
            employee: Объект Employee
            pinfl: PINFL номер (14 цифр)
            date: Дата для синхронизации (по умолчанию сегодня)
        
        Returns:
            dict: Результат синхронизации
        """
        if date is None:
            date = timezone.now().date()
        
        # Подготавливаем данные для API
        payload = {
            "login": employee.user.username if employee.user else employee.employee_id,
            "password": "default_password",  # В реальном проекте нужна логика для пароля
            "pinfl": pinfl,
            "date": date.strftime("%d-%m-%Y")
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            logger.info(f"Отправка PINFL синхронизации для сотрудника {employee.full_name} (PINFL: {pinfl})")
            
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            # Логируем ответ
            logger.info(f"Ответ SKUD API: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                # Успешная синхронизация
                result = {
                    "success": True,
                    "message": "PINFL успешно синхронизирован с SKUD",
                    "employee_id": str(employee.id),
                    "pinfl": pinfl,
                    "skud_response": response.json() if response.content else None,
                    "synced_at": timezone.now().isoformat()
                }
                
                # Обновляем PINFL в базе данных
                employee.pinfl = pinfl
                employee.save(update_fields=['pinfl'])
                
                logger.info(f"PINFL {pinfl} успешно синхронизирован для сотрудника {employee.full_name}")
                return result
            
            else:
                # Ошибка API
                error_message = f"Ошибка SKUD API: {response.status_code}"
                try:
                    error_data = response.json()
                    error_message += f" - {error_data.get('message', 'Неизвестная ошибка')}"
                except:
                    error_message += f" - {response.text}"
                
                result = {
                    "success": False,
                    "message": "Ошибка при синхронизации с SKUD API",
                    "employee_id": str(employee.id),
                    "pinfl": pinfl,
                    "error_details": error_message,
                    "skud_response": {
                        "status_code": response.status_code,
                        "response_text": response.text
                    }
                }
                
                logger.error(f"Ошибка синхронизации PINFL для {employee.full_name}: {error_message}")
                return result
                
        except requests.exceptions.Timeout:
            error_message = "Превышено время ожидания ответа от SKUD API"
            result = {
                "success": False,
                "message": "Ошибка подключения к SKUD API",
                "employee_id": str(employee.id),
                "pinfl": pinfl,
                "error_details": error_message
            }
            logger.error(f"Timeout при синхронизации PINFL для {employee.full_name}")
            return result
            
        except requests.exceptions.ConnectionError:
            error_message = "Ошибка подключения к SKUD API"
            result = {
                "success": False,
                "message": "Ошибка подключения к SKUD API",
                "employee_id": str(employee.id),
                "pinfl": pinfl,
                "error_details": error_message
            }
            logger.error(f"Connection error при синхронизации PINFL для {employee.full_name}")
            return result
            
        except Exception as e:
            error_message = f"Неожиданная ошибка: {str(e)}"
            result = {
                "success": False,
                "message": "Внутренняя ошибка сервера",
                "employee_id": str(employee.id),
                "pinfl": pinfl,
                "error_details": error_message
            }
            logger.error(f"Неожиданная ошибка при синхронизации PINFL для {employee.full_name}: {str(e)}")
            return result
    
    def get_employee_data(self, pinfl, date=None):
        """
        Получение данных сотрудника по PINFL из SKUD API
        
        Args:
            pinfl: PINFL номер сотрудника (14 цифр)
            date: Дата для запроса (по умолчанию сегодня)
        
        Returns:
            dict: Данные сотрудника или сообщение об ошибке
        """
        if date is None:
            date = timezone.now().date()
        
        # Валидация PINFL
        is_valid, error_msg = self.validate_pinfl_format(pinfl)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg,
                "data": None
            }
        
        # Подготавливаем данные для API
        payload = {
            "login": self.login,
            "password": self.password,
            "pinfl": pinfl,
            "date": date.strftime("%d-%m-%Y")
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"Запрос данных сотрудника по PINFL: {pinfl}")
            
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            # Логируем ответ
            logger.info(f"Ответ SKUD API: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    api_response = response.json()
                    
                    # API возвращает данные в поле 'result'
                    api_data = api_response.get("result", {})
                    
                    # Парсим ФИО (формат: "Фамилия Имя Отчество")
                    fio = api_data.get("fio", "")
                    first_name = ""
                    last_name = ""
                    middle_name = ""
                    
                    if fio:
                        fio_parts = fio.split()
                        if len(fio_parts) >= 1:
                            last_name = fio_parts[0]
                        if len(fio_parts) >= 2:
                            first_name = fio_parts[1]
                        if len(fio_parts) >= 3:
                            middle_name = " ".join(fio_parts[2:])
                    
                    # Обрабатываем рабочее время
                    work_duration = api_data.get("work_duration", {})
                    work_start_time = ""
                    work_end_time = ""
                    
                    if work_duration:
                        hours = work_duration.get("hour", 0)
                        minutes = work_duration.get("minute", 0)
                        # Предполагаем стандартное время начала работы 9:00
                        from datetime import datetime, time, timedelta
                        start_time = time(9, 0)
                        # Преобразуем время в datetime для вычислений
                        start_datetime = datetime.combine(datetime.today(), start_time)
                        duration = timedelta(hours=hours, minutes=minutes)
                        end_datetime = start_datetime + duration
                        end_time = end_datetime.time()
                        work_start_time = start_time.strftime("%H:%M:%S")
                        work_end_time = end_time.strftime("%H:%M:%S")
                    
                    # Извлекаем нужные поля
                    employee_data = {
                        "success": True,
                        "error": None,
                        "data": {
                            "fio": fio,
                            "id": api_data.get("pinfl", ""),  # Используем PINFL как ID
                            "first_name": first_name,
                            "last_name": last_name,
                            "middle_name": middle_name,
                            "work_start_time": work_start_time,
                            "work_end_time": work_end_time,
                            "birth_date": "",  # API не предоставляет дату рождения
                            "avatar": api_data.get("avatar", ""),  # Дополнительное поле
                            "pinfl": api_data.get("pinfl", ""),  # Дополнительное поле
                            "work_duration_hours": work_duration.get("hour", 0) if work_duration else 0,
                            "work_duration_minutes": work_duration.get("minute", 0) if work_duration else 0
                        }
                    }
                    
                    # Опционально: обновляем существующего сотрудника если он найден по PINFL
                    try:
                        from .models import Employee
                        employee = Employee.objects.filter(pinfl=pinfl).first()
                        if employee:
                            employee.update_from_api_data(employee_data["data"])
                            employee_data["employee_updated"] = True
                            employee_data["employee_id"] = str(employee.id)
                            employee_data["employee_found"] = True
                        else:
                            employee_data["employee_found"] = False
                            employee_data["message"] = f"Сотрудник с PINFL {pinfl} не найден в локальной базе данных. Данные получены из СКУД, но сотрудник не был обновлен."
                    except Exception as e:
                        logger.warning(f"Не удалось обновить сотрудника по PINFL {pinfl}: {str(e)}")
                        employee_data["employee_found"] = False
                        employee_data["update_error"] = str(e)
                    
                    logger.info(f"Данные сотрудника успешно получены для PINFL: {pinfl}")
                    return employee_data
                    
                except ValueError as e:
                    error_msg = "Ошибка парсинга JSON ответа от API"
                    logger.error(f"{error_msg}: {str(e)}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "data": None
                    }
            else:
                # Ошибка API
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', f'Ошибка API: {response.status_code}')
                except:
                    error_msg = f'Ошибка API: {response.status_code} - {response.text}'
                
                logger.error(f"Ошибка API при получении данных сотрудника: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "data": None
                }
                
        except requests.exceptions.Timeout:
            error_msg = "Превышено время ожидания ответа от API"
            logger.error(f"Timeout при получении данных сотрудника по PINFL: {pinfl}")
            return {
                "success": False,
                "error": error_msg,
                "data": None
            }
            
        except requests.exceptions.ConnectionError:
            error_msg = "Ошибка подключения к API"
            logger.error(f"Connection error при получении данных сотрудника по PINFL: {pinfl}")
            return {
                "success": False,
                "error": error_msg,
                "data": None
            }
            
        except Exception as e:
            error_msg = f"Неожиданная ошибка: {str(e)}"
            logger.error(f"Неожиданная ошибка при получении данных сотрудника по PINFL {pinfl}: {str(e)}")
            return {
                "success": False,
                "error": error_msg,
                "data": None
            }
    
    def sync_employee_by_pinfl(self, pinfl, date=None):
        """
        Синхронизация сотрудника по PINFL с внешним API
        
        Args:
            pinfl: PINFL номер сотрудника
            date: Дата для запроса (по умолчанию сегодня)
        
        Returns:
            dict: Результат синхронизации
        """
        try:
            from .models import Employee
            
            # Ищем сотрудника по PINFL
            employee = Employee.objects.filter(pinfl=pinfl).first()
            
            if not employee:
                return {
                    "success": False,
                    "error": f"Сотрудник с PINFL {pinfl} не найден в базе данных",
                    "employee_id": None
                }
            
            # Получаем данные из API
            api_result = self.get_employee_data(pinfl, date)
            
            if api_result["success"]:
                # Обновляем данные сотрудника
                employee.update_from_api_data(api_result["data"])
                
                return {
                    "success": True,
                    "message": f"Сотрудник {employee.full_name} успешно синхронизирован",
                    "employee_id": str(employee.id),
                    "data": api_result["data"]
                }
            else:
                return {
                    "success": False,
                    "error": api_result["error"],
                    "employee_id": str(employee.id)
                }
                
        except Exception as e:
            error_msg = f"Ошибка синхронизации сотрудника: {str(e)}"
            logger.error(f"Ошибка синхронизации сотрудника по PINFL {pinfl}: {str(e)}")
            return {
                "success": False,
                "error": error_msg,
                "employee_id": None
            }
    
    def create_employee_from_api(self, pinfl, date=None):
        """
        Создание нового сотрудника из данных API СКУД
        
        Args:
            pinfl: PINFL номер сотрудника
            date: Дата для запроса (по умолчанию сегодня)
        
        Returns:
            dict: Результат создания сотрудника
        """
        try:
            from .models import Employee, Organization, Department, Division
            
            # Проверяем, не существует ли уже сотрудник
            existing_employee = Employee.objects.filter(pinfl=pinfl).first()
            if existing_employee:
                return {
                    "success": False,
                    "error": f"Сотрудник с PINFL {pinfl} уже существует в базе данных",
                    "employee_id": str(existing_employee.id)
                }
            
            # Получаем данные из API
            api_result = self.get_employee_data(pinfl, date)
            
            if not api_result["success"]:
                return {
                    "success": False,
                    "error": f"Не удалось получить данные из API: {api_result['error']}",
                    "employee_id": None
                }
            
            api_data = api_result["data"]
            
            # Создаем нового сотрудника
            # Нужно найти или создать организацию, департамент и отдел по умолчанию
            default_org, _ = Organization.objects.get_or_create(
                name="СКУД Организация",
                defaults={'description': 'Организация из СКУД системы'}
            )
            
            default_dept, _ = Department.objects.get_or_create(
                name="СКУД Департамент",
                organization=default_org,
                defaults={'description': 'Департамент из СКУД системы'}
            )
            
            default_division, _ = Division.objects.get_or_create(
                name="СКУД Отдел",
                department=default_dept,
                defaults={'description': 'Отдел из СКУД системы'}
            )
            
            # Создаем сотрудника
            employee = Employee.objects.create(
                last_name=api_data.get("last_name", ""),
                first_name=api_data.get("first_name", ""),
                middle_name=api_data.get("middle_name", ""),
                pinfl=pinfl,
                birth_date="1990-01-01",  # По умолчанию, так как API не предоставляет
                gender="M",  # По умолчанию
                phone="+998900000000",  # По умолчанию
                email=f"{api_data.get('first_name', '').lower()}@skud.local",  # Генерируем email
                organization=default_org,
                department=default_dept,
                division=default_division,
                position="specialist",  # По умолчанию
                employee_id=f"SKUD-{pinfl[-6:]}",  # Генерируем табельный номер
                hire_date=timezone.now().date(),
                is_active=True
            )
            
            # Обновляем данные из API
            employee.update_from_api_data(api_data)
            
            return {
                "success": True,
                "message": f"Сотрудник {employee.full_name} успешно создан из данных СКУД",
                "employee_id": str(employee.id),
                "employee_name": employee.full_name,
                "data": api_data
            }
            
        except Exception as e:
            error_msg = f"Ошибка создания сотрудника: {str(e)}"
            logger.error(f"Ошибка создания сотрудника по PINFL {pinfl}: {str(e)}")
            return {
                "success": False,
                "error": error_msg,
                "employee_id": None
            }
    
    def validate_pinfl_format(self, pinfl):
        """
        Валидация формата PINFL
        
        Args:
            pinfl: PINFL для валидации
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not pinfl:
            return False, "PINFL не может быть пустым"
        
        if not isinstance(pinfl, str):
            return False, "PINFL должен быть строкой"
        
        if not pinfl.isdigit():
            return False, "PINFL должен содержать только цифры"
        
        if len(pinfl) != 14:
            return False, "PINFL должен содержать ровно 14 цифр"
        
        return True, None
    
    def test_connection(self):
        """
        Тестирование подключения к SKUD API
        
        Returns:
            dict: Результат теста подключения
        """
        test_payload = {
            "login": "test",
            "password": "test",
            "pinfl": "12345678901234",
            "date": datetime.now().strftime("%d-%m-%Y")
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.base_url,
                json=test_payload,
                headers=headers,
                timeout=10
            )
            
            return {
                "success": True,
                "status_code": response.status_code,
                "message": "Подключение к SKUD API успешно",
                "response_time": response.elapsed.total_seconds()
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка подключения к SKUD API: {str(e)}"
            }




# Глобальный экземпляр клиента
pinfl_client = PINFLAPIClient()


# API views для Django:
def get_employee_by_pinfl_api_view(request):
    """
    API view для получения данных сотрудника
    """
    pinfl = request.GET.get('pinfl')
    
    if not pinfl:
        return JsonResponse({
            "success": False,
            "error": "PINFL не указан"
        }, status=400)
    
    result = pinfl_client.get_employee_data(pinfl)
    
    if result["success"]:
        return JsonResponse(result)
    else:
        return JsonResponse(result, status=400)


def sync_employee_api_view(request):
    """
    API view для синхронизации сотрудника с внешним API
    """
    pinfl = request.GET.get('pinfl')
    
    if not pinfl:
        return JsonResponse({
            "success": False,
            "error": "PINFL не указан"
        }, status=400)
    
    result = pinfl_client.sync_employee_by_pinfl(pinfl)
    
    if result["success"]:
        return JsonResponse(result)
    else:
        return JsonResponse(result, status=400)


def create_employee_api_view(request):
    """
    API view для создания нового сотрудника из данных СКУД API
    """
    pinfl = request.GET.get('pinfl')
    
    if not pinfl:
        return JsonResponse({
            "success": False,
            "error": "PINFL не указан"
        }, status=400)
    
    result = pinfl_client.create_employee_from_api(pinfl)
    
    if result["success"]:
        return JsonResponse(result)
    else:
        return JsonResponse(result, status=400)


