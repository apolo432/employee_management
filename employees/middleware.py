"""
Middleware для системы ролей и прав доступа
"""

from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
import logging

from .permissions import PermissionChecker

logger = logging.getLogger(__name__)


class RoleBasedAccessMiddleware(MiddlewareMixin):
    """
    Middleware для добавления методов проверки прав в request
    """
    
    def process_request(self, request):
        """Добавляем методы проверки прав в request"""
        
        # Добавляем методы проверки прав
        request.can_view_employee = lambda emp: PermissionChecker.can_view_employee(request.user, emp, request)
        request.can_edit_employee = lambda emp: PermissionChecker.can_edit_employee(request.user, emp, request)
        request.can_manage_skud_devices = lambda device=None: PermissionChecker.can_manage_skud_devices(request.user, device, request)
        request.can_view_reports = lambda: PermissionChecker.can_view_reports(request.user, request)
        request.can_export_data = lambda: PermissionChecker.can_export_data(request.user, request)
        request.can_approve_vacation = lambda vacation: PermissionChecker.can_approve_vacation(request.user, vacation, request)
        request.can_manage_roles = lambda: PermissionChecker.can_manage_roles(request.user, request)
        
        # Добавляем методы для получения данных
        request.get_accessible_employees = lambda: PermissionChecker.get_accessible_employees(request.user)
        request.get_user_role_info = lambda: PermissionChecker.get_user_role_info(request.user)
        request.get_user_roles = lambda: PermissionChecker.get_user_roles(request.user)
        request.get_user_permissions = lambda: PermissionChecker.get_user_permissions(request.user)
        
        # Добавляем общий метод проверки прав
        request.has_permission = lambda codename, org=None, dept=None, div=None, emp=None: PermissionChecker.has_permission(
            request.user, codename, org, dept, div, emp
        )
        
        # Добавляем информацию о пользователе (только простые типы данных)
        if request.user.is_authenticated:
            # Получаем информацию о ролях, но не сохраняем datetime объекты
            user_roles = PermissionChecker.get_user_roles(request.user)
            role_names = [ur.role.name for ur in user_roles if ur.is_valid]
            
            request.is_hr = 'HR-менеджер' in role_names
            request.is_manager = any(role in ['Руководитель департамента', 'Руководитель отдела'] for role in role_names)
            request.is_analyst = 'Аналитик' in role_names
            request.is_skud_operator = 'СКУД-оператор' in role_names
            request.is_employee = 'Сотрудник' in role_names
        else:
            request.is_hr = False
            request.is_manager = False
            request.is_analyst = False
            request.is_skud_operator = False
            request.is_employee = False


class AccessLoggingMiddleware(MiddlewareMixin):
    """
    Middleware для логирования доступа к защищенным страницам
    """
    
    # Список URL-паттернов, которые нужно логировать
    PROTECTED_PATTERNS = [
        '/employees/',
        '/devices/',
        '/events/',
        '/attendance/',
        '/admin/',
        '/reports/',
    ]
    
    # Список URL-паттернов, которые не нужно логировать
    EXCLUDED_PATTERNS = [
        '/static/',
        '/media/',
        '/favicon.ico',
        '/api/status/',
    ]
    
    def process_request(self, request):
        """Логируем запросы к защищенным страницам"""
        
        # Пропускаем анонимных пользователей
        if isinstance(request.user, AnonymousUser):
            return
        
        # Пропускаем исключенные паттерны
        if any(request.path.startswith(pattern) for pattern in self.EXCLUDED_PATTERNS):
            return
        
        # Логируем только защищенные паттерны
        if any(request.path.startswith(pattern) for pattern in self.PROTECTED_PATTERNS):
            try:
                # Определяем тип действия по HTTP методу
                action_map = {
                    'GET': 'view',
                    'POST': 'add',
                    'PUT': 'change',
                    'PATCH': 'change',
                    'DELETE': 'delete',
                }
                action = action_map.get(request.method, 'view')
                
                # Определяем тип объекта по URL
                object_type = self._get_object_type_from_url(request.path)
                
                # Логируем доступ
                PermissionChecker.log_access(
                    user=request.user,
                    action=action,
                    object_type=object_type,
                    request=request
                )
                
            except Exception as e:
                logger.error(f"Ошибка логирования доступа: {e}")
    
    def _get_object_type_from_url(self, url_path):
        """Определяет тип объекта по URL"""
        if '/employees/' in url_path:
            return 'Employee'
        elif '/devices/' in url_path:
            return 'SKUDDevice'
        elif '/events/' in url_path:
            return 'SKUDEvent'
        elif '/attendance/' in url_path:
            return 'Attendance'
        elif '/admin/' in url_path:
            return 'Admin'
        elif '/reports/' in url_path:
            return 'Reports'
        else:
            return 'Unknown'


class SessionTimeoutMiddleware(MiddlewareMixin):
    """
    Middleware для контроля времени сессии
    """
    
    def process_request(self, request):
        """Проверяем время сессии"""
        
        # Пропускаем анонимных пользователей
        if isinstance(request.user, AnonymousUser):
            return
        
        # Проверяем время последней активности
        last_activity_timestamp = request.session.get('last_activity')
        if last_activity_timestamp:
            from datetime import timedelta
            timeout_duration = timedelta(hours=8)  # 8 часов бездействия
            last_activity = timezone.datetime.fromtimestamp(last_activity_timestamp, tz=timezone.get_current_timezone())
            
            if timezone.now() - last_activity > timeout_duration:
                # Сессия истекла, выходим из системы
                from django.contrib.auth import logout
                logout(request)
                logger.info(f"Сессия пользователя {request.user.username} истекла по таймауту")
                return
        
        # Обновляем время последней активности (сохраняем как timestamp)
        request.session['last_activity'] = timezone.now().timestamp()


class RoleContextMiddleware(MiddlewareMixin):
    """
    Middleware для добавления контекста ролей в шаблоны
    """
    
    def process_template_response(self, request, response):
        """Добавляем контекст ролей в шаблоны"""
        
        if hasattr(response, 'context_data') and response.context_data is not None:
            # Добавляем информацию о ролях пользователя (только простые типы данных)
            if request.user.is_authenticated:
                # Получаем роли без datetime объектов
                user_roles = PermissionChecker.get_user_roles(request.user)
                role_names = [ur.role.name for ur in user_roles if ur.is_valid]
                
                # Добавляем только простые данные в контекст
                response.context_data['user_role_names'] = role_names
                response.context_data['is_hr'] = 'HR-менеджер' in role_names
                response.context_data['is_manager'] = any(role in ['Руководитель департамента', 'Руководитель отдела'] for role in role_names)
                response.context_data['is_analyst'] = 'Аналитик' in role_names
                response.context_data['is_skud_operator'] = 'СКУД-оператор' in role_names
                response.context_data['is_employee'] = 'Сотрудник' in role_names
            else:
                response.context_data['user_role_names'] = []
                response.context_data['is_hr'] = False
                response.context_data['is_manager'] = False
                response.context_data['is_analyst'] = False
                response.context_data['is_skud_operator'] = False
                response.context_data['is_employee'] = False
        
        return response
