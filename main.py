import json
import logging
import os
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone, time as dtime
from pathlib import Path

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ================== LOAD ENV ==================
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ================== DUMMY SERVER ==================
def run_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running")

    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# ================== CONFIG ==================
STATE_PATH = Path("bot_state.json")
CODEFORCES_API_URL = "https://codeforces.com/api/contest.list?gym=false"

REMINDER_INTERVAL = 120  # 2 min
CHECK_INTERVAL = 60      # run every 1 min

# ================== LOGGING ==================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== STORAGE ==================
def load_state():
    if not STATE_PATH.exists():
        return {"chat_id": None, "active": {}, "confirmed": False}
    try:
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    except:
        return {"chat_id": None, "active": {}, "confirmed": False}

def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f)

def get_chat_id():
    return load_state().get("chat_id")

# ================== COMMANDS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot running!\nUse /watch")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/watch\n/status\n/upcoming\n/yes\n/no"
    )

async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    state["chat_id"] = update.effective_chat.id
    save_state(state)
    await update.message.reply_text("✅ Alerts enabled")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = get_chat_id()
    if cid:
        await update.message.reply_text(f"Active: {cid}")
    else:
        await update.message.reply_text("Use /watch")

async def yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    state["confirmed"] = True
    state["active"] = {}
    save_state(state)
    await update.message.reply_text("✅ OK, stopping reminders")

async def no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    state["confirmed"] = False
    state["active"] = {}
    save_state(state)
    await update.message.reply_text("❌ Cancelled")

# ================== UPCOMING ==================
async def upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contests = fetch_contests()
    contests.sort(key=lambda x: x["startTimeSeconds"])

    msg = "📅 Upcoming:\n\n"
    for c in contests[:5]:
        msg += f"{c['name']}\n{format_time(c['startTimeSeconds'])}\n\n"

    await update.message.reply_text(msg)

# ================== CORE ==================
def fetch_contests():
    try:
        res = requests.get(CODEFORCES_API_URL, timeout=10).json()
        return [c for c in res["result"] if c["phase"] == "BEFORE"]
    except:
        return []

def format_time(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

# ================== REMINDER LOGIC ==================
async def check_contests(context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_chat_id()
    if not chat_id:
        return

    state = load_state()
    now = int(time.time())
    contests = fetch_contests()

    for c in contests:
        cid = str(c["id"])
        name = c["name"]
        start = c["startTimeSeconds"]
        diff = start - now

        # 15 min window
        if 0 < diff <= 900:
            if state.get("confirmed"):
                continue

            data = state["active"].get(cid, {"last": 0})

            if now - data["last"] >= REMINDER_INTERVAL:
                msg = (
                    f"⚠️ {name}\n"
                    f"⏰ {format_time(start)}\n\n"
                    f"/yes or /no"
                )

                try:
                    await context.bot.send_message(chat_id, msg)
                except:
                    pass

                data["last"] = now
                state["active"][cid] = data

    save_state(state)

# ================== MORNING ==================
async def morning(context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_chat_id()
    if not chat_id:
        return

    contests = fetch_contests()
    contests.sort(key=lambda x: x["startTimeSeconds"])

    msg = "🌅 Good Morning\n\n"
    for c in contests[:3]:
        msg += f"{c['name']}\n{format_time(c['startTimeSeconds'])}\n\n"

    try:
        await context.bot.send_message(chat_id, msg)
    except:
        pass

# ================== MAIN ==================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("watch", watch))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("upcoming", upcoming))
    app.add_handler(CommandHandler("yes", yes))
    app.add_handler(CommandHandler("no", no))

    app.job_queue.run_repeating(check_contests, interval=CHECK_INTERVAL, first=10)
    app.job_queue.run_daily(morning, time=dtime(hour=8))

    print("🚀 Running...")
    app.run_polling()

if __name__ == "__main__":
    main()