# FunPay Steam Guard Bot

Automatically retrieves Steam Guard codes from an IMAP mailbox and sends them to buyers via FunPay chat.

## Features

- Steam Guard code extraction
- IMAP support
- Automatic retries
- Automatic runner restart
- Environment variables
- Logging

## Stack

- Python
- FunPayAPI
- IMAP
- Requests
- dotenv

## Requirements

- Python 3.11+
- FunPay account
- IMAP-enabled mailbox

## Project structure

bot/
    __init__.py
    __main__.py
    config.py
    handlers.py
    logger.py
    mail.py
    main.py

## Installation

pip install -r requirements.txt

## Configuration

Copy `.env.example` to `.env`.

## Run

python -m bot

## License

MIT