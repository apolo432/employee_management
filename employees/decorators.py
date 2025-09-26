"""
Декораторы для проверки прав доступа
"""

from functools import wraps
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import View
import logging

from .models import Employee, SKUDDevice, Vacation
from .permissions import PermissionChecker

logger = logging.getLogger(__name__)


def require_permission(permission_func, error_message="У вас нет прав для выполнения этого действия"):
    """
    Декоратор для проверки прав доступа
    
    Args:
        permission_func: Функция проверки прав (например, PermissionChecker.can_view_employee)
        error_message: Сообщение об ошибке при отказе в доступе
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Проверяем аутентификацию
            if not request.user.is_authenticated:
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({'error': 'Требуется аутентификация'}, status=401)
                messages.error(request, 'Требуется вход в систему')
                return redirect('login_view')
            
            # Получаем объект для проверки из kwargs
            employee_id = kwargs.get('employee_id')
            device_id = kwargs.get('device_id')
            vacation_id = kwargs.get('vacation_id')
            
            # Проверяем права в зависимости от типа объекта
            has_permission = False
            
            if employee_id:
                try:
                    employee = get_object_or_404(Employee, id=employee_id)
                    has_permission = permission_func(request.user, employee, request)
                except Exception as e:
                    logger.error(f"Ошибка при проверке прав для сотрудника {employee_id}: {e}")
                    has_permission = False
            
            elif device_id:
                try:
                    device = get_object_or_404(SKUDDevice, id=device_id)
                    has_permission = permission_func(request.user, device, request)
                except Exception as e:
                    logger.error(f"Ошибка при проверке прав для устройства {device_id}: {e}")
                    has_permission = False
            
            elif vacation_id:
                try:
                    vacation = get_object_or_404(Vacation, id=vacation_id)
                    has_permission = permission_func(request.user, vacation, request)
                except Exception as e:
                    logger.error(f"Ошибка при проверке прав для отпуска {vacation_id}: {e}")
                    has_permission = False
            
            else:
                # Для функций без конкретного объекта (например, просмотр отчетов)
                has_permission = permission_func(request.user, request=request)
            
            if not has_permission:
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({'error': error_message}, status=403)
                messages.error(request, error_message)
                return HttpResponseForbidden(f"<h1>Доступ запрещен</h1><p>{error_message}</p>")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_login(view_func):
    """Декоратор для проверки аутентификации"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({'error': 'Требуется аутентификация'}, status=401)
            messages.error(request, 'Требуется вход в систему')
            return redirect('login_view')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_superuser(view_func):
    """Декоратор для проверки прав суперпользователя"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({'error': 'Требуется аутентификация'}, status=401)
            messages.error(request, 'Требуется вход в систему')
            return redirect('login_view')
        
        if not request.user.is_superuser:
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({'error': 'Требуются права суперпользователя'}, status=403)
            messages.error(request, 'Требуются права суперпользователя')
            return HttpResponseForbidden("<h1>Доступ запрещен</h1><p>Требуются права суперпользователя</p>")
        
        return view_func(request, *args, **kwargs)
    return wrapper


def require_role(*role_names):
    """
    Декоратор для проверки наличия определенной роли
    
    Args:
        *role_names: Названия ролей, любая из которых должна быть у пользователя
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({'error': 'Требуется аутентификация'}, status=401)
                messages.error(request, 'Требуется вход в систему')
                return redirect('login_view')
            
            # Суперпользователь имеет все роли
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Проверяем роли пользователя
            user_roles = PermissionChecker.get_user_roles(request.user)
            user_role_names = [ur.role.name for ur in user_roles if ur.is_valid]
            
            if not any(role_name in user_role_names for role_name in role_names):
                error_message = f"Требуется одна из ролей: {', '.join(role_names)}"
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({'error': error_message}, status=403)
                messages.error(request, error_message)
                return HttpResponseForbidden(f"<h1>Доступ запрещен</h1><p>{error_message}</p>")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_permission_codename(permission_codename, error_message=None):
    """
    Декоратор для проверки конкретного права по кодовому имени
    
    Args:
        permission_codename: Кодовое имя права
        error_message: Сообщение об ошибке
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({'error': 'Требуется аутентификация'}, status=401)
                messages.error(request, 'Требуется вход в систему')
                return redirect('login_view')
            
            # Проверяем право
            has_permission = PermissionChecker.has_permission(request.user, permission_codename)
            
            if not has_permission:
                error_msg = error_message or f"У вас нет права: {permission_codename}"
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({'error': error_msg}, status=403)
                messages.error(request, error_msg)
                return HttpResponseForbidden(f"<h1>Доступ запрещен</h1><p>{error_msg}</p>")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# ДЕКОРАТОРЫ ДЛЯ КОНКРЕТНЫХ ДЕЙСТВИЙ
# =============================================================================

def can_view_employee(view_func):
    """Декоратор для проверки права просмотра сотрудника"""
    return require_permission(PermissionChecker.can_view_employee, 
                            "У вас нет прав для просмотра данных сотрудника")(view_func)


def can_edit_employee(view_func):
    """Декоратор для проверки права редактирования сотрудника"""
    return require_permission(PermissionChecker.can_edit_employee, 
                            "У вас нет прав для редактирования данных сотрудника")(view_func)


def can_manage_skud_devices(view_func):
    """Декоратор для проверки права управления СКУД устройствами"""
    return require_permission(PermissionChecker.can_manage_skud_devices, 
                            "У вас нет прав для управления СКУД устройствами")(view_func)


def can_view_reports(view_func):
    """Декоратор для проверки права просмотра отчетов"""
    return require_permission(PermissionChecker.can_view_reports, 
                            "У вас нет прав для просмотра отчетов")(view_func)


def can_export_data(view_func):
    """Декоратор для проверки права экспорта данных"""
    return require_permission(PermissionChecker.can_export_data, 
                            "У вас нет прав для экспорта данных")(view_func)


def can_approve_vacation(view_func):
    """Декоратор для проверки права утверждения отпуска"""
    return require_permission(PermissionChecker.can_approve_vacation, 
                            "У вас нет прав для утверждения отпусков")(view_func)


def can_manage_roles(view_func):
    """Декоратор для проверки права управления ролями"""
    return require_permission(PermissionChecker.can_manage_roles, 
                            "У вас нет прав для управления ролями")(view_func)


# =============================================================================
# ДЕКОРАТОРЫ ДЛЯ КЛАССОВ (CBV)
# =============================================================================

def class_view_decorator(decorator):
    """Декоратор для применения к методам класса"""
    def wrapper(cls):
        if hasattr(cls, 'dispatch'):
            cls.dispatch = method_decorator(decorator)(cls.dispatch)
        return cls
    return wrapper


# =============================================================================
# КОМБИНИРОВАННЫЕ ДЕКОРАТОРЫ
# =============================================================================

def hr_required(view_func):
    """Декоратор для HR-менеджеров"""
    return require_role('HR-менеджер')(view_func)


def manager_required(view_func):
    """Декоратор для руководителей (департамента или отдела)"""
    return require_role('Руководитель департамента', 'Руководитель отдела')(view_func)


def analyst_required(view_func):
    """Декоратор для аналитиков"""
    return require_role('Аналитик')(view_func)


def skud_operator_required(view_func):
    """Декоратор для СКУД-операторов"""
    return require_role('СКУД-оператор')(view_func)


# =============================================================================
# УТИЛИТЫ ДЛЯ ПРОВЕРКИ ПРАВ В ШАБЛОНАХ
# =============================================================================

def has_permission_in_template(user, permission_codename):
    """Функция для использования в шаблонах"""
    return PermissionChecker.has_permission(user, permission_codename)


def can_view_employee_in_template(user, employee):
    """Функция для проверки права просмотра сотрудника в шаблонах"""
    return PermissionChecker.can_view_employee(user, employee)


def can_edit_employee_in_template(user, employee):
    """Функция для проверки права редактирования сотрудника в шаблонах"""
    return PermissionChecker.can_edit_employee(user, employee)


def can_manage_skud_devices_in_template(user, device=None):
    """Функция для проверки права управления СКУД устройствами в шаблонах"""
    return PermissionChecker.can_manage_skud_devices(user, device)


def can_view_reports_in_template(user):
    """Функция для проверки права просмотра отчетов в шаблонах"""
    return PermissionChecker.can_view_reports(user)


def can_export_data_in_template(user):
    """Функция для проверки права экспорта данных в шаблонах"""
    return PermissionChecker.can_export_data(user)


def can_approve_vacation_in_template(user, vacation):
    """Функция для проверки права утверждения отпуска в шаблонах"""
    return PermissionChecker.can_approve_vacation(user, vacation)


def can_manage_roles_in_template(user):
    """Функция для проверки права управления ролями в шаблонах"""
    return PermissionChecker.can_manage_roles(user)


def get_user_accessible_employees_in_template(user):
    """Функция для получения доступных сотрудников в шаблонах"""
    return PermissionChecker.get_accessible_employees(user)


def get_user_role_info_in_template(user):
    """Функция для получения информации о ролях пользователя в шаблонах"""
    return PermissionChecker.get_user_role_info(user)
