# добавить обнаружение портов
# кэширование
# база данных
# система владельца (Windows)
# безопасность сайта
from flask import Flask, request, render_template_string
import requests
from datetime import datetime
import time

app = Flask(__name__)

# Кэш IP-ответов (очищается при перезапуске сервера)
ip_cache = {}

# HTML шаблон
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ваш IP</title>
    <style>
        body {
            background-color: #111;
            color: #00FF88;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            text-align: center;
        }
        .container {
            background-color: rgba(0, 0, 0, 0.7);
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.6);
        }
        .ip-box {
            font-size: 1.5em;
        }
        .title {
            font-size: 2em;
            margin-bottom: 20px;
            font-weight: bold;
        }
        .info {
            margin: 10px 0;
        }
        .footer {
            margin-top: 20px;
            font-size: 0.9em;
            color: #aaa;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="title">Информация о вашем IP</div>
        <div class="ip-box">
            <div class="info"><strong>Ваш IP:</strong> {{ ip }}</div>
            <div class="info"><strong>Страна:</strong> {{ country }}</div>
            <div class="info"><strong>Город:</strong> {{ city }}</div>
            <div class="info"><strong>Провайдер:</strong> {{ isp }}</div>
            <div class="info"><strong>Гео-локация:</strong> {{ location }}</div>
            <div class="info"><strong>Почтовый код:</strong> {{ postal }}</div>
        </div>
        <div class="footer">Данные получены через <a href="https://ipinfo.io/{{ ip }}" target="_blank" style="color: #00FF88;">ipinfo.io</a></div>
    </div>
</body>
</html>
"""

def get_ip_data(ip):
    if ip in ip_cache:
        return ip_cache[ip]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        # time.sleep(1)  # ← если хочешь замедлить запросы
        response = requests.get(f"https://ipinfo.io/{ip}/json", headers=headers, timeout=5)
        geo = response.json()

        data = {
            "country": geo.get("country", "Неизвестно"),
            "city": geo.get("city", "Неизвестно"),
            "isp": geo.get("org", "Неизвестно"),
            "location": geo.get("loc", "Неизвестно"),
            "postal": geo.get("postal", "Неизвестно")
            #"language": geo.get("languages", "Неизвестно").split(',')[0] if geo.get("languages") else "Неизвестно"
        }
        ip_cache[ip] = data
        return data
    except Exception as e:
        print(f"[Ошибка IPAPI]: {e}")
        return {
            "country": "Ошибка",
            "city": "Ошибка",
            "isp": "Ошибка",
            "location": "Ошибка",
            "postal": "Ошибка"
            #"latitude": "Ошибка",
            #"longitude": "Ошибка",
            #"language": "Ошибка"
        }

@app.route('/')
def show_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent')

    # Получаем IP данные
    geo = get_ip_data(ip)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Лог в файл
    with open("ips.log", "a", encoding="utf-8") as f:
        f.write(f"\n=== Новый вход ===\n")
        f.write(f"Время: {now}\n")
        f.write(f"IP: {ip}\n")
        f.write(f"Страна: {geo['country']}\n")
        f.write(f"Город: {geo['city']}\n")
        f.write(f"Провайдер: {geo['isp']}\n")
        f.write(f"Location: {geo['location']}\n")
        f.write(f"Postal: {geo['postal']}\n")
        #f.write(f"Широта: {geo['latitude']}\n")
        #f.write(f"Долгота: {geo['longitude']}\n")
        #f.write(f"Язык: {geo['language']}\n")
        f.write(f"User-Agent: {user_agent}\n")

    return render_template_string(HTML_TEMPLATE,
                                  ip=ip,
                                  country=geo['country'],
                                  city=geo['city'],
                                  isp=geo['isp'],
                                  postal=geo['postal'],
                                  location=geo['location'])
                                  #latitude=geo['latitude'],
                                  #longitude=geo['longitude'],
                                  #language=geo['language'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
