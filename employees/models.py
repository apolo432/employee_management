from django.db import models
from django.contrib.auth.models import User
from turbodrf.mixins import TurboDRFMixin
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
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
    
    # Связь с пользователем Django
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='employee_profile',
        verbose_name="Пользователь системы"
    )
    
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
    pinfl = models.CharField(
        max_length=14, 
        unique=True, 
        null=True,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\d{14}$',
            message="PINFL должен содержать ровно 14 цифр."
        )], 
        verbose_name="PINFL",
        help_text="14-значный персональный идентификационный номер физического лица"
    )
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
    
    # Учёт рабочего времени
    work_fraction = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.25')), MaxValueValidator(Decimal('2.00'))],
        verbose_name="Ставка работы",
        help_text="1.00 = полная ставка, 0.5 = полставки, 1.5 = полтора ставки"
    )
    daily_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('8.00'),
        validators=[MinValueValidator(Decimal('1.00')), MaxValueValidator(Decimal('24.00'))],
        verbose_name="Часов в день",
        help_text="Стандартное количество рабочих часов в день"
    )
    
    # Данные из внешнего API СКУД
    external_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
        verbose_name="ID в СКУД системе",
        help_text="Идентификатор сотрудника во внешней системе СКУД"
    )
    work_start_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Время начала работы",
        help_text="Стандартное время начала рабочего дня (из СКУД)"
    )
    work_end_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Время окончания работы", 
        help_text="Стандартное время окончания рабочего дня (из СКУД)"
    )
    
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
    
    @property
    def fio(self):
        """Полное ФИО (для совместимости с API)"""
        return self.full_name
    
    @property
    def work_duration_hours(self):
        """Количество рабочих часов в день (из СКУД или стандартное)"""
        if self.work_start_time and self.work_end_time:
            from datetime import datetime, timedelta
            start = datetime.combine(timezone.now().date(), self.work_start_time)
            end = datetime.combine(timezone.now().date(), self.work_end_time)
            if end < start:  # Если работа через полночь
                end += timedelta(days=1)
            return (end - start).total_seconds() / 3600
        return float(self.daily_hours)
    
    @property
    def work_experience(self):
        """Стаж работы сотрудника"""
        if not self.hire_date:
            return "Не указана дата приема"
        
        from datetime import date
        today = date.today()
        end_date = self.termination_date if self.termination_date else today
        
        # Рассчитываем разность в днях
        delta = end_date - self.hire_date
        total_days = delta.days
        
        if total_days < 0:
            return "Ошибка в датах"
        
        # Рассчитываем годы, месяцы и дни
        years = total_days // 365
        remaining_days = total_days % 365
        months = remaining_days // 30
        days = remaining_days % 30
        
        # Формируем строку стажа
        experience_parts = []
        
        if years > 0:
            if years == 1:
                experience_parts.append("1 год")
            elif years in [2, 3, 4]:
                experience_parts.append(f"{years} года")
            else:
                experience_parts.append(f"{years} лет")
        
        if months > 0:
            if months == 1:
                experience_parts.append("1 месяц")
            elif months in [2, 3, 4]:
                experience_parts.append(f"{months} месяца")
            else:
                experience_parts.append(f"{months} месяцев")
        
        if days > 0 and years == 0:  # Показываем дни только если нет лет
            if days == 1:
                experience_parts.append("1 день")
            elif days in [2, 3, 4]:
                experience_parts.append(f"{days} дня")
            else:
                experience_parts.append(f"{days} дней")
        
        if not experience_parts:
            return "Менее месяца"
        
        return ", ".join(experience_parts)
    
    def update_from_api_data(self, api_data):
        """
        Обновить данные сотрудника из API СКУД
        
        Args:
            api_data: Словарь с данными из API
        """
        if api_data.get('id'):
            self.external_id = api_data['id']
        
        if api_data.get('work_start_time'):
            from datetime import datetime
            try:
                # Предполагаем формат "HH:MM" или "HH:MM:SS"
                time_str = api_data['work_start_time']
                if len(time_str.split(':')) == 2:
                    time_str += ':00'  # Добавляем секунды если их нет
                self.work_start_time = datetime.strptime(time_str, '%H:%M:%S').time()
            except (ValueError, TypeError):
                pass  # Игнорируем неверный формат времени
        
        if api_data.get('work_end_time'):
            from datetime import datetime
            try:
                # Предполагаем формат "HH:MM" или "HH:MM:SS"
                time_str = api_data['work_end_time']
                if len(time_str.split(':')) == 2:
                    time_str += ':00'  # Добавляем секунды если их нет
                self.work_end_time = datetime.strptime(time_str, '%H:%M:%S').time()
            except (ValueError, TypeError):
                pass  # Игнорируем неверный формат времени
        
        # Сохраняем изменения
        self.save(update_fields=['external_id', 'work_start_time', 'work_end_time'])
    
    def get_expected_daily_seconds(self, date=None):
        """
        Получить ожидаемое количество секунд работы в день
        с учётом ставки и стандартных часов
        """
        if date is None:
            date = timezone.now().date()
        
        # Проверяем, есть ли отпуск или командировка на эту дату
        if self.has_vacation_on_date(date) or self.has_business_trip_on_date(date):
            return 0
        
        # Рассчитываем ожидаемые секунды: стандартные часы * ставка * 3600
        expected_hours = self.daily_hours * self.work_fraction
        return int(expected_hours * 3600)
    
    def has_vacation_on_date(self, date):
        """Проверить, есть ли отпуск на указанную дату"""
        return self.vacations.filter(
            start_date__lte=date,
            end_date__gte=date,
            status__in=['approved', 'taken']
        ).exists()
    
    def has_business_trip_on_date(self, date):
        """Проверить, есть ли командировка на указанную дату"""
        return self.business_trips.filter(
            start_date__lte=date,
            end_date__gte=date,
            status__in=['approved', 'in_progress']
        ).exists()

    @classmethod
    def turbodrf(cls):
        return {
            'fields': {
                'last_name': 'Фамилия',
                'first_name': 'Имя',
                'middle_name': 'Отчество',
                'pinfl': 'PINFL',
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


class WorkSession(models.Model):
    """Модель рабочей сессии (приход-уход)"""
    
    SESSION_STATUS_CHOICES = [
        ('auto', 'Автоматическая'),
        ('manual', 'Ручная'),
        ('open', 'Открытая (нет выхода)'),
        ('closed_manual', 'Закрыта вручную'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
                               related_name='work_sessions', verbose_name="Сотрудник")
    date = models.DateField(verbose_name="Дата", db_index=True)
    
    # Временные границы сессии
    start_time = models.DateTimeField(verbose_name="Время начала", db_index=True)
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="Время окончания")
    
    # Вычисляемые поля
    duration_seconds = models.PositiveIntegerField(
        null=True, blank=True, 
        verbose_name="Длительность (секунды)",
        help_text="Автоматически рассчитывается"
    )
    
    # Статус и источник
    status = models.CharField(
        max_length=20, 
        choices=SESSION_STATUS_CHOICES, 
        default='auto',
        verbose_name="Статус сессии"
    )
    
    # Связь с событиями СКУД
    source_events = models.ManyToManyField(
        SKUDEvent, 
        blank=True,
        related_name='work_sessions',
        verbose_name="Исходные события СКУД"
    )
    
    # Ручные корректировки
    manual_reason = models.TextField(
        blank=True,
        verbose_name="Причина ручной корректировки"
    )
    corrected_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Исправил"
    )
    
    # Системные поля
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Рабочая сессия"
        verbose_name_plural = "Рабочие сессии"
        ordering = ['-date', '-start_time']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['employee', 'start_time']),
            models.Index(fields=['date', 'status']),
        ]
    
    def __str__(self):
        if self.end_time:
            return f"{self.employee.full_name} - {self.date} ({self.start_time.time()} - {self.end_time.time()})"
        else:
            return f"{self.employee.full_name} - {self.date} ({self.start_time.time()} - открыта)"
    
    def save(self, *args, **kwargs):
        # Автоматический расчёт длительности
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.duration_seconds = int(delta.total_seconds())
        elif self.start_time and self.status == 'open':
            # Для открытых сессий считаем до текущего времени
            delta = timezone.now() - self.start_time
            self.duration_seconds = int(delta.total_seconds())
        
        super().save(*args, **kwargs)
    
    @property
    def is_open(self):
        """Проверить, открыта ли сессия (нет выхода)"""
        return self.status == 'open' or self.end_time is None
    
    @property
    def duration_hours(self):
        """Получить длительность в часах"""
        if self.duration_seconds:
            return round(self.duration_seconds / 3600, 2)
        return 0


class WorkDaySummary(models.Model):
    """Модель агрегированной сводки рабочего времени за день"""
    
    SUMMARY_STATUS_CHOICES = [
        ('present', 'Присутствовал'),
        ('absent', 'Отсутствовал'),
        ('excused', 'Уважительная причина'),
        ('partial', 'Частично присутствовал'),
        ('problem', 'Проблема (нет выхода)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
                               related_name='work_day_summaries', verbose_name="Сотрудник")
    date = models.DateField(verbose_name="Дата", db_index=True)
    
    # Временные границы дня
    first_entry = models.DateTimeField(null=True, blank=True, verbose_name="Первый вход")
    last_exit = models.DateTimeField(null=True, blank=True, verbose_name="Последний выход")
    
    # Агрегированные данные
    total_seconds_in_office = models.PositiveIntegerField(
        default=0,
        verbose_name="Общее время в офисе (секунды)"
    )
    expected_seconds = models.PositiveIntegerField(
        default=0,
        verbose_name="Ожидаемое время работы (секунды)"
    )
    overtime_seconds = models.IntegerField(
        default=0,
        verbose_name="Переработка (секунды)"
    )
    underwork_seconds = models.IntegerField(
        default=0,
        verbose_name="Недоработка (секунды)"
    )
    
    # Статистика сессий
    sessions_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество сессий"
    )
    
    # Статус дня
    status = models.CharField(
        max_length=20,
        choices=SUMMARY_STATUS_CHOICES,
        default='absent',
        verbose_name="Статус дня"
    )
    
    # Флаги проблем
    has_missing_exit = models.BooleanField(
        default=False,
        verbose_name="Есть незакрытые сессии"
    )
    has_manual_corrections = models.BooleanField(
        default=False,
        verbose_name="Есть ручные корректировки"
    )
    
    # Системные поля
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Сводка рабочего дня"
        verbose_name_plural = "Сводки рабочих дней"
        ordering = ['-date', 'employee']
        unique_together = ['employee', 'date']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date', 'status']),
            models.Index(fields=['employee', 'date', 'status']),
        ]
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.date} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Автоматический расчёт переработки/недоработки
        if self.total_seconds_in_office and self.expected_seconds:
            diff = self.total_seconds_in_office - self.expected_seconds
            if diff > 0:
                self.overtime_seconds = diff
                self.underwork_seconds = 0
            else:
                self.overtime_seconds = 0
                self.underwork_seconds = abs(diff)
        
        super().save(*args, **kwargs)
    
    @property
    def total_hours(self):
        """Получить общее время в часах"""
        return round(self.total_seconds_in_office / 3600, 2) if self.total_seconds_in_office else 0
    
    @property
    def expected_hours(self):
        """Получить ожидаемое время в часах"""
        return round(self.expected_seconds / 3600, 2) if self.expected_seconds else 0
    
    @property
    def overtime_hours(self):
        """Получить переработку в часах"""
        return round(self.overtime_seconds / 3600, 2) if self.overtime_seconds > 0 else 0
    
    @property
    def underwork_hours(self):
        """Получить недоработку в часах"""
        return round(self.underwork_seconds / 3600, 2) if self.underwork_seconds > 0 else 0


class WorkTimeAuditLog(models.Model):
    """Модель аудита изменений в системе учёта рабочего времени"""
    
    ACTION_CHOICES = [
        ('create_session', 'Создание сессии'),
        ('edit_session', 'Редактирование сессии'),
        ('delete_session', 'Удаление сессии'),
        ('close_session', 'Закрытие сессии'),
        ('create_summary', 'Создание сводки'),
        ('edit_summary', 'Редактирование сводки'),
        ('reprocess_day', 'Пересчёт дня'),
        ('bulk_import', 'Массовый импорт'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Что было изменено
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
                               related_name='audit_logs', verbose_name="Сотрудник")
    date = models.DateField(verbose_name="Дата изменений")
    
    # Детали действия
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Действие")
    description = models.TextField(verbose_name="Описание изменений")
    
    # Данные изменений
    old_value = models.JSONField(null=True, blank=True, verbose_name="Старое значение")
    new_value = models.JSONField(null=True, blank=True, verbose_name="Новое значение")
    reason = models.TextField(verbose_name="Причина изменения")
    
    # Кто и когда
    changed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Изменил"
    )
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Время изменения")
    
    class Meta:
        verbose_name = "Запись аудита"
        verbose_name_plural = "Записи аудита"
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['changed_at']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.action} - {self.date}"


# =============================================================================
# СИСТЕМА РОЛЕЙ И ПРАВ ДОСТУПА
# =============================================================================

class Role(models.Model, TurboDRFMixin):
    """Модель роли в системе"""
    
    ROLE_TYPES = [
        ('system', 'Системная роль'),
        ('business', 'Бизнес-роль'),
        ('temporary', 'Временная роль'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, verbose_name="Название роли")
    description = models.TextField(blank=True, verbose_name="Описание")
    role_type = models.CharField(max_length=20, choices=ROLE_TYPES, default='business', verbose_name="Тип роли")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    is_system_role = models.BooleanField(default=False, verbose_name="Системная роль", 
                                       help_text="Системные роли нельзя удалять или изменять")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"
        ordering = ['name']

    def __str__(self):
        return self.name

    @classmethod
    def turbodrf(cls):
        return {
            'fields': {
                'name': 'Название роли',
                'description': 'Описание',
                'role_type': 'Тип роли',
                'is_active': 'Активна',
            },
        }


class Permission(models.Model, TurboDRFMixin):
    """Модель права доступа"""
    
    PERMISSION_TYPES = [
        ('view', 'Просмотр'),
        ('add', 'Добавление'),
        ('change', 'Изменение'),
        ('delete', 'Удаление'),
        ('export', 'Экспорт'),
        ('approve', 'Утверждение'),
        ('manage', 'Управление'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Название права")
    codename = models.CharField(max_length=100, unique=True, verbose_name="Кодовое имя")
    description = models.TextField(blank=True, verbose_name="Описание")
    app_label = models.CharField(max_length=100, verbose_name="Приложение")
    model_name = models.CharField(max_length=100, verbose_name="Модель")
    permission_type = models.CharField(max_length=20, choices=PERMISSION_TYPES, verbose_name="Тип права")
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Право доступа"
        verbose_name_plural = "Права доступа"
        ordering = ['app_label', 'model_name', 'permission_type']

    def __str__(self):
        return f"{self.name} ({self.codename})"

    @classmethod
    def turbodrf(cls):
        return {
            'fields': {
                'name': 'Название права',
                'codename': 'Кодовое имя',
                'description': 'Описание',
                'app_label': 'Приложение',
                'model_name': 'Модель',
                'permission_type': 'Тип права',
                'is_active': 'Активно',
            },
        }


class RolePermission(models.Model):
    """Связь роли с правами доступа"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions', verbose_name="Роль")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='role_permissions', verbose_name="Право")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Право роли"
        verbose_name_plural = "Права ролей"
        unique_together = ['role', 'permission']
        ordering = ['role', 'permission']

    def __str__(self):
        return f"{self.role.name} - {self.permission.name}"


class UserRole(models.Model, TurboDRFMixin):
    """Связь пользователя с ролью"""
    
    SCOPE_TYPES = [
        ('global', 'Глобальная'),
        ('organization', 'По организации'),
        ('department', 'По департаменту'),
        ('division', 'По отделу'),
        ('employee', 'По сотруднику'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles', verbose_name="Пользователь")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles', verbose_name="Роль")
    
    # Область действия роли
    scope_type = models.CharField(max_length=20, choices=SCOPE_TYPES, default='global', verbose_name="Область действия")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, 
                                   related_name='user_roles', verbose_name="Организация")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True,
                                 related_name='user_roles', verbose_name="Департамент")
    division = models.ForeignKey(Division, on_delete=models.CASCADE, null=True, blank=True,
                               related_name='user_roles', verbose_name="Отдел")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True,
                               related_name='user_roles', verbose_name="Сотрудник")
    
    # Статус и временные рамки
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    valid_from = models.DateTimeField(default=timezone.now, verbose_name="Действует с")
    valid_until = models.DateTimeField(null=True, blank=True, verbose_name="Действует до")
    
    # Метаданные
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="Назначена")
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='assigned_roles', verbose_name="Назначена пользователем")
    reason = models.TextField(blank=True, verbose_name="Причина назначения")
    
    class Meta:
        verbose_name = "Роль пользователя"
        verbose_name_plural = "Роли пользователей"
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['scope_type', 'organization']),
            models.Index(fields=['scope_type', 'department']),
            models.Index(fields=['scope_type', 'division']),
        ]

    def __str__(self):
        scope_info = ""
        if self.scope_type == 'organization' and self.organization:
            scope_info = f" ({self.organization.name})"
        elif self.scope_type == 'department' and self.department:
            scope_info = f" ({self.department.name})"
        elif self.scope_type == 'division' and self.division:
            scope_info = f" ({self.division.name})"
        elif self.scope_type == 'employee' and self.employee:
            scope_info = f" ({self.employee.full_name})"
        
        return f"{self.user.username} - {self.role.name}{scope_info}"

    @property
    def is_valid(self):
        """Проверяет, действует ли роль в данный момент"""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from > now:
            return False
        if self.valid_until and self.valid_until < now:
            return False
        return True

    @classmethod
    def turbodrf(cls):
        return {
            'fields': {
                'user': 'Пользователь',
                'role': 'Роль',
                'scope_type': 'Область действия',
                'organization': 'Организация',
                'department': 'Департамент',
                'division': 'Отдел',
                'employee': 'Сотрудник',
                'is_active': 'Активна',
                'valid_from': 'Действует с',
                'valid_until': 'Действует до',
                'reason': 'Причина назначения',
            },
        }


class AccessLog(models.Model):
    """Лог доступа к данным для аудита"""
    
    ACTION_TYPES = [
        ('view', 'Просмотр'),
        ('add', 'Добавление'),
        ('change', 'Изменение'),
        ('delete', 'Удаление'),
        ('export', 'Экспорт'),
        ('approve', 'Утверждение'),
        ('deny', 'Отказ в доступе'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='access_logs', verbose_name="Пользователь")
    action = models.CharField(max_length=20, choices=ACTION_TYPES, verbose_name="Действие")
    object_type = models.CharField(max_length=100, verbose_name="Тип объекта")
    object_id = models.UUIDField(null=True, blank=True, verbose_name="ID объекта")
    object_name = models.CharField(max_length=200, blank=True, verbose_name="Название объекта")
    
    # Детали доступа
    ip_address = models.GenericIPAddressField(verbose_name="IP адрес")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    url = models.URLField(blank=True, verbose_name="URL")
    method = models.CharField(max_length=10, blank=True, verbose_name="HTTP метод")
    
    # Результат
    success = models.BooleanField(default=True, verbose_name="Успешно")
    error_message = models.TextField(blank=True, verbose_name="Сообщение об ошибке")
    
    # Временная метка
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время доступа")

    class Meta:
        verbose_name = "Запись доступа"
        verbose_name_plural = "Записи доступа"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['object_type', 'object_id']),
            models.Index(fields=['success', 'timestamp']),
        ]

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.user.username} - {self.get_action_display()} - {self.object_type} - {self.timestamp.strftime('%d.%m.%Y %H:%M')}"


class TemporaryPermission(models.Model):
    """Временные права доступа"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='temporary_permissions', verbose_name="Пользователь")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='temporary_permissions', verbose_name="Право")
    
    # Объект, на который распространяется право
    object_type = models.CharField(max_length=100, verbose_name="Тип объекта")
    object_id = models.UUIDField(verbose_name="ID объекта")
    
    # Временные рамки
    valid_from = models.DateTimeField(verbose_name="Действует с")
    valid_until = models.DateTimeField(verbose_name="Действует до")
    
    # Метаданные
    reason = models.TextField(verbose_name="Причина предоставления")
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='granted_temporary_permissions', verbose_name="Предоставлено пользователем")
    granted_at = models.DateTimeField(auto_now_add=True, verbose_name="Предоставлено")
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    class Meta:
        verbose_name = "Временное право"
        verbose_name_plural = "Временные права"
        ordering = ['-granted_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['valid_from', 'valid_until']),
            models.Index(fields=['object_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.permission.name} - {self.valid_from.strftime('%d.%m.%Y')} - {self.valid_until.strftime('%d.%m.%Y')}"

    @property
    def is_valid(self):
        """Проверяет, действует ли временное право в данный момент"""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from > now:
            return False
        if self.valid_until < now:
            return False
        return True
        