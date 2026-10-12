import logging
import time

from bs4 import BeautifulSoup
from FunPayAPI import Account
from FunPayAPI.common import exceptions
from FunPayAPI.types import OrderShortcut, OrderStatuses

from .config import (
    CONFIRM_REMINDER_BLOCK_RETRY_DELAY,
    CONFIRM_REMINDER_CHECK_INTERVAL,
    CONFIRM_REMINDER_INTERVAL,
    CONFIRM_REMINDER_SEND_DELAY,
    CONFIRM_REMINDER_TEXT,
    CONFIRM_REMINDER_TEXT_EN,
)
from .handlers import is_foreign_chat
from .state import confirm_reminder, keep_confirm_reminders, save_confirm_reminder

logger = logging.getLogger(__name__)


def _paid_orders(acc: Account) -> list[OrderShortcut]:
    orders = []
    start_from = None

    while True:
        start_from, page = acc.get_sells(
            start_from=start_from,
            include_paid=True,
            include_closed=False,
            include_refunded=False,
            state="paid",
        )
        orders.extend(page)

        if not start_from:
            return orders


def _order_chat_id(acc: Account, order_id: str) -> int | None:
    order = acc.get_order(order_id)

    if order.status is not OrderStatuses.PAID:
        return None

    parser = BeautifulSoup(order.html, "html.parser")
    chat = parser.find("div", {"class": "chat", "data-id": True})

    if chat is None:
        logger.warning("Заказ %s: не нашёл чат с покупателем.", order_id)
        return None

    return int(chat["data-id"])


def _remind(acc: Account, order: OrderShortcut, chat_id: int | None) -> bool:
    if chat_id is None:
        chat_id = _order_chat_id(acc, order.id)

        if chat_id is None:
            return False

    if is_foreign_chat(acc, chat_id):
        text = CONFIRM_REMINDER_TEXT_EN
    else:
        text = CONFIRM_REMINDER_TEXT

    acc.send_message(chat_id, text)
    save_confirm_reminder(order.id, chat_id, time.time())

    logger.info(
        "Заказ %s: напомнил %s подтвердить выполнение.",
        order.id,
        order.buyer_username,
    )
    return True


def remind_unconfirmed_orders(acc: Account) -> bool:
    orders = _paid_orders(acc)
    keep_confirm_reminders({order.id for order in orders})

    sent = 0
    attempted = 0
    failed_order = None

    for order in orders:
        record = confirm_reminder(order.id)

        if record:
            last_time = record["reminded_at"]
        else:
            last_time = order.date.timestamp()

        if time.time() - last_time < CONFIRM_REMINDER_INTERVAL:
            continue

        if attempted:
            time.sleep(CONFIRM_REMINDER_SEND_DELAY)

        attempted += 1

        try:
            delivered = _remind(
                acc,
                order,
                int(record["chat_id"]) if record else None,
            )
        except exceptions.MessageNotDeliveredError as error:
            logger.warning("Заказ %s: %s", order.id, error.short_str())
        except Exception:
            logger.exception(
                "Заказ %s: не удалось отправить напоминание.",
                order.id,
            )
        else:
            if delivered:
                sent += 1
                failed_order = None
            continue

        if failed_order is not None:
            logger.warning(
                "FunPay не даёт отправлять сообщения, остановился на "
                "заказе %s (%s). Повтор через %s секунд.",
                failed_order.id,
                failed_order.buyer_username,
                CONFIRM_REMINDER_BLOCK_RETRY_DELAY,
            )
            return True

        failed_order = order

    logger.info(
        "Неподтверждённых заказов: %s, напоминаний отправлено: %s.",
        len(orders),
        sent,
    )
    return False


def confirm_reminder_loop(acc: Account) -> None:
    while True:
        blocked = False

        try:
            blocked = remind_unconfirmed_orders(acc)
        except Exception:
            logger.exception("Ошибка при проверке неподтверждённых заказов.")

        if blocked:
            time.sleep(CONFIRM_REMINDER_BLOCK_RETRY_DELAY)
        else:
            time.sleep(CONFIRM_REMINDER_CHECK_INTERVAL)
