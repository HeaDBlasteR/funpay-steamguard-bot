import logging
import time
import threading

from FunPayAPI import Account, Runner

from .config import (
    GOLDEN_KEY,
    GOLDEN_SEAL,
    RESTART_DELAY_SECONDS,
    EVENT_HANDLER_MAX_WORKERS,
    validate_config,
)

from .handlers import handle_event
from .notifier import notify_crash
from .raiser import raise_lots_loop
from .restock import restock_lots_loop
from .session import enable_golden_seal_auto_refresh

logger = logging.getLogger(__name__)

_event_handler_semaphore = threading.Semaphore(EVENT_HANDLER_MAX_WORKERS)


def create_account() -> Account:
    acc = Account(GOLDEN_KEY, GOLDEN_SEAL, requests_timeout=20)
    enable_golden_seal_auto_refresh(acc)
    return acc.get()


def _handle_event_safely(acc: Account, event) -> None:
    try:
        handle_event(acc, event)
    except Exception:
        logger.exception("Ошибка обработки события")
    finally:
        _event_handler_semaphore.release()


def main() -> None:
    validate_config()
    logger.info("Запуск FunPay Steam Guard бота...")

    acc = create_account()
    logger.info(
        "Авторизован как: %s (id=%s)",
        acc.username,
        acc.id,
    )

    threading.Thread(
        target=raise_lots_loop,
        args=(acc,),
        daemon=True,
    ).start()

    threading.Thread(
        target=restock_lots_loop,
        args=(acc,),
        daemon=True,
    ).start()

    while True:
        try:
            acc.runner = None

            runner = Runner(acc)
            logger.info("Раннер запущен, слушаем события...")
            for event in runner.listen(requests_delay=30):
                _event_handler_semaphore.acquire()
                threading.Thread(
                    target=_handle_event_safely,
                    args=(acc, event),
                    daemon=True,
                ).start()

        except KeyboardInterrupt:
            logger.info("Бот остановлен вручную.")
            break
        except Exception as e:
            logger.exception(
                "Программа завершилась с ошибкой. Перезапуск через %s секунд.",
                RESTART_DELAY_SECONDS,
            )
            notify_crash(e)
            time.sleep(RESTART_DELAY_SECONDS)
