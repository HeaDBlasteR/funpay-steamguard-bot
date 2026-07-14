from FunPayAPI import enums

from .mail import get_steam_guard_code
from .config import (
    TRIGGER_CMD,
    MAX_CODE_REQUEST_ATTEMPTS,
    CODE_REQUEST_DELAY,
)

import logging
import time

logger = logging.getLogger(__name__)


def handle_event(acc, event) -> None:
    """Обрабатывает одно событие от раннера."""
    if event.type is not enums.EventTypes.NEW_MESSAGE:
        return

    msg = event.message

    if msg.author_id == acc.id:
        return

    if not msg.text:
        return

    text = msg.text.strip().lower()

    if text == TRIGGER_CMD:
        chat_id = msg.chat_id
        buyer = msg.author

        logger.info(
            f"Команда !code от {buyer}"
            f" в чате {chat_id}. Проверяю почту..."
        )

        code = None

        for attempt in range(1, MAX_CODE_REQUEST_ATTEMPTS + 1):
            logger.info(f"Попытка {attempt}/{MAX_CODE_REQUEST_ATTEMPTS} получить Steam Guard код...")

            code = get_steam_guard_code()
            if code:
                break

            if attempt < MAX_CODE_REQUEST_ATTEMPTS:
                logger.info(f"Код не найден. Ждем {CODE_REQUEST_DELAY} секунд...")
                time.sleep(CODE_REQUEST_DELAY)

        if code:
            reply = f"🔑 Steam Guard: {code}"
        else:
            reply = (
                "⚠️ Не удалось получить Steam Guard код. "
                "Письмо ещё не пришло — попробуйте позже."
            )

        try:
            acc.send_message(chat_id, reply)
            logger.info(f"Отправлено в чат {chat_id}: {reply}")
        except Exception:
            logger.exception("Ошибка отправки")