"""
Инициализация предопределенных ролей и прав доступа
"""

from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone
import logging

from .models import (
    Role, Permission, RolePermission, UserRole,
    Organization, Department, Division, Employee
)

logger = logging.getLogger(__name__)


class RoleInitializer:
    """Класс для инициализации ролей и прав доступа"""
    
    # Предопределенные права доступа
    PERMISSIONS = [
        # Права для сотрудников
        {'codename': 'view_employee', 'name': 'Просмотр сотрудника', 'app_label': 'employees', 'model_name': 'Employee', 'permission_type': 'view'},
        {'codename': 'add_employee', 'name': 'Добавление сотрудника', 'app_label': 'employees', 'model_name': 'Employee', 'permission_type': 'add'},
        {'codename': 'change_employee', 'name': 'Изменение сотрудника', 'app_label': 'employees', 'model_name': 'Employee', 'permission_type': 'change'},
        {'codename': 'delete_employee', 'name': 'Удаление сотрудника', 'app_label': 'employees', 'model_name': 'Employee', 'permission_type': 'delete'},
        
        # Права для СКУД устройств
        {'codename': 'view_skud_device', 'name': 'Просмотр СКУД устройства', 'app_label': 'employees', 'model_name': 'SKUDDevice', 'permission_type': 'view'},
        {'codename': 'add_skud_device', 'name': 'Добавление СКУД устройства', 'app_label': 'employees', 'model_name': 'SKUDDevice', 'permission_type': 'add'},
        {'codename': 'change_skud_device', 'name': 'Изменение СКУД устройства', 'app_label': 'employees', 'model_name': 'SKUDDevice', 'permission_type': 'change'},
        {'codename': 'delete_skud_device', 'name': 'Удаление СКУД устройства', 'app_label': 'employees', 'model_name': 'SKUDDevice', 'permission_type': 'delete'},
        {'codename': 'manage_skud_device', 'name': 'Управление СКУД устройством', 'app_label': 'employees', 'model_name': 'SKUDDevice', 'permission_type': 'manage'},
        
        # Права для событий СКУД
        {'codename': 'view_skud_event', 'name': 'Просмотр события СКУД', 'app_label': 'employees', 'model_name': 'SKUDEvent', 'permission_type': 'view'},
        {'codename': 'add_skud_event', 'name': 'Добавление события СКУД', 'app_label': 'employees', 'model_name': 'SKUDEvent', 'permission_type': 'add'},
        {'codename': 'change_skud_event', 'name': 'Изменение события СКУД', 'app_label': 'employees', 'model_name': 'SKUDEvent', 'permission_type': 'change'},
        {'codename': 'delete_skud_event', 'name': 'Удаление события СКУД', 'app_label': 'employees', 'model_name': 'SKUDEvent', 'permission_type': 'delete'},
        
        # Права для отпусков
        {'codename': 'view_vacation', 'name': 'Просмотр отпуска', 'app_label': 'employees', 'model_name': 'Vacation', 'permission_type': 'view'},
        {'codename': 'add_vacation', 'name': 'Добавление отпуска', 'app_label': 'employees', 'model_name': 'Vacation', 'permission_type': 'add'},
        {'codename': 'change_vacation', 'name': 'Изменение отпуска', 'app_label': 'employees', 'model_name': 'Vacation', 'permission_type': 'change'},
        {'codename': 'delete_vacation', 'name': 'Удаление отпуска', 'app_label': 'employees', 'model_name': 'Vacation', 'permission_type': 'delete'},
        {'codename': 'approve_vacation', 'name': 'Утверждение отпуска', 'app_label': 'employees', 'model_name': 'Vacation', 'permission_type': 'approve'},
        
        # Права для командировок
        {'codename': 'view_business_trip', 'name': 'Просмотр командировки', 'app_label': 'employees', 'model_name': 'BusinessTrip', 'permission_type': 'view'},
        {'codename': 'add_business_trip', 'name': 'Добавление командировки', 'app_label': 'employees', 'model_name': 'BusinessTrip', 'permission_type': 'add'},
        {'codename': 'change_business_trip', 'name': 'Изменение командировки', 'app_label': 'employees', 'model_name': 'BusinessTrip', 'permission_type': 'change'},
        {'codename': 'delete_business_trip', 'name': 'Удаление командировки', 'app_label': 'employees', 'model_name': 'BusinessTrip', 'permission_type': 'delete'},
        {'codename': 'approve_business_trip', 'name': 'Утверждение командировки', 'app_label': 'employees', 'model_name': 'BusinessTrip', 'permission_type': 'approve'},
        
        # Права для рабочего времени
        {'codename': 'view_work_time', 'name': 'Просмотр рабочего времени', 'app_label': 'employees', 'model_name': 'WorkSession', 'permission_type': 'view'},
        {'codename': 'change_work_time', 'name': 'Изменение рабочего времени', 'app_label': 'employees', 'model_name': 'WorkSession', 'permission_type': 'change'},
        {'codename': 'export_work_time', 'name': 'Экспорт рабочего времени', 'app_label': 'employees', 'model_name': 'WorkSession', 'permission_type': 'export'},
        
        # Права для отчетов
        {'codename': 'view_reports', 'name': 'Просмотр отчетов', 'app_label': 'employees', 'model_name': 'Reports', 'permission_type': 'view'},
        {'codename': 'export_reports', 'name': 'Экспорт отчетов', 'app_label': 'employees', 'model_name': 'Reports', 'permission_type': 'export'},
        
        # Права для ролей
        {'codename': 'view_role', 'name': 'Просмотр роли', 'app_label': 'employees', 'model_name': 'Role', 'permission_type': 'view'},
        {'codename': 'add_role', 'name': 'Добавление роли', 'app_label': 'employees', 'model_name': 'Role', 'permission_type': 'add'},
        {'codename': 'change_role', 'name': 'Изменение роли', 'app_label': 'employees', 'model_name': 'Role', 'permission_type': 'change'},
        {'codename': 'delete_role', 'name': 'Удаление роли', 'app_label': 'employees', 'model_name': 'Role', 'permission_type': 'delete'},
        {'codename': 'manage_roles', 'name': 'Управление ролями', 'app_label': 'employees', 'model_name': 'Role', 'permission_type': 'manage'},
        
        # Права для организационной структуры
        {'codename': 'view_organization', 'name': 'Просмотр организации', 'app_label': 'employees', 'model_name': 'Organization', 'permission_type': 'view'},
        {'codename': 'view_department', 'name': 'Просмотр департамента', 'app_label': 'employees', 'model_name': 'Department', 'permission_type': 'view'},
        {'codename': 'view_division', 'name': 'Просмотр отдела', 'app_label': 'employees', 'model_name': 'Division', 'permission_type': 'view'},
    ]
    
    # Предопределенные роли с их правами
    ROLES = {
        'Супер-администратор': {
            'description': 'Полный доступ ко всем данным, управление ролями и правами, системные настройки',
            'is_system_role': True,
            'permissions': [perm['codename'] for perm in PERMISSIONS],  # Все права
        },
        'HR-менеджер': {
            'description': 'Управление сотрудниками, отчеты, управление СКУД устройствами',
            'is_system_role': True,
            'permissions': [
                'view_employee', 'add_employee', 'change_employee', 'delete_employee',
                'view_skud_device', 'add_skud_device', 'change_skud_device', 'delete_skud_device', 'manage_skud_device',
                'view_skud_event', 'add_skud_event', 'change_skud_event', 'delete_skud_event',
                'view_vacation', 'add_vacation', 'change_vacation', 'delete_vacation', 'approve_vacation',
                'view_business_trip', 'add_business_trip', 'change_business_trip', 'delete_business_trip', 'approve_business_trip',
                'view_work_time', 'change_work_time', 'export_work_time',
                'view_reports', 'export_reports',
                'view_organization', 'view_department', 'view_division',
            ],
        },
        'Руководитель департамента': {
            'description': 'Управление своим департаментом, утверждение отпусков, отчеты по департаменту',
            'is_system_role': True,
            'permissions': [
                'view_employee', 'change_employee',
                'view_skud_event',
                'view_vacation', 'add_vacation', 'change_vacation', 'approve_vacation',
                'view_business_trip', 'add_business_trip', 'change_business_trip', 'approve_business_trip',
                'view_work_time', 'change_work_time',
                'view_reports', 'export_reports',
                'view_organization', 'view_department', 'view_division',
            ],
        },
        'Руководитель отдела': {
            'description': 'Управление своим отделом, редактирование данных подчиненных, отчеты по отделу',
            'is_system_role': True,
            'permissions': [
                'view_employee', 'change_employee',
                'view_skud_event',
                'view_vacation', 'add_vacation', 'change_vacation',
                'view_business_trip', 'add_business_trip', 'change_business_trip',
                'view_work_time', 'change_work_time',
                'view_reports',
                'view_organization', 'view_department', 'view_division',
            ],
        },
        'Сотрудник': {
            'description': 'Просмотр своих данных, просмотр своего рабочего времени, подача заявок на отпуск',
            'is_system_role': True,
            'permissions': [
                'view_employee',  # Только свои данные
                'view_vacation', 'add_vacation',  # Только свои отпуска
                'view_business_trip', 'add_business_trip',  # Только свои командировки
                'view_work_time',  # Только свое рабочее время
                'view_organization', 'view_department', 'view_division',
            ],
        },
        'СКУД-оператор': {
            'description': 'Управление СКУД устройствами, просмотр событий СКУД, техническая поддержка',
            'is_system_role': True,
            'permissions': [
                'view_skud_device', 'add_skud_device', 'change_skud_device', 'delete_skud_device', 'manage_skud_device',
                'view_skud_event', 'add_skud_event', 'change_skud_event', 'delete_skud_event',
                'view_employee',  # Для идентификации сотрудников
                'view_organization', 'view_department', 'view_division',
            ],
        },
        'Аналитик': {
            'description': 'Просмотр отчетов, экспорт данных, аналитика (только чтение)',
            'is_system_role': True,
            'permissions': [
                'view_employee',  # Только для аналитики
                'view_skud_event',
                'view_vacation', 'view_business_trip',
                'view_work_time',
                'view_reports', 'export_reports',
                'view_organization', 'view_department', 'view_division',
            ],
        },
    }
    
    @classmethod
    def initialize_permissions(cls):
        """Создание предопределенных прав доступа"""
        logger.info("Инициализация прав доступа...")
        
        created_count = 0
        for perm_data in cls.PERMISSIONS:
            permission, created = Permission.objects.get_or_create(
                codename=perm_data['codename'],
                defaults={
                    'name': perm_data['name'],
                    'app_label': perm_data['app_label'],
                    'model_name': perm_data['model_name'],
                    'permission_type': perm_data['permission_type'],
                    'description': f"Право {perm_data['name'].lower()}"
                }
            )
            if created:
                created_count += 1
                logger.info(f"Создано право: {permission.name}")
        
        logger.info(f"Создано {created_count} новых прав доступа")
        return created_count
    
    @classmethod
    def initialize_roles(cls):
        """Создание предопределенных ролей"""
        logger.info("Инициализация ролей...")
        
        created_count = 0
        for role_name, role_data in cls.ROLES.items():
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={
                    'description': role_data['description'],
                    'is_system_role': role_data['is_system_role'],
                    'role_type': 'system' if role_data['is_system_role'] else 'business'
                }
            )
            
            if created:
                created_count += 1
                logger.info(f"Создана роль: {role.name}")
            
            # Назначаем права роли
            cls._assign_permissions_to_role(role, role_data['permissions'])
        
        logger.info(f"Создано {created_count} новых ролей")
        return created_count
    
    @classmethod
    def _assign_permissions_to_role(cls, role, permission_codenames):
        """Назначение прав роли"""
        for codename in permission_codenames:
            try:
                permission = Permission.objects.get(codename=codename)
                RolePermission.objects.get_or_create(
                    role=role,
                    permission=permission
                )
            except Permission.DoesNotExist:
                logger.warning(f"Право {codename} не найдено для роли {role.name}")
    
    @classmethod
    def assign_default_roles(cls):
        """Назначение ролей по умолчанию существующим пользователям"""
        logger.info("Назначение ролей по умолчанию...")
        
        # Получаем первую организацию (если есть)
        try:
            organization = Organization.objects.first()
        except Organization.DoesNotExist:
            logger.warning("Организация не найдена, роли будут назначены без привязки к организации")
            organization = None
        
        assigned_count = 0
        
        # Назначаем роль "Сотрудник" всем пользователям, у которых есть профиль сотрудника
        employee_role = Role.objects.filter(name='Сотрудник').first()
        if employee_role:
            for user in User.objects.filter(employee_profile__isnull=False):
                # Проверяем, есть ли уже роль у пользователя
                if not UserRole.objects.filter(user=user, role=employee_role).exists():
                    UserRole.objects.create(
                        user=user,
                        role=employee_role,
                        scope_type='employee',
                        employee=user.employee_profile,
                        organization=organization,
                        department=user.employee_profile.department if hasattr(user.employee_profile, 'department') else None,
                        division=user.employee_profile.division if hasattr(user.employee_profile, 'division') else None,
                        reason='Автоматическое назначение роли по умолчанию'
                    )
                    assigned_count += 1
                    logger.info(f"Назначена роль 'Сотрудник' пользователю {user.username}")
        
        logger.info(f"Назначено {assigned_count} ролей по умолчанию")
        return assigned_count
    
    @classmethod
    def create_superuser_role(cls, user):
        """Создание роли супер-администратора для пользователя"""
        if not user.is_superuser:
            logger.warning(f"Пользователь {user.username} не является суперпользователем")
            return False
        
        superuser_role = Role.objects.filter(name='Супер-администратор').first()
        if not superuser_role:
            logger.error("Роль 'Супер-администратор' не найдена")
            return False
        
        # Проверяем, есть ли уже роль у пользователя
        if UserRole.objects.filter(user=user, role=superuser_role).exists():
            logger.info(f"Роль 'Супер-администратор' уже назначена пользователю {user.username}")
            return True
        
        # Получаем первую организацию
        organization = Organization.objects.first()
        
        UserRole.objects.create(
            user=user,
            role=superuser_role,
            scope_type='global',
            organization=organization,
            reason='Автоматическое назначение роли супер-администратора'
        )
        
        logger.info(f"Назначена роль 'Супер-администратор' пользователю {user.username}")
        return True
    
    @classmethod
    def initialize_all(cls):
        """Полная инициализация системы ролей"""
        logger.info("Начало инициализации системы ролей...")
        
        with transaction.atomic():
            # Создаем права доступа
            permissions_created = cls.initialize_permissions()
            
            # Создаем роли
            roles_created = cls.initialize_roles()
            
            # Назначаем роли по умолчанию
            roles_assigned = cls.assign_default_roles()
            
            # Назначаем роль супер-администратора всем суперпользователям
            superuser_roles_assigned = 0
            for user in User.objects.filter(is_superuser=True):
                if cls.create_superuser_role(user):
                    superuser_roles_assigned += 1
        
        logger.info(f"Инициализация завершена:")
        logger.info(f"  - Создано прав доступа: {permissions_created}")
        logger.info(f"  - Создано ролей: {roles_created}")
        logger.info(f"  - Назначено ролей по умолчанию: {roles_assigned}")
        logger.info(f"  - Назначено ролей супер-администратора: {superuser_roles_assigned}")
        
        return {
            'permissions_created': permissions_created,
            'roles_created': roles_created,
            'roles_assigned': roles_assigned,
            'superuser_roles_assigned': superuser_roles_assigned
        }
    
    @classmethod
    def reset_roles(cls):
        """Сброс всех ролей (только для разработки!)"""
        logger.warning("Сброс всех ролей и прав доступа...")
        
        with transaction.atomic():
            # Удаляем все связи ролей с пользователями
            UserRole.objects.all().delete()
            
            # Удаляем все связи ролей с правами
            RolePermission.objects.all().delete()
            
            # Удаляем все роли (кроме системных, если нужно)
            Role.objects.all().delete()
            
            # Удаляем все права доступа
            Permission.objects.all().delete()
        
        logger.info("Все роли и права доступа удалены")
    
    @classmethod
    def get_role_statistics(cls):
        """Получение статистики по ролям"""
        stats = {
            'total_roles': Role.objects.count(),
            'total_permissions': Permission.objects.count(),
            'total_user_roles': UserRole.objects.count(),
            'active_user_roles': UserRole.objects.filter(is_active=True).count(),
            'roles_by_name': {},
            'permissions_by_type': {},
        }
        
        # Статистика по ролям
        for role in Role.objects.all():
            user_count = UserRole.objects.filter(role=role, is_active=True).count()
            stats['roles_by_name'][role.name] = {
                'user_count': user_count,
                'permission_count': role.role_permissions.count(),
                'is_system_role': role.is_system_role
            }
        
        # Статистика по типам прав
        for permission in Permission.objects.all():
            perm_type = permission.permission_type
            if perm_type not in stats['permissions_by_type']:
                stats['permissions_by_type'][perm_type] = 0
            stats['permissions_by_type'][perm_type] += 1
        
        return stats
