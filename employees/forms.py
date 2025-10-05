"""
Формы для системы управления сотрудниками
"""

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date

from .models import Employee, Organization, Department, Division


class EmployeeRegistrationForm(forms.ModelForm):
    """Форма регистрации нового сотрудника"""
    
    # Поля для создания пользователя Django
    username = forms.CharField(
        max_length=150,
        label="Имя пользователя",
        help_text="Уникальное имя для входа в систему"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Пароль",
        help_text="Пароль для входа в систему"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        label="Подтверждение пароля"
    )
    
    # Поле PINFL с дополнительной валидацией
    pinfl = forms.CharField(
        max_length=14,
        min_length=14,
        label="PINFL",
        help_text="14-значный персональный идентификационный номер физического лица",
        widget=forms.TextInput(attrs={
            'placeholder': '',
            'pattern': '[0-9]{14}',
            'title': 'Введите 14 цифр'
        })
    )
    
    class Meta:
        model = Employee
        fields = [
            'last_name', 'first_name', 'middle_name', 'pinfl',
            'birth_date', 'gender', 'phone', 'email',
            'organization', 'department', 'division', 'position',
            'employee_id', 'hire_date', 'work_fraction', 'daily_hours'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
            'work_fraction': forms.NumberInput(attrs={'step': '0.25', 'min': '0.25', 'max': '2.00'}),
            'daily_hours': forms.NumberInput(attrs={'step': '0.5', 'min': '1', 'max': '24'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Устанавливаем значения по умолчанию
        self.fields['work_fraction'].initial = 1.00
        self.fields['daily_hours'].initial = 8.00
        self.fields['hire_date'].initial = date.today()
        
        # Делаем поля обязательными
        self.fields['pinfl'].required = True
        self.fields['last_name'].required = True
        self.fields['first_name'].required = True
        self.fields['birth_date'].required = True
        self.fields['gender'].required = True
        self.fields['phone'].required = True
        self.fields['email'].required = True
        self.fields['organization'].required = True
        self.fields['department'].required = True
        self.fields['division'].required = True
        self.fields['position'].required = True
        self.fields['employee_id'].required = True
        self.fields['hire_date'].required = True
    
    def clean_pinfl(self):
        """Валидация PINFL"""
        pinfl = self.cleaned_data.get('pinfl')
        
        if not pinfl:
            raise ValidationError("PINFL обязателен для заполнения")
        
        # Проверяем, что PINFL содержит только цифры
        if not pinfl.isdigit():
            raise ValidationError("PINFL должен содержать только цифры")
        
        # Проверяем длину
        if len(pinfl) != 14:
            raise ValidationError("PINFL должен содержать ровно 14 цифр")
        
        # Проверяем уникальность
        if Employee.objects.filter(pinfl=pinfl).exists():
            raise ValidationError("Сотрудник с таким PINFL уже существует")
        
        return pinfl
    
    def clean_username(self):
        """Валидация имени пользователя"""
        username = self.cleaned_data.get('username')
        
        if User.objects.filter(username=username).exists():
            raise ValidationError("Пользователь с таким именем уже существует")
        
        return username
    
    def clean_employee_id(self):
        """Валидация табельного номера"""
        employee_id = self.cleaned_data.get('employee_id')
        
        if Employee.objects.filter(employee_id=employee_id).exists():
            raise ValidationError("Сотрудник с таким табельным номером уже существует")
        
        return employee_id
    
    def clean(self):
        """Общая валидация формы"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        # Проверяем совпадение паролей
        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError("Пароли не совпадают")
        
        # Проверяем, что дата рождения не в будущем
        birth_date = cleaned_data.get('birth_date')
        if birth_date and birth_date > date.today():
            raise ValidationError("Дата рождения не может быть в будущем")
        
        # Проверяем, что дата приема не в будущем
        hire_date = cleaned_data.get('hire_date')
        if hire_date and hire_date > date.today():
            raise ValidationError("Дата приема на работу не может быть в будущем")
        
        # Проверяем, что дата приема не раньше даты рождения
        if birth_date and hire_date and hire_date < birth_date:
            raise ValidationError("Дата приема на работу не может быть раньше даты рождения")
        
        return cleaned_data
    
    def save(self, commit=True):
        """Сохранение формы с созданием пользователя Django"""
        employee = super().save(commit=False)
        
        # Создаем пользователя Django
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data['email']
        )
        
        # Связываем сотрудника с пользователем
        employee.user = user
        
        if commit:
            employee.save()
        
        return employee


class EmployeeEditForm(forms.ModelForm):
    """Форма редактирования сотрудника"""
    
    class Meta:
        model = Employee
        fields = [
            'last_name', 'first_name', 'middle_name', 'pinfl',
            'birth_date', 'gender', 'phone', 'email',
            'organization', 'department', 'division', 'position',
            'employee_id', 'hire_date', 'termination_date', 'is_active',
            'work_fraction', 'daily_hours'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'hire_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'termination_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'work_fraction': forms.NumberInput(attrs={'step': '0.25', 'min': '0.25', 'max': '2.00', 'class': 'form-control'}),
            'daily_hours': forms.NumberInput(attrs={'step': '0.5', 'min': '1', 'max': '24', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        
        # Добавляем CSS классы ко всем полям
        for field_name, field in self.fields.items():
            if field.widget.attrs.get('class'):
                field.widget.attrs['class'] += ' form-control'
            else:
                field.widget.attrs['class'] = 'form-control'
        
        # Делаем PINFL обязательным
        self.fields['pinfl'].required = True
    
    def clean_pinfl(self):
        """Валидация PINFL с учетом текущего сотрудника"""
        pinfl = self.cleaned_data.get('pinfl')
        
        if not pinfl:
            raise ValidationError("PINFL обязателен для заполнения")
        
        # Проверяем, что PINFL содержит только цифры
        if not pinfl.isdigit():
            raise ValidationError("PINFL должен содержать только цифры")
        
        # Проверяем длину
        if len(pinfl) != 14:
            raise ValidationError("PINFL должен содержать ровно 14 цифр")
        
        # Проверяем уникальность (исключая текущего сотрудника)
        existing_employee = Employee.objects.filter(pinfl=pinfl).exclude(id=self.employee.id if self.employee else None).first()
        if existing_employee:
            raise ValidationError("Сотрудник с таким PINFL уже существует")
        
        return pinfl
    
    def clean_employee_id(self):
        """Валидация табельного номера с учетом текущего сотрудника"""
        employee_id = self.cleaned_data.get('employee_id')
        
        existing_employee = Employee.objects.filter(employee_id=employee_id).exclude(id=self.employee.id if self.employee else None).first()
        if existing_employee:
            raise ValidationError("Сотрудник с таким табельным номером уже существует")
        
        return employee_id


