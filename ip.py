from flask import Flask, request, render_template_string
import requests
from datetime import datetime

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Информация о вашем IP</title>
    <style>
        body {
            background-color: #111;
            color: #00FF88;
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .container {
            background-color: rgba(0, 0, 0, 0.8);
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px #00FF88;
            text-align: center;
        }
        .info {
            margin: 10px 0;
            font-size: 1.2em;
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
        <h2>Информация о вашем IP</h2>
        <div class="info"><strong>IP:</strong> {{ ip }}</div>
        <div class="info"><strong>Страна:</strong> {{ country }}</div>
        <div class="info"><strong>Регион:</strong> {{ region }}</div>
        <div class="info"><strong>Город:</strong> {{ city }}</div>
        <div class="info"><strong>Провайдер:</strong> {{ isp }}</div>
        <div class="info"><strong>Широта:</strong> {{ latitude }}</div>
        <div class="info"><strong>Долгота:</strong> {{ longitude }}</div>
        <div class="info"><strong>VPN:</strong> {{ is_vpn }}</div>
        <div class="footer">Данные предоставлены сервисом <a href="https://ipwhois.io/" target="_blank" style="color: #00FF88;">IPWHOIS.io</a></div>
    </div>
</body>
</html>
"""

@app.route('/')
def show_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent')
    platform = request.user_agent.platform

    try:
        response = requests.get(f'https://ipwhois.app/json/{ip}?security=1')
        data = response.json()
        country = data.get('country', 'Неизвестно')
        region = data.get('region', 'Неизвестно')
        city = data.get('city', 'Неизвестно')
        isp = data.get('isp', 'Неизвестно')
        latitude = data.get('latitude', 'Неизвестно')
        longitude = data.get('longitude', 'Неизвестно')
        is_vpn = 'Да' if data.get('vpn', False) else 'Нет'
    except Exception as e:
        country = region = city = isp = latitude = longitude = 'Ошибка'
        is_vpn = 'Неизвестно'

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open("ips.log", "a", encoding="utf-8") as f:
        f.write(f"\n=== Новый вход ===\n")
        f.write(f"Время: {now}\n")
        f.write(f"IP: {ip}\n")
        f.write(f"Страна: {country}\n")
        f.write(f"Регион: {region}\n")
        f.write(f"Город: {city}\n")
        f.write(f"Провайдер: {isp}\n")
        f.write(f"Широта: {latitude}\n")
        f.write(f"Долгота: {longitude}\n")
        f.write(f"VPN: {is_vpn}\n")
        f.write(f"Платформа: {platform}\n")
        f.write(f"User-Agent: {user_agent}\n")

    return render_template_string(HTML_TEMPLATE,
                                  ip=ip,
                                  country=country,
                                  region=region,
                                  city=city,
                                  isp=isp,
                                  latitude=latitude,
                                  longitude=longitude,
                                  is_vpn=is_vpn)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
