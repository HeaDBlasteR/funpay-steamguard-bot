from FunPayAPI import enums

from .mail import get_steam_guard_code
from .config import (
    TRIGGER_CMD,
    MAX_CODE_REQUEST_ATTEMPTS,
    CODE_REQUEST_DELAY,
    EMAIL_LOGIN,
    EMAIL_PASSWORD,
    IMAP_SERVER,
    IMAP_PORT,
    MAIL_TIMEOUT,
)

import imaplib
import logging
import time

logger = logging.getLogger(__name__)


def _connect_mail() -> imaplib.IMAP4_SSL:
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=MAIL_TIMEOUT)
    mail.login(EMAIL_LOGIN, EMAIL_PASSWORD)
    return mail


def handle_event(acc, event) -> None:
    if event.type is not enums.EventTypes.NEW_MESSAGE:
        return

    msg = event.message

    if msg.author_id == acc.id:
        return

    if not msg.text:
        return

    text = msg.text.strip().lower()

    if text != TRIGGER_CMD:
        return

    chat_id = msg.chat_id
    buyer = msg.author

    logger.info(
        f"Команда !code от {buyer}"
        f" в чате {chat_id}. Проверяю почту..."
    )

    try:
        mail = _connect_mail()

    except Exception:
        logger.exception("Не удалось подключиться к почте.")

        try:
            acc.send_message(
                chat_id,
                "⚠️ Не удалось подключиться к почте для получения кода.",
            )
        except Exception:
            logger.exception("Ошибка отправки")

        return

    code = None

    try:
        for attempt in range(
            1,
            MAX_CODE_REQUEST_ATTEMPTS + 1,
        ):

            logger.info(
                f"Попытка {attempt}/{MAX_CODE_REQUEST_ATTEMPTS} "
                "получить Steam Guard код..."
            )

            try:
                code = get_steam_guard_code(mail)

            except (
                imaplib.IMAP4.abort,
                imaplib.IMAP4.error,
                OSError,
            ):

                logger.warning(
                    "IMAP-соединение оборвалось, переподключаюсь..."
                )

                try:
                    mail = _connect_mail()
                    code = get_steam_guard_code(mail)

                except Exception:
                    logger.exception(
                        "Не удалось переподключиться к почте."
                    )

            if code:
                break

            if attempt == 5:
                try:
                    acc.send_message(
                        chat_id,
                        "⏳ Письмо ещё не пришло, продолжаю проверять почту "
                        "(обычно доставка занимает до пары минут)...",
                    )
                except Exception:
                    logger.exception("Ошибка отправки")

            if attempt < MAX_CODE_REQUEST_ATTEMPTS:
                logger.info(
                    f"Код не найден. Ждем {CODE_REQUEST_DELAY} секунд..."
                )
                time.sleep(CODE_REQUEST_DELAY)

    finally:
        try:
            mail.logout()
        except Exception:
            pass

    if code:
        reply = (
            f"🔑 Steam Guard: {code}\n"
            "⭐Буду рад вашему отзыву <3"
        )
    else:
        reply = (
            "⚠️ Не удалось получить Steam Guard код за отведённое время. "
            "Попробуйте отправить !code ещё раз."
        )

    try:
        acc.send_message(chat_id, reply)

        logger.info(
            "Отправлено в чат %s: %s",
            chat_id,
            reply,
        )

    except Exception:
        logger.exception("Ошибка отправки")
