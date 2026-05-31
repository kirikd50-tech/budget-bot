from flask import Flask, request
import json
import requests
import os

app = Flask(__name__)

TOKEN = os.environ.get('TOKEN')
ALLOWED_USERS = [408407377, 436144761, 1800725002]

# Список месяцев
MONTHS = [
    'Январь_26', 'Февраль_26', 'Март_26', 'Апрель_26', 'Май_26', 'Июнь_26',
    'Июль_26', 'Август_26', 'Сентябрь_26', 'Октябрь_26', 'Ноябрь_26', 'Декабрь_26'
]

# Хранилище состояния пользователей
user_data = {}

def send_message(chat_id, text, keyboard=None):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    if keyboard:
        payload['reply_markup'] = json.dumps(keyboard)
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка: {e}")

def answer_callback(callback_id):
    url = f'https://api.telegram.org/bot{TOKEN}/answerCallbackQuery'
    try:
        requests.post(url, json={'callback_query_id': callback_id})
    except Exception as e:
        print(f"Ошибка: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = json.loads(request.get_data())
        message = data.get('message')
        callback = data.get('callback_query')
        
        # Обработка команды /start
        if message and message.get('text') == '/start':
            chat_id = message['chat']['id']
            if chat_id not in ALLOWED_USERS:
                send_message(chat_id, '❌ Нет доступа')
                return 'OK', 200
            
            keyboard = {"inline_keyboard": [[{"text": "➕ Добавить расход", "callback_data": "add_expense"}]]}
            send_message(chat_id, '🏠 Главное меню', keyboard)
        
        # Обработка нажатия кнопок
        if callback:
            chat_id = callback['message']['chat']['id']
            callback_data = callback['data']
            callback_id = callback['id']
            
            if chat_id not in ALLOWED_USERS:
                answer_callback(callback_id)
                return 'OK', 200
            
            if callback_data == 'add_expense':
                # Показываем список месяцев
                keyboard = {"inline_keyboard": []}
                for month in MONTHS:
                    keyboard["inline_keyboard"].append([{"text": month, "callback_data": f"month_{month}"}])
                send_message(chat_id, '📅 Выберите месяц:', keyboard)
                answer_callback(callback_id)
            
            elif callback_data.startswith('month_'):
                month = callback_data.replace('month_', '')
                user_data[chat_id] = {'month': month}
                # Временные категории для теста
                categories = ['Продукты', 'Одежда', 'Развлечения', 'Здоровье', 'Транспорт', 'Кафе']
                keyboard = {"inline_keyboard": []}
                for cat in categories:
                    keyboard["inline_keyboard"].append([{"text": cat, "callback_data": f"cat_{cat}"}])
                send_message(chat_id, f'📂 {month}\nВыберите категорию:', keyboard)
                answer_callback(callback_id)
            
            elif callback_data.startswith('cat_'):
                category = callback_data.replace('cat_', '')
                if chat_id in user_data:
                    user_data[chat_id]['category'] = category
                    user_data[chat_id]['waiting_amount'] = True
                send_message(chat_id, f'💰 Введите сумму для "{category}":')
                answer_callback(callback_id)
        
        # Обработка ввода суммы
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
                    
                    send_message(chat_id, f'✅ Расход добавлен!\n📅 {month}\n📂 {category}\n💰 {amount} ₽')
                    
                    if chat_id in user_data:
                        del user_data[chat_id]
                    
                    keyboard = {"inline_keyboard": [[{"text": "➕ Добавить расход", "callback_data": "add_expense"}]]}
                    send_message(chat_id, '🏠 Главное меню', keyboard)
                except ValueError:
                    send_message(chat_id, '❌ Введите корректную сумму (например: 500)')
        
        return 'OK', 200
    except Exception as e:
        print(f"Ошибка: {e}")
        return 'OK', 200

@app.route('/')
def home():
    return 'Bot is running!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
