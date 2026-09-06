# FunPay Steam Guard Bot

A FunPay toolkit: a chat bot that delivers Steam Guard codes to buyers on demand,
keeps lots bumped and restocked and stays logged in without manual intervention,
plus a desktop lot editor for changing prices and listing texts in bulk.

## Bot features

- **On-demand code delivery** — buyer sends `!code` in chat, the bot scans the mailbox for the latest Steam Guard email and replies with the code
- **Order verification** — the code is only delivered to buyers with a paid or closed order; buyers with no order or a refunded one are turned away
- **Per-buyer cooldown** — repeat `!code` requests from the same buyer within 60 seconds are deduped instead of re-triggering a mail lookup
- **Resilient mail fetching** — retries across multiple attempts, auto-reconnects on dropped IMAP connections, filters by sender and message freshness, and parses both English and Russian code formats
- **Automatic review replies** — a canned thank-you is posted under every 5-star review left on your sales. Reviews *you* leave as a buyer are never touched (the same FunPay endpoint serves reviews and seller replies, so replying to your own review would overwrite it)
- **Automatic lot bumping** — raises lots per category, honoring the wait time FunPay reports per category instead of guessing a fixed interval
- **Automatic restock** — periodically resets lot quantities so listings don't run dry, retrying transient HTTP errors
- **Automatic session refresh** — refreshes `PHPSESSID` on a timer and transparently picks up a rotated `golden_seal` from response cookies, persisting it back to `.env`
- **Parallel event handling** — each incoming chat event is processed in its own thread (capped at 10 concurrent), so a slow mail lookup for one buyer doesn't block others
- **Auto-restart** — the runner loop restarts itself if it crashes, with an optional Telegram notification on each crash
- **Structured logging** — to console and to a rotating log file. Request bodies are never logged on API errors, since a lot's `payment_msg` contains the account credentials sent to buyers

## Lot editor

A desktop app (`price_editor.py`) for the things that are slow to do on the site:

- All lots in one scrollable list with inline price editing — change several prices, then apply them in one go
- Full lot editing: titles, descriptions and post-payment messages (RU/EN), price, quantity, active flag
- **Cyrillic check** — saving is blocked if the English title, description or payment message contains Russian letters
- **Color emoji** in lot titles, rendered the way they look on FunPay (see below)
- Search box to filter the list by title

Lot fields are re-read immediately before saving, so an edit never clobbers a
quantity the restock loop changed in the meantime.

### About emoji

Tk renders emoji monochrome — it has no support for color font tables. Lot
titles in the list are therefore drawn to images with Pillow using the system
`Segoe UI Emoji` font, which reproduces the site's appearance. Editable text
fields cannot show images, so emoji inside the input boxes stay monochrome; a
color preview is shown under each title field instead. If Pillow or the fonts
are missing, the app falls back to plain text.

## Stack

- Python
- [FunPayAPI](https://github.com/woopertail/FunPayAPI)
- requests + BeautifulSoup4 (lot editing)
- Pillow (color emoji rendering)
- tkinter (desktop UI, ships with Python)
- python-dotenv

## Requirements

- Python 3.11+
- FunPay account
- IMAP-enabled mailbox receiving Steam Guard emails

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file (copy `.env.example`) with your credentials:

- `GOLDEN_KEY`, `GOLDEN_SEAL` — FunPay account cookies
- `EMAIL_LOGIN`, `EMAIL_PASSWORD` — mailbox credentials
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — optional, enables a Telegram notification whenever the runner crashes and restarts

Everything else (IMAP server, timing intervals, restock amount, retry limits,
review reply text, fonts) is configured via constants in `bot/config.py`.

## Run

The bot:

```bash
python -m bot
```

or

```bash
python run.py
```

The lot editor:

```bash
python price_editor.py
```

## Deployment (dedicated Ubuntu/Debian server)

For running the bot on a server instead of a desktop, `deploy/setup_server.sh`
automates the one-time setup: system packages, a dedicated non-root user, a
virtualenv, `.env` scaffolding, a hardened systemd service (auto-restart on
crash and on reboot), automatic security updates, NTP time sync (needed for the
mail freshness check in `bot/mail.py`), and a firewall that only allows SSH in.

```bash
git clone <repo-url> /opt/funpay-steamguard-bot
cd /opt/funpay-steamguard-bot
sudo bash deploy/setup_server.sh

sudo -u funpaybot nano .env   # fill in real credentials
sudo systemctl start funpay-bot
sudo systemctl status funpay-bot
sudo journalctl -u funpay-bot -f
```

The service is enabled at boot and set to `Restart=always`, so it survives both
an in-process crash and a server reboot. The lot editor is desktop-only and is
not part of the server deployment.

## License

MIT
