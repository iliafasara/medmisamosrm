import os
import requests
from flask import Flask, request, jsonify, redirect

app = Flask(__name__)

# ========================
# НАСТРОЙКИ — заполни сам
# ========================
AMOCRM_SUBDOMAIN = os.environ.get("AMOCRM_SUBDOMAIN", "")        # например: mycompany
AMOCRM_CLIENT_ID = os.environ.get("AMOCRM_CLIENT_ID", "")
AMOCRM_CLIENT_SECRET = os.environ.get("AMOCRM_CLIENT_SECRET", "")
AMOCRM_REDIRECT_URI = os.environ.get("AMOCRM_REDIRECT_URI", "")  # твой railway url + /callback
AMOCRM_ACCESS_TOKEN = os.environ.get("AMOCRM_ACCESS_TOKEN", "")
AMOCRM_REFRESH_TOKEN = os.environ.get("AMOCRM_REFRESH_TOKEN", "")

# ========================
# OAuth — получение токена
# ========================
@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Нет кода авторизации", 400

    url = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru/oauth2/access_token"
    data = {
        "client_id": AMOCRM_CLIENT_ID,
        "client_secret": AMOCRM_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": AMOCRM_REDIRECT_URI,
    }
    resp = requests.post(url, json=data)
    tokens = resp.json()

    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")

    return f"""
    <h2>✅ Токены получены!</h2>
    <p><b>ACCESS_TOKEN:</b> {access_token}</p>
    <p><b>REFRESH_TOKEN:</b> {refresh_token}</p>
    <p>Скопируй их и добавь в переменные окружения Railway</p>
    """

# ========================
# Webhook от MedMIS
# ========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400

    print("📥 Входящий webhook:", data)

    # Извлекаем имя и телефон пациента
    # Поля могут отличаться — подправим после первого теста
    patient = data.get("patient", data)
    name = patient.get("fullName") or patient.get("name") or "Без имени"
    phone = patient.get("phone") or patient.get("phoneNumber") or ""

    result = create_amocrm_lead(name, phone)
    return jsonify(result)

# ========================
# Создание лида в amoCRM
# ========================
def create_amocrm_lead(name, phone):
    url = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru/api/v4/leads/complex"
    headers = {
        "Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = [
        {
            "name": f"Запись: {name}",
            "contacts": [
                {
                    "first_name": name,
                    "custom_fields_values": [
                        {
                            "field_code": "PHONE",
                            "values": [{"value": phone, "enum_code": "MOB"}],
                        }
                    ],
                }
            ],
        }
    ]
    resp = requests.post(url, json=payload, headers=headers)
    print("📤 amoCRM ответ:", resp.status_code, resp.text)
    return {"status": resp.status_code, "response": resp.json()}

# ========================
# Проверка что сервер живой
# ========================
@app.route("/")
def index():
    return "✅ Сервер работает!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
