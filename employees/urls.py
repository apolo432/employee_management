"""
URL configuration for employees app
"""

from django.urls import path, include
from . import skud_api, frontend_views, role_views

urlpatterns = [
    # СКУД API endpoints
    path('api/skud/event/', skud_api.SKUDEventEndpoint.as_view(), name='skud_event'),
    path('api/skud/status/', skud_api.SKUDStatusEndpoint.as_view(), name='skud_status'),
    path('api/skud/device/<uuid:device_id>/', skud_api.SKUDDeviceInfoEndpoint.as_view(), name='skud_device_info'),
    path('api/skud/events/', skud_api.SKUDEventsEndpoint.as_view(), name='skud_events'),
    path('api/skud/health/', skud_api.SKUDHealthCheckEndpoint.as_view(), name='skud_health'),
    path('api/skud/test/', skud_api.skud_test_endpoint, name='skud_test'),
    
    # Frontend views
    path('', frontend_views.dashboard, name='dashboard'),
    path('devices/', frontend_views.devices_list, name='devices_list'),
    path('devices/add/', frontend_views.add_device, name='add_device'),
    path('devices/<uuid:device_id>/', frontend_views.device_detail, name='device_detail'),
    path('devices/<uuid:device_id>/delete/', frontend_views.delete_device, name='delete_device'),
    path('devices/<uuid:device_id>/deactivate/', frontend_views.deactivate_device, name='deactivate_device'),
    path('devices/<uuid:device_id>/activate/', frontend_views.activate_device, name='activate_device'),
    path('events/', frontend_views.events_list, name='events_list'),
    path('employees/', frontend_views.employees_list, name='employees_list'),
    path('employees/create/', frontend_views.create_employee, name='create_employee'),
    path('employees/<uuid:employee_id>/', frontend_views.employee_detail, name='employee_detail'),
    path('employees/<uuid:employee_id>/edit/', frontend_views.edit_employee, name='edit_employee'),
    path('employees/<uuid:employee_id>/events/', frontend_views.employee_events, name='employee_events'),
    path('send-test-event/', frontend_views.send_test_event, name='send_test_event'),
    
    # AJAX endpoints
    path('test-device/<uuid:device_id>/', frontend_views.test_device, name='test_device'),
    path('api/status/', frontend_views.api_status, name='api_status'),
    path('check-devices-health/', frontend_views.check_devices_health, name='check_devices_health'),
    path('api/analytics/', frontend_views.analytics_data, name='analytics_data'),
    path('api/departments/', frontend_views.get_departments, name='get_departments'),
    path('api/divisions/', frontend_views.get_divisions, name='get_divisions'),
    
    # REST API для системы учёта рабочего времени
    path('api/worktime/', include('employees.api_urls')),
    
    # PINFL API endpoints
    path('api/pinfl/get/', frontend_views.get_employee_by_pinfl_api_view, name='get_employee_by_pinfl'),
    path('api/pinfl/sync/', frontend_views.sync_employee_api_view, name='sync_employee_by_pinfl'),
    path('api/pinfl/create/', frontend_views.create_employee_api_view, name='create_employee_by_pinfl'),
    
    
    # Административная страница тестирования PINFL API
    path('system/test-pinfl-api/', frontend_views.admin_test_pinfl_api, name='admin_test_pinfl_api'),
    
    
    # Контроль прибытия и отбытия
    path('attendance/', frontend_views.attendance_control, name='attendance_control'),
    path('attendance/export/', frontend_views.export_attendance_excel, name='export_attendance_excel'),
    
    # Отчеты
    path('reports/', frontend_views.reports_dashboard, name='reports_dashboard'),
    
    # Рабочее время
    path('work-time/summaries/', frontend_views.work_time_summaries, name='work_time_summaries'),
    path('work-time/sessions/', frontend_views.work_sessions, name='work_sessions'),
    path('work-time/report/', frontend_views.employee_report, name='employee_report'),
    
    # Аутентификация (временная система логина)
    path('login/', frontend_views.login_view, name='login_view'),
    path('logout/', frontend_views.logout_view, name='logout_view'),
    path('profile/', frontend_views.profile_view, name='profile_view'),
    
    # Управление ролями и правами доступа
    path('roles/', role_views.roles_list, name='roles_list'),
    path('roles/<uuid:role_id>/', role_views.role_detail, name='role_detail'),
    path('users-roles/', role_views.users_roles, name='users_roles'),
    path('users-roles/assign/<int:user_id>/', role_views.assign_role, name='assign_role'),
    path('users-roles/revoke/<uuid:user_role_id>/', role_views.revoke_role, name='revoke_role'),
    path('access-logs/', role_views.access_logs, name='access_logs'),
    path('role-statistics/', role_views.role_statistics, name='role_statistics'),
    path('user-permissions/<int:user_id>/', role_views.user_permissions, name='user_permissions'),
    path('temporary-permissions/', role_views.temporary_permissions, name='temporary_permissions'),
]
