import logging
from pathlib import Path

from dotenv import set_key
from FunPayAPI import Account

logger = logging.getLogger(__name__)

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _persist_golden_seal(value: str) -> None:
    try:
        set_key(str(ENV_PATH), "GOLDEN_SEAL", value)
    except Exception:
        logger.exception("Не удалось сохранить обновлённый GOLDEN_SEAL в .env")


def refresh_session(acc: Account) -> bool:
    try:
        acc.get(update_phpsessid=True)
        logger.info("Сессия аккаунта обновлена (PHPSESSID/csrf-token).")
        return True
    except Exception:
        logger.exception("Не удалось обновить сессию аккаунта.")
        return False


def enable_golden_seal_auto_refresh(acc: Account) -> None:
    original_method = acc.method

    def method_with_seal_refresh(*args, **kwargs):
        response = original_method(*args, **kwargs)
        new_seal = response.cookies.get("golden_seal")
        if new_seal and new_seal != acc.golden_seal:
            logger.info("Получен новый GOLDEN_SEAL от FunPay, обновляю...")
            acc.golden_seal = new_seal
            _persist_golden_seal(new_seal)
        return response

    acc.method = method_with_seal_refresh
