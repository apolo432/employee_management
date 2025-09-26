from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from .models import (
    Organization, Department, Division, Employee, Vacation, BusinessTrip, 
    WorkTimeRecord, SKUDDevice, SKUDEvent, WorkSession, WorkDaySummary, WorkTimeAuditLog,
    Role, Permission, RolePermission, UserRole, AccessLog, TemporaryPermission
)


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


class WorkSessionInline(admin.TabularInline):
    model = WorkSession
    extra = 0
    fields = ['date', 'start_time', 'end_time', 'duration_hours_display', 'status']
    readonly_fields = ['duration_hours_display']
    
    def duration_hours_display(self, obj):
        return f"{obj.duration_hours}ч" if obj.duration_seconds else "—"
    duration_hours_display.short_description = 'Длительность'


class WorkDaySummaryInline(admin.TabularInline):
    model = WorkDaySummary
    extra = 0
    fields = ['date', 'status', 'total_hours_display', 'expected_hours_display', 'overtime_hours_display']
    readonly_fields = ['total_hours_display', 'expected_hours_display', 'overtime_hours_display']
    
    def total_hours_display(self, obj):
        return f"{obj.total_hours}ч"
    total_hours_display.short_description = 'Отработано'
    
    def expected_hours_display(self, obj):
        return f"{obj.expected_hours}ч"
    expected_hours_display.short_description = 'Ожидалось'
    
    def overtime_hours_display(self, obj):
        if obj.overtime_hours > 0:
            return f"+{obj.overtime_hours}ч"
        elif obj.underwork_hours > 0:
            return f"-{obj.underwork_hours}ч"
        return "—"
    overtime_hours_display.short_description = 'Переработка/Недоработка'


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
        ('Учёт рабочего времени', {
            'fields': ('work_fraction', 'daily_hours'),
            'description': 'Настройки для расчёта рабочего времени'
        }),
        ('Системные поля', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [VacationInline, BusinessTripInline, WorkTimeRecordInline, WorkSessionInline, WorkDaySummaryInline]

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


@admin.register(WorkSession)
class WorkSessionAdmin(admin.ModelAdmin):
    """Админка для рабочих сессий"""
    list_display = [
        'employee_name', 'date', 'start_time_display', 'end_time_display', 
        'duration_display', 'status_display', 'is_open_display'
    ]
    list_filter = [
        'status', 'date', 'employee__department', 'employee__division',
        ('start_time', admin.DateFieldListFilter),
    ]
    search_fields = [
        'employee__first_name', 'employee__last_name', 'employee__employee_id'
    ]
    date_hierarchy = 'date'
    ordering = ['-date', '-start_time']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('employee', 'date', 'start_time', 'end_time', 'status')
        }),
        ('Расчётные поля', {
            'fields': ('duration_seconds', 'duration_hours_display'),
            'classes': ('collapse',)
        }),
        ('Ручные корректировки', {
            'fields': ('manual_reason', 'corrected_by'),
            'classes': ('collapse',)
        }),
        ('Системные поля', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'duration_seconds', 'duration_hours_display'
    ]
    
    actions = ['close_open_sessions', 'mark_as_manual', 'reprocess_sessions']
    
    def employee_name(self, obj):
        return obj.employee.full_name
    employee_name.short_description = 'Сотрудник'
    employee_name.admin_order_field = 'employee__last_name'
    
    def start_time_display(self, obj):
        return obj.start_time.strftime('%H:%M:%S')
    start_time_display.short_description = 'Начало'
    start_time_display.admin_order_field = 'start_time'
    
    def end_time_display(self, obj):
        return obj.end_time.strftime('%H:%M:%S') if obj.end_time else '—'
    end_time_display.short_description = 'Окончание'
    end_time_display.admin_order_field = 'end_time'
    
    def duration_display(self, obj):
        if obj.duration_seconds:
            hours = obj.duration_seconds // 3600
            minutes = (obj.duration_seconds % 3600) // 60
            return f"{hours}ч {minutes}м"
        return "—"
    duration_display.short_description = 'Длительность'
    
    def status_display(self, obj):
        colors = {
            'auto': 'green',
            'manual': 'blue', 
            'open': 'red',
            'closed_manual': 'orange'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Статус'
    
    def is_open_display(self, obj):
        if obj.is_open:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ Открыта</span>'
            )
        return format_html('<span style="color: green;">✅ Закрыта</span>')
    is_open_display.short_description = 'Статус сессии'
    
    def duration_hours_display(self, obj):
        return f"{obj.duration_hours} часов" if obj.duration_seconds else "Не рассчитано"
    duration_hours_display.short_description = 'Длительность (часы)'
    
    def close_open_sessions(self, request, queryset):
        """Действие для закрытия открытых сессий"""
        from django.utils import timezone
        
        closed_count = 0
        for session in queryset.filter(status='open'):
            session.end_time = timezone.now()
            session.status = 'closed_manual'
            session.manual_reason = f"Закрыто администратором {request.user.username}"
            session.corrected_by = request.user
            session.save()
            closed_count += 1
        
        self.message_user(request, f"Закрыто {closed_count} открытых сессий")
    close_open_sessions.short_description = "Закрыть открытые сессии"
    
    def mark_as_manual(self, request, queryset):
        """Действие для отметки сессий как ручных корректировок"""
        updated_count = 0
        for session in queryset:
            if session.status == 'auto':
                session.status = 'manual'
                session.manual_reason = f"Отмечено как ручная корректировка администратором {request.user.username}"
                session.corrected_by = request.user
                session.save()
                updated_count += 1
        
        self.message_user(request, f"Отмечено как ручные корректировки: {updated_count} сессий")
    mark_as_manual.short_description = "Отметить как ручные корректировки"
    
    def reprocess_sessions(self, request, queryset):
        """Действие для пересчёта сессий"""
        from .work_time_processor import WorkTimeProcessor
        
        processor = WorkTimeProcessor()
        processed_count = 0
        
        # Группируем сессии по сотрудникам и датам
        sessions_by_employee_date = {}
        for session in queryset:
            key = (session.employee, session.date)
            if key not in sessions_by_employee_date:
                sessions_by_employee_date[key] = []
            sessions_by_employee_date[key].append(session)
        
        # Пересчитываем для каждой уникальной комбинации сотрудник-дата
        for (employee, date), sessions in sessions_by_employee_date.items():
            if processor.process_skud_events_for_employee(employee, date):
                processed_count += 1
        
        self.message_user(request, f"Пересчитано {processed_count} дней")
    reprocess_sessions.short_description = "Пересчитать сессии"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('employee', 'corrected_by')


@admin.register(WorkDaySummary)
class WorkDaySummaryAdmin(admin.ModelAdmin):
    """Админка для сводок рабочих дней"""
    list_display = [
        'employee_name', 'date', 'status_display', 'total_hours_display',
        'expected_hours_display', 'overtime_hours_display', 'underwork_hours_display',
        'sessions_count', 'problem_flags'
    ]
    list_filter = [
        'status', 'has_missing_exit', 'has_manual_corrections',
        'employee__department', 'employee__division',
        ('date', admin.DateFieldListFilter),
    ]
    search_fields = [
        'employee__first_name', 'employee__last_name', 'employee__employee_id'
    ]
    date_hierarchy = 'date'
    ordering = ['-date', 'employee']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('employee', 'date', 'status')
        }),
        ('Временные границы', {
            'fields': ('first_entry', 'last_exit'),
            'classes': ('collapse',)
        }),
        ('Агрегированные данные', {
            'fields': (
                'total_seconds_in_office', 'expected_seconds',
                'overtime_seconds', 'underwork_seconds', 'sessions_count'
            )
        }),
        ('Расчётные поля', {
            'fields': (
                'total_hours_display', 'expected_hours_display',
                'overtime_hours_display', 'underwork_hours_display'
            ),
            'classes': ('collapse',)
        }),
        ('Флаги проблем', {
            'fields': ('has_missing_exit', 'has_manual_corrections'),
            'classes': ('collapse',)
        }),
        ('Системные поля', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'total_seconds_in_office', 'expected_seconds',
        'overtime_seconds', 'underwork_seconds', 'sessions_count',
        'total_hours_display', 'expected_hours_display', 'overtime_hours_display', 'underwork_hours_display'
    ]
    
    actions = ['reprocess_summaries', 'mark_problems_resolved']
    
    def employee_name(self, obj):
        return obj.employee.full_name
    employee_name.short_description = 'Сотрудник'
    employee_name.admin_order_field = 'employee__last_name'
    
    def status_display(self, obj):
        colors = {
            'present': 'green',
            'absent': 'gray',
            'excused': 'blue',
            'partial': 'orange',
            'problem': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Статус'
    
    def total_hours_display(self, obj):
        return f"{obj.total_hours}ч"
    total_hours_display.short_description = 'Отработано'
    
    def expected_hours_display(self, obj):
        return f"{obj.expected_hours}ч"
    expected_hours_display.short_description = 'Ожидалось'
    
    def overtime_hours_display(self, obj):
        if obj.overtime_hours > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">+{}ч</span>',
                obj.overtime_hours
            )
        return "—"
    overtime_hours_display.short_description = 'Переработка'
    
    def underwork_hours_display(self, obj):
        if obj.underwork_hours > 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">-{}ч</span>',
                obj.underwork_hours
            )
        return "—"
    underwork_hours_display.short_description = 'Недоработка'
    
    def problem_flags(self, obj):
        flags = []
        if obj.has_missing_exit:
            flags.append(format_html('<span style="color: red;">⚠️ Нет выхода</span>'))
        if obj.has_manual_corrections:
            flags.append(format_html('<span style="color: orange;">✏️ Ручные правки</span>'))
        
        return format_html(' '.join(flags)) if flags else format_html('<span style="color: green;">✅</span>')
    problem_flags.short_description = 'Проблемы'
    
    def reprocess_summaries(self, request, queryset):
        """Действие для пересчёта сводок"""
        from .work_time_processor import WorkTimeProcessor
        
        processor = WorkTimeProcessor()
        processed_count = 0
        
        for summary in queryset:
            if processor.process_skud_events_for_employee(summary.employee, summary.date):
                processed_count += 1
        
        self.message_user(request, f"Пересчитано {processed_count} сводок")
    reprocess_summaries.short_description = "Пересчитать сводки"
    
    def mark_problems_resolved(self, request, queryset):
        """Действие для отметки проблем как решённых"""
        updated_count = 0
        for summary in queryset:
            if summary.has_missing_exit or summary.has_manual_corrections:
                summary.has_missing_exit = False
                summary.has_manual_corrections = False
                summary.save()
                updated_count += 1
        
        self.message_user(request, f"Проблемы отмечены как решённые для {updated_count} сводок")
    mark_problems_resolved.short_description = "Отметить проблемы как решённые"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('employee')


@admin.register(WorkTimeAuditLog)
class WorkTimeAuditLogAdmin(admin.ModelAdmin):
    """Админка для аудита изменений в системе учёта рабочего времени"""
    list_display = [
        'employee_name', 'date', 'action_display', 'changed_by_name',
        'changed_at_display', 'description_short'
    ]
    list_filter = [
        'action', 'date',
        ('changed_at', admin.DateFieldListFilter),
        'changed_by',
    ]
    search_fields = [
        'employee__first_name', 'employee__last_name', 'employee__employee_id',
        'description', 'reason'
    ]
    date_hierarchy = 'changed_at'
    ordering = ['-changed_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('employee', 'date', 'action', 'description')
        }),
        ('Детали изменений', {
            'fields': ('reason', 'old_value', 'new_value'),
            'classes': ('collapse',)
        }),
        ('Системные поля', {
            'fields': ('id', 'changed_by', 'changed_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'id', 'changed_at', 'old_value', 'new_value'
    ]
    
    def employee_name(self, obj):
        return obj.employee.full_name
    employee_name.short_description = 'Сотрудник'
    employee_name.admin_order_field = 'employee__last_name'
    
    def action_display(self, obj):
        colors = {
            'create_session': 'green',
            'edit_session': 'blue',
            'delete_session': 'red',
            'close_session': 'orange',
            'create_summary': 'green',
            'edit_summary': 'blue',
            'reprocess_day': 'purple',
            'bulk_import': 'brown'
        }
        color = colors.get(obj.action, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_display.short_description = 'Действие'
    
    def changed_by_name(self, obj):
        return obj.changed_by.username if obj.changed_by else 'Система'
    changed_by_name.short_description = 'Изменил'
    
    def changed_at_display(self, obj):
        return obj.changed_at.strftime('%d.%m.%Y %H:%M:%S')
    changed_at_display.short_description = 'Время'
    changed_at_display.admin_order_field = 'changed_at'
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Описание'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('employee', 'changed_by')


# =============================================================================
# АДМИНКИ ДЛЯ СИСТЕМЫ РОЛЕЙ И ПРАВ ДОСТУПА
# =============================================================================

class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0
    fields = ['permission']
    autocomplete_fields = ['permission']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'role_type', 'is_system_role', 'is_active', 'permissions_count', 'users_count', 'created_at']
    list_filter = ['role_type', 'is_system_role', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'role_type', 'is_active')
        }),
        ('Системные настройки', {
            'fields': ('is_system_role',),
            'description': 'Системные роли нельзя удалять или изменять'
        }),
        ('Системные поля', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [RolePermissionInline]
    
    def permissions_count(self, obj):
        return obj.role_permissions.count()
    permissions_count.short_description = 'Количество прав'
    
    def users_count(self, obj):
        return obj.user_roles.filter(is_active=True).count()
    users_count.short_description = 'Пользователей'


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'codename', 'app_label', 'model_name', 'permission_type', 'is_active', 'roles_count']
    list_filter = ['app_label', 'model_name', 'permission_type', 'is_active', 'created_at']
    search_fields = ['name', 'codename', 'description']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'codename', 'description')
        }),
        ('Классификация', {
            'fields': ('app_label', 'model_name', 'permission_type')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
        ('Системные поля', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def roles_count(self, obj):
        return obj.role_permissions.count()
    roles_count.short_description = 'Количество ролей'


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'scope_type', 'scope_info', 'is_active', 'is_valid', 'assigned_at']
    list_filter = ['role', 'scope_type', 'is_active', 'assigned_at']
    search_fields = ['user__username', 'user__email', 'role__name']
    readonly_fields = ['id', 'assigned_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'role', 'scope_type')
        }),
        ('Область действия', {
            'fields': ('organization', 'department', 'division', 'employee'),
            'description': 'Укажите область действия роли'
        }),
        ('Временные рамки', {
            'fields': ('is_active', 'valid_from', 'valid_until'),
            'description': 'Настройте временные рамки действия роли'
        }),
        ('Метаданные', {
            'fields': ('assigned_by', 'reason'),
            'classes': ('collapse',)
        }),
        ('Системные поля', {
            'fields': ('id', 'assigned_at'),
            'classes': ('collapse',)
        }),
    )
    
    def scope_info(self, obj):
        if obj.scope_type == 'organization' and obj.organization:
            return obj.organization.name
        elif obj.scope_type == 'department' and obj.department:
            return obj.department.name
        elif obj.scope_type == 'division' and obj.division:
            return obj.division.name
        elif obj.scope_type == 'employee' and obj.employee:
            return obj.employee.full_name
        return 'Глобальная'
    scope_info.short_description = 'Область действия'
    
    def is_valid(self, obj):
        return obj.is_valid
    is_valid.boolean = True
    is_valid.short_description = 'Действует'


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'object_type', 'object_name', 'success', 'ip_address', 'timestamp']
    list_filter = ['action', 'object_type', 'success', 'timestamp']
    search_fields = ['user__username', 'object_name', 'ip_address']
    readonly_fields = ['id', 'timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'action', 'object_type', 'object_id', 'object_name')
        }),
        ('Детали доступа', {
            'fields': ('ip_address', 'user_agent', 'url', 'method'),
            'classes': ('collapse',)
        }),
        ('Результат', {
            'fields': ('success', 'error_message'),
        }),
        ('Системные поля', {
            'fields': ('id', 'timestamp'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(TemporaryPermission)
class TemporaryPermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'permission', 'object_type', 'object_id', 'is_valid', 'valid_from', 'valid_until', 'granted_at']
    list_filter = ['permission', 'object_type', 'is_active', 'granted_at']
    search_fields = ['user__username', 'permission__name', 'reason']
    readonly_fields = ['id', 'granted_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'permission')
        }),
        ('Объект', {
            'fields': ('object_type', 'object_id'),
            'description': 'Тип и ID объекта, на который распространяется право'
        }),
        ('Временные рамки', {
            'fields': ('valid_from', 'valid_until', 'is_active'),
            'description': 'Настройте временные рамки действия права'
        }),
        ('Метаданные', {
            'fields': ('reason', 'granted_by'),
            'classes': ('collapse',)
        }),
        ('Системные поля', {
            'fields': ('id', 'granted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_valid(self, obj):
        return obj.is_valid
    is_valid.boolean = True
    is_valid.short_description = 'Действует'


# Настройка заголовков админки
admin.site.site_header = "Система управления сотрудниками"
admin.site.site_title = "Управление сотрудниками"
admin.site.index_title = "Панель администратора"
