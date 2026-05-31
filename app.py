from flask import Flask, request
import json
import requests
import os

app = Flask(__name__)

TOKEN = os.environ.get('TOKEN')
ALLOWED_USERS = [408407377, 436144761, 1800725002]

@app.route('/')
def home():
    return 'Bot is running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = json.loads(request.get_data())
        message = data.get('message')
        
        if message and message.get('text') == '/start':
            chat_id = message['chat']['id']
            if chat_id not in ALLOWED_USERS:
                return 'OK', 200
            
            url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
            keyboard = {"inline_keyboard": [[{"text": "➕ Добавить расход", "callback_data": "add_expense"}]]}
            payload = {
                'chat_id': chat_id,
                'text': '🏠 Главное меню',
                'reply_markup': json.dumps(keyboard)
            }
            requests.post(url, json=payload)
        
        if message and message.get('text') and not message.get('text').startswith('/'):
            chat_id = message['chat']['id']
            if chat_id not in ALLOWED_USERS:
                return 'OK', 200
            
            url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
            payload = {'chat_id': chat_id, 'text': f'✅ Вы ввели: {message["text"]}'}
            requests.post(url, json=payload)
        
        return 'OK', 200
    except Exception as e:
        print(e)
        return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
