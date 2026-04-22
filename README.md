# Telegram Bot

This workspace contains a simple Python Telegram bot scaffold.

## Setup

1. Create a virtual environment and activate it if not already active.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file from `.env.example`, add your Telegram bot token, and optionally add `TELEGRAM_CHAT_ID`.

4. Start the bot:
   ```bash
   python main.py
   ```

5. Register a chat for contest alerts by sending `/watch` to the bot from the chat where you want notifications.

## Environment variables

- `TELEGRAM_BOT_TOKEN` — your bot token from BotFather.
- `TELEGRAM_CHAT_ID` — optional chat ID or group ID to receive contest start alerts. If omitted, use `/watch` in the target chat after the bot starts.

## Files

- `main.py` — starter Telegram bot implementation
- `requirements.txt` — Python dependencies
- `.env.example` — example environment variables
- `.gitignore` — ignores virtualenv and Python artifacts
# Cf_Notifier_Bot
