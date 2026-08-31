import logging
import time

from FunPayAPI import Account
from FunPayAPI.common import exceptions

from .config import (
    RAISE_CHECK_INTERVAL,
    RAISE_RETRY_DELAY,
    SESSION_REFRESH_INTERVAL,
)
from .session import refresh_session

logger = logging.getLogger(__name__)


def raise_lots_loop(acc: Account) -> None:
    next_raise_time: dict[int, float] = {}
    last_session_refresh = time.time()

    while True:
        now = time.time()

        if now - last_session_refresh > SESSION_REFRESH_INTERVAL:
            if refresh_session(acc):
                last_session_refresh = now

        try:
            user_obj = acc.get_user(acc.id)
            categories = {}
            for lot in user_obj.get_lots():
                cat = lot.subcategory.category
                categories[cat.id] = cat

            now = time.time()
            for cat_id, category in categories.items():
                if next_raise_time.get(cat_id, 0) > now:
                    continue
                try:
                    acc.raise_lots(cat_id)
                    logger.info(
                        "Лоты категории '%s' подняты.",
                        category.name,
                    )
                    next_raise_time[cat_id] = now + RAISE_RETRY_DELAY
                except exceptions.UnauthorizedError:
                    logger.warning(
                        "Сессия протухла при поднятии '%s', обновляю...",
                        category.name,
                    )
                    if refresh_session(acc):
                        last_session_refresh = time.time()
                    next_raise_time[cat_id] = now + RAISE_RETRY_DELAY
                except exceptions.RaiseError as e:
                    if e.wait_time:
                        next_raise_time[cat_id] = now + e.wait_time
                        logger.info(
                            "'%s': подождать %sс.",
                            category.name,
                            e.wait_time,
                        )
                    else:
                        logger.warning(
                            "Не удалось поднять '%s': %s",
                            category.name,
                            e.short_str(),
                        )
                        next_raise_time[cat_id] = now + RAISE_RETRY_DELAY
                except Exception as e:
                    logger.error(
                        "Ошибка поднятия категории %s: %s",
                        cat_id,
                        e,
                    )
                    next_raise_time[cat_id] = now + RAISE_RETRY_DELAY
                time.sleep(2)
        except exceptions.UnauthorizedError:
            logger.warning(
                "Сессия протухла при получении списка лотов, обновляю..."
            )
            if refresh_session(acc):
                last_session_refresh = time.time()
        except Exception as e:
            logger.error(
                "Ошибка получения списка лотов: %s",
                e,
            )

        time.sleep(RAISE_CHECK_INTERVAL)
