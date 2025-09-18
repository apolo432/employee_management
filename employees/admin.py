from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from .models import Organization, Department, Division, Employee, Vacation, BusinessTrip, WorkTimeRecord, SKUDDevice, SKUDEvent


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at']


class DivisionInline(admin.TabularInline):
    model = Division
    extra = 0
    fields = ['name', 'description', 'manager']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'manager', 'created_at']
    list_filter = ['organization', 'created_at']
    search_fields = ['name', 'organization__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [DivisionInline]


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'manager', 'created_at']
    list_filter = ['department__organization', 'department', 'created_at']
    search_fields = ['name', 'department__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


class VacationInline(admin.TabularInline):
    model = Vacation
    extra = 0
    fields = ['start_date', 'end_date', 'days_count', 'status']


class BusinessTripInline(admin.TabularInline):
    model = BusinessTrip
    extra = 0
    fields = ['destination', 'start_date', 'end_date', 'status']


class WorkTimeRecordInline(admin.TabularInline):
    model = WorkTimeRecord
    extra = 0
    fields = ['date', 'arrival_time', 'departure_time', 'total_hours', 'is_present']


class SKUDEventInline(admin.TabularInline):
    model = SKUDEvent
    extra = 0
    fields = ['event_type', 'event_time', 'employee', 'card_number', 'is_processed']
    readonly_fields = ['event_time']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'employee_id', 'position', 'department', 'division', 'is_active', 'hire_date']
    list_filter = ['is_active', 'position', 'department__organization', 'department', 'division', 'gender']
    search_fields = ['last_name', 'first_name', 'middle_name', 'employee_id', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'age']
    fieldsets = (
        ('Основная информация', {
            'fields': ('last_name', 'first_name', 'middle_name', 'photo')
        }),
        ('Личные данные', {
            'fields': ('birth_date', 'age', 'gender', 'phone', 'email')
        }),
        ('Рабочая информация', {
            'fields': ('organization', 'department', 'division', 'position', 'employee_id')
        }),
        ('Статус', {
            'fields': ('hire_date', 'termination_date', 'is_active')
        }),
        ('Системные поля', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [VacationInline, BusinessTripInline, WorkTimeRecordInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization', 'department', 'division')


@admin.register(Vacation)
class VacationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'start_date', 'end_date', 'days_count', 'status', 'created_at']
    list_filter = ['status', 'start_date', 'created_at']
    search_fields = ['employee__last_name', 'employee__first_name', 'employee__employee_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'start_date'


@admin.register(BusinessTrip)
class BusinessTripAdmin(admin.ModelAdmin):
    list_display = ['employee', 'destination', 'start_date', 'end_date', 'status', 'created_at']
    list_filter = ['status', 'start_date', 'created_at']
    search_fields = ['employee__last_name', 'employee__first_name', 'employee__employee_id', 'destination']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'start_date'


@admin.register(WorkTimeRecord)
class WorkTimeRecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'arrival_time', 'departure_time', 'total_hours', 'is_present']
    list_filter = ['is_present', 'date', 'created_at']
    search_fields = ['employee__last_name', 'employee__first_name', 'employee__employee_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('employee')


@admin.register(SKUDDevice)
class SKUDDeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'device_type', 'ip_address', 'port', 'location', 'status', 'is_active', 'last_communication']
    list_filter = ['device_type', 'status', 'is_active', 'created_at']
    search_fields = ['name', 'serial_number', 'ip_address', 'location']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_communication']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'device_type', 'serial_number', 'location', 'description')
        }),
        ('Сетевые настройки', {
            'fields': ('ip_address', 'port')
        }),
        ('Статус', {
            'fields': ('status', 'is_active', 'last_communication')
        }),
        ('Системные поля', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [SKUDEventInline]
    
    actions = ['test_connection', 'sync_time']
    
    def test_connection(self, request, queryset):
        """Действие для тестирования соединения с устройствами"""
        from .skud_device_communication import SKUDDeviceCommunicator
        
        communicator = SKUDDeviceCommunicator()
        results = []
        
        for device in queryset:
            is_online, message = communicator.test_device_connection(device)
            results.append(f"{device.name}: {'✓' if is_online else '✗'} {message}")
        
        self.message_user(request, mark_safe('<br>'.join(results)))
    
    test_connection.short_description = "Тестировать соединение с выбранными устройствами"
    
    def sync_time(self, request, queryset):
        """Действие для синхронизации времени устройств"""
        from .skud_device_communication import SKUDDeviceCommunicator
        
        communicator = SKUDDeviceCommunicator()
        results = []
        
        for device in queryset:
            success = communicator.sync_device_time(device)
            results.append(f"{device.name}: {'✓ Время синхронизировано' if success else '✗ Ошибка синхронизации'}")
        
        self.message_user(request, mark_safe('<br>'.join(results)))
    
    sync_time.short_description = "Синхронизировать время выбранных устройств"


@admin.register(SKUDEvent)
class SKUDEventAdmin(admin.ModelAdmin):
    list_display = ['event_time', 'device_name', 'employee_name', 'event_type', 'card_number', 'is_processed']
    list_filter = ['event_type', 'is_processed', 'device', 'event_time']
    search_fields = ['employee__last_name', 'employee__first_name', 'employee__employee_id', 'card_number', 'device__name']
    readonly_fields = ['id', 'event_time', 'created_at', 'raw_data']
    date_hierarchy = 'event_time'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('device', 'employee', 'card_number', 'event_type', 'event_time')
        }),
        ('Обработка', {
            'fields': ('is_processed',)
        }),
        ('Исходные данные', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
        ('Системные поля', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_processed', 'process_events']
    
    def device_name(self, obj):
        return obj.device.name
    device_name.short_description = 'Устройство'
    
    def employee_name(self, obj):
        return obj.employee.full_name if obj.employee else 'Неизвестный'
    employee_name.short_description = 'Сотрудник'
    
    def mark_as_processed(self, request, queryset):
        """Действие для отметки событий как обработанных"""
        updated = queryset.update(is_processed=True)
        self.message_user(request, f"{updated} событий отмечено как обработанные")
    
    mark_as_processed.short_description = "Отметить как обработанные"
    
    def process_events(self, request, queryset):
        """Действие для обработки событий"""
        from .skud_device_communication import SKUDEventProcessor
        
        processor = SKUDEventProcessor()
        processed_count = 0
        
        for event in queryset:
            if not event.is_processed:
                processor._process_single_event(event)
                processed_count += 1
        
        self.message_user(request, f"Обработано {processed_count} событий")
    
    process_events.short_description = "Обработать выбранные события"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('device', 'employee')


# Настройка заголовков админки
admin.site.site_header = "Система управления сотрудниками"
admin.site.site_title = "Управление сотрудниками"
admin.site.index_title = "Панель администратора"
