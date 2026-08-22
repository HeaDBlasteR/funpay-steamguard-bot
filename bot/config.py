from dotenv import load_dotenv
import os

load_dotenv()

GOLDEN_KEY = os.getenv("GOLDEN_KEY")
GOLDEN_SEAL = os.getenv("GOLDEN_SEAL")

EMAIL_LOGIN = os.getenv("EMAIL_LOGIN")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_TIMEOUT = 10

IMAP_SERVER = "imap.yandex.ru"
IMAP_PORT = 993
MAIL_TIMEOUT = 60

CODE_MAX_AGE_SECONDS = 600
MAIL_SCAN_LIMIT = 3

TRIGGER_CMD = "!code"

RESTART_DELAY_SECONDS = 15

EVENT_HANDLER_MAX_WORKERS = 10

LOG_FILE = "bot.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5

MAX_CODE_REQUEST_ATTEMPTS = 10
CODE_REQUEST_DELAY = 10
CODE_REQUEST_COOLDOWN_SECONDS = 60

RAISE_CHECK_INTERVAL = 60
RAISE_DEFAULT_DELAY = 4 * 3600
RAISE_RETRY_DELAY = 300
SESSION_REFRESH_INTERVAL = 30 * 60

RESTOCK_INTERVAL = 24 * 3600
RESTOCK_AMOUNT = 5
RESTOCK_DELAY_BETWEEN_LOTS = 5
RESTOCK_FETCH_RETRY_ATTEMPTS = 3
RESTOCK_FETCH_RETRY_DELAY = 5


def validate_config() -> None:
    required = {
        "GOLDEN_KEY": GOLDEN_KEY,
        "GOLDEN_SEAL": GOLDEN_SEAL,
        "EMAIL_LOGIN": EMAIL_LOGIN,
        "EMAIL_PASSWORD": EMAIL_PASSWORD,
    }

    missing = [name for name, value in required.items() if not value]

    if missing:
        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
        )
