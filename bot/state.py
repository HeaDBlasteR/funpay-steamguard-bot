import json
import logging
import threading

from datetime import date, timedelta
from pathlib import Path

from .config import HELP_OFFERED_FILE, STATS_FILE, STATS_HISTORY_DAYS

logger = logging.getLogger(__name__)

STATS_KEYS = ("orders", "messages", "codes", "denied")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_lock = threading.Lock()
_paused = False
_history: dict[str, dict[str, int]] | None = None
_help_offered: set[str] | None = None


def is_paused() -> bool:
    with _lock:
        return _paused


def set_paused(value: bool) -> None:
    global _paused

    with _lock:
        _paused = value


def _stats_path() -> Path:
    return DATA_DIR / STATS_FILE


def _read_history() -> dict[str, dict[str, int]]:
    path = _stats_path()

    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Не удалось прочитать статистику из %s.", path)
        return {}

    if not isinstance(raw, dict):
        return {}

    return {
        day: {key: int(counters.get(key, 0)) for key in STATS_KEYS}
        for day, counters in raw.items()
        if isinstance(day, str) and isinstance(counters, dict)
    }


def _write_history(history: dict[str, dict[str, int]]) -> None:
    path = _stats_path()

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(history, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except Exception:
        logger.exception("Не удалось сохранить статистику в %s.", path)


def _loaded_history() -> dict[str, dict[str, int]]:
    global _history

    if _history is None:
        _history = _read_history()

    return _history


def _prune(history: dict[str, dict[str, int]]) -> None:
    oldest = (date.today() - timedelta(days=STATS_HISTORY_DAYS)).isoformat()

    for day in [day for day in history if day < oldest]:
        del history[day]


def period_start(days: int) -> date:
    return date.today() - timedelta(days=days - 1)


def record(key: str) -> None:
    with _lock:
        history = _loaded_history()
        counters = history.setdefault(
            date.today().isoformat(),
            dict.fromkeys(STATS_KEYS, 0),
        )
        counters[key] = counters.get(key, 0) + 1

        _prune(history)
        _write_history(history)


def snapshot(days: int = 1) -> dict[str, int]:
    with _lock:
        history = _loaded_history()
        first = period_start(days).isoformat()
        last = date.today().isoformat()

        totals = dict.fromkeys(STATS_KEYS, 0)

        for day, counters in history.items():
            if first <= day <= last:
                for key in STATS_KEYS:
                    totals[key] += counters.get(key, 0)

        return totals


def stats_day() -> date:
    return date.today()


def _help_offered_path() -> Path:
    return DATA_DIR / HELP_OFFERED_FILE


def _read_help_offered() -> set[str]:
    path = _help_offered_path()

    if not path.exists():
        return set()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Не удалось прочитать список чатов из %s.", path)
        return set()

    if not isinstance(raw, list):
        return set()

    return {str(chat_id) for chat_id in raw}


def _write_help_offered(chats: set[str]) -> None:
    path = _help_offered_path()

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(sorted(chats), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        logger.exception("Не удалось сохранить список чатов в %s.", path)


def mark_help_offered(chat_id: int | str) -> bool:
    global _help_offered

    with _lock:
        if _help_offered is None:
            _help_offered = _read_help_offered()

        key = str(chat_id)

        if key in _help_offered:
            return False

        _help_offered.add(key)
        _write_help_offered(_help_offered)
        return True
