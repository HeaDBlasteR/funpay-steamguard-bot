import logging

from FunPayAPI import Account
from FunPayAPI.types import LotShortcut

from .lots import fetch_lot_fields

logger = logging.getLogger(__name__)


def load_lots(acc: Account) -> list[LotShortcut]:
    return acc.get_user(acc.id).get_lots()


def parse_price(value: str) -> float:
    price = float(value.replace(",", ".").strip())

    if price <= 0:
        raise ValueError("price must be positive")

    return price


def parse_amount(value: str) -> int | None:
    value = value.strip()

    if not value:
        return None

    amount = int(value)

    if amount < 0:
        raise ValueError("amount must not be negative")

    return amount


def format_price(price: float | None) -> str:
    if price is None:
        return ""

    return f"{price:.2f}".rstrip("0").rstrip(".")


def set_lot_price(acc: Account, lot: LotShortcut, price: float) -> None:
    fields = fetch_lot_fields(acc, lot)
    fields.price = price
    acc.save_lot(fields)

    logger.info(
        "Лот id=%s: цена изменена на %s.",
        lot.id,
        price,
    )
