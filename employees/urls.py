"""
URL configuration for employees app
"""

from django.urls import path
from . import skud_api, frontend_views

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
    path('events/', frontend_views.events_list, name='events_list'),
    path('employees/', frontend_views.employees_list, name='employees_list'),
    path('employees/<uuid:employee_id>/events/', frontend_views.employee_events, name='employee_events'),
    path('test/', frontend_views.quick_test, name='quick_test'),
    path('send-test-event/', frontend_views.send_test_event, name='send_test_event'),
    
    # AJAX endpoints
    path('test-device/<uuid:device_id>/', frontend_views.test_device, name='test_device'),
    path('api/status/', frontend_views.api_status, name='api_status'),
    path('check-devices-health/', frontend_views.check_devices_health, name='check_devices_health'),
]
