import base64
import hmac
import json
import logging
import struct
import time

from hashlib import sha1
from pathlib import Path

from .config import (
    GUARD_CODE_ALPHABET,
    GUARD_CODE_INTERVAL,
    GUARD_CODE_LENGTH,
    GUARD_CODE_MIN_REMAINING,
    GUARD_MAFILE_PATH,
)

logger = logging.getLogger(__name__)

MAFILE_GLOB = "*.maFile"
SHARED_SECRET_KEY = "shared_secret"

_cached_secret: str | None = None
_secret_loaded = False


def find_mafile(path: Path) -> Path | None:
    if path.is_dir():
        found = sorted(path.glob(MAFILE_GLOB))
        return found[0] if found else None

    return path if path.is_file() else None


def extract_secret(data) -> str | None:
    if not isinstance(data, dict):
        return None

    secret = data.get(SHARED_SECRET_KEY)

    if isinstance(secret, str) and secret:
        return secret

    for value in data.values():
        found = extract_secret(value)

        if found:
            return found

    return None


def load_shared_secret(path: str | None) -> str | None:
    if not path:
        return None

    mafile = find_mafile(Path(path))

    if mafile is None:
        logger.error("maFile не найден по пути %s.", path)
        return None

    try:
        data = json.loads(mafile.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Не удалось прочитать maFile %s.", mafile)
        return None

    secret = extract_secret(data)

    if not secret:
        logger.error(
            "В maFile %s нет поля %s.",
            mafile,
            SHARED_SECRET_KEY,
        )

    return secret


def get_shared_secret() -> str | None:
    global _cached_secret, _secret_loaded

    if not _secret_loaded:
        _cached_secret = load_shared_secret(GUARD_MAFILE_PATH)
        _secret_loaded = True

    return _cached_secret


def seconds_until_next_code(timestamp: float) -> float:
    return GUARD_CODE_INTERVAL - timestamp % GUARD_CODE_INTERVAL


def generate_code(secret: str, timestamp: float) -> str:
    key = base64.b64decode(secret)
    counter = int(timestamp // GUARD_CODE_INTERVAL)
    digest = hmac.new(key, struct.pack(">Q", counter), sha1).digest()
    offset = digest[-1] & 0x0F
    value = int.from_bytes(digest[offset:offset + 4], "big") & 0x7FFFFFFF

    code = ""

    for _ in range(GUARD_CODE_LENGTH):
        code += GUARD_CODE_ALPHABET[value % len(GUARD_CODE_ALPHABET)]
        value //= len(GUARD_CODE_ALPHABET)

    return code


def get_local_code() -> str | None:
    secret = get_shared_secret()

    if not secret:
        return None

    try:
        now = time.time()
        remaining = seconds_until_next_code(now)

        if remaining < GUARD_CODE_MIN_REMAINING:
            logger.info(
                "До смены кода %.1fс, жду следующее окно.",
                remaining,
            )
            time.sleep(remaining)
            now = time.time()

        code = generate_code(secret, now)
    except Exception:
        logger.exception("Не удалось сгенерировать Steam Guard код локально.")
        return None

    logger.info("Steam Guard код сгенерирован локально.")

    return code
