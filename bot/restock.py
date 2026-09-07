import logging
import time

import requests

from FunPayAPI import Account
from FunPayAPI.common import exceptions
from FunPayAPI.types import LotShortcut

from .config import (
    RESTOCK_INTERVAL,
    RESTOCK_AMOUNT,
    RESTOCK_DELAY_BETWEEN_LOTS,
    RESTOCK_FETCH_RETRY_ATTEMPTS,
    RESTOCK_FETCH_RETRY_DELAY,
)
from .lots import fetch_lot_fields
from .session import refresh_session

logger = logging.getLogger(__name__)


def _restock_lot(acc: Account, lot: LotShortcut) -> None:
    for attempt in range(1, RESTOCK_FETCH_RETRY_ATTEMPTS + 1):
        try:
            fields = fetch_lot_fields(acc, lot)

            if fields.amount is None:
                logger.info(
                    "Лот id=%s пропущен: у него нет параметра "
                    "'количество товара'.",
                    lot.id,
                )
                return

            fields.amount = RESTOCK_AMOUNT
            acc.save_lot(fields)

            logger.info(
                "Лот id=%s: количество товара выставлено на %s.",
                lot.id,
                RESTOCK_AMOUNT,
            )
            return
        except exceptions.UnauthorizedError:
            raise
        except (
            ValueError,
            requests.exceptions.RequestException,
            exceptions.RequestFailedError,
        ):
            if attempt == RESTOCK_FETCH_RETRY_ATTEMPTS:
                raise
            logger.warning(
                "Лот %s: попытка %s/%s не удалась, повтор через %sс...",
                lot.id,
                attempt,
                RESTOCK_FETCH_RETRY_ATTEMPTS,
                RESTOCK_FETCH_RETRY_DELAY,
            )
            time.sleep(RESTOCK_FETCH_RETRY_DELAY)


def restock_all_lots(acc: Account) -> None:
    try:
        user_obj = acc.get_user(acc.id)
        lots = user_obj.get_lots()

        logger.info(
            "Пополнение остатков: найдено %s лотов.",
            len(lots),
        )

        for lot in lots:
            try:
                _restock_lot(acc, lot)
            except exceptions.UnauthorizedError:
                logger.warning(
                    "Сессия просрочена при обновлении лота %s, "
                    "обновляю...",
                    lot.id,
                )
                if refresh_session(acc):
                    try:
                        _restock_lot(acc, lot)
                    except exceptions.RequestFailedError as e:
                        logger.error(
                            "Не удалось обновить лот %s после "
                            "переподключения: %s",
                            lot.id,
                            e.short_str(),
                        )
                    except Exception:
                        logger.exception(
                            "Не удалось обновить лот %s после "
                            "переподключения.",
                            lot.id,
                        )
            except exceptions.RequestFailedError as e:
                logger.error(
                    "Ошибка обновления количества товара лота %s: %s",
                    lot.id,
                    e.short_str(),
                )
            except Exception:
                logger.exception(
                    "Ошибка обновления количества товара лота %s.",
                    lot.id,
                )

            time.sleep(RESTOCK_DELAY_BETWEEN_LOTS)

    except exceptions.UnauthorizedError:
        logger.warning(
            "Сессия просрочена при получении списка лотов, обновляю..."
        )
        refresh_session(acc)
    except Exception:
        logger.exception("Ошибка получения списка лотов для пополнения.")


def restock_lots_loop(acc: Account) -> None:
    while True:
        restock_all_lots(acc)
        time.sleep(RESTOCK_INTERVAL)
