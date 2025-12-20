"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Utilidad auxiliar para enviar correos electrónicos utilizando un 
               Webhook de Google Apps Script. Permite enviar correos simples y 
               con adjuntos (PDFs) codificados en Base64.
--------------------------------------------------------------------------------
"""
# usuarios/utils.py
import base64
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def enviar_correo_via_webhook(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str = "",
    attachment_bytes: bytes | None = None,
    filename: str | None = None,
    content_type: str = "application/pdf",
) -> bool:
    """
    Envía un correo usando el Webhook de Google Apps Script.
    Soporta adjuntos enviando Base64 + filename.
    """

    # Obtiene URL y secreto desde settings
    url = getattr(settings, "APPSCRIPT_WEBHOOK_URL", None)
    secret = getattr(settings, "APPSCRIPT_WEBHOOK_SECRET", None)

    if not url or not secret:
        logger.error("[WEBHOOK EMAIL] Falta APPSCRIPT_WEBHOOK_URL o APPSCRIPT_WEBHOOK_SECRET")
        return False

    # Prepara payload básico
    payload = {
        "secret": secret,
        "to": to_email,
        "subject": subject or "Sin asunto",
        "html_body": html_body or "",
        "text_body": text_body or " ",
    }

    # DEBUG: confirma si viene adjunto y cuánto pesa
    logger.warning(
        f"[WEBHOOK EMAIL] to={to_email} filename={filename} "
        f"has_attachment_bytes={attachment_bytes is not None} "
        f"bytes_len={(len(attachment_bytes) if attachment_bytes is not None else 'None')}"
    )

    # Adjuntar si viene archivo (aunque sea b"" lo detectamos)
    if attachment_bytes is not None and filename:
        if len(attachment_bytes) == 0:
            # PDF vacío → no adjuntamos (pero lo dejamos registrado)
            logger.error("[WEBHOOK EMAIL] PDF vacío (0 bytes). No se adjunta.")
        else:
            payload["filename"] = filename
            payload["content_type"] = content_type
            # Codifica a Base64 para envío HTTP
            payload["attachment"] = base64.b64encode(attachment_bytes).decode("utf-8")

            logger.warning(
                f"[WEBHOOK EMAIL] Adjuntando: {filename} "
                f"attachment_b64_len={len(payload['attachment'])}"
            )

    try:
        # Envía la petición POST al Webhook
        resp = requests.post(
            url,
            json=payload,   #  correcto
            timeout=30,     # un poco más por el tamaño del PDF
        )
        resp.raise_for_status()

        data = resp.json() if resp.content else {}
        if data.get("status") == "ok":
            return True

        logger.error(f"[WEBHOOK EMAIL] Respuesta no-ok: {data}")
        return False

    except Exception as e:
        logger.exception(f"[WEBHOOK EMAIL] Error llamando al webhook: {e}")
        return False