import asyncio
import logging
import os
import sys
import random
import pytz
from datetime import datetime
from aiohttp import web
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Local Imports
from config import Config
from database import add_user, get_user, update_usage, get_total_users, get_all_users
from utils import get_random_mix_id, is_subscribed, get_subscribe_buttons, START_BTNS
from downloader import download_media

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(Config.LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- STRINGS ---
START_TXT = """<b>ʜᴇʏ, {}! {}</b> 

ɪ'ᴍ ᴀɴ <b>ᴀʟʟ-ɪɴ-ᴏɴᴇ sᴏᴄɪᴀʟ ᴍᴇᴅɪᴀ ᴅᴏᴡɴʟᴏᴀᴅᴇʀ ʙᴏᴛ</b> 📥
ɪ ᴄᴀɴ ᴅᴏᴡɴʟᴏᴀᴅ ᴠɪᴅᴇᴏs, ʀᴇᴇʟs, ᴘᴏsᴛs & ᴀᴜᴅɪᴏ ғʀᴏᴍ ᴘᴏᴘᴜʟᴀʀ ᴘʟᴀᴛғᴏʀᴍs 🌐

ᴊᴜsᴛ sᴇɴᴅ ᴍᴇ ᴀ ʟɪɴᴋ — ᴀɴᴅ ɪ'ʟʟ ᴅᴏᴡɴʟᴏᴀᴅ ɪᴛ ғᴏʀ ʏᴏᴜ! 🚀"""

INFO_TXT = """<b>👤 USER INFO</b>
━━━━━━━━━━━━━━━━━━
<b>First Name:</b> {first}
<b>Last Name:</b> {last}
<b>Telegram ID:</b> <code>{id}</code>
<b>DC ID:</b> {dc}
<b>Username:</b> @{user}
<b>Profile Link:</b> <a href='tg://user?id={id}'>Click Here</a>"""

# --- HELPERS ---
def get_greeting():
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    hour = now.hour
    if 5 <= hour < 12: return "Good Morning 🌅"
    elif 12 <= hour < 17: return "Good Afternoon ☀️"
    elif 17 <= hour < 21: return "Good Evening 🌆"
    else: return "Good Night 🌙"

# --- HEALTH CHECK SERVER (For Koyeb Port 8080) ---
async def handle_health(request):
    return web.Response(text="Bot is Alive and Running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    # Koyeb uses port 8080 by default
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Health Check Server started on port 8080")

# --- BOT CLIENT ---
app = Client(
    "ZeroDownloader",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    parse_mode=enums.ParseMode.HTML
)

# --- HANDLERS ---

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user_id = message.from_user.id
    await add_user(user_id, message.from_user.first_name, message.from_user.username)
    
    # Force Sub Check
    if not await is_subscribed(client, user_id):
        return await message.reply_text(
            "⚠️ **Access Denied!**\n\nPlease join our update channels to use this bot.",
            reply_markup=get_subscribe_buttons()
        )

    # Animated Sticker Logic
    sticker = await message.reply_sticker("CAACAgIAAxkBAAEQZtFpgEdROhGouBVFD3e0K-YjmVHwsgACtCMAAphLKUjeub7NKlvk2TgE")
    await asyncio.sleep(2)
    await sticker.delete()

    # Welcome Image Logic
    img_url = f"{random.choice(Config.PICS_URL)}?r={get_random_mix_id()}"
    await message.reply_photo(
        photo=img_url,
        caption=START_TXT.format(message.from_user.first_name, get_greeting()),
        reply_markup=START_BTNS
    )

@app.on_message(filters.command("info") & filters.private)
async def info_cmd(client, message):
    user = message.from_user
    photos = [p async for p in client.get_chat_photos(user.id, limit=1)]
    caption = INFO_TXT.format(
        first=user.first_name,
        last=user.last_name or "None",
        id=user.id,
        dc=user.dc_id or "N/A",
        user=user.username or "None"
    )
    if photos:
        await message.reply_photo(photos[0].file_id, caption=caption)
    else:
        await message.reply_text(caption)

@app.on_message(filters.regex(r'http') & filters.private)
async def auto_downloader(client, message):
    user_id = message.from_user.id
    user_data = await get_user(user_id)
    
    # Plan Check
    if user_data.get('plan') == 'free' and user_data.get('usage_count', 0) >= 5:
        return await message.reply_text("❌ **Limit Reached!**\nFree users are limited to 5 downloads. Contact @Venuboyy for Premium.")

    status = await message.reply_text("🔎 **Detecting Link...**", quote=True)
    try:
        # Note: downloader.py should handle the heavy lifting
        file_path = await download_media(message.text)
        await status.edit("📤 **Uploading to Telegram...**")
        await message.reply_document(file_path)
        await update_usage(user_id)
        os.remove(file_path)
        await status.delete()
    except Exception as e:
        await status.edit(f"❌ **Error:** `{str(e)}`")

# --- ADMIN COMMANDS ---

@app.on_message(filters.command("stats") & filters.user(Config.ADMIN_ID))
async def stats_cmd(client, message):
    count = await get_total_users()
    await message.reply_text(f"📊 **Current Bot Stats:**\nTotal Users: `{count}`")

@app.on_message(filters.command("logs") & filters.user(Config.ADMIN_ID))
async def logs_cmd(client, message):
    if os.path.exists(Config.LOG_FILE):
        await message.reply_document(Config.LOG_FILE)
    else:
        await message.reply_text("Log file not found.")

@app.on_message(filters.command("restart") & filters.user(Config.ADMIN_ID))
async def restart_cmd(client, message):
    await message.reply_text("🔄 **Restarting Bot...**")
    os.execl(sys.executable, sys.executable, *sys.argv)

@app.on_message(filters.command("broadcast") & filters.user(Config.ADMIN_ID))
async def broadcast_cmd(client, message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to a message to broadcast.")
    
    msg = await message.reply_text("🚀 **Processing Broadcast...**")
    users = await get_all_users()
    success, failed = 0, 0
    
    async for user in users:
        try:
            await message.reply_to_message.copy(user['user_id'])
            success += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await message.reply_to_message.copy(user['user_id'])
            success += 1
        except:
            failed += 1
    
    await msg.edit(f"✅ **Broadcast Done!**\n\nSuccess: `{success}`\nFailed: `{failed}`")

# --- MAIN EXECUTION ---
async def main():
    await start_web_server() # Port 8080 logic
    await app.start()
    logger.info("Bot is running...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
