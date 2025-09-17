from django.contrib import admin
from django.utils.html import format_html
from .models import Organization, Department, Division, Employee, Vacation, BusinessTrip, WorkTimeRecord


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


# Настройка заголовков админки
admin.site.site_header = "Система управления сотрудниками"
admin.site.site_title = "Управление сотрудниками"
admin.site.index_title = "Панель администратора"
