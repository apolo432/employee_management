"""
Сериализаторы для API системы учёта рабочего времени
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, date
from decimal import Decimal

from .models import (
    Employee, WorkSession, WorkDaySummary, WorkTimeAuditLog,
    SKUDEvent, SKUDDevice
)


class EmployeeSerializer(serializers.ModelSerializer):
    """Сериализатор для сотрудников"""
    
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    division_name = serializers.CharField(source='division.name', read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'last_name', 'first_name', 'middle_name', 'full_name',
            'birth_date', 'age', 'gender', 'phone', 'email',
            'organization', 'department', 'department_name',
            'division', 'division_name', 'position', 'employee_id',
            'hire_date', 'termination_date', 'is_active',
            'work_fraction', 'daily_hours', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SKUDDeviceSerializer(serializers.ModelSerializer):
    """Сериализатор для СКУД устройств"""
    
    device_type_display = serializers.CharField(source='get_device_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    full_address = serializers.SerializerMethodField()
    
    class Meta:
        model = SKUDDevice
        fields = [
            'id', 'name', 'device_type', 'device_type_display',
            'serial_number', 'ip_address', 'port', 'full_address',
            'location', 'description', 'status', 'status_display',
            'is_active', 'last_communication', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_full_address(self, obj):
        return obj.get_full_address()


class SKUDEventSerializer(serializers.ModelSerializer):
    """Сериализатор для событий СКУД"""
    
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    
    class Meta:
        model = SKUDEvent
        fields = [
            'id', 'device', 'device_name', 'employee', 'employee_name',
            'card_number', 'event_type', 'event_type_display',
            'event_time', 'raw_data', 'is_processed', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WorkSessionSerializer(serializers.ModelSerializer):
    """Сериализатор для рабочих сессий"""
    
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_hours = serializers.ReadOnlyField()
    is_open = serializers.ReadOnlyField()
    corrected_by_name = serializers.CharField(source='corrected_by.username', read_only=True)
    
    class Meta:
        model = WorkSession
        fields = [
            'id', 'employee', 'employee_name', 'date',
            'start_time', 'end_time', 'duration_seconds', 'duration_hours',
            'status', 'status_display', 'is_open',
            'manual_reason', 'corrected_by', 'corrected_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'duration_seconds', 'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        """Валидация данных сессии"""
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError(
                    "Время окончания должно быть позже времени начала"
                )
            
            # Проверяем максимальную длительность сессии (24 часа)
            duration = (end_time - start_time).total_seconds()
            if duration > 24 * 60 * 60:
                raise serializers.ValidationError(
                    "Длительность сессии не может превышать 24 часа"
                )
        
        return data


class WorkSessionCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рабочих сессий (только для админов)"""
    
    class Meta:
        model = WorkSession
        fields = [
            'employee', 'date', 'start_time', 'end_time',
            'status', 'manual_reason'
        ]
    
    def validate(self, data):
        """Валидация при создании сессии"""
        # Проверяем, что статус не 'auto' для ручного создания
        if data.get('status') == 'auto':
            raise serializers.ValidationError(
                "Нельзя создавать автоматические сессии вручную"
            )
        
        return data


class WorkDaySummarySerializer(serializers.ModelSerializer):
    """Сериализатор для сводок рабочих дней"""
    
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_hours = serializers.ReadOnlyField()
    expected_hours = serializers.ReadOnlyField()
    overtime_hours = serializers.ReadOnlyField()
    underwork_hours = serializers.ReadOnlyField()
    
    class Meta:
        model = WorkDaySummary
        fields = [
            'id', 'employee', 'employee_name', 'date',
            'first_entry', 'last_exit',
            'total_seconds_in_office', 'total_hours',
            'expected_seconds', 'expected_hours',
            'overtime_seconds', 'overtime_hours',
            'underwork_seconds', 'underwork_hours',
            'sessions_count', 'status', 'status_display',
            'has_missing_exit', 'has_manual_corrections',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_seconds_in_office', 'expected_seconds',
            'overtime_seconds', 'underwork_seconds', 'sessions_count',
            'created_at', 'updated_at'
        ]


class WorkTimeAuditLogSerializer(serializers.ModelSerializer):
    """Сериализатор для аудита изменений"""
    
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)
    
    class Meta:
        model = WorkTimeAuditLog
        fields = [
            'id', 'employee', 'employee_name', 'date',
            'action', 'action_display', 'description',
            'old_value', 'new_value', 'reason',
            'changed_by', 'changed_by_name', 'changed_at'
        ]
        read_only_fields = ['id', 'changed_at']


class EmployeeWorkTimeStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики рабочего времени сотрудника"""
    
    employee = EmployeeSerializer(read_only=True)
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    total_days = serializers.IntegerField()
    present_days = serializers.IntegerField()
    absent_days = serializers.IntegerField()
    excused_days = serializers.IntegerField()
    problem_days = serializers.IntegerField()
    total_hours_worked = serializers.DecimalField(max_digits=6, decimal_places=2)
    total_hours_expected = serializers.DecimalField(max_digits=6, decimal_places=2)
    total_overtime_hours = serializers.DecimalField(max_digits=6, decimal_places=2)
    total_underwork_hours = serializers.DecimalField(max_digits=6, decimal_places=2)
    average_hours_per_day = serializers.DecimalField(max_digits=5, decimal_places=2)
    work_efficiency_percent = serializers.DecimalField(max_digits=5, decimal_places=2)


class DepartmentWorkTimeStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики рабочего времени отдела"""
    
    department_name = serializers.CharField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    total_employees = serializers.IntegerField()
    total_days = serializers.IntegerField()
    total_hours_worked = serializers.DecimalField(max_digits=8, decimal_places=2)
    total_hours_expected = serializers.DecimalField(max_digits=8, decimal_places=2)
    average_hours_per_employee = serializers.DecimalField(max_digits=6, decimal_places=2)
    work_efficiency_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    problem_days_count = serializers.IntegerField()


class ReprocessWorkTimeSerializer(serializers.Serializer):
    """Сериализатор для запроса пересчёта рабочего времени"""
    
    employee_id = serializers.UUIDField(required=False)
    date = serializers.DateField(required=False)
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)
    force_reprocess = serializers.BooleanField(default=False)
    
    def validate(self, data):
        """Валидация параметров пересчёта"""
        # Проверяем, что указан либо конкретная дата, либо период
        if data.get('date') and (data.get('from_date') or data.get('to_date')):
            raise serializers.ValidationError(
                "Укажите либо конкретную дату, либо период (from_date/to_date)"
            )
        
        if data.get('from_date') and data.get('to_date'):
            if data['from_date'] > data['to_date']:
                raise serializers.ValidationError(
                    "Дата начала периода не может быть позже даты окончания"
                )
        
        return data


class BirthdayEmployeeSerializer(serializers.ModelSerializer):
    """Сериализатор для именинников"""
    
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    division_name = serializers.CharField(source='division.name', read_only=True)
    days_until_birthday = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id', 'last_name', 'first_name', 'middle_name', 'full_name',
            'birth_date', 'age', 'department_name', 'division_name',
            'days_until_birthday'
        ]
    
    def get_days_until_birthday(self, obj):
        """Вычисляет количество дней до дня рождения"""
        today = timezone.now().date()
        this_year_birthday = obj.birth_date.replace(year=today.year)
        
        # Если день рождения уже прошел в этом году, считаем до следующего года
        if this_year_birthday < today:
            next_year_birthday = obj.birth_date.replace(year=today.year + 1)
            return (next_year_birthday - today).days
        else:
            return (this_year_birthday - today).days

