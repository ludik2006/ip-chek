from flask import Flask, request, render_template_string, make_response
import requests
from datetime import datetime
import re
import json

app = Flask(__name__)

# Кэш для IP-данных
ip_cache = {}
COOKIE_CONSENT = "cookie_consent"

def get_ip_data(ip):
    if ip in ip_cache:
        return ip_cache[ip]

    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        geo = response.json()
        data = {
            "country": geo.get("country", "Неизвестно"),
            "city": geo.get("city", "Неизвестно"),
            "isp": geo.get("org", "Неизвестно")
        }
        ip_cache[ip] = data
        return data
    except Exception as e:
        print(f"[Ошибка IPAPI]: {e}")
        return {"country": "Ошибка", "city": "Ошибка", "isp": "Ошибка"}

def parse_user_agent(user_agent):
    os_patterns = {
        'Windows 11': r'Windows NT 10.0; Win64; x64',
        'Windows 10': r'Windows NT 10.0',
        'Linux': r'Linux',
        'Android': r'Android',
        'iOS': r'iPhone|iPad|iPod',
        'Mac OS X': r'Macintosh'
    }

    browser_patterns = {
        'Chrome': r'Chrome',
        'Firefox': r'Firefox',
        'Safari': r'Safari',
        'Edge': r'Edg'
    }

    # Определение ОС
    os = "Неизвестно"
    for name, pattern in os_patterns.items():
        if re.search(pattern, user_agent):
            os = name
            break

    # Определение браузера
    browser = "Неизвестно"
    for name, pattern in browser_patterns.items():
        if re.search(pattern, user_agent):
            browser = name
            break

    # Тип устройства
    device = "Смартфон/Планшет" if ('Mobile' in user_agent or 'Android' in user_agent or 'iPhone' in user_agent) else "Компьютер"

    return os, browser, device

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
            color: #00FF88; 
            font-family: Arial; 
            margin: 0; 
            padding: 0;
        }
        .container { 
            background-color: rgba(0, 0, 0, 0.7); 
            border-radius: 10px; 
            padding: 20px; 
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.6); 
            max-width: 800px; 
            margin: 20px auto;
        }
        h1 { text-align: center; }
        .info-block { 
            margin: 15px 0; 
            padding: 10px; 
            border-bottom: 1px solid #333; 
        }
        .warning { color: #FF5555; }
        
        /* Стили для модального окна */
        #consentModal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.9);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            color: white;
            text-align: center;
        }
        .consent-box {
            background-color: #222;
            padding: 30px;
            border-radius: 10px;
            max-width: 600px;
        }
        .consent-buttons {
            margin-top: 20px;
        }
        .consent-btn {
            padding: 10px 20px;
            margin: 0 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .accept-btn {
            background-color: #00AA00;
            color: white;
        }
        .reject-btn {
            background-color: #AA0000;
            color: white;
        }
        
        /* Стили для уведомления о куки */
        #cookieNotice {
            position: fixed;
            top: 20px;
            left: 20px;
            background-color: #333;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.5);
            z-index: 1001;
            display: none;
        }
    </style>
</head>
<body>
    <!-- Модальное окно согласия -->
    <div id="consentModal">
        <div class="consent-box">
            <h1>Добро пожаловать!</h1>
            <p>Для продолжения работы с сайтом необходимо согласиться на использование cookies и сбор данных.</p>
            <p>Нажимая "Принять", вы разрешаете нам собирать информацию о вашем устройстве и местоположении.</p>
            <div class="consent-buttons">
                <button class="consent-btn accept-btn" onclick="acceptConsent()">Принять</button>
                <button class="consent-btn reject-btn" onclick="rejectConsent()">Отклонить</button>
            </div>
        </div>
    </div>

    <!-- Уведомление о куки -->
    <div id="cookieNotice">
        <p>Разрешаете ли вы использование cookie-файлов?</p>
        <button onclick="confirmCookies()">Разрешить</button>
        <button onclick="hideCookieNotice()">Отклонить</button>
    </div>

    <!-- Основной контент (скрыт до согласия) -->
    <div id="mainContent" style="display: none;">
        <div class="container">
            <h1>🔍 Полная информация об устройстве</h1>
            
            <div class="info-block">
                <h2>🌍 Сеть и местоположение</h2>
                <p><strong>IP:</strong> {{ ip }}</p>
                <p><strong>Страна:</strong> {{ country }}</p>
                <p><strong>Город:</strong> {{ city }}</p>
                <p><strong>Провайдер:</strong> {{ isp }}</p>
                <div id="gpsData" style="display: none;">
                    <p><strong>Точные координаты:</strong> <span id="coordinates"></span></p>
                    <p><strong>Адрес:</strong> <span id="address"></span></p>
                    <div id="map" style="height: 300px; margin-top: 15px;"></div>
                </div>
            </div>

            <div class="info-block">
                <h2>💻 Система</h2>
                <p><strong>ОС:</strong> <span id="os">{{ os }}</span></p>
                <p><strong>Браузер:</strong> <span id="browser">{{ browser }}</span></p>
                <p><strong>Устройство:</strong> <span id="device">{{ device }}</span></p>
                <p><strong>Логические процессоры:</strong> <span id="cpuCores"></span> <span id="cpuWarning" class="warning"></span></p>
                <p><strong>GPU:</strong> <span id="gpu"></span></p>
            </div>

            <div class="info-block">
                <h2>🖥️ Экран</h2>
                <p><strong>Разрешение:</strong> <span id="screenResolution"></span></p>
                <p><strong>Глубина цвета:</strong> <span id="colorDepth"></span></p>
            </div>

            <div class="info-block">
                <h2>🔋 Батарея</h2>
                <p><strong>Заряд:</strong> <span id="batteryLevel"></span> <span id="batteryWarning" class="warning"></span></p>
                <p><strong>Состояние:</strong> <span id="batteryCharging"></span></p>
            </div>

            <div class="info-block">
                <h2>🔌 WebRTC (локальный IP)</h2>
                <p><strong>Локальный IP:</strong> <span id="webrtcIp">Определяется...</span></p>
            </div>

            <div class="info-block">
                <h2>🖋️ Установленные шрифты</h2>
                <p><strong>Доступные шрифты:</strong> <span id="installedFonts">Определяется...</span></p>
            </div>

            <div class="info-block">
                <h2>🖐️ Цифровой отпечаток</h2>
                <p><strong>Canvas Fingerprint:</strong> <span id="fingerprint"></span></p>
            </div>

            <div class="info-block warning">
                <h2>⚠️ Внимание!</h2>
                <p>Вы только что стали жертвой учебной фишинговой атаки. Нажав "Принять", вы добровольно передали свои данные.</p>
                <p><strong>Урок безопасности:</strong> Всегда проверяйте, кому вы даёте доступ к вашей информации!</p>
                <button onclick="deleteMyData()" style="background: #ff9800; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Удалить мои данные</button>
            </div>
        </div>
    </div>

    <script>
        // Проверяем, дал ли пользователь согласие
        function checkConsent() {
            return document.cookie.includes("{{ COOKIE_CONSENT }}=true");
        }

        // Показываем модальное окно, если нет согласия
        if (!checkConsent()) {
            document.getElementById('consentModal').style.display = 'flex';
        } else {
            document.getElementById('mainContent').style.display = 'block';
            loadAllData();
        }

        function acceptConsent() {
            // Устанавливаем куки на 30 дней
            const date = new Date();
            date.setTime(date.getTime() + (30 * 24 * 60 * 60 * 1000));
            document.cookie = "{{ COOKIE_CONSENT }}=true; expires=" + date.toUTCString() + "; path=/";
            
            document.getElementById('consentModal').style.display = 'none';
            document.getElementById('mainContent').style.display = 'block';
            document.getElementById('cookieNotice').style.display = 'block';
        }

        function rejectConsent() {
            window.location.href = "https://www.google.com";
        }

        function confirmCookies() {
            document.getElementById('cookieNotice').style.display = 'none';
            loadAllData();
        }

        function hideCookieNotice() {
            document.getElementById('cookieNotice').style.display = 'none';
        }

        function loadAllData() {
            // Загружаем все данные
            getCPUInfo();
            getGPUInfo();
            getScreenInfo();
            getBatteryInfo();
            getWebRTCIP();
            getFonts();
            getFingerprint();
            getLocation();
        }

        function getCPUInfo() {
            const cores = navigator.hardwareConcurrency;
            let warning = "";
            
            if (/Android|iPhone|iPad/i.test(navigator.userAgent)) {
                warning = " (мобильные процессоры показывают только кластеры)";
            }
            else if (cores >= 8) {
                warning = " (возможно, учитываются только Performance-ядра)";
            }
            
            document.getElementById('cpuCores').textContent = cores || "Неизвестно";
            document.getElementById('cpuWarning').textContent = warning;
        }

        function getGPUInfo() {
            if (navigator.gpu) {
                navigator.gpu.requestAdapter()
                    .then(adapter => {
                        const info = adapter.info || {};
                        document.getElementById('gpu').textContent = 
                            info.description || "Неизвестно";
                    })
                    .catch(() => {
                        document.getElementById('gpu').textContent = "Не удалось определить";
                    });
            } else {
                document.getElementById('gpu').textContent = "API не поддерживается";
            }
        }

        function getScreenInfo() {
            document.getElementById('screenResolution').textContent = 
                window.screen.width + "x" + window.screen.height;
            document.getElementById('colorDepth').textContent = 
                window.screen.colorDepth + " бит";
        }

        function getBatteryInfo() {
            if ('getBattery' in navigator) {
                navigator.getBattery()
                    .then(battery => {
                        document.getElementById('batteryLevel').textContent = 
                            Math.round(battery.level * 100) + "%";
                        document.getElementById('batteryCharging').textContent = 
                            battery.charging ? "Заряжается" : "Не заряжается";
                    })
                    .catch(() => {
                        showBatteryWarning();
                    });
            } else {
                showBatteryWarning();
            }
        }

        function showBatteryWarning() {
            document.getElementById('batteryLevel').textContent = "Недоступно";
            document.getElementById('batteryWarning').textContent = 
                " (требуется HTTPS или специальные разрешения)";
        }

        function getWebRTCIP() {
            const rtc = new RTCPeerConnection({ 
                iceServers: [{ urls: "stun:stun.l.google.com:19302" }] 
            });
            rtc.createDataChannel("");
            rtc.onicecandidate = e => {
                if (e.candidate) {
                    const ipRegex = /([0-9]{1,3}(\.[0-9]{1,3}){3})/;
                    const ipMatch = e.candidate.candidate.match(ipRegex);
                    if (ipMatch) {
                        document.getElementById('webrtcIp').textContent = ipMatch[1];
                        rtc.close();
                    }
                }
            };
            rtc.createOffer().then(offer => rtc.setLocalDescription(offer));
        }

        function getFonts() {
            const fonts = ["Arial", "Times New Roman", "Courier New", "Verdana", "Georgia"];
            const availableFonts = [];
            const canvas = document.createElement("canvas");
            const context = canvas.getContext("2d");
            
            fonts.forEach(font => {
                context.font = `12px "${font}"`;
                if (context.measureText("test").width > 0) availableFonts.push(font);
            });
            document.getElementById('installedFonts').textContent = 
                availableFonts.join(", ") || "Неизвестно";
        }

        function getFingerprint() {
            const fingerprintCanvas = document.createElement("canvas");
            const fingerprintCtx = fingerprintCanvas.getContext("2d");
            fingerprintCtx.fillStyle = "rgb(128, 0, 128)";
            fingerprintCtx.fillRect(0, 0, 100, 50);
            fingerprintCtx.fillStyle = "rgb(255, 255, 0)";
            fingerprintCtx.font = "18px Arial";
            fingerprintCtx.fillText("Fingerprint", 10, 30);
            document.getElementById('fingerprint').textContent = 
                fingerprintCanvas.toDataURL().slice(-32);
        }

        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    position => {
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        const acc = position.coords.accuracy;
                        
                        document.getElementById('coordinates').textContent = 
                            `${lat.toFixed(6)}, ${lon.toFixed(6)} (точность: ±${Math.round(acc)} м)`;
                        
                        // Получаем адрес
                        fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`)
                            .then(response => response.json())
                            .then(data => {
                                const address = data.address || {};
                                document.getElementById('address').textContent = 
                                    `${address.road || ''} ${address.house_number || ''}, ${address.city || address.town || address.village || ''}`;
                                
                                // Показываем карту
                                showMap(lat, lon);
                            });
                        
                        document.getElementById('gpsData').style.display = 'block';
                    },
                    error => {
                        console.error("Ошибка геолокации:", error);
                    },
                    { enableHighAccuracy: true }
                );
            }
        }

        function showMap(lat, lon) {
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

        function deleteMyData() {
            fetch('/delete-data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
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
def show_ip():
    consent = request.cookies.get(COOKIE_CONSENT)
    if not consent:
        return render_template_string(HTML_TEMPLATE, COOKIE_CONSENT=COOKIE_CONSENT)

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', "Неизвестно")
    os, browser, device = parse_user_agent(user_agent)
    geo = get_ip_data(ip)
    
    # Логирование в файл
    log_entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip,
        "country": geo['country'],
        "city": geo['city'],
        "isp": geo['isp'],
        "os": os,
        "browser": browser,
        "device": device,
        "user_agent": user_agent
    }
    
    with open("user_logs.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    return render_template_string(HTML_TEMPLATE,
                                ip=ip,
                                country=geo['country'],
                                city=geo['city'],
                                isp=geo['isp'],
                                os=os,
                                browser=browser,
                                device=device,
                                COOKIE_CONSENT=COOKIE_CONSENT)

@app.route('/delete-data', methods=['POST'])
def delete_data():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    try:
        # Читаем все логи
        with open("user_logs.json", "r") as f:
            logs = [json.loads(line) for line in f.readlines() if line.strip()]
        
        # Фильтруем логи, удаляя записи с текущим IP
        new_logs = [log for log in logs if log.get('ip') != ip]
        
        # Перезаписываем файл
        with open("user_logs.json", "w") as f:
            for log in new_logs:
                f.write(json.dumps(log) + "\n")
        
        return {'success': True}
    except Exception as e:
        print(f"Ошибка при удалении данных: {e}")
        return {'success': False}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
