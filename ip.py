from flask import Flask, request, render_template_string, jsonify
import requests
from datetime import datetime

app = Flask(__name__)
ip_cache = {}

# HTML шаблон с порт-сканированием + уведомление и подтверждение
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang=\"ru\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Ваш IP</title>
    <style>
        body {
            background-color: #111;
            color: #00FF88;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            text-align: center;
        }
        .container {
            background-color: rgba(0, 0, 0, 0.7);
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.6);
        }
        .ip-box {
            font-size: 1.5em;
        }
        .title {
            font-size: 2em;
            margin-bottom: 20px;
            font-weight: bold;
        }
        .info {
            margin: 10px 0;
        }
        .footer {
            margin-top: 20px;
            font-size: 0.9em;
            color: #aaa;
        }
    </style>
</head>
<body>
    <div class=\"container\">
        <div class=\"title\">Информация о вашем IP</div>
        <div class=\"ip-box\">
            <div class=\"info\"><strong>Ваш IP:</strong> {{ ip }}</div>
            <div class=\"info\"><strong>Страна:</strong> {{ country }}</div>
            <div class=\"info\"><strong>Город:</strong> {{ city }}</div>
            <div class=\"info\"><strong>Провайдер:</strong> {{ isp }}</div>
            <div class=\"info\"><strong>Гео-локация:</strong> {{ location }}</div>
            <div class=\"info\"><strong>Почтовый код:</strong> {{ postal }}</div>
            <div class=\"info\" id=\"ports\">Сканирование портов...</div>
        </div>
        <div class=\"footer\">Данные получены через <a href=\"https://ipinfo.io/{{ ip }}\" target=\"_blank\" style=\"color: #00FF88;\">ipinfo.io</a></div>
    </div>

    <script>
        async function scanPorts() {
            if (!confirm("Разрешаете определить открытые порты на вашем устройстве?")) {
                document.getElementById("ports").textContent = "Сканирование отменено пользователем.";
                return;
            }

            const commonPorts = [21, 22, 23, 25, 53, 67, 68, 80, 110, 123, 135, 139, 143, 161, 389, 443, 445, 587, 993, 995, 1433, 1521, 1723, 3306, 3389, 5432, 5900, 8080];
            const results = [];

            for (let port of commonPorts) {
                try {
                    const controller = new AbortController();
                    const timeout = setTimeout(() => controller.abort(), 1000);
                    await fetch(`http://localhost:${port}`, {
                        mode: 'no-cors',
                        signal: controller.signal
                    });
                    clearTimeout(timeout);
                    results.push(port);
                } catch (e) {}
            }

            document.getElementById("ports").textContent = results.length
                ? "Открытые порты: " + results.join(', ')
                : "Открытые порты не обнаружены";

            fetch("/report_ports", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ ports: results })
            });
        }

        window.onload = scanPorts;
    </script>
</body>
</html>
"""

def get_ip_data(ip):
    if ip in ip_cache:
        return ip_cache[ip]

    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        geo = response.json()
        data = {
            "country": geo.get("country", "Неизвестно"),
            "city": geo.get("city", "Неизвестно"),
            "isp": geo.get("org", "Неизвестно"),
            "location": geo.get("loc", "Неизвестно"),
            "postal": geo.get("postal", "Неизвестно")
        }
        ip_cache[ip] = data
        return data
    except Exception as e:
        print(f"[Ошибка геолокации]: {e}")
        return {
            "country": "Ошибка",
            "city": "Ошибка",
            "isp": "Ошибка",
            "location": "Ошибка",
            "postal": "Ошибка"
        }

@app.route('/')
def show_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent')
    geo = get_ip_data(ip)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open("ips.log", "a", encoding="utf-8") as f:
        f.write(f"\n=== Новый вход ===\n")
        f.write(f"Время: {now}\n")
        f.write(f"IP: {ip}\n")
        f.write(f"Страна: {geo['country']}\n")
        f.write(f"Город: {geo['city']}\n")
        f.write(f"Провайдер: {geo['isp']}\n")
        f.write(f"Локация: {geo['location']}\n")
        f.write(f"Почтовый код: {geo['postal']}\n")
        f.write(f"User-Agent: {user_agent}\n")

    return render_template_string(HTML_TEMPLATE,
                                  ip=ip,
                                  country=geo['country'],
                                  city=geo['city'],
                                  isp=geo['isp'],
                                  location=geo['location'],
                                  postal=geo['postal'])

@app.route('/report_ports', methods=['POST'])
def report_ports():
    data = request.json
    ports = data.get("ports", [])
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open("ips.log", "a", encoding="utf-8") as f:
        f.write(f"[Открытые порты от {ip} @ {now}]: {', '.join(map(str, ports)) or 'ничего не найдено'}\n")

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
