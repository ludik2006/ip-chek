from flask import Flask, request, render_template_string, make_response
import requests
from datetime import datetime
import re
import os
import json

app = Flask(__name__)

# Конфигурация
LOG_FILE = "user_logs.json"
COOKIE_NAME = "data_consent"

def get_ip_data(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        return response.json()
    except:
        return {"error": "Не удалось получить данные"}

def get_device_info(user_agent):
    # Анализ User-Agent
    os = browser = "Неизвестно"
    
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

    return {
        "os": os,
        "browser": browser,
        "device": device,
        "cpu_cores": navigator.hardwareConcurrency if 'navigator' in globals() else "Неизвестно"
    }

def log_user_data(ip, user_data):
    # Загрузка существующих логов
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                logs = json.load(f)
            except:
                pass
    
    # Добавление новых данных
    logs.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip,
        **user_data
    })
    
    # Сохранение
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

def delete_user_data(ip):
    if not os.path.exists(LOG_FILE):
        return False

    with open(LOG_FILE, "r") as f:
        logs = json.load(f)

    new_logs = [entry for entry in logs if entry.get("ip") != ip]

    with open(LOG_FILE, "w") as f:
        json.dump(new_logs, f, indent=2)

    return len(logs) != len(new_logs)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Сервис аналитики</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        .cookie-banner {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #f1f1f1;
            padding: 15px;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .cookie-banner p {
            margin: 0;
            flex-grow: 1;
        }
        .cookie-btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 8px 16px;
            margin-left: 10px;
            border-radius: 4px;
            cursor: pointer;
        }
        .cookie-btn.deny {
            background: #f44336;
        }
        .info-block {
            background: #f9f9f9;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .warning-box {
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 15px;
            margin-top: 30px;
        }
        #userData {
            display: none;
        }
    </style>
</head>
<body>
    <div id="userData">
        <h1>Ваши технические данные</h1>
        
        <div class="info-block">
            <h3>🌐 Сетевая информация</h3>
            <p><strong>IP-адрес:</strong> <span id="ip"></span></p>
            <p><strong>Местоположение (IP):</strong> <span id="ipLocation"></span></p>
            <p><strong>Точные координаты:</strong> <span id="gpsCoords"></span></p>
            <p><strong>Точность:</strong> <span id="gpsAccuracy"></span></p>
        </div>

        <div class="info-block">
            <h3>💻 Системная информация</h3>
            <p><strong>ОС:</strong> <span id="os"></span></p>
            <p><strong>Браузер:</strong> <span id="browser"></span></p>
            <p><strong>Устройство:</strong> <span id="device"></span></p>
            <p><strong>Ядер CPU:</strong> <span id="cpuCores"></span></p>
        </div>

        <div class="warning-box">
            <h3>⚠️ Важное предупреждение</h3>
            <p>Вы только что стали жертвой учебной фишинговой атаки. Нажав "Принять" в cookie-баннере, вы добровольно предоставили доступ к своим данным.</p>
            <p><strong>Урок безопасности:</strong> Всегда внимательно читайте, кому вы даёте доступ к вашей информации!</p>
            <button onclick="deleteMyData()" style="background: #ff9800; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Удалить мои данные</button>
        </div>
    </div>

    <div id="cookieBanner" class="cookie-banner">
        <p>Мы используем cookies для анализа данных. Продолжая использовать сайт, вы соглашаетесь на сбор информации о вашем устройстве и местоположении.</p>
        <div>
            <button class="cookie-btn deny" onclick="denyConsent()">Отклонить</button>
            <button class="cookie-btn" onclick="acceptConsent()">Принять</button>
        </div>
    </div>

    <script>
        // Проверяем, есть ли уже согласие
        if (document.cookie.includes("{{ COOKIE_NAME }}=true")) {
            document.getElementById('cookieBanner').style.display = 'none';
            loadUserData();
        }

        function acceptConsent() {
            // Устанавливаем куку на 1 год
            document.cookie = "{{ COOKIE_NAME }}=true; max-age=31536000; path=/";
            document.getElementById('cookieBanner').style.display = 'none';
            
            // Сразу начинаем сбор данных
            loadUserData();
        }

        function denyConsent() {
            window.location.href = "/deny";
        }

        function loadUserData() {
            // Показываем блок с данными
            document.getElementById('userData').style.display = 'block';
            
            // Получаем IP и базовые данные
            fetch('/get-ip')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('ip').textContent = data.ip;
                    document.getElementById('ipLocation').textContent = 
                        `${data.city || 'Неизвестно'}, ${data.country || 'Неизвестно'}`;
                    
                    // Получаем точные координаты
                    getGeolocation(data.ip);
                });
            
            // Заполняем системную информацию
            const deviceInfo = getDeviceInfo();
            document.getElementById('os').textContent = deviceInfo.os;
            document.getElementById('browser').textContent = deviceInfo.browser;
            document.getElementById('device').textContent = deviceInfo.device;
            document.getElementById('cpuCores').textContent = deviceInfo.cpu_cores;
        }

        function getDeviceInfo() {
            return {
                os: navigator.platform,
                browser: navigator.userAgent,
                device: /Mobi|Android|iPhone/i.test(navigator.userAgent) ? "Мобильное" : "Компьютер",
                cpu_cores: navigator.hardwareConcurrency || "Неизвестно"
            };
        }

        function getGeolocation(ip) {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    position => {
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        const acc = position.coords.accuracy;
                        
                        document.getElementById('gpsCoords').textContent = 
                            `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
                        document.getElementById('gpsAccuracy').textContent = 
                            `±${Math.round(acc)} метров`;
                        
                        // Отправляем данные на сервер
                        fetch('/log-gps', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                lat: lat,
                                lon: lon,
                                acc: acc,
                                ip: ip
                            })
                        });
                    },
                    error => {
                        document.getElementById('gpsCoords').textContent = 
                            "Доступ запрещен";
                    },
                    { enableHighAccuracy: true }
                );
            }
        }

        function deleteMyData() {
            fetch('/delete-data', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert("Ваши данные были удалены!");
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
    consent = request.cookies.get(COOKIE_NAME) == 'true'
    return render_template_string(HTML_TEMPLATE, COOKIE_NAME=COOKIE_NAME)

@app.route('/get-ip')
def get_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    geo = get_ip_data(ip)
    return {
        "ip": ip,
        "country": geo.get("country", "Неизвестно"),
        "city": geo.get("city", "Неизвестно")
    }

@app.route('/log-gps', methods=['POST'])
def log_gps():
    data = request.json
    ip = data.get('ip', request.headers.get('X-Forwarded-For', request.remote_addr))
    user_agent = request.headers.get('User-Agent', 'Неизвестно')
    
    device_info = {
        "os": "Неизвестно",
        "browser": "Неизвестно",
        "device": "Неизвестно",
        "cpu_cores": "Неизвестно",
        "location": {
            "lat": data.get('lat'),
            "lon": data.get('lon'),
            "accuracy": data.get('acc')
        }
    }
    
    log_user_data(ip, device_info)
    return {'status': 'success'}

@app.route('/delete-data', methods=['POST'])
def delete_data():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    success = delete_user_data(ip)
    return {'success': success}

@app.route('/deny')
def deny():
    resp = make_response("Вы отказались от сбора данных. Спасибо за визит!")
    resp.set_cookie(COOKIE_NAME, 'false', max_age=31536000)
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
