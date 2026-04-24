from __future__ import annotations

import requests

from backend.config import settings


def send_telegram(signal: dict) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    text = (
        f"Nivel {signal.get('level')} · {signal.get('ticker')}\n"
        f"Score: {signal.get('score_total')} | Calidad dato: {signal.get('data_quality')}\n"
        f"Precio: {signal.get('price')} | Stop: {signal.get('stop')} | Objetivo: {signal.get('target')}\n"
        f"Veredicto: {signal.get('verdict')}"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": settings.telegram_chat_id, "text": text},
            timeout=10,
        )
    except Exception:
        return
