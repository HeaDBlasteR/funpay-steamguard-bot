# FunPay Steam Guard Bot

A FunPay chat bot that delivers Steam Guard codes to buyers on demand, keeps lots bumped and restocked, and stays logged in without manual intervention.

## Features

- **On-demand code delivery** — buyer sends `!code` in chat, the bot scans the mailbox for the latest Steam Guard email and replies with the code
- **Resilient mail fetching** — retries across multiple attempts, auto-reconnects on dropped IMAP connections, filters by sender and message freshness, and parses both English and Russian code formats
- **Automatic lot bumping** — raises lots per category on a schedule, honoring FunPay's rate-limit wait times
- **Automatic restock** — periodically resets lot quantities so listings don't run dry
- **Automatic session refresh** — refreshes `PHPSESSID` on a timer and transparently picks up a rotated `golden_seal` from response cookies, persisting it back to `.env`
- **Parallel event handling** — each incoming chat event is processed in its own thread, so a slow mail lookup for one buyer doesn't block others
- **Auto-restart** — the runner loop restarts itself if it crashes
- **Structured logging**

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

Everything else (IMAP server, timing intervals, restock amount, retry limits, etc.) is configured via constants in `bot/config.py`.

## Run

```bash
python -m bot
```

or

```bash
python run.py
```

## License

MIT
