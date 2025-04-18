from flask import Flask, request, render_template_string
import requests
from datetime import datetime
import base64

app = Flask(__name__)

# 🔐 Вставь свои данные сюда
MAXMIND_USER_ID = "your_user_id"
MAXMIND_LICENSE_KEY = "your_license_key"

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
            <div class="info"><strong>Регион:</strong> {{ region }}</div>
            <div class="info"><strong>Город:</strong> {{ city }}</div>
            <div class="info"><strong>Провайдер:</strong> {{ isp }}</div>
            <div class="info"><strong>Координаты:</strong> {{ latitude }}, {{ longitude }}</div>
            <div class="info"><strong>Язык:</strong> {{ language }}</div>
            <div class="info"><strong>Платформа:</strong> {{ platform }}</div>
            <div class="info"><strong>Использует VPN:</strong> {{ is_vpn }}</div>
        </div>
        <div class="footer">Данные от MaxMind GeoIP2 + ProxyCheck</div>
    </div>
</body>
</html>
"""

def get_ip_info(ip):
    try:
        # Basic auth для MaxMind
        auth_string = f"{MAXMIND_USER_ID}:{MAXMIND_LICENSE_KEY}"
        headers = {
            "Authorization": "Basic " + base64.b64encode(auth_string.encode()).decode()
        }

        response = requests.get(f"https://geoip.maxmind.com/geoip/v2.1/city/{ip}", headers=headers)
        data = response.json()

        country = data.get("country", {}).get("names", {}).get("ru", "Неизвестно")
        region = data.get("subdivisions", [{}])[0].get("names", {}).get("ru", "Неизвестно")
        city = data.get("city", {}).get("names", {}).get("ru", "Неизвестно")
        latitude = data.get("location", {}).get("latitude", "Неизвестно")
        longitude = data.get("location", {}).get("longitude", "Неизвестно")
        isp = data.get("traits", {}).get("isp", "Неизвестно")

        return {
            "country": country,
            "region": region,
            "city": city,
            "latitude": latitude,
            "longitude": longitude,
            "isp": isp,
            "language": "—"  # можно дополнить позже
        }
    except Exception as e:
        print(f"[Ошибка MaxMind]: {e}")
        return {key: "Ошибка" for key in ["country", "region", "city", "latitude", "longitude", "isp", "language"]}

def check_vpn(ip):
    try:
        res = requests.get(f"https://proxycheck.io/v2/{ip}?vpn=1").json()
        if ip in res and "proxy" in res[ip]:
            return "Да" if res[ip]["proxy"] == "yes" else "Нет"
    except Exception as e:
        print(f"[Ошибка VPN API]: {e}")
    return "Неизвестно"

@app.route('/')
def show_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip in ['127.0.0.1', 'localhost']:
        ip = request.remote_addr

    user_agent = request.headers.get('User-Agent')
    platform = request.user_agent.platform or "—"

    ip_info = get_ip_info(ip)
    is_vpn = check_vpn(ip)

    # Лог
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("ips.log", "a", encoding="utf-8") as f:
        f.write(f"\n=== Новый вход ===\nВремя: {now}\nIP: {ip}\n")
        for key, val in ip_info.items():
            f.write(f"{key.capitalize()}: {val}\n")
        f.write(f"VPN: {is_vpn}\nUser-Agent: {user_agent}\n")

    return render_template_string(HTML_TEMPLATE,
                                  ip=ip,
                                  country=ip_info["country"],
                                  region=ip_info["region"],
                                  city=ip_info["city"],
                                  isp=ip_info["isp"],
                                  latitude=ip_info["latitude"],
                                  longitude=ip_info["longitude"],
                                  language=ip_info["language"],
                                  platform=platform,
                                  is_vpn=is_vpn)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
