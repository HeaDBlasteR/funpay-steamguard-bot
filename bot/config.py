from dotenv import load_dotenv
import os

load_dotenv()

GOLDEN_KEY = os.getenv("GOLDEN_KEY")
GOLDEN_SEAL = os.getenv("GOLDEN_SEAL")

EMAIL_LOGIN = os.getenv("EMAIL_LOGIN")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

GUARD_MAFILE_PATH = os.getenv("GUARD_MAFILE_PATH")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_TIMEOUT = 10
TELEGRAM_POLL_TIMEOUT = 30
TELEGRAM_POLL_ERROR_DELAY = 5
TELEGRAM_CHAT_MAP_LIMIT = 500
TELEGRAM_LOTS_LIMIT = 40
TELEGRAM_MESSAGE_LIMIT = 3500
TELEGRAM_MUTED_SNIPPETS = (
    "выдан покупателю",
    "Буду рад вашему отзыву",
    "Новый заказ #",
    "Пароль:",
    "Password:",
)

STATS_FILE = "stats.json"
STATS_HISTORY_DAYS = 180
STATS_WEEK_DAYS = 7
STATS_MONTH_DAYS = 30

IMAP_SERVER = "imap.yandex.ru"
IMAP_PORT = 993
MAIL_TIMEOUT = 60

GUARD_CODE_ALPHABET = "23456789BCDFGHJKMNPQRTVWXY"
GUARD_CODE_LENGTH = 5
GUARD_CODE_INTERVAL = 30
GUARD_CODE_MIN_REMAINING = 5

CODE_MAX_AGE_SECONDS = 600
MAIL_SCAN_LIMIT = 3

TRIGGER_CMD = "!code"
HELP_CMD = "!help"

HELP_OFFERED_FILE = "help_offered.json"
HELP_COOLDOWN_SECONDS = 60
HELP_MESSAGE_DELAY = 1

CHAT_LANGUAGE_TITLE = "Язык собеседника"
NATIVE_LANGUAGE = "Русский"

HELP_GUIDE_URL = (
    "https://docs.google.com/document/d/"
    "1h_o2-8_-HMkCTcPtxdx8OGcFBDTg-uU8SVAgHvlPr-8/edit"
)

HELP_HINT_TEXT = (
    "👋 Напишите !help — пришлю ответы на частые вопросы "
    "и инструкцию по офлайн-активации."
)
HELP_HINT_TEXT_EN = (
    "👋 Send !help to get answers to common questions "
    "and the offline activation guide."
)

HELP_MESSAGES = (
    "📖 Как это работает\n"
    "Вы получаете логин и пароль от Steam-аккаунта с игрой, скачиваете её "
    "и играете в автономном режиме Steam. Код Steam Guard для входа "
    "выдаётся автоматически: после оплаты напишите !code.\n"
    "\n"
    "❓ Доступ навсегда?\n"
    "Да, игра остаётся у вас на этом ПК, пока вы соблюдаете инструкцию. "
    "Играть можно только в автономном режиме — за игру онлайн доступ "
    "аннулируется без возврата средств.\n"
    "\n"
    "❓ Можно играть на другом ПК?\n"
    "Нет, активация работает только на компьютере, с которого вы вошли "
    "в аккаунт.",
    "⚠️ До первого запуска игры: обновите драйвера видеокарты, "
    "перезагрузите ПК, отключите Zapret и другие обходы блокировок, "
    "отключите обновления Windows и Windows Defender.\n"
    "\n"
    "❗ После первого запуска нельзя: переустанавливать Windows, игру "
    "или Steam, менять комплектующие и BIOS, включать спящий режим, "
    "аварийно выключать ПК. Иначе активация слетит, а гарантия "
    "аннулируется.\n"
    "\n"
    f"📄 Полная инструкция (обязательно прочитать целиком): {HELP_GUIDE_URL}",
)
HELP_MESSAGES_EN = (
    "📖 How it works\n"
    "You receive the login and password of a Steam account with the game, "
    "download it and play in Steam offline mode. The Steam Guard code is "
    "sent automatically: after payment, send !code.\n"
    "\n"
    "❓ Is access permanent?\n"
    "Yes, the game stays with you on this PC as long as you follow the "
    "guide. Play only in offline mode — playing online voids access with "
    "no refund.\n"
    "\n"
    "❓ Can I play on another PC?\n"
    "No, the activation works only on the computer you logged in from.",
    "⚠️ Before the first launch: update your GPU drivers, reboot your PC, "
    "disable Zapret and other blocking bypass tools, disable Windows and "
    "Windows Defender updates.\n"
    "\n"
    "❗ After the first launch, do NOT: reinstall Windows, the game or "
    "Steam, change PC components or BIOS, use sleep mode, or let the PC "
    "shut down abruptly. Otherwise the activation breaks and the warranty "
    "is void.\n"
    "\n"
    f"📄 Full guide (read it completely): {HELP_GUIDE_URL}",
)

CONFIRM_REMINDER_FILE = "confirm_reminders.json"
CONFIRM_REMINDER_INTERVAL = 24 * 3600
CONFIRM_REMINDER_CHECK_INTERVAL = 3600
CONFIRM_REMINDER_SEND_DELAY = 10
CONFIRM_REMINDER_BLOCK_RETRY_DELAY = 60

CONFIRM_REMINDER_TEXT = (
    "Пожалуйста, не забудьте подтвердить заказ. Зайдите в раздел "
    "«Покупки», выберите его в списке и нажмите кнопку "
    "«Подтвердить выполнение заказа»."
)
CONFIRM_REMINDER_TEXT_EN = (
    "Please don't forget to confirm the order. Go to the «Purchases» "
    "section, select it in the list and press the button that confirms "
    "the order is completed."
)

RESTART_DELAY_SECONDS = 15

EVENT_HANDLER_MAX_WORKERS = 10

LOG_FILE = "bot.log"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5

MAX_CODE_REQUEST_ATTEMPTS = 10
CODE_REQUEST_DELAY = 10
CODE_REQUEST_COOLDOWN_SECONDS = 60

RAISE_CHECK_INTERVAL = 60
RAISE_RETRY_DELAY = 300
SESSION_REFRESH_INTERVAL = 30 * 60

RESTOCK_INTERVAL = 24 * 3600
RESTOCK_AMOUNT = 5
RESTOCK_DELAY_BETWEEN_LOTS = 5
RESTOCK_FETCH_RETRY_ATTEMPTS = 3
RESTOCK_FETCH_RETRY_DELAY = 5

PRICE_SAVE_DELAY = 1

UI_FONT_PATH = r"C:\Windows\Fonts\segoeui.ttf"
UI_FONT_BOLD_PATH = r"C:\Windows\Fonts\segoeuib.ttf"
EMOJI_FONT_PATH = r"C:\Windows\Fonts\seguiemj.ttf"
UI_FONT_SIZE = 12

REVIEW_REPLY_MIN_STARS = 5
REVIEW_REPLY_TEXT = (
    "🙏 Спасибо за доверие и отзыв!⭐️"
)


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
