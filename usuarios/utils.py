# usuarios/utils.py
import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def enviar_correo_via_webhook(to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """
    Envía un correo usando el Webhook de Google Apps Script.
    """
    url = getattr(settings, "APPSCRIPT_WEBHOOK_URL", None)
    secret = getattr(settings, "APPSCRIPT_WEBHOOK_SECRET", None)

    if not url or not secret:
        logger.error("[WEBHOOK EMAIL] Falta configuración de APPSCRIPT_WEBHOOK_URL o SECRET")
        return False

    payload = {
        "secret": secret,
        "to": to_email,
        "subject": subject,
        "html_body": html_body,
        "text_body": text_body or " "
    }

    try:
        resp = requests.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "ok":
            return True
        logger.error(f"[WEBHOOK EMAIL] Respuesta error: {data}")
    except Exception as e:
        logger.exception(f"[WEBHOOK EMAIL] Error llamando al webhook: {e}")

    return False
