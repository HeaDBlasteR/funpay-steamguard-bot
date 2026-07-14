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

## Installation

pip install -r requirements.txt

## Configuration

Create a `.env` file, copy `.env.example` into it, and paste your data in there.

## Run

python -m bot

## License

MIT