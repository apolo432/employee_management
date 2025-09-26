"""
Система проверки прав доступа для приложения управления сотрудниками
"""

from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
from typing import List, Optional, Union
import logging

from .models import (
    Role, Permission, UserRole, AccessLog, TemporaryPermission,
    Employee, Organization, Department, Division, SKUDDevice, SKUDEvent,
    Vacation, BusinessTrip, WorkSession, WorkDaySummary
)

logger = logging.getLogger(__name__)


class PermissionChecker:
    """Основной класс для проверки прав доступа"""
    
    @staticmethod
    def log_access(user: User, action: str, object_type: str, object_id: str = None, 
                   object_name: str = None, success: bool = True, 
                   error_message: str = None, request=None):
        """Логирование доступа к данным"""
        try:
            AccessLog.objects.create(
                user=user,
                action=action,
                object_type=object_type,
                object_id=object_id,
                object_name=object_name,
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1') if request else '127.0.0.1',
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
                url=request.build_absolute_uri() if request else '',
                method=request.method if request else '',
                success=success,
                error_message=error_message or ''
            )
        except Exception as e:
            logger.error(f"Ошибка логирования доступа: {e}")
    
    @staticmethod
    def get_user_roles(user: User) -> List[UserRole]:
        """Получить все активные роли пользователя"""
        if not user or not user.is_authenticated:
            return []
        
        now = timezone.now()
        return UserRole.objects.filter(
            user=user,
            is_active=True,
            valid_from__lte=now
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gt=now)
        ).select_related('role', 'organization', 'department', 'division', 'employee')
    
    @staticmethod
    def get_user_permissions(user: User) -> List[Permission]:
        """Получить все права пользователя через роли"""
        if not user or not user.is_authenticated:
            return []
        
        user_roles = PermissionChecker.get_user_roles(user)
        role_ids = [ur.role.id for ur in user_roles]
        
        return Permission.objects.filter(
            role_permissions__role_id__in=role_ids,
            is_active=True
        ).distinct()
    
    @staticmethod
    def has_permission(user: User, permission_codename: str, 
                      organization: Organization = None,
                      department: Department = None,
                      division: Division = None,
                      employee: Employee = None) -> bool:
        """Проверить, есть ли у пользователя конкретное право"""
        if not user or not user.is_authenticated:
            return False
        
        # Суперпользователь имеет все права
        if user.is_superuser:
            return True
        
        # Проверяем временные права
        if PermissionChecker.has_temporary_permission(user, permission_codename, organization, department, division, employee):
            return True
        
        # Получаем роли пользователя
        user_roles = PermissionChecker.get_user_roles(user)
        
        # Проверяем права через роли
        for user_role in user_roles:
            if not user_role.is_valid:
                continue
            
            # Проверяем область действия роли
            if not PermissionChecker._check_role_scope(user_role, organization, department, division, employee):
                continue
            
            # Проверяем, есть ли у роли нужное право
            if user_role.role.role_permissions.filter(
                permission__codename=permission_codename,
                permission__is_active=True
            ).exists():
                return True
        
        return False
    
    @staticmethod
    def has_temporary_permission(user: User, permission_codename: str,
                               organization: Organization = None,
                               department: Department = None,
                               division: Division = None,
                               employee: Employee = None) -> bool:
        """Проверить временные права доступа"""
        if not user or not user.is_authenticated:
            return False
        
        now = timezone.now()
        temp_permissions = TemporaryPermission.objects.filter(
            user=user,
            permission__codename=permission_codename,
            is_active=True,
            valid_from__lte=now,
            valid_until__gte=now
        )
        
        for temp_perm in temp_permissions:
            # Проверяем соответствие объекта
            if temp_perm.object_type == 'organization' and organization and str(organization.id) == str(temp_perm.object_id):
                return True
            elif temp_perm.object_type == 'department' and department and str(department.id) == str(temp_perm.object_id):
                return True
            elif temp_perm.object_type == 'division' and division and str(division.id) == str(temp_perm.object_id):
                return True
            elif temp_perm.object_type == 'employee' and employee and str(employee.id) == str(temp_perm.object_id):
                return True
            elif temp_perm.object_type == 'global':
                return True
        
        return False
    
    @staticmethod
    def _check_role_scope(user_role: UserRole, organization: Organization = None,
                         department: Department = None, division: Division = None,
                         employee: Employee = None) -> bool:
        """Проверить область действия роли"""
        if user_role.scope_type == 'global':
            return True
        elif user_role.scope_type == 'organization' and organization:
            return user_role.organization == organization
        elif user_role.scope_type == 'department' and department:
            return user_role.department == department
        elif user_role.scope_type == 'division' and division:
            return user_role.division == division
        elif user_role.scope_type == 'employee' and employee:
            return user_role.employee == employee
        
        return False
    
    # =============================================================================
    # СПЕЦИФИЧНЫЕ ПРОВЕРКИ ПРАВ ДЛЯ РАЗЛИЧНЫХ ОБЪЕКТОВ
    # =============================================================================
    
    @staticmethod
    def can_view_employee(user: User, employee: Employee, request=None) -> bool:
        """Может ли пользователь просматривать сотрудника"""
        if not user or not user.is_authenticated or not employee:
            return False
        
        # Суперпользователь может видеть всех
        if user.is_superuser:
            PermissionChecker.log_access(user, 'view', 'Employee', str(employee.id), 
                                       employee.full_name, True, request=request)
            return True
        
        # Сотрудник может видеть только себя
        if hasattr(user, 'employee_profile') and user.employee_profile == employee:
            PermissionChecker.log_access(user, 'view', 'Employee', str(employee.id), 
                                       employee.full_name, True, request=request)
            return True
        
        # Проверяем права через роли
        user_roles = PermissionChecker.get_user_roles(user)
        
        for user_role in user_roles:
            if not user_role.is_valid:
                continue
            
            role_name = user_role.role.name
            
            # HR-менеджер может видеть всех
            if role_name == 'HR-менеджер':
                PermissionChecker.log_access(user, 'view', 'Employee', str(employee.id), 
                                           employee.full_name, True, request=request)
                return True
            
            # Руководитель департамента видит свой департамент
            if role_name == 'Руководитель департамента':
                if (user_role.department and employee.department == user_role.department) or \
                   (user_role.scope_type == 'global'):
                    PermissionChecker.log_access(user, 'view', 'Employee', str(employee.id), 
                                               employee.full_name, True, request=request)
                    return True
            
            # Руководитель отдела видит свой отдел
            if role_name == 'Руководитель отдела':
                if (user_role.division and employee.division == user_role.division) or \
                   (user_role.scope_type == 'global'):
                    PermissionChecker.log_access(user, 'view', 'Employee', str(employee.id), 
                                               employee.full_name, True, request=request)
                    return True
            
            # Аналитик может видеть всех (только для просмотра)
            if role_name == 'Аналитик':
                PermissionChecker.log_access(user, 'view', 'Employee', str(employee.id), 
                                           employee.full_name, True, request=request)
                return True
        
        # Логируем отказ в доступе
        PermissionChecker.log_access(user, 'deny', 'Employee', str(employee.id), 
                                   employee.full_name, False, "Нет прав для просмотра сотрудника", request=request)
        return False
    
    @staticmethod
    def can_edit_employee(user: User, employee: Employee, request=None) -> bool:
        """Может ли пользователь редактировать сотрудника"""
        if not user or not user.is_authenticated or not employee:
            return False
        
        # Суперпользователь может редактировать всех
        if user.is_superuser:
            PermissionChecker.log_access(user, 'change', 'Employee', str(employee.id), 
                                       employee.full_name, True, request=request)
            return True
        
        # Сотрудник может редактировать только свои данные (ограниченно)
        if hasattr(user, 'employee_profile') and user.employee_profile == employee:
            # Сотрудник может редактировать только личные данные, не рабочие
            PermissionChecker.log_access(user, 'change', 'Employee', str(employee.id), 
                                       employee.full_name, True, request=request)
            return True
        
        # Проверяем права через роли
        user_roles = PermissionChecker.get_user_roles(user)
        
        for user_role in user_roles:
            if not user_role.is_valid:
                continue
            
            role_name = user_role.role.name
            
            # HR-менеджер может редактировать всех
            if role_name == 'HR-менеджер':
                PermissionChecker.log_access(user, 'change', 'Employee', str(employee.id), 
                                           employee.full_name, True, request=request)
                return True
            
            # Руководитель департамента может редактировать свой департамент
            if role_name == 'Руководитель департамента':
                if (user_role.department and employee.department == user_role.department) or \
                   (user_role.scope_type == 'global'):
                    PermissionChecker.log_access(user, 'change', 'Employee', str(employee.id), 
                                               employee.full_name, True, request=request)
                    return True
            
            # Руководитель отдела может редактировать свой отдел
            if role_name == 'Руководитель отдела':
                if (user_role.division and employee.division == user_role.division) or \
                   (user_role.scope_type == 'global'):
                    PermissionChecker.log_access(user, 'change', 'Employee', str(employee.id), 
                                               employee.full_name, True, request=request)
                    return True
        
        # Логируем отказ в доступе
        PermissionChecker.log_access(user, 'deny', 'Employee', str(employee.id), 
                                   employee.full_name, False, "Нет прав для редактирования сотрудника", request=request)
        return False
    
    @staticmethod
    def can_manage_skud_devices(user: User, device: SKUDDevice = None, request=None) -> bool:
        """Может ли пользователь управлять СКУД устройствами"""
        if not user or not user.is_authenticated:
            return False
        
        # Суперпользователь может управлять всеми устройствами
        if user.is_superuser:
            if device:
                PermissionChecker.log_access(user, 'manage', 'SKUDDevice', str(device.id), 
                                           device.name, True, request=request)
            return True
        
        # Проверяем права через роли
        user_roles = PermissionChecker.get_user_roles(user)
        
        for user_role in user_roles:
            if not user_role.is_valid:
                continue
            
            role_name = user_role.role.name
            
            # HR-менеджер и СКУД-оператор могут управлять устройствами
            if role_name in ['HR-менеджер', 'СКУД-оператор']:
                if device:
                    PermissionChecker.log_access(user, 'manage', 'SKUDDevice', str(device.id), 
                                               device.name, True, request=request)
                return True
        
        # Логируем отказ в доступе
        if device:
            PermissionChecker.log_access(user, 'deny', 'SKUDDevice', str(device.id), 
                                       device.name, False, "Нет прав для управления СКУД устройствами", request=request)
        return False
    
    @staticmethod
    def can_view_reports(user: User, request=None) -> bool:
        """Может ли пользователь просматривать отчеты"""
        if not user or not user.is_authenticated:
            return False
        
        # Суперпользователь может видеть все отчеты
        if user.is_superuser:
            PermissionChecker.log_access(user, 'view', 'Reports', None, 'Отчеты', True, request=request)
            return True
        
        # Проверяем права через роли
        user_roles = PermissionChecker.get_user_roles(user)
        
        for user_role in user_roles:
            if not user_role.is_valid:
                continue
            
            role_name = user_role.role.name
            
            # HR-менеджер, руководители и аналитик могут видеть отчеты
            if role_name in ['HR-менеджер', 'Руководитель департамента', 'Руководитель отдела', 'Аналитик']:
                PermissionChecker.log_access(user, 'view', 'Reports', None, 'Отчеты', True, request=request)
                return True
        
        # Логируем отказ в доступе
        PermissionChecker.log_access(user, 'deny', 'Reports', None, 'Отчеты', False, 
                                   "Нет прав для просмотра отчетов", request=request)
        return False
    
    @staticmethod
    def can_export_data(user: User, request=None) -> bool:
        """Может ли пользователь экспортировать данные"""
        if not user or not user.is_authenticated:
            return False
        
        # Суперпользователь может экспортировать все
        if user.is_superuser:
            PermissionChecker.log_access(user, 'export', 'Data', None, 'Экспорт данных', True, request=request)
            return True
        
        # Проверяем права через роли
        user_roles = PermissionChecker.get_user_roles(user)
        
        for user_role in user_roles:
            if not user_role.is_valid:
                continue
            
            role_name = user_role.role.name
            
            # HR-менеджер и аналитик могут экспортировать данные
            if role_name in ['HR-менеджер', 'Аналитик']:
                PermissionChecker.log_access(user, 'export', 'Data', None, 'Экспорт данных', True, request=request)
                return True
        
        # Логируем отказ в доступе
        PermissionChecker.log_access(user, 'deny', 'Data', None, 'Экспорт данных', False, 
                                   "Нет прав для экспорта данных", request=request)
        return False
    
    @staticmethod
    def can_approve_vacation(user: User, vacation: Vacation, request=None) -> bool:
        """Может ли пользователь утверждать отпуск"""
        if not user or not user.is_authenticated or not vacation:
            return False
        
        # Суперпользователь может утверждать все отпуска
        if user.is_superuser:
            PermissionChecker.log_access(user, 'approve', 'Vacation', str(vacation.id), 
                                       f"Отпуск {vacation.employee.full_name}", True, request=request)
            return True
        
        # Проверяем права через роли
        user_roles = PermissionChecker.get_user_roles(user)
        
        for user_role in user_roles:
            if not user_role.is_valid:
                continue
            
            role_name = user_role.role.name
            
            # HR-менеджер может утверждать все отпуска
            if role_name == 'HR-менеджер':
                PermissionChecker.log_access(user, 'approve', 'Vacation', str(vacation.id), 
                                           f"Отпуск {vacation.employee.full_name}", True, request=request)
                return True
            
            # Руководитель департамента может утверждать отпуска своего департамента
            if role_name == 'Руководитель департамента':
                if (user_role.department and vacation.employee.department == user_role.department) or \
                   (user_role.scope_type == 'global'):
                    PermissionChecker.log_access(user, 'approve', 'Vacation', str(vacation.id), 
                                               f"Отпуск {vacation.employee.full_name}", True, request=request)
                    return True
        
        # Логируем отказ в доступе
        PermissionChecker.log_access(user, 'deny', 'Vacation', str(vacation.id), 
                                   f"Отпуск {vacation.employee.full_name}", False, 
                                   "Нет прав для утверждения отпуска", request=request)
        return False
    
    @staticmethod
    def can_manage_roles(user: User, request=None) -> bool:
        """Может ли пользователь управлять ролями"""
        if not user or not user.is_authenticated:
            return False
        
        # Только суперпользователь может управлять ролями
        if user.is_superuser:
            PermissionChecker.log_access(user, 'manage', 'Roles', None, 'Управление ролями', True, request=request)
            return True
        
        # Логируем отказ в доступе
        PermissionChecker.log_access(user, 'deny', 'Roles', None, 'Управление ролями', False, 
                                   "Только суперпользователь может управлять ролями", request=request)
        return False
    
    @staticmethod
    def get_accessible_employees(user: User) -> List[Employee]:
        """Получить список сотрудников, к которым у пользователя есть доступ"""
        if not user or not user.is_authenticated:
            return Employee.objects.none()
        
        # Суперпользователь видит всех
        if user.is_superuser:
            return Employee.objects.filter(is_active=True)
        
        accessible_ids = []
        user_roles = PermissionChecker.get_user_roles(user)
        
        for user_role in user_roles:
            if not user_role.is_valid:
                continue
            
            role_name = user_role.role.name
            
            # HR-менеджер видит всех
            if role_name == 'HR-менеджер':
                return Employee.objects.filter(is_active=True)
            
            # Руководитель департамента видит свой департамент
            if role_name == 'Руководитель департамента':
                if user_role.department:
                    dept_employees = Employee.objects.filter(
                        is_active=True,
                        department=user_role.department
                    ).values_list('id', flat=True)
                    accessible_ids.extend(dept_employees)
                elif user_role.scope_type == 'global':
                    return Employee.objects.filter(is_active=True)
            
            # Руководитель отдела видит свой отдел
            if role_name == 'Руководитель отдела':
                if user_role.division:
                    div_employees = Employee.objects.filter(
                        is_active=True,
                        division=user_role.division
                    ).values_list('id', flat=True)
                    accessible_ids.extend(div_employees)
                elif user_role.scope_type == 'global':
                    return Employee.objects.filter(is_active=True)
            
            # Аналитик видит всех (только для просмотра)
            if role_name == 'Аналитик':
                return Employee.objects.filter(is_active=True)
        
        # Сотрудник видит только себя
        if hasattr(user, 'employee_profile') and user.employee_profile:
            accessible_ids.append(user.employee_profile.id)
        
        return Employee.objects.filter(id__in=set(accessible_ids), is_active=True)
    
    @staticmethod
    def get_user_role_info(user: User) -> dict:
        """Получить информацию о ролях пользователя"""
        if not user or not user.is_authenticated:
            return {'roles': [], 'permissions': [], 'is_superuser': False}
        
        user_roles = PermissionChecker.get_user_roles(user)
        permissions = PermissionChecker.get_user_permissions(user)
        
        return {
            'roles': [
                {
                    'name': ur.role.name,
                    'scope_type': ur.scope_type,
                    'organization': ur.organization.name if ur.organization else None,
                    'department': ur.department.name if ur.department else None,
                    'division': ur.division.name if ur.division else None,
                    'employee': ur.employee.full_name if ur.employee else None,
                    'valid_until': ur.valid_until,
                    'is_valid': ur.is_valid
                }
                for ur in user_roles
            ],
            'permissions': [p.codename for p in permissions],
            'is_superuser': user.is_superuser
        }
