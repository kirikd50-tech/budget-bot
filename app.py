from flask import Flask, request
import json
import requests
import gspread
from google.oauth2.service_account import Credentials
import os
import time
from functools import lru_cache

app = Flask(__name__)

TOKEN = os.environ.get('TOKEN')
ALLOWED_USERS = [408407377, 436144761, 1800725002]

MONTHS = [
    'Январь_26', 'Февраль_26', 'Март_26', 'Апрель_26', 'Май_26', 'Июнь_26',
    'Июль_26', 'Август_26', 'Сентябрь_26', 'Октябрь_26', 'Ноябрь_26', 'Декабрь_26',
    'Январь_27', 'Февраль_27', 'Март_27', 'Апрель_27', 'Май_27', 'Июнь_27'
]

CATEGORY_START_ROW = 11
DROPDOWN_START_ROW = 8
SHEET_ID = '1SCRNSvorQKItq_hPZiZPL1iGq0c2byQBc79VYiEz2Xw'

user_data = {}
# Долгое кэширование: 1 час (3600 секунд)
categories_cache = {}
CACHE_TIME = 3600

def get_sheet():
    try:
        creds_json = os.environ.get('GOOGLE_CREDS')
        if not creds_json:
            print("GOOGLE_CREDS не найдена")
            return None
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID)
    except Exception as e:
        print(f"Ошибка get_sheet: {e}")
        return None

def get_categories(month_name):
    # Проверяем кэш
    if month_name in categories_cache:
        cache_time, categories = categories_cache[month_name]
        if time.time() - cache_time < CACHE_TIME:
            print(f"Категории из кэша: {month_name} (загружены {int((time.time() - cache_time)/60)} мин назад)")
            return categories
    
    print(f"Загружаем категории из таблицы для {month_name}...")
    try:
        sheet = get_sheet()
        if not sheet:
            print("Нет подключения к таблице")
            return ['Продукты', 'Одежда', 'Развлечения', 'Здоровье', 'Транспорт', 'Кафе', 'Аптека']

        worksheet = sheet.worksheet(month_name)
        categories = []
        for row_num in range(11, 36):
            try:
                cell_value = worksheet.cell(row_num, 2).value
                if cell_value and cell_value.strip():
                    categories.append(cell_value.strip())
            except:
                continue

        categories = list(dict.fromkeys(categories))
        categories_cache[month_name] = (time.time(), categories)
        print(f"Загружено категорий для {month_name}: {len(categories)}")
        return categories
    except Exception as e:
        print(f"Ошибка get_categories: {e}")
        return ['Продукты', 'Одежда', 'Развлечения', 'Здоровье', 'Транспорт', 'Кафе', 'Аптека']

def save_expense(month_name, category, amount):
    try:
        sheet = get_sheet()
        if not sheet:
            print("Нет подключения к таблице для сохранения")
            return False

        worksheet = sheet.worksheet(month_name)
        row = DROPDOWN_START_ROW
        max_row = 100
        while row <= max_row:
            cell_value = worksheet.cell(row, 5).value
            if not cell_value or cell_value.strip() == '':
                break
            row += 1
        
        if row > max_row:
            print(f"Не найдено пустой строки до {max_row}")
            return False

        worksheet.update_cell(row, 5, category)
        worksheet.update_cell(row, 6, amount)
        print(f"Сохранено: {month_name}, {category}, {amount}, строка {row}")
        return True
    except Exception as e:
        print(f"Ошибка save_expense: {e}")
        return False

# ... (остальные функции send_message, answer_callback, webhook остаются такими же)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
