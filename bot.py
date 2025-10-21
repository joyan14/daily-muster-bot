import discord
from discord.ext import commands, tasks
import datetime
from zoneinfo import ZoneInfo
import json
import os
import sys

# ===== CONFIG =====
TOKEN = os.getenv("DISCORD_TOKEN")  # pulled from Render env var
GUILD_ID = 123456789012345678       # replace with your server ID
CHANNEL_ID = 123456789012345678     # replace with your #daily-muster channel ID
TZ = ZoneInfo("America/Los_Angeles")

POST_TIME   = (5, 0)    # 0500 PST - post muster
REPORT_TIME = (7, 30)   # 0730 PST - post summary
RESET_TIME  = (9, 0)    # 0900 PST - reset & TORIS message

STATE_FILE = "muster_state.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== Data Handling =====
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"mustered": [], "last_post": None, "last_post_date": None}

def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

state = load_state()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    scheduler.start()

# ===== Main Scheduler =====
@tasks.loop(minutes=1)
async def scheduler():
    now = datetime.datetime.now(TZ)
    hm = (now.hour, now.minute)

    if hm == POST_TIME:
        await post_muster()
    elif hm == REPORT_TIME:
        await post_report()
    elif hm == RESET_TIME:
        await reset_and_toris()

# ===== Post the Daily Muster (0500) =====
async def post_muster():
    channel = bot.get_channel(CHANNEL_ID)
    today = datetime.datetime.now(TZ).strftime("%d %b %Y")

    msg = await channel.send(
        f"⚓ **Daily Muster — {today}**\n"
        f"✅ React below to mark yourself present.\n"
        f"🕔 Muster window: **0500 PST today – 0730 PST tomorrow.**"
    )
    await msg.add_reaction("✅")

    state["mustered"] = []
    state["last_post"] = msg.id
    state["last_post_date"] = today
    save_state()

    print(f"[{today}] Muster posted @ 0500 PST")

# ===== Post the Daily Report (0730) =====
async def post_report():
    guild = bot.get_guild(GUILD_ID)
    channel = bot.get_channel(CHANNEL_ID)
    today = datetime.datetime.now(TZ).strftime("%d %b %Y")

    all_members = [m for m in guild.members if not m.bot]
    mustered_ids = set(state["mustered"])

    mustered = [m.name for m in all_members if m.id in mustered_ids]
    missing = [m.name for m in all_members if m.id not in mustered_ids]

    report = (
        f"📅 **Daily Muster Report — {today}**\n"
        f"✅ **Mustered:** {', '.join(mustered) if mustered else 'None'}\n"
        f"❌ **Not Mustered:** {', '.join(missing) if missing else 'All accounted for!'}"
    )
    await channel.send(report)
    print(f"[{today}] Report posted @ 0730 PST")

# ===== Reset & TORIS Message (0900) =====
async def reset_and_toris():
    channel = bot.get_channel(CHANNEL_ID)
    today = datetime.datetime.now(TZ).strftime("%d %b %Y")

    await channel.send(
        f"🕘 **{today} 0900 PST:** Late will be taking muster in TORIS the next day "
        f"or the next available days."
    )

    # Reset data
    state["mustered"] = []
    state["last_post"] = None
    save_state()

    print(f"
