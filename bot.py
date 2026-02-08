import discord
from discord.ext import commands
import asyncio
import random
import json
import re
from datetime import datetime, timedelta, date
from config import TOKEN
import os
from flask import Flask
from threading import Thread

# ========== WEB SERVER FOR RENDER ==========
app = Flask('')

@app.route('/')
def home():
    return "🤖 Productivity Bot is running!"

def run():
    port = int(os.environ.get("PORT", 8080))  # Render provides PORT
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    server = Thread(target=run)
    server.start()

# ========== CONFIG ==========
CHALLENGE_CHANNEL_ID = 1469324380231172351   # 🔁 Replace with your challenge channel ID
REMINDER_CHANNEL_ID  = 1469738442135965757   # 🔁 Replace with your reminder channel ID
DATA_FILE = "data.json"

# ========== INTENTS & BOT ==========
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ========== STATE ==========
session_active = False
challenge_task = None

# ========== DATA HELPERS ==========
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"streak": 0, "last_day": ""}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ========== CHALLENGES ==========
challenges = [
    "🧠 Solve 1 DSA problem",
    "🧘 Meditate for 5 minutes",
    "📵 No phone for 10 minutes",
    "🚶 Walk for 2 minutes",
    "💧 Drink water"
]

# ========== EVENTS ==========
@bot.event
async def on_ready():
    print(f"🤖 Bot is online as {bot.user}")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    if reaction.emoji == "✅":
        data = load_data()
        today = str(date.today())

        if data.get("last_day") != today:
            data["streak"] = data.get("streak", 0) + 1
            data["last_day"] = today

        save_data(data)

        await reaction.message.channel.send(
            f"🔥 Nice job {user.name}! Streak: **{data['streak']}**"
        )

# ========== COMMANDS ==========
@bot.command()
async def start(ctx):
    global session_active, challenge_task

    if session_active:
        await ctx.send("⚠️ Session already running!")
        return

    session_active = True
    await ctx.send("🚀 Productivity mode ON! Challenges & reminders started.")

    challenge_task = bot.loop.create_task(challenge_loop())

@bot.command()
async def bye(ctx):
    global session_active, challenge_task

    if not session_active:
        await ctx.send("⚠️ No active session to stop.")
        return

    session_active = False

    if challenge_task:
        challenge_task.cancel()

    await ctx.send("🌙 Session stopped. See you tomorrow, champ 😎")

@bot.command()
async def challenge(ctx):
    challenge_text = random.choice(challenges)
    msg = await ctx.send(
        f"🔥 **Challenge Time!**\n{challenge_text}\n\nReact with ✅ when done!"
    )
    await msg.add_reaction("✅")

@bot.command()
async def remind(ctx, *, arg):
    """
    Usage: !remind <task> at <HH:MM>
    Example: !remind Revise DSA at 22:30
    """
    if not session_active:
        await ctx.send("⚠️ Start a session first using `!start`.")
        return

    pattern = r"(.+)\s+at\s+(\d{1,2}:\d{2})"
    match = re.match(pattern, arg)

    if not match:
        await ctx.send("❌ Format: `!remind <task> at <HH:MM>`\nExample: `!remind Revise trees at 22:30`")
        return

    task, time_str = match.groups()

    try:
        now = datetime.now()
        remind_time = datetime.strptime(time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )

        if remind_time <= now:
            remind_time += timedelta(days=1)

        delay = (remind_time - now).total_seconds()

    except ValueError:
        await ctx.send("❌ Time must be in HH:MM format (24-hour).")
        return

    reminder_channel = bot.get_channel(REMINDER_CHANNEL_ID)

    await ctx.send(f"⏰ Got it! I'll remind you to **{task}** at `{remind_time.strftime('%H:%M')}`")

    async def reminder_task():
        await asyncio.sleep(delay)
        if session_active:
            await reminder_channel.send(f"🔔 Reminder for {ctx.author.mention}: **{task}**")

    bot.loop.create_task(reminder_task())

# ========== BACKGROUND TASK ==========
async def challenge_loop():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHALLENGE_CHANNEL_ID)

    while session_active:
        wait_time = random.randint(3600, 7200)  # 1–2 hours
        await asyncio.sleep(wait_time)

        if not session_active:
            break

        challenge_text = random.choice(challenges)
        msg = await channel.send(
            f"⚡ **Random Challenge!**\n{challenge_text}\nReact with ✅ when done!"
        )
        await msg.add_reaction("✅")

# ========== RUN ==========
if __name__ == "__main__":
    keep_alive()  # Start the web server
    bot.run(TOKEN)
