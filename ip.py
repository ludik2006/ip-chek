from flask import Flask, request, render_template_string
import requests
from datetime import datetime

app = Flask(__name__)

# HTML-шаблон с улучшенным дизайном
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
        </div>
        <div class="footer">Данные получены через <a href="https://ipapi.co/" target="_blank" style="color: #00FF88;">ipapi.co</a></div>
    </div>
</body>
</html>
"""

@app.route('/')
def show_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent')

    # Получаем геоданные
    try:
        geo = requests.get(f"https://ipapi.co/{ip}/json/").json()
        country = geo.get('country_name', 'Неизвестно')
        city = geo.get('city', 'Неизвестно')
        isp = geo.get('org', 'Неизвестно')  # Провайдер
    except:
        country = city = isp = "Ошибка запроса"

    # Время
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Лог в файл
    with open("ips.log", "a", encoding="utf-8") as f:
        f.write(f"\n=== Новый вход ===\n")
        f.write(f"Время: {now}\n")
        f.write(f"IP: {ip}\n")
        f.write(f"Страна: {country}\n")
        f.write(f"Город: {city}\n")
        f.write(f"Провайдер: {isp}\n")
        f.write(f"User-Agent: {user_agent}\n")

    return render_template_string(HTML_TEMPLATE, ip=ip, country=country, city=city)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
