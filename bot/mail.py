import email
import imaplib
import logging
import re

from datetime import datetime, timezone
from email.message import Message
from email.utils import parsedate_to_datetime, parseaddr

from .config import CODE_MAX_AGE_SECONDS, MAIL_SCAN_LIMIT

logger = logging.getLogger(__name__)

STEAM_CODE_PATTERNS = (
    r">\s*([A-Z0-9]{5})\s*<",
    r"(?i:guard)[^A-Z0-9]{1,30}([A-Z0-9]{5})",
    r"(?i:code)[^A-Z0-9]{1,10}([A-Z0-9]{5})",
    r"(?i:код)[^A-Z0-9А-Яа-я]{1,10}([A-Z0-9]{5})",
)


def extract_body(message: Message) -> str:
    body = ""

    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() not in (
                "text/plain",
                "text/html",
            ):
                continue

            try:
                charset = part.get_content_charset() or "utf-8"

                body += part.get_payload(
                    decode=True,
                ).decode(
                    charset,
                    errors="replace",
                )

            except Exception:
                pass

    else:
        try:
            charset = message.get_content_charset() or "utf-8"

            body = message.get_payload(
                decode=True,
            ).decode(
                charset,
                errors="replace",
            )

        except Exception:
            pass

    return body


def extract_code(text: str) -> str | None:
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
    date_header = message.get("Date")

    if not date_header:
        logger.warning('В сообщении отсутствует заголовок "Date".')
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
    _, data = mail.fetch(message_id, "(RFC822)")

    return email.message_from_bytes(data[0][1])


def get_steam_guard_code(
    mail: imaplib.IMAP4_SSL,
) -> str | None:
    status, _ = mail.select(
        "INBOX",
        readonly=True,
    )

    if status != "OK":
        logger.error("Не удалось открыть INBOX")
        return None

    status, data = mail.search(
        None,
        "ALL",
    )

    if status != "OK":
        logger.error("Не удалось получить список писем")
        return None

    message_ids = data[0].split()

    if not message_ids:
        logger.warning(
            "Адреса электронной почты Steam не найдены."
        )
        return None

    for message_id in reversed(message_ids[-MAIL_SCAN_LIMIT:]):

        message = fetch_message(
            mail,
            message_id,
        )

        sender = parseaddr(
            message.get("From")
        )[1].lower()

        if sender != "noreply@steampowered.com":
            continue

        if not is_fresh(message):
            continue

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
