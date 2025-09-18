from django.db import models
from turbodrf.mixins import TurboDRFMixin
from django.core.validators import RegexValidator
from django.utils import timezone
import uuid


class Organization(models.Model, TurboDRFMixin):
    """Модель организации"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Название организации")
    description = models.TextField(blank=True, verbose_name="Описание")
    address = models.TextField(verbose_name="Адрес")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    email = models.EmailField(verbose_name="Email")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Организация"
        verbose_name_plural = "Организации"
        ordering = ['name']

    def __str__(self):
        return self.name

    @classmethod
    def turbodrf(cls):
        return {
            'fields': {
                'name': 'Название организации',
                'description': 'Описание',
                'address': 'Адрес',
                'phone': 'Телефон',
                'email': 'Email',
            },
            'relations': {
                'departments': {
                    'type': 'many',
                    'model': 'Department',
                    'fields': ['organization'],
                },
            },
            'filters': {
                'name': 'Название организации',
                'description': 'Описание',
                'address': 'Адрес',
                'phone': 'Телефон',
                'email': 'Email',
            },
            'actions': {
                'create': 'Создать организацию',
                'update': 'Обновить организацию',
                'delete': 'Удалить организацию',
            },
        }


class Department(models.Model, TurboDRFMixin):
    """Модель департамента"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, 
                                   related_name='departments', verbose_name="Организация")
    name = models.CharField(max_length=200, verbose_name="Название департамента")
    description = models.TextField(blank=True, verbose_name="Описание")
    manager = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='managed_departments', verbose_name="Руководитель")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Департамент"
        verbose_name_plural = "Департаменты"
        ordering = ['name']

    def __str__(self):
        return f"{self.organization.name} - {self.name}"

    @classmethod
    def turbodrf(cls):
        return {
            'fields': {
                'name': 'Название департамента',
                'description': 'Описание',
                'manager': 'Руководитель',
            },
        }


class Division(models.Model, TurboDRFMixin):
    """Модель отдела"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE,
                                 related_name='divisions', verbose_name="Департамент")
    name = models.CharField(max_length=200, verbose_name="Название отдела")
    description = models.TextField(blank=True, verbose_name="Описание")
    manager = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='managed_divisions', verbose_name="Руководитель")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Отдел"
        verbose_name_plural = "Отделы"
        ordering = ['name']

    def __str__(self):
        return f"{self.department} - {self.name}"

    @classmethod
    def turbodrf(cls):
        return {
            'fields': {
                'name': 'Название отдела',
                'description': 'Описание',
                'manager': 'Руководитель',
            },
        }


class Employee(models.Model, TurboDRFMixin):
    """Модель сотрудника"""
    POSITION_CHOICES = [
        ('junior', 'Младший специалист'),
        ('specialist', 'Специалист'),
        ('senior', 'Старший специалист'),
        ('lead', 'Ведущий специалист'),
        ('manager', 'Менеджер'),
        ('senior_manager', 'Старший менеджер'),
        ('director', 'Директор'),
    ]

    GENDER_CHOICES = [
        ('M', 'Мужской'),
        ('F', 'Женский'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Основная информация
    last_name = models.CharField(max_length=100, verbose_name="Фамилия")
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    middle_name = models.CharField(max_length=100, blank=True, verbose_name="Отчество")
    
    # Фото
    photo = models.ImageField(upload_to='employee_photos/', null=True, blank=True, 
                            verbose_name="Фото")
    
    # Личные данные
    birth_date = models.DateField(verbose_name="Дата рождения")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="Пол")
    phone = models.CharField(max_length=20, validators=[RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Номер телефона должен быть в формате: '+999999999'. До 15 цифр."
    )], verbose_name="Телефон")
    email = models.EmailField(verbose_name="Email")
    
    # Рабочая информация
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                   related_name='employees', verbose_name="Организация")
    department = models.ForeignKey(Department, on_delete=models.CASCADE,
                                 related_name='employees', verbose_name="Департамент")
    division = models.ForeignKey(Division, on_delete=models.CASCADE,
                               related_name='employees', verbose_name="Отдел")
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, 
                              verbose_name="Должность")
    employee_id = models.CharField(max_length=20, unique=True, verbose_name="Табельный номер")
    
    # Даты
    hire_date = models.DateField(verbose_name="Дата приема на работу")
    termination_date = models.DateField(null=True, blank=True, verbose_name="Дата увольнения")
    is_active = models.BooleanField(default=True, verbose_name="Активный сотрудник")
    
    # Системные поля
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}".strip()

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}".strip()

    @property
    def age(self):
        today = timezone.now().date()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

    @classmethod
    def turbodrf(cls):
        return {
            'fields': {
                'last_name': 'Фамилия',
                'first_name': 'Имя',
                'middle_name': 'Отчество',
                'photo': 'Фото',
            },
        }


class Vacation(models.Model, TurboDRFMixin):
    """Модель отпуска"""
    STATUS_CHOICES = [
        ('planned', 'Запланирован'),
        ('approved', 'Одобрен'),
        ('taken', 'Использован'),
        ('cancelled', 'Отменен'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
                               related_name='vacations', verbose_name="Сотрудник")
    start_date = models.DateField(verbose_name="Дата начала отпуска")
    end_date = models.DateField(verbose_name="Дата окончания отпуска")
    days_count = models.PositiveIntegerField(verbose_name="Количество дней")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, 
                            default='planned', verbose_name="Статус")
    reason = models.TextField(blank=True, verbose_name="Причина")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Отпуск"
        verbose_name_plural = "Отпуска"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.employee.full_name} - {self.start_date} до {self.end_date}"

    @classmethod
    def turbodrf(cls):
        return {
            'fields': {
                'start_date': 'Дата начала отпуска',
                'end_date': 'Дата окончания отпуска',
                'days_count': 'Количество дней',
                'status': 'Статус',
                'reason': 'Причина',
            },
        }

class BusinessTrip(models.Model, TurboDRFMixin):
    """Модель командировки"""
    STATUS_CHOICES = [
        ('planned', 'Запланирована'),
        ('approved', 'Одобрена'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
                               related_name='business_trips', verbose_name="Сотрудник")
    destination = models.CharField(max_length=200, verbose_name="Место назначения")
    start_date = models.DateField(verbose_name="Дата начала командировки")
    end_date = models.DateField(verbose_name="Дата окончания командировки")
    purpose = models.TextField(verbose_name="Цель командировки")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                            default='planned', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Командировка"
        verbose_name_plural = "Командировки"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.employee.full_name} - {self.destination} ({self.start_date})"

    @classmethod
    def turbodrf(cls):
        return {
            'fields': {
                'destination': 'Место назначения',
                'start_date': 'Дата начала командировки',
                'end_date': 'Дата окончания командировки',
                'purpose': 'Цель командировки',
                'status': 'Статус',
            },
        }

class SKUDDevice(models.Model):
    """Модель СКУД устройства"""
    DEVICE_TYPES = [
        ('turnstile', 'Турникет'),
        ('reader', 'Считыватель'),
        ('controller', 'Контроллер'),
        ('gate', 'Шлагбаум'),
        ('door', 'Дверь'),
        ('other', 'Другое'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Активно'),
        ('inactive', 'Неактивно'),
        ('maintenance', 'На обслуживании'),
        ('error', 'Ошибка'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Название устройства")
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, 
                                 verbose_name="Тип устройства")
    serial_number = models.CharField(max_length=100, unique=True, 
                                   verbose_name="Серийный номер")
    ip_address = models.GenericIPAddressField(unique=True, verbose_name="IP адрес")
    port = models.PositiveIntegerField(default=80, verbose_name="Порт")
    location = models.CharField(max_length=200, verbose_name="Местоположение")
    description = models.TextField(blank=True, verbose_name="Описание")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, 
                            default='active', verbose_name="Статус")
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    last_communication = models.DateTimeField(null=True, blank=True, 
                                            verbose_name="Последняя связь")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "СКУД устройство"
        verbose_name_plural = "СКУД устройства"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.ip_address})"

    def get_full_address(self):
        """Получить полный адрес устройства (IP:PORT)"""
        return f"{self.ip_address}:{self.port}"

    @classmethod
    def turbodrf(cls):
        return {
            'fields': {
                'name': 'Название устройства',
                'device_type': 'Тип устройства',
                'serial_number': 'Серийный номер',
                'ip_address': 'IP адрес',
                'port': 'Порт',
                'location': 'Местоположение',
                'description': 'Описание',
                'status': 'Статус',
                'is_active': 'Активно',
                'last_communication': 'Последняя связь',
            },
        }

class SKUDEvent(models.Model):
    """Модель события СКУД (проход через устройство)"""
    EVENT_TYPES = [
        ('entry', 'Вход'),
        ('exit', 'Выход'),
        ('denied', 'Отказ в доступе'),
        ('alarm', 'Тревога'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(SKUDDevice, on_delete=models.CASCADE,
                             related_name='events', verbose_name="Устройство")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True,
                               related_name='skud_events', verbose_name="Сотрудник")
    card_number = models.CharField(max_length=50, blank=True, verbose_name="Номер карты")
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, 
                                verbose_name="Тип события")
    event_time = models.DateTimeField(verbose_name="Время события")
    raw_data = models.TextField(blank=True, verbose_name="Исходные данные")
    is_processed = models.BooleanField(default=False, verbose_name="Обработано")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Событие СКУД"
        verbose_name_plural = "События СКУД"
        ordering = ['-event_time']

    def __str__(self):
        employee_name = self.employee.full_name if self.employee else "Неизвестный"
        return f"{employee_name} - {self.get_event_type_display()} ({self.event_time})"

    @classmethod
    def turbodrf(cls):
        return {
            'fields': {
                'device': 'Устройство',
                'employee': 'Сотрудник',
                'card_number': 'Номер карты',
                'event_type': 'Тип события',
                'event_time': 'Время события',
                'raw_data': 'Исходные данные',
                'is_processed': 'Обработано',
            },
        }

class WorkTimeRecord(models.Model, TurboDRFMixin):
    """Модель записи рабочего времени (для интеграции с СКУД)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
                               related_name='work_time_records', verbose_name="Сотрудник")
    date = models.DateField(verbose_name="Дата")
    arrival_time = models.TimeField(null=True, blank=True, verbose_name="Время прихода")
    departure_time = models.TimeField(null=True, blank=True, verbose_name="Время ухода")
    total_hours = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True,
                                    verbose_name="Общее время работы (часы)")
    is_present = models.BooleanField(default=False, verbose_name="Присутствовал")
    notes = models.TextField(blank=True, verbose_name="Примечания")
    # Связь с СКУД событиями
    arrival_event = models.ForeignKey(SKUDEvent, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='arrival_records', verbose_name="Событие входа")
    departure_event = models.ForeignKey(SKUDEvent, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='departure_records', verbose_name="Событие выхода")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Запись рабочего времени"
        verbose_name_plural = "Записи рабочего времени"
        ordering = ['-date', 'employee']
        unique_together = ['employee', 'date']

    def __str__(self):
        return f"{self.employee.full_name} - {self.date}"

    def save(self, *args, **kwargs):
        # Автоматический расчет общего времени работы
        if self.arrival_time and self.departure_time:
            # Преобразуем время в минуты для расчета
            arrival_minutes = self.arrival_time.hour * 60 + self.arrival_time.minute
            departure_minutes = self.departure_time.hour * 60 + self.departure_time.minute
            
            # Если уход на следующий день
            if departure_minutes < arrival_minutes:
                departure_minutes += 24 * 60
            
            total_minutes = departure_minutes - arrival_minutes
            self.total_hours = round(total_minutes / 60, 2)
            self.is_present = True
        
        super().save(*args, **kwargs)