import threading

from datetime import date

STATS_KEYS = ("orders", "messages", "codes", "denied")

_lock = threading.Lock()
_paused = False
_stats_day = date.today()
_counters = dict.fromkeys(STATS_KEYS, 0)


def is_paused() -> bool:
    with _lock:
        return _paused


def set_paused(value: bool) -> None:
    global _paused

    with _lock:
        _paused = value


def _rollover(today: date) -> None:
    global _stats_day, _counters

    if today != _stats_day:
        _stats_day = today
        _counters = dict.fromkeys(STATS_KEYS, 0)


def record(key: str) -> None:
    with _lock:
        _rollover(date.today())
        _counters[key] += 1


def snapshot() -> dict:
    with _lock:
        _rollover(date.today())
        return dict(_counters)


def stats_day() -> date:
    with _lock:
        return _stats_day
