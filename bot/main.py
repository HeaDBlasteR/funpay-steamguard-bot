import logging
import time

from FunPayAPI import Account, Runner

from .config import (
    GOLDEN_KEY,
    GOLDEN_SEAL,
    RESTART_DELAY_SECONDS,
    validate_config,
)

from .handlers import handle_event

logger = logging.getLogger(__name__)


def create_account() -> Account:
    return Account(GOLDEN_KEY, GOLDEN_SEAL).get()


def main() -> None:
    validate_config()
    logger.info("Запуск FunPay Steam Guard бота...")

    acc = create_account()
    logger.info(
        "Авторизован как: %s (id=%s)",
        acc.username,
        acc.id,
    )

    while True:
        try:
            acc.runner = None

            runner = Runner(acc)
            logger.info("Раннер запущен, слушаем события...")
            for event in runner.listen(requests_delay=30):
                try:
                    handle_event(acc, event)
                except Exception:
                    logger.exception("Ошибка обработки события")

        except KeyboardInterrupt:
            logger.info("Бот остановлен вручную.")
            break
        except Exception:
            logger.exception(
                "Программа завершилась с ошибкой. Перезапуск через %s секунд.",
                RESTART_DELAY_SECONDS,
            )
            time.sleep(RESTART_DELAY_SECONDS)