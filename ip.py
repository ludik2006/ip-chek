from flask import Flask, request, render_template_string
import requests
from datetime import datetime
import base64
import json

app = Flask(__name__)

MAXMIND_USER_ID = "your_user_id"
MAXMIND_LICENSE_KEY = "your_license_key"
PROXYCHECK_API_KEY = ""  # опционально добавь свой ключ

HTML_TEMPLATE = """..."""  # Без изменений, оставляем как есть (твой шаблон)

def get_ip_info(ip):
    # Сначала пытаемся через MaxMind
    try:
        auth_string = f"{MAXMIND_USER_ID}:{MAXMIND_LICENSE_KEY}"
        headers = {
            "Authorization": "Basic " + base64.b64encode(auth_string.encode()).decode()
        }
        res = requests.get(f"https://geoip.maxmind.com/geoip/v2.1/city/{ip}", headers=headers, timeout=5)
        data = res.json()

        return {
            "country": data.get("country", {}).get("names", {}).get("ru", "Неизвестно"),
            "region": data.get("subdivisions", [{}])[0].get("names", {}).get("ru", "Неизвестно"),
            "city": data.get("city", {}).get("names", {}).get("ru", "Неизвестно"),
            "latitude": data.get("location", {}).get("latitude", "—"),
            "longitude": data.get("location", {}).get("longitude", "—"),
            "isp": data.get("traits", {}).get("isp", "—"),
            "language": "—"
        }
    except Exception as e:
        print(f"[MaxMind Ошибка]: {e}")

    # Если MaxMind не сработал — fallback на ipapi.co
    try:
        ipapi = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5).json()
        return {
            "country": ipapi.get("country_name", "Неизвестно"),
            "region": ipapi.get("region", "Неизвестно"),
            "city": ipapi.get("city", "Неизвестно"),
            "latitude": ipapi.get("latitude", "—"),
            "longitude": ipapi.get("longitude", "—"),
            "isp": ipapi.get("org", "—"),
            "language": ipapi.get("languages", "—").split(",")[0] if ipapi.get("languages") else "—"
        }
    except Exception as e:
        print(f"[ipapi Ошибка]: {e}")
        return {key: "Ошибка" for key in ["country", "region", "city", "latitude", "longitude", "isp", "language"]}


def check_vpn(ip):
    try:
        url = f"https://proxycheck.io/v2/{ip}?vpn=1&asn=1"
        if PROXYCHECK_API_KEY:
            url += f"&key={PROXYCHECK_API_KEY}"
        res = requests.get(url, timeout=5).json()

        data = res.get(ip, {})
        if data.get("proxy") == "yes" or data.get("type") in ["VPN", "TOR"]:
            return "Да"
        elif data.get("proxy") == "no":
            return "Нет"
    except Exception as e:
        print(f"[VPN API Ошибка]: {e}")
    return "Неизвестно"


@app.route('/')
def show_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip in ['127.0.0.1', 'localhost']:
        ip = request.remote_addr

    user_agent = request.headers.get('User-Agent')
    platform = request.user_agent.platform or "—"

    ip_info = get_ip_info(ip)
    is_vpn = check_vpn(ip)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open("ips.log", "a", encoding="utf-8") as f:
        f.write(f"\n=== Новый вход ===\n")
        f.write(f"Время: {now}\n")
        f.write(f"IP: {ip}\n")
        for key, val in ip_info.items():
            f.write(f"{key.capitalize()}: {val}\n")
        f.write(f"VPN: {is_vpn}\n")
        f.write(f"User-Agent: {user_agent}\n")
        f.write(f"Заголовки: {json.dumps(dict(request.headers), ensure_ascii=False, indent=2)}\n")

    return render_template_string(HTML_TEMPLATE,
                                  ip=ip,
                                  country=ip_info["country"],
                                  region=ip_info["region"],
                                  city=ip_info["city"],
                                  isp=ip_info["isp"],
                                  latitude=ip_info["latitude"],
                                  longitude=ip_info["longitude"],
                                  language=ip_info["language"],
                                  platform=platform,
                                  is_vpn=is_vpn)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
