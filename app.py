from flask import Flask, request
import json
import requests
import gspread
from google.oauth2.service_account import Credentials
import os
import time

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
categories_cache = {}
CACHE_TIME = 600

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
    if month_name in categories_cache:
        cache_time, categories = categories_cache[month_name]
        if time.time() - cache_time < CACHE_TIME:
            print(f"Категории из кэша: {month_name}")
            return categories
    
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
        while True:
            cell_value = worksheet.cell(row, 5).value
            if not cell_value or cell_value.strip() == '':
                break
            row += 1

        worksheet.update_cell(row, 5, category)
        worksheet.update_cell(row, 6, amount)
        print(f"Сохранено: {month_name}, {category}, {amount}, строка {row}")
        return True
    except Exception as e:
        print(f"Ошибка save_expense: {e}")
        return False

def send_message(chat_id, text, keyboard=None):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    if keyboard:
        payload['reply_markup'] = json.dumps(keyboard)
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Ошибка send_message: {e}")

def answer_callback(callback_id):
    url = f'https://api.telegram.org/bot{TOKEN}/answerCallbackQuery'
    try:
        requests.post(url, json={'callback_query_id': callback_id}, timeout=3)
    except Exception as e:
        print(f"Ошибка answer_callback: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = json.loads(request.get_data())
        message = data.get('message')
        callback = data.get('callback_query')

        if message and message.get('text') == '/start':
            chat_id = message['chat']['id']
            if chat_id not in ALLOWED_USERS:
                send_message(chat_id, '❌ Нет доступа')
                return 'OK', 200

            keyboard = {"inline_keyboard": [[{"text": "➕ Добавить расход", "callback_data": "add_expense"}]]}
            send_message(chat_id, '🏠 Главное меню', keyboard)

        if callback:
            chat_id = callback['message']['chat']['id']
            callback_data = callback['data']
            callback_id = callback['id']

            if chat_id not in ALLOWED_USERS:
                answer_callback(callback_id)
                return 'OK', 200

            if callback_data == 'add_expense':
                keyboard = {"inline_keyboard": []}
                for month in MONTHS:
                    keyboard["inline_keyboard"].append([{"text": month, "callback_data": f"month_{month}"}])
                keyboard["inline_keyboard"].append([{"text": "🔙 Назад", "callback_data": "back_main"}])
                send_message(chat_id, '📅 Выберите месяц:', keyboard)
                answer_callback(callback_id)

            elif callback_data.startswith('month_'):
                month = callback_data.replace('month_', '')
                user_data[chat_id] = {'month': month}
                categories = get_categories(month)

                if not categories:
                    send_message(chat_id, f'⚠️ В листе "{month}" нет категорий.\nПроверьте столбец B с {CATEGORY_START_ROW} строки.')
                    answer_callback(callback_id)
                    return 'OK', 200

                keyboard = {"inline_keyboard": []}
                for i in range(0, len(categories), 2):
                    row = [{"text": categories[i], "callback_data": f"cat_{categories[i]}"}]
                    if i+1 < len(categories):
                        row.append({"text": categories[i+1], "callback_data": f"cat_{categories[i+1]}"})
                    keyboard["inline_keyboard"].append(row)
                keyboard["inline_keyboard"].append([{"text": "🔙 Назад", "callback_data": "add_expense"}])

                send_message(chat_id, f'📂 {month}\nВыберите категорию:', keyboard)
                answer_callback(callback_id)

            elif callback_data.startswith('cat_'):
                category = callback_data.replace('cat_', '')
                if chat_id in user_data:
                    user_data[chat_id]['category'] = category
                    user_data[chat_id]['waiting_amount'] = True
                send_message(chat_id, f'💰 Введите сумму для "{category}":')
                answer_callback(callback_id)

            elif callback_data == 'back_main':
                keyboard = {"inline_keyboard": [[{"text": "➕ Добавить расход", "callback_data": "add_expense"}]]}
                send_message(chat_id, '🏠 Главное меню', keyboard)
                answer_callback(callback_id)

        if message and message.get('text') and not message.get('text').startswith('/'):
            chat_id = message['chat']['id']
            text = message['text']

            if chat_id not in ALLOWED_USERS:
                return 'OK', 200

            if chat_id in user_data and user_data[chat_id].get('waiting_amount'):
                try:
                    amount = float(text.replace(',', '.'))
                    month = user_data[chat_id].get('month')
                    category = user_data[chat_id].get('category')

                    if save_expense(month, category, amount):
                        send_message(chat_id, f'✅ Расход добавлен!\n📅 {month}\n📂 {category}\n💰 {amount} ₽')
                    else:
                        send_message(chat_id, '❌ Ошибка при сохранении в таблицу.\nПроверьте, что лист существует и у бота есть доступ к таблице.')

                    if chat_id in user_data:
                        del user_data[chat_id]

                    keyboard = {"inline_keyboard": [[{"text": "➕ Добавить расход", "callback_data": "add_expense"}]]}
                    send_message(chat_id, '🏠 Главное меню', keyboard)
                except ValueError:
                    send_message(chat_id, '❌ Введите корректную сумму (например: 500)')

        return 'OK', 200
    except Exception as e:
        print(f"Ошибка webhook: {e}")
        return 'OK', 200

@app.route('/')
def home():
    return 'Bot is running!'

@app.route('/test-creds')
def test_creds():
    try:
        creds_json = os.environ.get('GOOGLE_CREDS')
        if not creds_json:
            return "❌ GOOGLE_CREDS не найдена"
        creds_dict = json.loads(creds_json)
        return f"✅ JSON корректен! client_email: {creds_dict.get('client_email', 'не найден')}"
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

@app.route('/test-sheet')
def test_sheet():
    try:
        sheet = get_sheet()
        if sheet:
            worksheets = [ws.title for ws in sheet.worksheets()]
            return f"✅ Таблица найдена: {sheet.title}\n\nЛисты в таблице: {', '.join(worksheets)}"
        else:
            return "❌ Не удалось подключиться к таблице. Проверьте GOOGLE_CREDS и доступ к таблице."
    except Exception as e:
        return f"❌ Ошибка: {e}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
