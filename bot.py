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
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Import Configurations & Strings
from config import Config
from script import START_TXT, HELP_TXT, ABOUT_TXT
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

# --- HELPERS ---
def get_greeting():
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    hour = now.hour
    if 5 <= hour < 12: return "Good Morning 🌅"
    elif 12 <= hour < 17: return "Good Afternoon ☀️"
    elif 17 <= hour < 21: return "Good Evening 🌆"
    else: return "Good Night 🌙"

# --- HEALTH CHECK SERVER (For Koyeb Web Service) ---
async def handle_health(request):
    return web.Response(text="Bot is Alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

# --- BOT CLIENT ---
app = Client(
    "ZeroDownloader",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    parse_mode=enums.ParseMode.HTML
)

# --- COMMAND HANDLERS ---

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user_id = message.from_user.id
    await add_user(user_id, message.from_user.first_name, message.from_user.username)
    
    if not await is_subscribed(client, user_id):
        return await message.reply_text(
            "⚠️ **Access Denied!**\n\nPlease join our update channels to use this bot.",
            reply_markup=get_subscribe_buttons()
        )

    # Animated Sticker
    sticker = await message.reply_sticker("CAACAgIAAxkBAAEQZtFpgEdROhGouBVFD3e0K-YjmVHwsgACtCMAAphLKUjeub7NKlvk2TgE")
    await asyncio.sleep(2)
    await sticker.delete()

    # Welcome Image
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
    caption = f"<b>👤 USER INFO</b>\n\n<b>Name:</b> {user.first_name}\n<b>ID:</b> <code>{user.id}</code>\n<b>DC:</b> {user.dc_id}"
    
    if photos:
        await message.reply_photo(photos[0].file_id, caption=caption)
    else:
        await message.reply_text(caption)

@app.on_message(filters.regex(r'http') & filters.private)
async def auto_downloader(client, message):
    user_id = message.from_user.id
    user_data = await get_user(user_id)
    
    if user_data.get('plan') == 'free' and user_data.get('usage_count', 0) >= 5:
        return await message.reply_text("❌ **Limit Reached!** Contact @Venuboyy for Premium.")

    status = await message.reply_text("🔎 **Processing...**", quote=True)
    try:
        file_path = await download_media(message.text)
        await status.edit("📤 **Uploading...**")
        await message.reply_document(file_path)
        await update_usage(user_id)
        os.remove(file_path)
        await status.delete()
    except Exception as e:
        await status.edit(f"❌ **Error:** `{str(e)}`")

# --- CALLBACK HANDLER (Fixes the Buttons) ---

@app.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    if query.data == "help":
        await query.message.edit_text(
            text=HELP_TXT,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="start_back")]])
        )
    elif query.data == "about":
        await query.message.edit_text(
            text=ABOUT_TXT.format(client.me.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="start_back")]])
        )
    elif query.data == "start_back":
        await query.message.edit_text(
            text=START_TXT.format(query.from_user.first_name, get_greeting()),
            reply_markup=START_BTNS
        )
    elif query.data == "stats":
        count = await get_total_users()
        await query.answer(f"📊 Total Users: {count}", show_alert=True)
    elif query.data == "close":
        await query.message.delete()
    elif query.data == "check_sub":
        if await is_subscribed(client, query.from_user.id):
            await query.message.edit_text(
                text=START_TXT.format(query.from_user.first_name, get_greeting()),
                reply_markup=START_BTNS
            )
        else:
            await query.answer("❌ You are still not a member!", show_alert=True)

# --- ADMIN COMMANDS ---

@app.on_message(filters.command("broadcast") & filters.user(Config.ADMIN_ID))
async def broadcast_cmd(client, message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to a message to broadcast.")
    
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
    await message.reply_text(f"✅ Broadcast Done!\nSuccess: {success}\nFailed: {failed}")

@app.on_message(filters.command("restart") & filters.user(Config.ADMIN_ID))
async def restart_cmd(client, message):
    await message.reply_text("🔄 Restarting...")
    os.execl(sys.executable, sys.executable, *sys.argv)

# --- MAIN RUNNER ---
async def main():
    await start_web_server()
    await app.start()
    logger.info("Bot is active.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
