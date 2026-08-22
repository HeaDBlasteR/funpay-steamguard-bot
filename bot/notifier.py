import logging

import requests

from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_API_TIMEOUT

logger = logging.getLogger(__name__)


def notify_crash(error: BaseException) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    text = f"⚠️ FunPay Steam Guard бот упал с ошибкой:\n{error!r}"

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=TELEGRAM_API_TIMEOUT,
        )
    except Exception:
        logger.exception("Не удалось отправить уведомление в Telegram.")
