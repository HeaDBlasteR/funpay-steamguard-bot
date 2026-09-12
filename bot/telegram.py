import logging
import threading
import time

import requests

from FunPayAPI import Account

from . import state
from .config import (
    STATS_MONTH_DAYS,
    STATS_WEEK_DAYS,
    TELEGRAM_API_TIMEOUT,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_CHAT_MAP_LIMIT,
    TELEGRAM_LOTS_LIMIT,
    TELEGRAM_MESSAGE_LIMIT,
    TELEGRAM_POLL_ERROR_DELAY,
    TELEGRAM_POLL_TIMEOUT,
)
from .pricing import format_price, load_lots, parse_price, set_lot_price
from .restock import restock_all_lots

logger = logging.getLogger(__name__)

API_URL = "https://api.telegram.org/bot{token}/{method}"

HELP_TEXT = (
    "/stats_day — статистика за сегодня\n"
    "/stats_week — статистика за неделю\n"
    "/stats_month — статистика за месяц\n"
    "/lots — список лотов с ценами\n"
    "/price <id> <цена> — сменить цену лота\n"
    "/restock — пополнить остатки прямо сейчас\n"
    "/pause — приостановить выдачу кодов\n"
    "/resume — возобновить выдачу кодов\n\n"
    "Ответ на уведомление о сообщении уходит покупателю в чат FunPay."
)

_chat_map: dict[int, int] = {}
_chat_map_lock = threading.Lock()


def is_enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def _call(method: str, payload: dict, timeout: int) -> dict | None:
    try:
        response = requests.post(
            API_URL.format(token=TELEGRAM_BOT_TOKEN, method=method),
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        logger.exception("Ошибка запроса %s к Telegram.", method)
        return None


def send(text: str) -> int | None:
    if not is_enabled():
        return None

    data = _call(
        "sendMessage",
        {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text[:TELEGRAM_MESSAGE_LIMIT],
        },
        TELEGRAM_API_TIMEOUT,
    )

    if not data or not data.get("ok"):
        logger.warning("Сообщение в Telegram не отправлено: %r", text)
        return None

    message_id = data["result"]["message_id"]

    logger.info(
        "В Telegram отправлено (message_id=%s): %s",
        message_id,
        text.replace("\n", " | "),
    )

    return message_id


def remember_chat(message_id: int | None, chat_id: int) -> None:
    if message_id is None:
        return

    with _chat_map_lock:
        _chat_map[message_id] = chat_id

        while len(_chat_map) > TELEGRAM_CHAT_MAP_LIMIT:
            _chat_map.pop(next(iter(_chat_map)))


def chat_for_message(message_id: int | None) -> int | None:
    if message_id is None:
        return None

    with _chat_map_lock:
        return _chat_map.get(message_id)


def notify_startup(acc: Account) -> None:
    send(f"🚀 Бот запущен: {acc.username} (id={acc.id})")


def notify_new_order(order) -> None:
    state.record("orders")
    send(
        f"🛒 Новый заказ #{order.id}\n"
        f"{order.description}\n"
        f"{format_price(order.price)} ₽ · покупатель {order.buyer_username}"
    )


def notify_buyer_message(msg) -> None:
    state.record("messages")
    remember_chat(send(f"💬 {msg.author}:\n{msg.text}"), msg.chat_id)


def notify_code_sent(buyer: str, code: str) -> None:
    state.record("codes")
    send(f"🔑 Код {code} выдан покупателю {buyer}.")


def _stats_header(days: int) -> str:
    if days <= 1:
        return f"📊 Статистика за {state.stats_day():%d.%m.%Y}"

    return (
        f"📊 Статистика за {days} дн. "
        f"({state.period_start(days):%d.%m} — {state.stats_day():%d.%m})"
    )


def _format_stats(days: int = 1) -> str:
    counters = state.snapshot(days)
    status = "на паузе" if state.is_paused() else "работает"

    return (
        f"{_stats_header(days)}\n"
        f"Заказы: {counters['orders']}\n"
        f"Сообщения: {counters['messages']}\n"
        f"Выдано кодов: {counters['codes']}\n"
        f"Отказов: {counters['denied']}\n"
        f"Статус: {status}"
    )


def _format_lots(acc: Account) -> str:
    lots = load_lots(acc)

    lines = [
        f"{lot.id} · {format_price(lot.price)} ₽ · {lot.title}"
        for lot in lots[:TELEGRAM_LOTS_LIMIT]
    ]

    if len(lots) > TELEGRAM_LOTS_LIMIT:
        lines.append(f"... и ещё {len(lots) - TELEGRAM_LOTS_LIMIT}")

    return "📦 Лотов: {}\n\n{}".format(len(lots), "\n".join(lines))


def _change_price(acc: Account, argument: str) -> str:
    parts = argument.split()

    if len(parts) != 2:
        return "Формат: /price <id лота> <цена>"

    lot_id, raw_price = parts

    try:
        price = parse_price(raw_price)
    except ValueError:
        return "Цена должна быть положительным числом."

    for lot in load_lots(acc):
        if str(lot.id) == lot_id:
            set_lot_price(acc, lot, price)
            return f"✅ Лот {lot_id}: цена изменена на {format_price(price)} ₽."

    return f"Лот {lot_id} не найден."


def _handle_command(acc: Account, text: str) -> str:
    command, _, argument = text.partition(" ")
    command = command.split("@")[0].lower()

    if command == "/stats_day":
        return _format_stats()

    if command == "/stats_week":
        return _format_stats(STATS_WEEK_DAYS)

    if command == "/stats_month":
        return _format_stats(STATS_MONTH_DAYS)

    if command == "/lots":
        return _format_lots(acc)

    if command == "/price":
        return _change_price(acc, argument)

    if command == "/restock":
        threading.Thread(
            target=restock_all_lots,
            args=(acc,),
            daemon=True,
        ).start()
        return "♻️ Пополнение остатков запущено."

    if command == "/pause":
        state.set_paused(True)
        return "⏸ Выдача кодов приостановлена."

    if command == "/resume":
        state.set_paused(False)
        return "▶️ Выдача кодов возобновлена."

    return HELP_TEXT


def _reply_to_buyer(acc: Account, chat_id: int, text: str) -> None:
    try:
        acc.send_message(chat_id, text)
        send("✅ Отправлено покупателю.")
        logger.info("Из Telegram отправлено в чат %s: %s", chat_id, text)
    except Exception:
        logger.exception("Не удалось отправить сообщение в чат %s.", chat_id)
        send("⚠️ Не удалось отправить сообщение покупателю.")


def handle_update(acc: Account, update: dict) -> None:
    message = update.get("message") or {}
    chat = message.get("chat") or {}

    if str(chat.get("id")) != str(TELEGRAM_CHAT_ID):
        return

    text = (message.get("text") or "").strip()

    if not text:
        return

    reply_to = message.get("reply_to_message") or {}
    chat_id = chat_for_message(reply_to.get("message_id"))

    if chat_id is not None and not text.startswith("/"):
        _reply_to_buyer(acc, chat_id, text)
        return

    try:
        send(_handle_command(acc, text))
    except Exception:
        logger.exception("Ошибка выполнения команды %r.", text)
        send("⚠️ Команда не выполнена, подробности в логах.")


def _skip_backlog() -> int | None:
    data = _call(
        "getUpdates",
        {"offset": -1, "timeout": 0},
        TELEGRAM_API_TIMEOUT,
    )

    if not data or not data.get("ok") or not data.get("result"):
        return None

    return data["result"][-1]["update_id"] + 1


def telegram_loop(acc: Account) -> None:
    if not is_enabled():
        logger.info(
            "Telegram-панель отключена: нет TELEGRAM_BOT_TOKEN "
            "или TELEGRAM_CHAT_ID."
        )
        return

    offset = _skip_backlog()
    notify_startup(acc)
    logger.info("Telegram-панель запущена.")

    while True:
        payload = {"timeout": TELEGRAM_POLL_TIMEOUT}

        if offset is not None:
            payload["offset"] = offset

        data = _call(
            "getUpdates",
            payload,
            TELEGRAM_POLL_TIMEOUT + TELEGRAM_API_TIMEOUT,
        )

        if not data or not data.get("ok"):
            time.sleep(TELEGRAM_POLL_ERROR_DELAY)
            continue

        for update in data["result"]:
            offset = update["update_id"] + 1

            try:
                handle_update(acc, update)
            except Exception:
                logger.exception("Ошибка обработки Telegram-обновления.")
