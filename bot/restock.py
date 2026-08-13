import logging
import time

from bs4 import BeautifulSoup

from FunPayAPI import Account, types
from FunPayAPI.common import exceptions
from FunPayAPI.types import LotShortcut

from .config import (
    RESTOCK_INTERVAL,
    RESTOCK_AMOUNT,
    RESTOCK_DELAY_BETWEEN_LOTS,
)

logger = logging.getLogger(__name__)

FETCH_RETRY_ATTEMPTS = 3
FETCH_RETRY_DELAY = 5


def _fetch_lot_fields(acc: Account, lot: LotShortcut) -> types.LotFields:
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/json",
        "x-requested-with": "XMLHttpRequest",
        "referer": lot.subcategory.private_link,
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    }
    response = acc.method(
        "get",
        f"lots/offerEdit?node={lot.subcategory.id}&offer={lot.id}",
        headers,
        {},
        raise_not_200=True,
    )

    try:
        json_response = response.json()
        html = json_response["html"]
    except ValueError:
        html = response.text

    bs = BeautifulSoup(html, "html.parser")
    form = bs.find("input", {"name": "csrf_token"})
    form = form.find_parent("form") if form else bs

    result = {"active": "", "deactivate_after_sale": ""}

    inputs = form.find_all("input")
    result.update({
        field["name"]: field.get("value") or ""
        for field in inputs
        if field.get("name")
        and field["name"] not in ["active", "deactivate_after_sale"]
    })

    textareas = form.find_all("textarea")
    result.update({
        field["name"]: field.text or ""
        for field in textareas
        if field.get("name")
    })

    selects = form.find_all("select")
    result.update({
        field["name"]: field.find("option", selected=True)["value"]
        for field in selects
        if field.get("name") and field.find("option", selected=True)
    })

    checkboxes = form.find_all(
        "input", {"type": "checkbox"}, checked=True,
    )
    result.update({
        field["name"]: "on"
        for field in checkboxes
        if field.get("name")
    })

    if result.get("amount") is None and result.get("price") is None:
        logger.error(
            "Лот %s: не удалось найти поля формы редактирования ни в "
            "JSON, ни в HTML (status=%s). Начало тела ответа: %r",
            lot.id,
            response.status_code,
            response.text[:500],
        )
        raise ValueError("lot edit form fields not found")

    return types.LotFields(lot.id, result)


def _restock_lot(acc: Account, lot: LotShortcut) -> None:
    fields = None

    for attempt in range(1, FETCH_RETRY_ATTEMPTS + 1):
        try:
            fields = _fetch_lot_fields(acc, lot)
            break
        except ValueError:
            if attempt == FETCH_RETRY_ATTEMPTS:
                raise
            logger.warning(
                "Лот %s: попытка %s/%s не удалась, повтор через %sс...",
                lot.id,
                attempt,
                FETCH_RETRY_ATTEMPTS,
                FETCH_RETRY_DELAY,
            )
            time.sleep(FETCH_RETRY_DELAY)

    if fields.amount is None:
        logger.info(
            "Лот id=%s пропущен: у него нет параметра 'количество товара'.",
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


def restock_lots_loop(acc: Account) -> None:
    while True:
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
                    try:
                        acc.get(update_phpsessid=True)
                        _restock_lot(acc, lot)
                    except Exception:
                        logger.exception(
                            "Не удалось обновить лот %s после "
                            "переподключения.",
                            lot.id,
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
            try:
                acc.get(update_phpsessid=True)
            except Exception:
                logger.exception("Не удалось обновить сессию аккаунта.")
        except Exception:
            logger.exception("Ошибка получения списка лотов для пополнения.")

        time.sleep(RESTOCK_INTERVAL)
