import logging
import re

from bs4 import BeautifulSoup

from FunPayAPI import Account, types
from FunPayAPI.types import LotShortcut

logger = logging.getLogger(__name__)

LOT_TEXT_FIELDS = {
    "title_ru": "fields[summary][ru]",
    "title_en": "fields[summary][en]",
    "description_ru": "fields[desc][ru]",
    "description_en": "fields[desc][en]",
    "payment_msg_ru": "fields[payment_msg][ru]",
    "payment_msg_en": "fields[payment_msg][en]",
}

ENGLISH_LOT_FIELDS = ("title_en", "description_en", "payment_msg_en")

LOT_FIELD_LABELS = {
    "title_ru": "Название (RU)",
    "title_en": "Название (EN)",
    "description_ru": "Описание (RU)",
    "description_en": "Описание (EN)",
    "payment_msg_ru": "Сообщение после оплаты (RU)",
    "payment_msg_en": "Сообщение после оплаты (EN)",
}

RUSSIAN_LETTERS_RE = re.compile(r"[а-яёА-ЯЁ]")


def fetch_lot_fields(acc: Account, lot: LotShortcut) -> types.LotFields:
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


def strip_broken_surrogates(value: str) -> str:
    return "".join(
        char for char in value if not 0xD800 <= ord(char) <= 0xDFFF
    )


def read_lot_values(fields: types.LotFields) -> dict[str, str]:
    raw = fields.fields

    return {
        name: raw.get(key) or ""
        for name, key in LOT_TEXT_FIELDS.items()
    }


def find_russian_in_english(values: dict[str, str]) -> list[str]:
    return [
        name
        for name in ENGLISH_LOT_FIELDS
        if RUSSIAN_LETTERS_RE.search(values.get(name) or "")
    ]


def apply_lot_values(
    fields: types.LotFields,
    values: dict[str, str],
    price: float,
    amount: int | None,
    active: bool,
) -> types.LotFields:
    clean = {
        name: strip_broken_surrogates(value) for name, value in values.items()
    }

    fields.title_ru = clean["title_ru"]
    fields.title_en = clean["title_en"]
    fields.description_ru = clean["description_ru"]
    fields.description_en = clean["description_en"]
    fields.edit_fields({
        LOT_TEXT_FIELDS["payment_msg_ru"]: clean["payment_msg_ru"],
        LOT_TEXT_FIELDS["payment_msg_en"]: clean["payment_msg_en"],
    })
    fields.price = price
    fields.amount = amount
    fields.active = active

    return fields


def save_lot_values(
    acc: Account,
    lot: LotShortcut,
    values: dict[str, str],
    price: float,
    amount: int | None,
    active: bool,
) -> None:
    fields = fetch_lot_fields(acc, lot)
    apply_lot_values(fields, values, price, amount, active)
    acc.save_lot(fields)

    logger.info("Лот id=%s сохранён.", lot.id)
