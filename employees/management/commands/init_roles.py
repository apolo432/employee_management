"""
Django команда для инициализации системы ролей и прав доступа
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
import logging

from employees.role_initializer import RoleInitializer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Инициализация системы ролей и прав доступа'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Сбросить все роли и права доступа перед инициализацией',
        )
        parser.add_argument(
            '--permissions-only',
            action='store_true',
            help='Создать только права доступа',
        )
        parser.add_argument(
            '--roles-only',
            action='store_true',
            help='Создать только роли',
        )
        parser.add_argument(
            '--assign-default',
            action='store_true',
            help='Назначить роли по умолчанию существующим пользователям',
        )
        parser.add_argument(
            '--superuser-role',
            type=str,
            help='Назначить роль супер-администратора указанному пользователю',
        )
        parser.add_argument(
            '--statistics',
            action='store_true',
            help='Показать статистику по ролям и правам',
        )

    def handle(self, *args, **options):
        try:
            if options['statistics']:
                self.show_statistics()
                return

            if options['reset']:
                self.stdout.write(
                    self.style.WARNING('Сброс всех ролей и прав доступа...')
                )
                RoleInitializer.reset_roles()

            if options['permissions_only']:
                self.stdout.write('Создание прав доступа...')
                created = RoleInitializer.initialize_permissions()
                self.stdout.write(
                    self.style.SUCCESS(f'Создано {created} прав доступа')
                )
                return

            if options['roles_only']:
                self.stdout.write('Создание ролей...')
                created = RoleInitializer.initialize_roles()
                self.stdout.write(
                    self.style.SUCCESS(f'Создано {created} ролей')
                )
                return

            if options['assign_default']:
                self.stdout.write('Назначение ролей по умолчанию...')
                assigned = RoleInitializer.assign_default_roles()
                self.stdout.write(
                    self.style.SUCCESS(f'Назначено {assigned} ролей по умолчанию')
                )
                return

            if options['superuser_role']:
                username = options['superuser_role']
                try:
                    user = User.objects.get(username=username)
                    if RoleInitializer.create_superuser_role(user):
                        self.stdout.write(
                            self.style.SUCCESS(f'Роль супер-администратора назначена пользователю {username}')
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'Не удалось назначить роль пользователю {username}')
                        )
                except User.DoesNotExist:
                    raise CommandError(f'Пользователь {username} не найден')
                return

            # Полная инициализация
            self.stdout.write('Начало инициализации системы ролей...')
            
            with transaction.atomic():
                result = RoleInitializer.initialize_all()
            
            self.stdout.write(
                self.style.SUCCESS('Инициализация системы ролей завершена успешно!')
            )
            self.stdout.write(f'Создано прав доступа: {result["permissions_created"]}')
            self.stdout.write(f'Создано ролей: {result["roles_created"]}')
            self.stdout.write(f'Назначено ролей по умолчанию: {result["roles_assigned"]}')
            self.stdout.write(f'Назначено ролей супер-администратора: {result["superuser_roles_assigned"]}')

        except Exception as e:
            logger.error(f"Ошибка при инициализации ролей: {e}")
            raise CommandError(f'Ошибка при инициализации ролей: {e}')

    def show_statistics(self):
        """Показать статистику по ролям и правам"""
        stats = RoleInitializer.get_role_statistics()
        
        self.stdout.write(self.style.SUCCESS('=== СТАТИСТИКА СИСТЕМЫ РОЛЕЙ ==='))
        self.stdout.write(f'Всего ролей: {stats["total_roles"]}')
        self.stdout.write(f'Всего прав доступа: {stats["total_permissions"]}')
        self.stdout.write(f'Всего назначений ролей: {stats["total_user_roles"]}')
        self.stdout.write(f'Активных назначений ролей: {stats["active_user_roles"]}')
        
        self.stdout.write('\n=== РОЛИ ===')
        for role_name, role_stats in stats['roles_by_name'].items():
            system_mark = ' (системная)' if role_stats['is_system_role'] else ''
            self.stdout.write(
                f'  {role_name}{system_mark}: '
                f'{role_stats["user_count"]} пользователей, '
                f'{role_stats["permission_count"]} прав'
            )
        
        self.stdout.write('\n=== ПРАВА ПО ТИПАМ ===')
        for perm_type, count in stats['permissions_by_type'].items():
            self.stdout.write(f'  {perm_type}: {count}')
        
        self.stdout.write('\n=== ПОЛЬЗОВАТЕЛИ БЕЗ РОЛЕЙ ===')
        users_without_roles = User.objects.filter(
            user_roles__isnull=True,
            is_active=True
        ).exclude(is_superuser=True)
        
        if users_without_roles.exists():
            for user in users_without_roles:
                self.stdout.write(f'  {user.username} ({user.email or "нет email"})')
        else:
            self.stdout.write('  Все пользователи имеют роли')
