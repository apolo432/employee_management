"""
URL-маршруты для API системы учёта рабочего времени
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api_views import (
    WorkSessionViewSet, WorkDaySummaryViewSet, EmployeeViewSet,
    WorkTimeProcessorViewSet, WorkTimeAuditLogViewSet,
    SKUDEventViewSet, SKUDDeviceViewSet
)

# Создаём роутер для ViewSets
router = DefaultRouter()
router.register(r'sessions', WorkSessionViewSet, basename='worksession')
router.register(r'summaries', WorkDaySummaryViewSet, basename='workdaysummary')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'processor', WorkTimeProcessorViewSet, basename='worktimeprocessor')
router.register(r'audit-logs', WorkTimeAuditLogViewSet, basename='worktimeauditlog')
router.register(r'skud-events', SKUDEventViewSet, basename='skudevent')
router.register(r'skud-devices', SKUDDeviceViewSet, basename='skuddevice')

urlpatterns = [
    # API маршруты через роутер
    path('', include(router.urls)),
]
