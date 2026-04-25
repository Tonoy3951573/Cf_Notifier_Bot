import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ================== LOAD ENV ==================
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ================== CONFIG ==================
STATE_PATH = Path("bot_state.json")
CODEFORCES_API_URL = "https://codeforces.com/api/contest.list?gym=false"

CHECK_INTERVAL = 300  # 5 minutes
ALERTS = [3600, 900]  # 1 hour, 15 minutes

# ================== LOGGING ==================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ================== STORAGE ==================
def load_state():
    if not STATE_PATH.exists():
        return {}
    try:
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f)

def get_chat_id():
    state = load_state()
    return state.get("chat_id")

# ================== COMMANDS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot is running!\nUse /watch to receive Codeforces alerts."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Start bot\n"
        "/watch - Enable alerts\n"
        "/status - Check status\n"
        "/upcoming - Show upcoming contests"
    )

async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    state["chat_id"] = update.effective_chat.id
    save_state(state)

    await update.message.reply_text("✅ This chat will now receive alerts.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_chat_id()
    if not chat_id:
        await update.message.reply_text("❌ No chat registered. Use /watch")
    else:
        await update.message.reply_text(f"✅ Alerts active for chat: {chat_id}")

# ================== NEW FEATURE ==================
async def upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contests = fetch_contests()

    if not contests:
        await update.message.reply_text("❌ Could not fetch contests.")
        return

    contests.sort(key=lambda x: x["startTimeSeconds"])

    msg = "📅 Upcoming Codeforces Contests:\n\n"

    for c in contests[:5]:
        name = c["name"]
        start = c["startTimeSeconds"]
        cid = c["id"]

        msg += (
            f"📌 {name}\n"
            f"⏰ {format_time(start)}\n"
            f"🔗 https://codeforces.com/contest/{cid}\n\n"
        )

    await update.message.reply_text(msg)

# ================== CORE LOGIC ==================
def fetch_contests():
    try:
        res = requests.get(CODEFORCES_API_URL, timeout=10).json()
        return [c for c in res["result"] if c["phase"] == "BEFORE"]
    except Exception as e:
        logger.warning("API error: %s", e)
        return []

def format_time(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

async def check_contests(context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_chat_id()
    if not chat_id or not isinstance(chat_id, int):
        return

    state = load_state()
    notified = set(state.get("sent", []))

    now = int(time.time())
    contests = fetch_contests()

    for c in contests:
        cid = c["id"]
        name = c["name"]
        start = c["startTimeSeconds"]

        diff = start - now

        for alert in ALERTS:
            key = f"{cid}_{alert}"

            if 0 < diff <= alert and key not in notified:
                msg = (
                    f"🚀 Upcoming Codeforces Contest!\n\n"
                    f"📌 {name}\n"
                    f"⏰ Start: {format_time(start)}\n"
                    f"🔗 https://codeforces.com/contest/{cid}\n\n"
                    f"⚡ Starts in {alert//60} minutes!"
                )

                try:
                    await context.bot.send_message(chat_id=chat_id, text=msg)
                    notified.add(key)
                    logger.info("Sent alert for %s", name)
                except Exception as e:
                    logger.warning("Send failed: %s", e)

    state["sent"] = list(notified)
    save_state(state)

# ================== MAIN ==================
def main():
    if not TOKEN:
        raise Exception("❌ TELEGRAM_BOT_TOKEN missing")

    app = Application.builder().token(TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("watch", watch))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("upcoming", upcoming))

    # scheduler
    app.job_queue.run_repeating(check_contests, interval=CHECK_INTERVAL, first=10)

    print("🚀 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()