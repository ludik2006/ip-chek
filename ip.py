from flask import Flask, request, render_template_string
import requests
from datetime import datetime
import re

app = Flask(__name__)

def get_ip_data(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        return response.json()
    except:
        return {"error": "Не удалось получить данные"}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Точная геолокация</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 15px;
            line-height: 1.6;
        }
        .info-block {
            background: #f5f5f5;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
        }
        button {
            background: #4285f4;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 16px;
            width: 100%;
            cursor: pointer;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        #map {
            height: 250px;
            width: 100%;
            border-radius: 12px;
            margin-top: 15px;
            border: 1px solid #ddd;
        }
        .accuracy {
            display: inline-block;
            padding: 3px 8px;
            background: #4285f4;
            color: white;
            border-radius: 10px;
            font-size: 12px;
        }
        .loading {
            display: none;
            text-align: center;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="info-block">
        <h2>📍 Основная информация</h2>
        <p><strong>IP:</strong> {{ ip }}</p>
        <p><strong>Местоположение (по IP):</strong> {{ city }}, {{ country }}</p>
    </div>

    <button onclick="getPreciseLocation()">Определить точное местоположение</button>
    
    <div id="loading" class="loading">
        <p>Определение местоположения...</p>
    </div>
    
    <div id="geoResult" class="info-block" style="display:none;">
        <h2>🗺 Точные координаты</h2>
        <div id="positionData"></div>
        <div id="addressData"></div>
        <div id="map"></div>
    </div>

    <script>
        // Улучшенная геолокация для мобильных устройств
        function getPreciseLocation() {
            const loading = document.getElementById('loading');
            const resultBlock = document.getElementById('geoResult');
            
            loading.style.display = 'block';
            resultBlock.style.display = 'none';
            
            if (!navigator.geolocation) {
                showError("Ваш браузер не поддерживает геолокацию");
                return;
            }

            const options = {
                enableHighAccuracy: true,  // Используем GPS на мобильных
                timeout: 10000,           // 10 секунд ожидания
                maximumAge: 0             // Не использовать кешированные данные
            };

            navigator.geolocation.getCurrentPosition(
                position => {
                    loading.style.display = 'none';
                    resultBlock.style.display = 'block';
                    showPrecisePosition(position);
                },
                error => {
                    loading.style.display = 'none';
                    handleGeolocationError(error);
                },
                options
            );
        }

        function showPrecisePosition(position) {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            const acc = position.coords.accuracy;
            
            document.getElementById('positionData').innerHTML = `
                <p><strong>Широта:</strong> ${lat.toFixed(6)}</p>
                <p><strong>Долгота:</strong> ${lon.toFixed(6)}</p>
                <p><strong>Точность:</strong> <span class="accuracy">±${Math.round(acc)} метров</span></p>
            `;

            // Используем Mapbox для лучшего отображения на мобильных
            showMapboxMap(lat, lon);
            
            // Получаем детализированный адрес
            getReverseGeocoding(lat, lon);
        }

        function showMapboxMap(lat, lon) {
            // Бесплатный ключ для демонстрации (ограничение 50,000 запросов/месяц)
            const mapboxToken = 'pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw';
            
            document.getElementById('map').innerHTML = `
                <iframe
                    width="100%"
                    height="100%"
                    frameborder="0"
                    scrolling="no"
                    marginheight="0"
                    marginwidth="0"
                    src="https://api.mapbox.com/styles/v1/mapbox/streets-v11.html?title=false&access_token=${mapboxToken}&zoom=15&center=${lon},${lat}&marker=${lon},${lat}"
                ></iframe>
            `;
        }

        function getReverseGeocoding(lat, lon) {
            // Используем OpenStreetMap Nominatim API
            fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lon}`)
                .then(response => response.json())
                .then(data => {
                    const address = data.address || {};
                    let addressStr = '';
                    
                    if (address.road) addressStr += `${address.road}`;
                    if (address.house_number) addressStr += `, ${address.house_number}`;
                    if (addressStr === '') addressStr = 'Адрес не определён';
                    
                    document.getElementById('addressData').innerHTML = `
                        <p><strong>Примерный адрес:</strong> ${addressStr}</p>
                        ${address.city ? `<p><strong>Город:</strong> ${address.city}</p>` : ''}
                        ${address.country ? `<p><strong>Страна:</strong> ${address.country}</p>` : ''}
                    `;
                })
                .catch(() => {
                    document.getElementById('addressData').innerHTML = 
                        '<p>Не удалось определить адрес</p>';
                });
        }

        function handleGeolocationError(error) {
            let message;
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    message = "Вы отказали в доступе к геолокации. Разрешите доступ в настройках браузера.";
                    break;
                case error.POSITION_UNAVAILABLE:
                    message = "Информация о местоположении недоступна. Проверьте подключение к интернету и GPS.";
                    break;
                case error.TIMEOUT:
                    message = "Время ожидания истекло. Убедитесь, что GPS включён.";
                    break;
                default:
                    message = "Произошла неизвестная ошибка при определении местоположения.";
            }
            alert(message);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    geo = get_ip_data(ip)
    
    return render_template_string(HTML_TEMPLATE,
        ip=ip,
        country=geo.get('country', 'Неизвестно'),
        city=geo.get('city', 'Неизвестно')
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
