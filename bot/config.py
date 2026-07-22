from dotenv import load_dotenv
import os

load_dotenv()

GOLDEN_KEY = os.getenv("GOLDEN_KEY")
GOLDEN_SEAL = os.getenv("GOLDEN_SEAL")

EMAIL_LOGIN = os.getenv("EMAIL_LOGIN")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

IMAP_SERVER = "imap.yandex.ru"
IMAP_PORT = 993

CODE_MAX_AGE_SECONDS = 600

TRIGGER_CMD = "!code"

RESTART_DELAY_SECONDS = 15

MAX_CODE_REQUEST_ATTEMPTS = 5
CODE_REQUEST_DELAY = 10

RAISE_CHECK_INTERVAL = 60
RAISE_DEFAULT_DELAY = 4 * 3600
RAISE_RETRY_DELAY = 300


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