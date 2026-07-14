import email
import imaplib
import logging
import re

from datetime import datetime, timezone
from email.message import Message
from email.utils import parsedate_to_datetime

from .config import (
    EMAIL_LOGIN,
    EMAIL_PASSWORD,
    IMAP_SERVER,
    IMAP_PORT,
    CODE_MAX_AGE_SECONDS,
)

logger = logging.getLogger(__name__)

STEAM_CODE_PATTERNS = (
    r">\s*([A-Z0-9]{5})\s*<",
    r"[Gg]uard[^A-Z0-9]{1,30}([A-Z0-9]{5})",
    r"[Cc]ode[^A-Z0-9]{1,10}([A-Z0-9]{5})",
    r"[Кк]од[^A-Z0-9А-Яа-я]{1,10}([A-Z0-9]{5})",
    r"(?:^|\n)\s*([A-Z0-9]{5})\s*(?:\n|$)",
)


def extract_body(message: Message) -> str:
    """Возвращает текст письма."""

    body = ""

    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() not in (
                "text/plain",
                "text/html",
            ):
                continue

            charset = part.get_content_charset() or "utf-8"

            body += part.get_payload(
                decode=True,
            ).decode(
                charset,
                errors="replace",
            )
    else:
        charset = message.get_content_charset() or "utf-8"

        body = message.get_payload(
            decode=True,
        ).decode(
            charset,
            errors="replace",
        )

    return body


def extract_code(text: str) -> str | None:
    """Извлекает Steam Guard код из текста."""

    for pattern in STEAM_CODE_PATTERNS:
        match = re.search(pattern, text, re.MULTILINE)

        if match:
            code = match.group(1)

            logger.info(
                "Steam Guard код найден: %s",
                code,
            )

            return code

    return None


def is_fresh(message: Message) -> bool:
    """Проверяет, что письмо достаточно свежее."""

    date_header = message.get("Дата")

    if not date_header:
        logger.warning("В сообщении отсутствует заголовок "Дата".")
        return False

    try:
        message_date = parsedate_to_datetime(date_header)

        if message_date.tzinfo is None:
            message_date = message_date.replace(
                tzinfo=timezone.utc,
            )

        age = (
            datetime.now(timezone.utc) - message_date
        ).total_seconds()

        logger.info("Возраст сообщения: %.0f секунд", age)

        return age <= CODE_MAX_AGE_SECONDS

    except Exception:
        logger.exception("Не удалось обработать дату сообщения.")
        return False


def fetch_message(
    mail: imaplib.IMAP4_SSL,
    message_id: bytes,
) -> Message:
    """Получает письмо по его ID."""

    _, data = mail.fetch(message_id, "(RFC822)")

    raw = data[0][1]

    return email.message_from_bytes(raw)


def get_steam_guard_code() -> str | None:
    """
    Возвращает последний актуальный Steam Guard код.
    """

    mail = None

    try:
        mail = imaplib.IMAP4_SSL(
            IMAP_SERVER,
            IMAP_PORT,
        )

        mail.login(
            EMAIL_LOGIN,
            EMAIL_PASSWORD,
        )

        mail.select("INBOX")

        _, data = mail.search(
            None,
            'FROM "noreply@steampowered.com"',
        )

        message_ids = data[0].split()

        if not message_ids:
            logger.warning(
                "Адреса электронной почты Steam не найдены."
            )
            return None

        for message_id in reversed(message_ids):
            message = fetch_message(
                mail,
                message_id,
            )

            if not is_fresh(message):
                break

            body = extract_body(message)

            code = extract_code(body)

            if code:
                return code

            logger.warning(
                "Код Steam не найден в сообщении %s.",
                message_id.decode(),
            )

        logger.warning(
            "Новые коды Steam Guard не найдены."
        )

        return None

    except imaplib.IMAP4.error:
        logger.exception("IMAP error.")
        return None

    except Exception:
        logger.exception("Не удалось прочитать почту.")
        return None

    finally:
        if mail is not None:
            try:
                mail.logout()
            except Exception:
                pass