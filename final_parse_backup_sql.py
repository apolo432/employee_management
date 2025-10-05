#!/usr/bin/env python
"""
Финальный скрипт для парсинга backup.sql файла и экспорта данных сотрудников в Excel
"""

import re
import pandas as pd
from datetime import datetime
import os


def parse_backup_sql():
    """Парсинг backup.sql файла и извлечение данных сотрудников"""
    
    print("=== Парсинг backup.sql файла ===")
    
    # Проверяем наличие файла
    if not os.path.exists('backup.sql'):
        print("❌ Файл backup.sql не найден!")
        return
    
    # Читаем файл
    print("📖 Чтение файла backup.sql...")
    with open('backup.sql', 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Находим строку с COPY public.users
    copy_pattern = r'COPY public\.users \([^)]+\) FROM stdin;'
    copy_match = re.search(copy_pattern, content)
    
    if not copy_match:
        print("❌ Не найдена таблица users в файле!")
        return
    
    print("✅ Найдена таблица users")
    
    # Получаем позицию начала данных
    data_start = copy_match.end()
    
    # Находим конец данных (строка с \.)
    data_end_pattern = r'\n\\\.\n'
    data_end_match = re.search(data_end_pattern, content[data_start:])
    
    if not data_end_match:
        print("❌ Не найден конец данных!")
        return
    
    # Извлекаем данные
    data_content = content[data_start:data_start + data_end_match.start()]
    data_lines = data_content.strip().split('\n')
    
    print(f"📊 Найдено {len(data_lines)} записей")
    
    # Парсим данные
    employees = []
    
    for line_num, line in enumerate(data_lines, 1):
        if not line.strip():
            continue
            
        try:
            # Разбиваем строку по табуляции
            fields = line.split('\t')
            
            if len(fields) < 39:  # Минимальное количество полей
                continue
            
            # Создаем словарь для текущего сотрудника
            employee_data = {
                'fio': fields[4].strip() if len(fields) > 4 and fields[4] != '\\N' else '',
                'id': fields[0].strip() if len(fields) > 0 and fields[0] != '\\N' else '',
                'first_name': fields[1].strip() if len(fields) > 1 and fields[1] != '\\N' else '',
                'last_name': fields[2].strip() if len(fields) > 2 and fields[2] != '\\N' else '',
                'middle_name': fields[3].strip() if len(fields) > 3 and fields[3] != '\\N' else '',
                'work_start_time': fields[20].strip() if len(fields) > 20 and fields[20] != '\\N' else '',
                'work_end_time': fields[21].strip() if len(fields) > 21 and fields[21] != '\\N' else '',
                'birth_date': fields[34].strip() if len(fields) > 34 and fields[34] != '\\N' else ''
            }
            
            employees.append(employee_data)
            
        except Exception as e:
            print(f"⚠️ Ошибка в строке {line_num}: {e}")
            continue
    
    print(f"✅ Успешно обработано {len(employees)} записей")
    
    return employees


def export_to_excel(employees, filename='employees_final.xlsx'):
    """Экспорт данных в Excel файл"""
    
    print(f"\n=== Экспорт в Excel файл: {filename} ===")
    
    if not employees:
        print("❌ Нет данных для экспорта!")
        return
    
    # Создаем DataFrame
    df = pd.DataFrame(employees)
    
    # Устанавливаем порядок колонок
    columns_order = [
        'fio',
        'id', 
        'first_name',
        'last_name',
        'middle_name',
        'work_start_time',
        'work_end_time',
        'birth_date'
    ]
    
    df = df[columns_order]
    
    # Переименовываем колонки на русский
    column_names = {
        'fio': 'ФИО',
        'id': 'ID',
        'first_name': 'Имя',
        'last_name': 'Фамилия', 
        'middle_name': 'Отчество',
        'work_start_time': 'Время начала работы',
        'work_end_time': 'Время окончания работы',
        'birth_date': 'Дата рождения'
    }
    
    df = df.rename(columns=column_names)
    
    # Обрабатываем время работы
    def format_time(time_str):
        if not time_str or time_str.strip() == '':
            return ''
        try:
            # Если время в формате HH:MM:SS или HH:MM
            if ':' in time_str:
                return time_str
            # Если время в числовом формате (например, 900 для 09:00)
            elif time_str.isdigit() and len(time_str) >= 3:
                hours = int(time_str) // 100
                minutes = int(time_str) % 100
                return f"{hours:02d}:{minutes:02d}"
            else:
                return time_str
        except:
            return time_str
    
    df['Время начала работы'] = df['Время начала работы'].apply(format_time)
    df['Время окончания работы'] = df['Время окончания работы'].apply(format_time)
    
    # Обрабатываем дату рождения
    def format_date(date_str):
        if not date_str or date_str.strip() == '':
            return ''
        return date_str
    
    df['Дата рождения'] = df['Дата рождения'].apply(format_date)
    
    # Экспортируем в Excel
    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Сотрудники', index=False)
            
            # Настраиваем ширину колонок
            worksheet = writer.sheets['Сотрудники']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        print(f"✅ Файл {filename} успешно создан!")
        print(f"📊 Экспортировано {len(df)} записей")
        
        # Показываем статистику
        print(f"\n=== Статистика ===")
        print(f"Всего записей: {len(df)}")
        print(f"С ФИО: {len(df[df['ФИО'].str.strip() != ''])}")
        print(f"С именем: {len(df[df['Имя'].str.strip() != ''])}")
        print(f"С фамилией: {len(df[df['Фамилия'].str.strip() != ''])}")
        print(f"С отчеством: {len(df[df['Отчество'].str.strip() != ''])}")
        print(f"С временем начала: {len(df[df['Время начала работы'].str.strip() != ''])}")
        print(f"С временем окончания: {len(df[df['Время окончания работы'].str.strip() != ''])}")
        print(f"С датой рождения: {len(df[df['Дата рождения'].str.strip() != ''])}")
        
        # Показываем примеры записей с временем работы
        print(f"\n=== Примеры записей с временем работы ===")
        with_time = df[(df['Время начала работы'].str.strip() != '') | (df['Время окончания работы'].str.strip() != '')]
        if len(with_time) > 0:
            print(f"Найдено {len(with_time)} записей с временем работы:")
            print(with_time.head(10).to_string(index=False))
        else:
            print("ℹ️ В базе данных нет записей с указанным временем работы")
        
        # Показываем первые 10 записей
        print(f"\n=== Первые 10 записей ===")
        print(df.head(10).to_string(index=False))
        
        # Показываем примеры с датой рождения
        print(f"\n=== Примеры записей с датой рождения ===")
        with_birth_date = df[df['Дата рождения'].str.strip() != '']
        if len(with_birth_date) > 0:
            print(f"Найдено {len(with_birth_date)} записей с датой рождения:")
            print(with_birth_date[['ФИО', 'Дата рождения']].head(10).to_string(index=False))
        
    except Exception as e:
        print(f"❌ Ошибка при экспорте в Excel: {e}")


def main():
    """Основная функция"""
    
    print("🚀 Запуск финального парсера backup.sql")
    print(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Парсим данные
    employees = parse_backup_sql()
    
    if employees:
        # Экспортируем в Excel
        export_to_excel(employees)
        
        print(f"\n✅ Парсинг завершен успешно!")
        print(f"📁 Файл employees_final.xlsx создан в текущей директории")
        print(f"\n📋 Экспортированные поля:")
        print(f"   • ФИО")
        print(f"   • ID") 
        print(f"   • Имя")
        print(f"   • Фамилия")
        print(f"   • Отчество")
        print(f"   • Время начала работы")
        print(f"   • Время окончания работы")
        print(f"   • Дата рождения")
    else:
        print(f"\n❌ Парсинг завершился с ошибками")


if __name__ == "__main__":
    main()




