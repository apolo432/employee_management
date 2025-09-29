"""
Views для управления ролями и правами доступа
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import Role, Permission, UserRole, AccessLog, Employee, Organization, Department, Division, TemporaryPermission
from .decorators import require_login, can_manage_roles
from .permissions import PermissionChecker


@require_login
@can_manage_roles
def roles_list(request):
    """Список ролей"""
    roles = Role.objects.prefetch_related('role_permissions', 'user_roles').all().order_by('name')
    
    # Фильтры
    role_type = request.GET.get('type')
    is_active = request.GET.get('active')
    
    if role_type:
        roles = roles.filter(role_type=role_type)
    
    if is_active is not None:
        roles = roles.filter(is_active=is_active == 'true')
    
    # Добавляем аннотацию для подсчета активных пользователей
    from django.db.models import Count, Q
    roles = roles.annotate(
        active_users_count=Count('user_roles', filter=Q(user_roles__is_active=True))
    )
    
    # Пагинация
    paginator = Paginator(roles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'roles': page_obj,
        'current_filters': {
            'type': role_type,
            'active': is_active,
        }
    }
    
    return render(request, 'employees/roles_list.html', context)


@require_login
@can_manage_roles
def role_detail(request, role_id):
    """Детальная информация о роли"""
    role = get_object_or_404(Role, id=role_id)
    
    # Права роли
    permissions = role.role_permissions.select_related('permission').all()
    
    # Пользователи с этой ролью
    user_roles = role.user_roles.filter(is_active=True).select_related('user').all()
    
    context = {
        'role': role,
        'permissions': permissions,
        'user_roles': user_roles,
    }
    
    return render(request, 'employees/role_detail.html', context)


@require_login
@can_manage_roles
def users_roles(request):
    """Управление ролями пользователей"""
    # Получаем всех пользователей с их ролями
    users = User.objects.filter(is_active=True).prefetch_related('user_roles__role').order_by('username')
    
    # Фильтры
    search_query = request.GET.get('search', '').strip()
    role_filter = request.GET.get('role')
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if role_filter:
        users = users.filter(user_roles__role_id=role_filter, user_roles__is_active=True)
    
    # Пагинация
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Данные для фильтров
    roles = Role.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'users': page_obj,
        'roles': roles,
        'current_filters': {
            'search': search_query,
            'role': role_filter,
        }
    }
    
    return render(request, 'employees/users_roles.html', context)


@require_login
@can_manage_roles
def assign_role(request, user_id):
    """Назначение роли пользователю"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        role_id = request.POST.get('role_id')
        scope_type = request.POST.get('scope_type', 'global')
        organization_id = request.POST.get('organization_id')
        department_id = request.POST.get('department_id')
        division_id = request.POST.get('division_id')
        employee_id = request.POST.get('employee_id')
        valid_until = request.POST.get('valid_until')
        reason = request.POST.get('reason', '')
        
        try:
            role = Role.objects.get(id=role_id)
            
            # Получаем объекты области действия
            organization = None
            department = None
            division = None
            employee = None
            
            if organization_id:
                organization = Organization.objects.get(id=organization_id)
            if department_id:
                department = Department.objects.get(id=department_id)
            if division_id:
                division = Division.objects.get(id=division_id)
            if employee_id:
                employee = Employee.objects.get(id=employee_id)
            
            # Проверяем, нет ли уже такой роли у пользователя
            existing_role = UserRole.objects.filter(
                user=user,
                role=role,
                scope_type=scope_type,
                organization=organization,
                department=department,
                division=division,
                employee=employee,
                is_active=True
            ).first()
            
            if existing_role:
                messages.warning(request, f'У пользователя {user.username} уже есть роль "{role.name}" с такими параметрами')
                return redirect('assign_role', user_id=user_id)
            
            # Создаем новую роль
            user_role = UserRole.objects.create(
                user=user,
                role=role,
                scope_type=scope_type,
                organization=organization,
                department=department,
                division=division,
                employee=employee,
                valid_until=timezone.datetime.fromisoformat(valid_until) if valid_until else None,
                reason=reason,
                assigned_by=request.user
            )
            
            messages.success(request, f'Роль "{role.name}" успешно назначена пользователю {user.username}')
            return redirect('users_roles')
            
        except Exception as e:
            messages.error(request, f'Ошибка при назначении роли: {str(e)}')
    
    # GET запрос - показываем форму
    roles = Role.objects.filter(is_active=True).order_by('name')
    organizations = Organization.objects.all().order_by('name')
    departments = Department.objects.all().order_by('name')
    divisions = Division.objects.all().order_by('name')
    employees = Employee.objects.filter(is_active=True).order_by('last_name', 'first_name')
    
    # Текущие роли пользователя
    current_roles = user.user_roles.filter(is_active=True).select_related('role').all()
    
    context = {
        'user': user,
        'roles': roles,
        'organizations': organizations,
        'departments': departments,
        'divisions': divisions,
        'employees': employees,
        'current_roles': current_roles,
    }
    
    return render(request, 'employees/assign_role.html', context)


@require_login
@can_manage_roles
def revoke_role(request, user_role_id):
    """Отзыв роли у пользователя"""
    user_role = get_object_or_404(UserRole, id=user_role_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        # Деактивируем роль
        user_role.is_active = False
        user_role.reason = f"{user_role.reason}\n\nОтозвана: {reason}"
        user_role.save()
        
        messages.success(request, f'Роль "{user_role.role.name}" отозвана у пользователя {user_role.user.username}')
        return redirect('users_roles')
    
    context = {
        'user_role': user_role,
    }
    
    return render(request, 'employees/revoke_role.html', context)


@require_login
@can_manage_roles
def access_logs(request):
    """Логи доступа к системе"""
    logs = AccessLog.objects.select_related('user').order_by('-timestamp')
    
    # Фильтры
    user_id = request.GET.get('user')
    action = request.GET.get('action')
    object_type = request.GET.get('object_type')
    success = request.GET.get('success')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    if action:
        logs = logs.filter(action=action)
    
    if object_type:
        logs = logs.filter(object_type=object_type)
    
    if success is not None:
        logs = logs.filter(success=success == 'true')
    
    if date_from:
        try:
            date_from_obj = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Пагинация
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Данные для фильтров
    users = User.objects.filter(access_logs__isnull=False).distinct().order_by('username')
    actions = AccessLog.ACTION_TYPES
    object_types = AccessLog.objects.values_list('object_type', flat=True).distinct().order_by('object_type')
    
    context = {
        'page_obj': page_obj,
        'logs': page_obj,
        'users': users,
        'actions': actions,
        'object_types': object_types,
        'current_filters': {
            'user': user_id,
            'action': action,
            'object_type': object_type,
            'success': success,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'employees/access_logs.html', context)


@require_login
@can_manage_roles
def role_statistics(request):
    """Статистика по ролям и правам"""
    from .role_initializer import RoleInitializer
    
    stats = RoleInitializer.get_role_statistics()
    
    # Дополнительная статистика
    recent_logs = AccessLog.objects.filter(
        timestamp__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    failed_access_attempts = AccessLog.objects.filter(
        success=False,
        timestamp__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    context = {
        'stats': stats,
        'recent_logs': recent_logs,
        'failed_access_attempts': failed_access_attempts,
    }
    
    return render(request, 'employees/role_statistics.html', context)


@require_login
@can_manage_roles
def user_permissions(request, user_id):
    """Просмотр прав пользователя"""
    user = get_object_or_404(User, id=user_id)
    
    # Получаем информацию о ролях и правах пользователя
    role_info = PermissionChecker.get_user_role_info(user)
    accessible_employees = PermissionChecker.get_accessible_employees(user)
    
    context = {
        'user': user,
        'role_info': role_info,
        'accessible_employees': accessible_employees,
    }
    
    return render(request, 'employees/user_permissions.html', context)


@require_login
@can_manage_roles
def temporary_permissions(request):
    """Управление временными правами"""
    temp_permissions = TemporaryPermission.objects.select_related('user', 'permission', 'granted_by').order_by('-granted_at')
    
    # Фильтры
    user_id = request.GET.get('user')
    permission_id = request.GET.get('permission')
    is_active = request.GET.get('active')
    
    if user_id:
        temp_permissions = temp_permissions.filter(user_id=user_id)
    
    if permission_id:
        temp_permissions = temp_permissions.filter(permission_id=permission_id)
    
    if is_active is not None:
        temp_permissions = temp_permissions.filter(is_active=is_active == 'true')
    
    # Пагинация
    paginator = Paginator(temp_permissions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Данные для фильтров
    users = User.objects.filter(temporary_permissions__isnull=False).distinct().order_by('username')
    permissions = Permission.objects.filter(temporary_permissions__isnull=False).distinct().order_by('name')
    
    context = {
        'page_obj': page_obj,
        'temp_permissions': page_obj,
        'users': users,
        'permissions': permissions,
        'current_filters': {
            'user': user_id,
            'permission': permission_id,
            'active': is_active,
        }
    }
    
    return render(request, 'employees/temporary_permissions.html', context)
