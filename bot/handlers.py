from FunPayAPI import enums

from .mail import get_steam_guard_code
from .config import (
    TRIGGER_CMD,
    MAX_CODE_REQUEST_ATTEMPTS,
    CODE_REQUEST_DELAY,
    CODE_REQUEST_COOLDOWN_SECONDS,
    EMAIL_LOGIN,
    EMAIL_PASSWORD,
    IMAP_SERVER,
    IMAP_PORT,
    MAIL_TIMEOUT,
)

import imaplib
import logging
import threading
import time

logger = logging.getLogger(__name__)

_last_request_lock = threading.Lock()
_last_request_time: dict[int, float] = {}


def _connect_mail() -> imaplib.IMAP4_SSL:
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=MAIL_TIMEOUT)
    mail.login(EMAIL_LOGIN, EMAIL_PASSWORD)
    return mail


def _is_rate_limited(buyer_id: int) -> bool:
    now = time.time()

    with _last_request_lock:
        last = _last_request_time.get(buyer_id, 0)

        if now - last < CODE_REQUEST_COOLDOWN_SECONDS:
            return True

        _last_request_time[buyer_id] = now
        return False


def _buyer_has_valid_order(acc, buyer_username: str) -> bool:
    _, orders = acc.get_sells(
        buyer=buyer_username,
        include_paid=True,
        include_closed=True,
        include_refunded=False,
    )
    return bool(orders)


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
        f" в чате {chat_id}."
    )

    if _is_rate_limited(msg.author_id):
        logger.info(
            "Повторный запрос от %s раньше чем через %s секунд, игнорирую.",
            buyer,
            CODE_REQUEST_COOLDOWN_SECONDS,
        )

        try:
            acc.send_message(
                chat_id,
                "⏳ Код уже был запрошен недавно, подождите немного и попробуйте снова.",
            )
        except Exception:
            logger.exception("Ошибка отправки")

        return

    try:
        has_valid_order = _buyer_has_valid_order(acc, buyer)
    except Exception:
        logger.exception(
            "Не удалось проверить заказы покупателя %s.",
            buyer,
        )

        try:
            acc.send_message(
                chat_id,
                "⚠️ Не удалось проверить заказ. Попробуйте позже.",
            )
        except Exception:
            logger.exception("Ошибка отправки")

        return

    if not has_valid_order:
        logger.info(
            "У %s нет оплаченного или закрытого заказа, код не выдан.",
            buyer,
        )

        try:
            acc.send_message(
                chat_id,
                "❌ Код выдаётся только по оплаченному или закрытому заказу.",
            )
        except Exception:
            logger.exception("Ошибка отправки")

        return

    logger.info("Проверяю почту...")

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
