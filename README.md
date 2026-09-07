# FunPay Steam Guard Bot

A FunPay toolkit: a chat bot that delivers Steam Guard codes to buyers on demand,
keeps lots bumped and restocked, stays logged in without manual intervention and
is driven from a Telegram chat, plus a desktop lot editor for changing prices and
listing texts in bulk.

## Bot features

- **On-demand code delivery** — buyer sends `!code` in chat and the bot replies with the code
- **Instant local codes** — the code is computed from a Steam `maFile` secret and answered in a second, with the mailbox as a fallback, see below
- **Order verification** — the code is only delivered to buyers with a paid or closed order; buyers with no order or a refunded one are turned away
- **Per-buyer cooldown** — repeat `!code` requests from the same buyer within 60 seconds are deduped instead of re-triggering a mail lookup
- **Resilient mail fetching** — retries across multiple attempts, auto-reconnects on dropped IMAP connections, filters by sender and message freshness, and parses both English and Russian code formats
- **Automatic review replies** — a canned thank-you is posted under every 5-star review left on your sales. Reviews *you* leave as a buyer are never touched (the same FunPay endpoint serves reviews and seller replies, so replying to your own review would overwrite it)
- **Automatic lot bumping** — raises lots per category, honoring the wait time FunPay reports per category instead of guessing a fixed interval
- **Automatic restock** — periodically resets lot quantities so listings don't run dry, retrying transient HTTP errors
- **Automatic session refresh** — refreshes `PHPSESSID` on a timer and transparently picks up a rotated `golden_seal` from response cookies, persisting it back to `.env`
- **Parallel event handling** — each incoming chat event is processed in its own thread (capped at 10 concurrent), so a slow mail lookup for one buyer doesn't block others
- **Auto-restart** — the runner loop restarts itself if it crashes, with an optional Telegram notification on each crash
- **Telegram control panel** — notifications and commands in your own chat, see below
- **Structured logging** — to console and to a rotating log file. Request bodies are never logged on API errors, since a lot's `payment_msg` contains the account credentials sent to buyers

## Steam Guard codes

Two sources, tried in this order:

1. **`maFile`** — if `GUARD_MAFILE_PATH` points at a `maFile` (or at the folder holding one), the bot reads `shared_secret` once at startup and computes the code itself: HMAC-SHA1 over the 30-second counter, mapped onto Steam's `23456789BCDFGHJKMNPQRTVWXY` alphabet. A code with less than 5 seconds of life left is held back until the next window, so a buyer never gets one that expires while they paste it.
2. **The mailbox** — with no secret configured, or if reading it fails, the bot polls IMAP for the latest Steam Guard email, exactly as before.

A `maFile` comes from binding the account's mobile authenticator with
[steamguard-cli](https://github.com/dyc3/steamguard-cli) (`steamguard setup`) or
Steam Desktop Authenticator; both write `shared_secret` into it. Note that
binding a mobile authenticator stops the emailed codes, so the mail path only
stays useful for accounts still on email Guard.

The file is a second factor in plain text: keep it out of the repo, `chmod 600`,
and back it up along with the revocation code — losing both leaves only Steam
support. Generated codes depend on a correct clock, so keep NTP running on the
host.

## Telegram panel

With `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` set, the bot polls Telegram in a
background thread and answers only in that one chat. Without them the thread
exits at startup and everything else runs unchanged.

Notifications: startup, new order, new buyer message, delivered code, crash.

Commands:

- `/stats` — orders, messages, delivered codes and refusals for the current day, plus paused/running status
- `/lots` — all lots with id, price and title
- `/price <id> <price>` — change one lot's price
- `/restock` — run a restock pass immediately instead of waiting for the timer
- `/pause` / `/resume` — stop and resume code delivery; while paused buyers are told to come back later

Replying to a "new buyer message" notification sends your text straight to that
FunPay chat. Pending updates from before a restart are dropped, so a queued
command never fires against a bot that has just come back up.

Counters live in memory only and reset at midnight and on restart.

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
- A Steam `maFile`, an IMAP-enabled mailbox receiving Steam Guard emails, or both
- Optional: a Telegram bot token and your chat id for the panel

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file (copy `.env.example`) with your credentials:

- `GOLDEN_KEY`, `GOLDEN_SEAL` — FunPay account cookies
- `EMAIL_LOGIN`, `EMAIL_PASSWORD` — mailbox credentials
- `GUARD_MAFILE_PATH` — optional, path to a `maFile` (or to the folder holding it) for local code generation
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — optional, enables the Telegram panel and crash notifications

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
crash and on reboot), automatic security updates, NTP time sync (needed both for
local code generation and for the mail freshness check in `bot/mail.py`), and a
firewall that only allows SSH in.

```bash
git clone <repo-url> /opt/funpay-steamguard-bot
cd /opt/funpay-steamguard-bot
sudo bash deploy/setup_server.sh

sudo -u funpaybot install -d -m 700 secrets   # for the maFile, if you use one
sudo -u funpaybot nano .env                   # fill in real credentials
sudo systemctl start funpay-bot
sudo systemctl status funpay-bot
sudo journalctl -u funpay-bot -f
```

The service is enabled at boot and set to `Restart=always`, so it survives both
an in-process crash and a server reboot. Run exactly one instance per FunPay
account: two runners fight over `golden_seal` rotation and answer buyers twice.
The lot editor is desktop-only and is not part of the server deployment.

## License

MIT
