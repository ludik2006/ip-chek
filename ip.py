from flask import Flask, request, render_template_string, redirect, url_for
import requests
from datetime import datetime
import re
import os

app = Flask(__name__)

# База данных для хранения согласий (в реальном проекте используйте SQLite/PostgreSQL)
user_consents = {}
LOG_FILE = "ips.log"

def get_ip_data(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        return response.json()
    except:
        return {"error": "Не удалось получить данные"}

def parse_user_agent(user_agent):
    os = browser = device = "Неизвестно"
    os_patterns = {
        'Windows 11': r'Windows NT 10.0; Win64; x64',
        'Windows 10': r'Windows NT 10.0',
        'Linux': r'Linux',
        'Android': r'Android',
        'iOS': r'iPhone|iPad|iPod',
        'Mac OS X': r'Macintosh'
    }
    
    for name, pattern in os_patterns.items():
        if re.search(pattern, user_agent):
            os = name
            break

    browser_patterns = {
        'Chrome': r'Chrome',
        'Firefox': r'Firefox',
        'Safari': r'Safari',
        'Edge': r'Edg'
    }
    
    for name, pattern in browser_patterns.items():
        if re.search(pattern, user_agent):
            browser = name
            break

    device = "Смартфон/Планшет" if ('Mobile' in user_agent or 'Android' in user_agent or 'iPhone' in user_agent) else "Компьютер"

    return os, browser, device

def log_data(ip, user_agent, geo, os, browser, device, gps_data=None):
    log_entry = f"""
=== Новый вход ===
Время: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
IP: {ip}
Страна: {geo.get('country', 'Неизвестно')}
Город: {geo.get('city', 'Неизвестно')}
Провайдер: {geo.get('org', 'Неизвестно')}
ОС: {os}
Браузер: {browser}
Устройство: {device}
User-Agent: {user_agent}
"""
    if gps_data:
        log_entry += f"""GPS данные:
Широта: {gps_data.get('lat', '')}
Долгота: {gps_data.get('lon', '')}
Точность: {gps_data.get('acc', '')} м
Адрес: {gps_data.get('address', '')}
"""
    log_entry += "------------------------------------\n"
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

def delete_user_logs(ip):
    if not os.path.exists(LOG_FILE):
        return False

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    skip = False
    for line in lines:
        if line.startswith("=== Новый вход ==="):
            skip = False
        if f"IP: {ip}" in line:
            skip = True
        if not skip:
            new_lines.append(line)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return True

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Сервис геолокации</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        .consent-box, .warning-box {
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .consent-box {
            background-color: #f0f8ff;
            border: 1px solid #d0e3ff;
        }
        .warning-box {
            background-color: #fff0f0;
            border: 1px solid #ffd0d0;
        }
        button {
            padding: 10px 20px;
            margin: 10px 5px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .btn-accept {
            background-color: #4CAF50;
            color: white;
        }
        .btn-deny {
            background-color: #f44336;
            color: white;
        }
        .btn-delete {
            background-color: #ff9800;
            color: white;
        }
        #geoResult, #phishing-warning {
            display: none;
        }
    </style>
</head>
<body>
    {% if not consent_given %}
    <div class="consent-box">
        <h2>Согласие на сбор данных</h2>
        <p>Мы используем cookies и собираем данные о вашем местоположении для улучшения сервиса. Продолжая, вы соглашаетесь с нашей политикой конфиденциальности.</p>
        <div>
            <button class="btn-accept" onclick="giveConsent()">Принять</button>
            <button class="btn-deny" onclick="window.location.href='/deny'">Отклонить</button>
        </div>
    </div>
    {% endif %}

    <div id="geoResult" class="consent-box">
        <h2>Определение местоположения</h2>
        <button onclick="getLocation()">Определить моё местоположение</button>
        <div id="locationData"></div>
        <div id="map" style="height: 300px; margin-top: 15px;"></div>
    </div>

    <div id="phishing-warning" class="warning-box">
        <h2>⚠️ Внимание! Фишинговая атака</h2>
        <p>Вы только что стали жертвой учебной фишинговой атаки. Нажав "Принять", вы добровольно передали свои геоданные.</p>
        <p><strong>Урок безопасности:</strong> Всегда проверяйте, кому вы даёте доступ к вашей геолокации!</p>
        <button class="btn-delete" onclick="deleteMyData()">Удалить мои данные из логов</button>
    </div>

    <script>
        function giveConsent() {
            fetch('/give-consent', { method: 'POST' })
                .then(() => {
                    document.querySelector('.consent-box').style.display = 'none';
                    document.getElementById('geoResult').style.display = 'block';
                });
        }

        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    showPosition,
                    showError,
                    { enableHighAccuracy: true }
                );
            } else {
                alert("Геолокация не поддерживается вашим браузером");
            }
        }

        function showPosition(position) {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            const acc = position.coords.accuracy;
            
            document.getElementById('locationData').innerHTML = `
                <p><strong>Широта:</strong> ${lat.toFixed(6)}</p>
                <p><strong>Долгота:</strong> ${lon.toFixed(6)}</p>
                <p><strong>Точность:</strong> ±${Math.round(acc)} метров</p>
            `;

            // Отправка данных на сервер
            fetch('/log-gps', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lat: lat,
                    lon: lon,
                    acc: acc
                })
            });

            // Показать предупреждение о фишинге
            document.getElementById('phishing-warning').style.display = 'block';
            document.getElementById('geoResult').style.display = 'none';
        }

        function showError(error) {
            alert("Ошибка при определении местоположения: " + error.message);
        }

        function deleteMyData() {
            fetch('/delete-logs', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if(data.success) {
                        alert("Ваши данные были удалены из логов!");
                        document.getElementById('phishing-warning').style.display = 'none';
                    } else {
                        alert("Не удалось удалить данные");
                    }
                });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Неизвестно')
    geo = get_ip_data(ip)
    os, browser, device = parse_user_agent(user_agent)
    
    consent_given = user_consents.get(ip, False)
    
    if not consent_given:
        log_data(ip, user_agent, geo, os, browser, device)
    
    return render_template_string(HTML_TEMPLATE, consent_given=consent_given)

@app.route('/give-consent', methods=['POST'])
def give_consent():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_consents[ip] = True
    return {'status': 'success'}

@app.route('/log-gps', methods=['POST'])
def log_gps():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Неизвестно')
    geo = get_ip_data(ip)
    os, browser, device = parse_user_agent(user_agent)
    
    log_data(ip, user_agent, geo, os, browser, device, request.json)
    
    return {'status': 'success'}

@app.route('/delete-logs', methods=['POST'])
def handle_delete_logs():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    success = delete_user_logs(ip)
    return {'success': success}

@app.route('/deny')
def deny():
    return "Вы отказались от предоставления данных. Спасибо за визит!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
