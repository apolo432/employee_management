"""
Модуль для обработки событий СКУД и формирования рабочих сессий
"""

import logging
from datetime import datetime, timedelta, time
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from .models import (
    Employee, SKUDEvent, WorkSession, WorkDaySummary, 
    WorkTimeAuditLog, Vacation, BusinessTrip
)

logger = logging.getLogger(__name__)


class WorkTimeProcessor:
    """Класс для обработки событий СКУД и формирования рабочих сессий"""
    
    # Константы для бизнес-правил
    MIN_SESSION_DURATION_SECONDS = 3 * 60  # 3 минуты
    MAX_SESSION_DURATION_SECONDS = 24 * 60 * 60  # 24 часа
    BREAK_MERGE_THRESHOLD_SECONDS = 15 * 60  # 15 минут
    
    def __init__(self):
        self.logger = logger
    
    def process_skud_events_for_employee(self, employee: Employee, date: datetime.date) -> bool:
        """
        Обработка всех событий СКУД для конкретного сотрудника на конкретную дату
        
        Args:
            employee: Сотрудник
            date: Дата для обработки
            
        Returns:
            bool: Успех обработки
        """
        try:
            with transaction.atomic():
                # Получаем все события сотрудника за день
                events = self._get_employee_events_for_date(employee, date)
                
                if not events:
                    # Создаём пустую сводку если нет событий
                    self._create_empty_summary(employee, date)
                    return True
                
                # Обрабатываем события в сессии
                sessions = self._create_sessions_from_events(events)
                
                # Создаём или обновляем сводку дня
                summary = self._create_or_update_summary(employee, date, sessions)
                
                # Логируем результат
                self._log_processing_result(employee, date, len(events), len(sessions))
                
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка обработки событий для {employee.full_name} на {date}: {e}")
            return False
    
    def _get_employee_events_for_date(self, employee: Employee, date: datetime.date) -> List[SKUDEvent]:
        """Получение событий сотрудника за день, отсортированных по времени"""
        start_datetime = timezone.make_aware(datetime.combine(date, time.min))
        end_datetime = timezone.make_aware(datetime.combine(date, time.max))
        
        return list(SKUDEvent.objects.filter(
            employee=employee,
            event_time__gte=start_datetime,
            event_time__lte=end_datetime
        ).order_by('event_time'))
    
    def _create_sessions_from_events(self, events: List[SKUDEvent]) -> List[WorkSession]:
        """Создание рабочих сессий из событий СКУД"""
        sessions = []
        current_session_events = []
        
        # Удаляем существующие автоматические сессии для этих событий
        self._cleanup_existing_auto_sessions(events)
        
        for i, event in enumerate(events):
            # Определяем тип события
            event_type = self._determine_event_type(event)
            
            if event_type == 'entry':
                # Если есть открытая сессия, закрываем её
                if current_session_events:
                    session = self._close_session(current_session_events, events[i-1])
                    if session:
                        sessions.append(session)
                
                # Начинаем новую сессию
                current_session_events = [event]
                
            elif event_type == 'exit' and current_session_events:
                # Завершаем текущую сессию
                current_session_events.append(event)
                session = self._close_session(current_session_events, event)
                if session:
                    sessions.append(session)
                current_session_events = []
        
        # Если осталась открытая сессия
        if current_session_events:
            session = self._create_open_session(current_session_events)
            if session:
                sessions.append(session)
        
        return sessions
    
    def _determine_event_type(self, event: SKUDEvent) -> str:
        """Определение типа события (вход/выход)"""
        if hasattr(event, 'event_type') and event.event_type:
            event_type = event.event_type.lower()
            if event_type in ['entry', 'in', 'вход']:
                return 'entry'
            elif event_type in ['exit', 'out', 'выход']:
                return 'exit'
        
        # Если event_type не определён, пробуем определить из raw_data
        if event.raw_data:
            try:
                import json
                data = json.loads(event.raw_data)
                direction = data.get('direction', '').lower()
                if direction in ['in', 'entry', 'вход']:
                    return 'entry'
                elif direction in ['out', 'exit', 'выход']:
                    return 'exit'
            except (json.JSONDecodeError, KeyError):
                pass
        
        # По умолчанию считаем входом
        return 'entry'
    
    def _cleanup_existing_auto_sessions(self, events: List[SKUDEvent]):
        """Удаление существующих автоматических сессий для данных событий"""
        if not events:
            return
        
        # Получаем дату первого события
        date = events[0].event_time.date()
        
        # Удаляем автоматические сессии на эту дату
        WorkSession.objects.filter(
            employee=events[0].employee,
            date=date,
            status='auto'
        ).delete()
    
    def _close_session(self, events: List[SKUDEvent], exit_event: SKUDEvent) -> Optional[WorkSession]:
        """Закрытие сессии с событиями входа и выхода"""
        if len(events) < 2:
            return None
        
        entry_event = events[0]
        
        # Проверяем минимальную длительность сессии
        duration = (exit_event.event_time - entry_event.event_time).total_seconds()
        if duration < self.MIN_SESSION_DURATION_SECONDS:
            self.logger.warning(f"Слишком короткая сессия: {duration} секунд")
            return None
        
        # Проверяем максимальную длительность сессии
        if duration > self.MAX_SESSION_DURATION_SECONDS:
            self.logger.warning(f"Слишком длинная сессия: {duration} секунд")
        
        # Создаём сессию
        session = WorkSession.objects.create(
            employee=entry_event.employee,
            date=entry_event.event_time.date(),
            start_time=entry_event.event_time,
            end_time=exit_event.event_time,
            status='auto'
        )
        
        # Связываем с событиями
        session.source_events.set(events)
        
        return session
    
    def _create_open_session(self, events: List[SKUDEvent]) -> Optional[WorkSession]:
        """Создание открытой сессии (без выхода)"""
        if not events:
            return None
        
        entry_event = events[0]
        
        # Создаём открытую сессию
        session = WorkSession.objects.create(
            employee=entry_event.employee,
            date=entry_event.event_time.date(),
            start_time=entry_event.event_time,
            status='open'
        )
        
        # Связываем с событиями
        session.source_events.set(events)
        
        self.logger.warning(f"Создана открытая сессия для {entry_event.employee.full_name}")
        
        return session
    
    def _create_or_update_summary(self, employee: Employee, date: datetime.date, sessions: List[WorkSession]) -> WorkDaySummary:
        """Создание или обновление сводки рабочего дня"""
        summary, created = WorkDaySummary.objects.get_or_create(
            employee=employee,
            date=date,
            defaults={}
        )
        
        # Рассчитываем агрегированные данные
        total_seconds = sum(s.duration_seconds or 0 for s in sessions)
        expected_seconds = employee.get_expected_daily_seconds(date)
        
        # Определяем статус дня
        status = self._determine_day_status(employee, date, sessions, total_seconds, expected_seconds)
        
        # Обновляем сводку
        summary.first_entry = min(s.start_time for s in sessions) if sessions else None
        summary.last_exit = max(s.end_time for s in sessions if s.end_time) if sessions else None
        summary.total_seconds_in_office = total_seconds
        summary.expected_seconds = expected_seconds
        summary.sessions_count = len(sessions)
        summary.status = status
        summary.has_missing_exit = any(s.is_open for s in sessions)
        summary.has_manual_corrections = any(s.status != 'auto' for s in sessions)
        
        summary.save()
        
        return summary
    
    def _determine_day_status(self, employee: Employee, date: datetime.date, 
                            sessions: List[WorkSession], total_seconds: int, expected_seconds: int) -> str:
        """Определение статуса рабочего дня"""
        
        # Проверяем отпуска и командировки
        if employee.has_vacation_on_date(date) or employee.has_business_trip_on_date(date):
            return 'excused'
        
        # Если нет сессий
        if not sessions:
            return 'absent'
        
        # Если есть открытые сессии
        if any(s.is_open for s in sessions):
            return 'problem'
        
        # Если есть ручные корректировки
        if any(s.status != 'auto' for s in sessions):
            return 'partial'
        
        # Если время работы значительно меньше ожидаемого
        if expected_seconds > 0 and total_seconds < expected_seconds * 0.5:
            return 'partial'
        
        # По умолчанию - присутствовал
        return 'present'
    
    def _create_empty_summary(self, employee: Employee, date: datetime.date):
        """Создание пустой сводки для дня без событий"""
        expected_seconds = employee.get_expected_daily_seconds(date)
        status = 'excused' if expected_seconds == 0 else 'absent'
        
        WorkDaySummary.objects.get_or_create(
            employee=employee,
            date=date,
            defaults={
                'total_seconds_in_office': 0,
                'expected_seconds': expected_seconds,
                'sessions_count': 0,
                'status': status,
                'has_missing_exit': False,
                'has_manual_corrections': False,
            }
        )
    
    def _log_processing_result(self, employee: Employee, date: datetime.date, 
                             events_count: int, sessions_count: int):
        """Логирование результата обработки"""
        self.logger.info(
            f"Обработано {events_count} событий для {employee.full_name} "
            f"на {date}: создано {sessions_count} сессий"
        )
    
    def reprocess_employee_day(self, employee: Employee, date: datetime.date) -> bool:
        """Пересчёт рабочего времени для конкретного сотрудника на конкретную дату"""
        return self.process_skud_events_for_employee(employee, date)
    
    def reprocess_employee_period(self, employee: Employee, start_date: datetime.date, end_date: datetime.date) -> int:
        """Пересчёт рабочего времени для сотрудника за период"""
        processed_days = 0
        current_date = start_date
        
        while current_date <= end_date:
            if self.process_skud_events_for_employee(employee, current_date):
                processed_days += 1
            current_date += timedelta(days=1)
        
        return processed_days
    
    def reprocess_all_employees_day(self, date: datetime.date) -> Dict[str, int]:
        """Пересчёт рабочего времени для всех сотрудников на конкретную дату"""
        results = {'processed': 0, 'errors': 0}
        
        employees = Employee.objects.filter(is_active=True)
        
        for employee in employees:
            try:
                if self.process_skud_events_for_employee(employee, date):
                    results['processed'] += 1
                else:
                    results['errors'] += 1
            except Exception as e:
                self.logger.error(f"Ошибка пересчёта для {employee.full_name}: {e}")
                results['errors'] += 1
        
        return results


class WorkTimeAuditManager:
    """Менеджер для аудита изменений в системе учёта рабочего времени"""
    
    @staticmethod
    def log_session_change(action: str, session: WorkSession, user=None, reason: str = "", 
                          old_value: Dict = None, new_value: Dict = None):
        """Логирование изменения сессии"""
        WorkTimeAuditLog.objects.create(
            employee=session.employee,
            date=session.date,
            action=action,
            description=f"{action} для сессии {session.id}",
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            changed_by=user
        )
    
    @staticmethod
    def log_summary_change(action: str, summary: WorkDaySummary, user=None, reason: str = "",
                          old_value: Dict = None, new_value: Dict = None):
        """Логирование изменения сводки"""
        WorkTimeAuditLog.objects.create(
            employee=summary.employee,
            date=summary.date,
            action=action,
            description=f"{action} для сводки {summary.id}",
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            changed_by=user
        )
