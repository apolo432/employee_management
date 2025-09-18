"""
Утилиты для кэширования данных
"""

from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SKUDCache:
    """Класс для кэширования данных СКУД системы"""
    
    # Ключи кэша
    CACHE_KEYS = {
        'device_stats': 'skud_device_stats',
        'event_stats': 'skud_event_stats',
        'recent_events': 'skud_recent_events',
        'device_status': 'skud_device_status',
        'api_status': 'skud_api_status',
    }
    
    # Время жизни кэша (в секундах)
    CACHE_TIMEOUTS = {
        'device_stats': 300,      # 5 минут
        'event_stats': 60,        # 1 минута
        'recent_events': 30,      # 30 секунд
        'device_status': 300,     # 5 минут
        'api_status': 60,         # 1 минута
    }
    
    @classmethod
    def get_device_stats(cls) -> Optional[Dict[str, Any]]:
        """Получение статистики устройств из кэша"""
        return cache.get(cls.CACHE_KEYS['device_stats'])
    
    @classmethod
    def set_device_stats(cls, stats: Dict[str, Any]) -> None:
        """Сохранение статистики устройств в кэш"""
        cache.set(
            cls.CACHE_KEYS['device_stats'], 
            stats, 
            cls.CACHE_TIMEOUTS['device_stats']
        )
        logger.info("Device stats cached")
    
    @classmethod
    def get_event_stats(cls) -> Optional[Dict[str, Any]]:
        """Получение статистики событий из кэша"""
        return cache.get(cls.CACHE_KEYS['event_stats'])
    
    @classmethod
    def set_event_stats(cls, stats: Dict[str, Any]) -> None:
        """Сохранение статистики событий в кэш"""
        cache.set(
            cls.CACHE_KEYS['event_stats'], 
            stats, 
            cls.CACHE_TIMEOUTS['event_stats']
        )
        logger.info("Event stats cached")
    
    @classmethod
    def get_recent_events(cls) -> Optional[list]:
        """Получение последних событий из кэша"""
        return cache.get(cls.CACHE_KEYS['recent_events'])
    
    @classmethod
    def set_recent_events(cls, events: list) -> None:
        """Сохранение последних событий в кэш"""
        cache.set(
            cls.CACHE_KEYS['recent_events'], 
            events, 
            cls.CACHE_TIMEOUTS['recent_events']
        )
        logger.info("Recent events cached")
    
    @classmethod
    def get_device_status(cls) -> Optional[Dict[str, Dict]]:
        """Получение статуса устройств из кэша"""
        return cache.get(cls.CACHE_KEYS['device_status'])
    
    @classmethod
    def set_device_status(cls, status: Dict[str, Dict]) -> None:
        """Сохранение статуса устройств в кэш"""
        cache.set(
            cls.CACHE_KEYS['device_status'], 
            status, 
            cls.CACHE_TIMEOUTS['device_status']
        )
        logger.info("Device status cached")
    
    @classmethod
    def get_api_status(cls) -> Optional[Dict[str, Any]]:
        """Получение статуса API из кэша"""
        return cache.get(cls.CACHE_KEYS['api_status'])
    
    @classmethod
    def set_api_status(cls, status: Dict[str, Any]) -> None:
        """Сохранение статуса API в кэш"""
        cache.set(
            cls.CACHE_KEYS['api_status'], 
            status, 
            cls.CACHE_TIMEOUTS['api_status']
        )
        logger.info("API status cached")
    
    @classmethod
    def clear_all(cls) -> None:
        """Очистка всего кэша СКУД"""
        for key in cls.CACHE_KEYS.values():
            cache.delete(key)
        logger.info("All SKUD cache cleared")
    
    @classmethod
    def clear_device_cache(cls) -> None:
        """Очистка кэша устройств"""
        cache.delete(cls.CACHE_KEYS['device_stats'])
        cache.delete(cls.CACHE_KEYS['device_status'])
        logger.info("Device cache cleared")
    
    @classmethod
    def clear_event_cache(cls) -> None:
        """Очистка кэша событий"""
        cache.delete(cls.CACHE_KEYS['event_stats'])
        cache.delete(cls.CACHE_KEYS['recent_events'])
        logger.info("Event cache cleared")


def cache_dashboard_data():
    """Функция для кэширования данных дашборда"""
    from .models import SKUDDevice, SKUDEvent
    from django.db.models import Count, Q
    
    try:
        # Статистика устройств
        device_stats = SKUDDevice.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            error=Count('id', filter=Q(status='error')),
            maintenance=Count('id', filter=Q(status='maintenance'))
        )
        SKUDCache.set_device_stats(device_stats)
        
        # Статистика событий
        today = timezone.now().date()
        event_stats = SKUDEvent.objects.aggregate(
            total=Count('id'),
            today=Count('id', filter=Q(event_time__date=today)),
            entry=Count('id', filter=Q(event_type='entry')),
            exit=Count('id', filter=Q(event_type='exit'))
        )
        SKUDCache.set_event_stats(event_stats)
        
        # Последние события
        recent_events = list(
            SKUDEvent.objects.select_related('device', 'employee')
            .order_by('-event_time')[:10]
            .values(
                'id', 'event_time', 'event_type', 'card_number',
                'device__name', 'employee__first_name', 'employee__last_name'
            )
        )
        SKUDCache.set_recent_events(recent_events)
        
        logger.info("Dashboard data cached successfully")
        
    except Exception as e:
        logger.error(f"Error caching dashboard data: {e}")


def get_cached_dashboard_data():
    """Получение кэшированных данных дашборда"""
    device_stats = SKUDCache.get_device_stats()
    event_stats = SKUDCache.get_event_stats()
    recent_events = SKUDCache.get_recent_events()
    
    # Если данные не в кэше, генерируем их
    if not all([device_stats, event_stats, recent_events]):
        cache_dashboard_data()
        device_stats = SKUDCache.get_device_stats()
        event_stats = SKUDCache.get_event_stats()
        recent_events = SKUDCache.get_recent_events()
    
    return {
        'device_stats': device_stats or {},
        'event_stats': event_stats or {},
        'recent_events': recent_events or [],
    }

