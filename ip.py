from flask import Flask, request, render_template_string
import requests
from datetime import datetime
import re

app = Flask(__name__)

# Кэш для IP-данных
ip_cache = {}

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
    # Обновлённые правила для Windows 11
    os_patterns = [
        (r'Windows 11', 'Windows 11'),
        (r'Windows NT 10.0', 'Windows 10/11'),
        (r'Linux x86_64', 'Linux (PC)'),
        (r'Linux armv8l', 'Linux (Android)'),
        (r'Android', 'Android'),
        (r'iPhone|iPad|iPod', 'iOS'),
        (r'Mac OS X', 'macOS')
    ]

    browser_patterns = [
        (r'Edg', 'Microsoft Edge'),
        (r'Chrome', 'Google Chrome'),
        (r'Firefox', 'Mozilla Firefox'),
        (r'Safari', 'Safari')
    ]

    # Определение ОС
    os = "Неизвестно"
    for pattern, name in os_patterns.items():
        if re.search(pattern, user_agent):
            os = name
            break

    # Дополнительная проверка для Windows 11
    if os == "Windows 10/11":
        if "Win64; x64" in user_agent and "Trident/7.0" not in user_agent:
            os = "Windows 11"
        else:
            os = "Windows 10"

    # Определение браузера
    browser = "Неизвестно"
    for pattern, name in browser_patterns.items():
        if re.search(pattern, user_agent):
            browser = name
            break

    # Тип устройства
    if 'Mobile' in user_agent or 'Android' in user_agent or 'iPhone' in user_agent:
        device = "Смартфон/Планшет"
    else:
        device = "ПК"

    return os, browser, device

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Анализ устройства</title>
    <style>
        body { background-color: #111; color: #00FF88; font-family: Arial; margin: 0; padding: 20px; }
        .container { background-color: rgba(0, 0, 0, 0.7); border-radius: 10px; padding: 20px; box-shadow: 0 0 20px rgba(0, 255, 136, 0.6); max-width: 800px; margin: 0 auto; }
        h1 { text-align: center; }
        .info-block { margin: 15px 0; padding: 10px; border-bottom: 1px solid #333; }
        .warning { color: #FF5555; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Полная информация об устройстве</h1>
        
        <div class="info-block">
            <h2>🌍 Сеть и местоположение</h2>
            <p><strong>IP:</strong> {{ ip }}</p>
            <p><strong>Страна:</strong> {{ country }}</p>
            <p><strong>Город:</strong> {{ city }}</p>
            <p><strong>Провайдер:</strong> {{ isp }}</p>
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
    </div>

    <script>
        // Улучшенное определение процессора
        function getCPUInfo() {
            const cores = navigator.hardwareConcurrency;
            let warning = "";
            
            // Предупреждение для мобильных устройств
            if (/Android|iPhone|iPad/i.test(navigator.userAgent)) {
                warning = " (мобильные процессоры показывают только кластеры)";
            }
            // Предупреждение для современных CPU
            else if (cores >= 8) {
                warning = " (возможно, учитываются только Performance-ядра)";
            }
            
            document.getElementById('cpuCores').textContent = cores || "Неизвестно";
            document.getElementById('cpuWarning').textContent = warning;
        }

        // Определение GPU
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

        // Альтернативный метод для батареи
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

        // Инициализация всех функций
        window.onload = function() {
            // Системная информация
            getCPUInfo();
            getGPUInfo();
            document.getElementById('screenResolution').textContent = 
                window.screen.width + "x" + window.screen.height;
            document.getElementById('colorDepth').textContent = 
                window.screen.colorDepth + " бит";

            // Батарея
            getBatteryInfo();

            // WebRTC IP
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

            // Шрифты
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

            // Canvas Fingerprinting
            const fingerprintCanvas = document.createElement("canvas");
            const fingerprintCtx = fingerprintCanvas.getContext("2d");
            fingerprintCtx.fillStyle = "rgb(128, 0, 128)";
            fingerprintCtx.fillRect(0, 0, 100, 50);
            fingerprintCtx.fillStyle = "rgb(255, 255, 0)";
            fingerprintCtx.font = "18px Arial";
            fingerprintCtx.fillText("Fingerprint", 10, 30);
            document.getElementById('fingerprint').textContent = 
                fingerprintCanvas.toDataURL().slice(-32);
        };
    </script>
</body>
</html>
"""

@app.route('/')
def show_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', "Неизвестно")
    os, browser, device = parse_user_agent(user_agent)
    geo = get_ip_data(ip)
    
    # Логирование в файл
    log_entry = f"""
=== Новый вход ===
Время: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
IP: {ip}
Страна: {geo['country']}
Город: {geo['city']}
Провайдер: {geo['isp']}
ОС: {os}
Браузер: {browser}
Устройство: {device}
User-Agent: {user_agent}
------------------------------------
"""
    with open("ips.log", "a", encoding="utf-8") as f:
        f.write(log_entry)
    
    return render_template_string(HTML_TEMPLATE,
                                ip=ip,
                                country=geo['country'],
                                city=geo['city'],
                                isp=geo['isp'],
                                os=os,
                                browser=browser,
                                device=device)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
