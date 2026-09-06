import logging
import time

from FunPayAPI import Account

from .config import PRICE_SAVE_DELAY
from .lots import find_russian_in_english
from .pricing import parse_amount, parse_price, set_lot_price

logger = logging.getLogger(__name__)

EMPTY_TITLE = "empty_title"
RUSSIAN_IN_ENGLISH = "russian_in_english"
BAD_PRICE = "bad_price"
BAD_AMOUNT = "bad_amount"


def title_column_width(
    available: int, columns_width: int, padding: int, minimum: int
) -> int:
    return max(available - columns_width - padding, minimum)


def matches_filter(title: str, needle: str) -> bool:
    return needle.strip().lower() in title.lower()


def format_counter(shown: int, total: int) -> str:
    if shown == total:
        return f"Лотов: {total}"

    return f"Найдено: {shown} из {total}"


def collect_price_changes(entries):
    changes = []
    invalid = []

    for key, current, original in entries:
        value = current.strip()

        if value == original:
            continue

        try:
            price = parse_price(value)
        except ValueError:
            invalid.append(key)
            continue

        changes.append((key, price))

    return changes, invalid


def apply_price_changes(
    acc: Account, changes, on_progress=None, sleep=time.sleep
):
    saved = []
    failed = []
    total = len(changes)

    for index, (key, lot, price) in enumerate(changes, start=1):
        if on_progress is not None:
            on_progress(index, total)

        try:
            set_lot_price(acc, lot, price)
        except Exception as error:
            logger.error("Лот %s: не удалось изменить цену: %s", lot.id, error)
            failed.append((lot, error))
        else:
            saved.append((key, price))

        if index < total:
            sleep(PRICE_SAVE_DELAY)

    return saved, failed


def validate_lot_form(
    values: dict[str, str], price_text: str, amount_text: str
):
    if not values["title_ru"].strip():
        return None, None, (EMPTY_TITLE, [])

    russian = find_russian_in_english(values)

    if russian:
        return None, None, (RUSSIAN_IN_ENGLISH, russian)

    try:
        price = parse_price(price_text)
    except ValueError:
        return None, None, (BAD_PRICE, [])

    try:
        amount = parse_amount(amount_text)
    except ValueError:
        return None, None, (BAD_AMOUNT, [])

    return price, amount, None


def should_scroll_inner(first: float, last: float, delta: int) -> bool:
    if delta > 0:
        return first > 0.0

    return last < 1.0
