# FunPay Steam Guard Bot

A FunPay chat bot that delivers Steam Guard codes to buyers on demand, keeps lots bumped and restocked, and stays logged in without manual intervention.

## Features

- **On-demand code delivery** — buyer sends `!code` in chat, the bot scans the mailbox for the latest Steam Guard email and replies with the code
- **Order verification** — the code is only delivered to buyers with a paid or closed order; buyers with no order or a refunded one are turned away
- **Per-buyer cooldown** — repeat `!code` requests from the same buyer within 60 seconds are deduped instead of re-triggering a mail lookup
- **Resilient mail fetching** — retries across multiple attempts, auto-reconnects on dropped IMAP connections, filters by sender and message freshness, and parses both English and Russian code formats
- **Automatic lot bumping** — raises lots per category on a schedule, honoring FunPay's rate-limit wait times
- **Automatic restock** — periodically resets lot quantities so listings don't run dry
- **Automatic session refresh** — refreshes `PHPSESSID` on a timer and transparently picks up a rotated `golden_seal` from response cookies, persisting it back to `.env`
- **Parallel event handling** — each incoming chat event is processed in its own thread (capped at 10 concurrent), so a slow mail lookup for one buyer doesn't block others
- **Auto-restart** — the runner loop restarts itself if it crashes, with an optional Telegram notification on each crash
- **Structured logging** — to console and to a rotating log file

## Stack

- Python
- [FunPayAPI](https://github.com/woopertail/FunPayAPI)
- requests + BeautifulSoup4 (lot editing)
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

Everything else (IMAP server, timing intervals, restock amount, retry limits, etc.) is configured via constants in `bot/config.py`.

## Run

```bash
python -m bot
```

or

```bash
python run.py
```

## Deployment (dedicated Ubuntu/Debian server)

For a server running only this bot, `deploy/setup_server.sh` automates the
one-time setup: system packages, a dedicated non-root user, a virtualenv,
`.env` scaffolding, a hardened systemd service (auto-restart on crash and on
reboot), automatic security updates, NTP time sync (needed for the mail
freshness check in `bot/mail.py`), and a firewall that only allows SSH in.

```bash
git clone <repo-url> /opt/funpay-steamguard-bot
cd /opt/funpay-steamguard-bot
sudo bash deploy/setup_server.sh

sudo -u funpaybot nano .env   # fill in real credentials
sudo systemctl start funpay-bot
sudo systemctl status funpay-bot
sudo journalctl -u funpay-bot -f
```

The service is enabled at boot and set to `Restart=always`, so it survives
both an in-process crash and a server reboot.

## License

MIT
