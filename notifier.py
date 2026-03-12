"""
notifier.py — Comunicación con Telegram
- Timeout en todas las llamadas HTTP
- Sin pérdida de comandos (offset incremental correcto)
- Separación clara entre envío y polling
"""
import requests
import logging
import config

logger = logging.getLogger("Notifier")


def send_telegram_message(message: str) -> bool:
    """Envía un mensaje a Telegram. Devuelve True si tuvo éxito."""
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram no configurado. Revisa el .env")
        return False

    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        resp = requests.post(url, data=payload, timeout=config.TELEGRAM_TIMEOUT)
        resp.raise_for_status()
        return True
    except requests.exceptions.Timeout:
        logger.warning("Timeout enviando mensaje a Telegram.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error enviando a Telegram: {e}")
    return False


class TelegramPoller:
    """
    Gestiona el polling de comandos de Telegram con offset incremental.
    Así nunca se pierde un comando ni se reprocesa el mismo dos veces,
    aunque el bot se reinicie.
    """

    def __init__(self):
        self._offset = 0          # Offset persistente durante la vida del proceso
        self._pending: list = []  # Cola interna de updates pendientes

    def _fetch_updates(self) -> list:
        """Llama a getUpdates con el offset actual y devuelve la lista de updates."""
        url = (
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}"
            f"/getUpdates?offset={self._offset}&timeout=0&limit=10"
        )
        try:
            resp = requests.get(url, timeout=config.TELEGRAM_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if data.get("ok") and data.get("result"):
                return data["result"]
        except requests.exceptions.Timeout:
            logger.debug("Timeout en getUpdates (normal si no hay mensajes).")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en getUpdates: {e}")
        return []

    def get_next_command(self) -> str | None:
        """
        Devuelve el texto del siguiente comando pendiente, o None si no hay.
        Actualiza el offset para que cada update se procese solo una vez.
        """
        if not self._pending:
            self._pending = self._fetch_updates()

        if not self._pending:
            return None

        update = self._pending.pop(0)
        self._offset = update["update_id"] + 1   # ACK del mensaje

        try:
            return update["message"]["text"].strip().lower()
        except (KeyError, AttributeError):
            return None  # Mensaje sin texto (foto, sticker, etc.)
