import requests
import config
import logging

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': config.TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    requests.post(url, data=payload)

def check_telegram_commands():
    """Devuelve el texto y el ID del último mensaje."""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/getUpdates?offset=-1"
    try:
        response = requests.get(url).json()
        if response["ok"] and response["result"]:
            last_update = response["result"][-1]
            # Sacamos el texto y el ID único del mensaje
            return last_update["message"]["text"], last_update["update_id"]
    except Exception:
        pass
    return None, None

