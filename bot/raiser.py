import logging
import time

from FunPayAPI import Account
from FunPayAPI.common import exceptions

from .config import (
    RAISE_CHECK_INTERVAL,
    RAISE_DEFAULT_DELAY,
    RAISE_RETRY_DELAY,
)

logger = logging.getLogger(__name__)


def raise_lots_loop(acc: Account) -> None:
    next_raise_time: dict[int, float] = {}

    while True:
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
                    next_raise_time[cat_id] = now + RAISE_DEFAULT_DELAY
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
        except Exception as e:
            logger.error(
                "Ошибка получения списка лотов: %s",
                e,
            )

        time.sleep(RAISE_CHECK_INTERVAL)