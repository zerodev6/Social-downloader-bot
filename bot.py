import asyncio
import os
import sys
import random
from aiohttp import web
from pyrogram import Client, filters, enums
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from script import START_TXT, HELP_TXT, ABOUT_TXT
from database import add_user, get_user, update_usage, get_total_users, get_all_users
from utils import get_greeting, get_random_mix_id, is_subscribed, get_subscribe_buttons, START_BTNS, ABOUT_BTNS
from downloader import download_media

# --- HEALTH CHECK FOR KOYEB ---
async def handle_health(request):
    return web.Response(text="ZeroDev Bot is Online 🚀")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

# --- BOT CLIENT ---
app = Client(
    "ZeroBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    parse_mode=enums.ParseMode.HTML
)

# --- USER COMMANDS ---

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    user_id = message.from_user.id
    await add_user(user_id, message.from_user.first_name, message.from_user.username)
    
    if not await is_subscribed(client, user_id):
        return await message.reply_text(
            "⚠️ **Access Denied!**\nPlease join our channels to use this bot.",
            reply_markup=get_subscribe_buttons(),
            quote=True
        )

    sticker = await message.reply_sticker(
        "CAACAgQAAxkBAAEQqAVppTbJHAjruWesm0z6g7MZOPQjLQACUAEAAqghIQaxvfG1zemEojoE",
        quote=True
    )
    await asyncio.sleep(2)
    await sticker.delete()

    img_url = f"{random.choice(Config.PICS_URL)}?r={get_random_mix_id()}"
    await message.reply_photo(
        photo=img_url,
        caption=START_TXT.format(message.from_user.first_name, get_greeting()),
        reply_markup=START_BTNS,
        quote=True
    )

@app.on_message(filters.command("info") & filters.private)
async def info_handler(client, message):
    user = message.from_user
    photos = [p async for p in client.get_chat_photos(user.id, limit=1)]
    
    info_caption = (
        f"<b>👤 USER INFO</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>First Name:</b> {user.first_name}\n"
        f"<b>Last Name:</b> {user.last_name or 'N/A'}\n"
        f"<b>Telegram ID:</b> <code>{user.id}</code>\n"
        f"<b>DC ID:</b> {user.dc_id or 'Unknown'}\n"
        f"<b>Username:</b> @{user.username or 'None'}\n"
        f"<b>Profile:</b> <a href='tg://user?id={user.id}'>Clickable Link</a>"
    )
    
    if photos:
        await message.reply_photo(photos[0].file_id, caption=info_caption, quote=True)
    else:
        await message.reply_text(info_caption, quote=True)

# --- DOWNLOADER ---

@app.on_message(filters.regex(r'http') & filters.private)
async def dl_handler(client, message):
    if not await is_subscribed(client, message.from_user.id):
        return await message.reply_text(
            "⚠️ **Access Denied!**\nPlease join our channels to use this bot.",
            reply_markup=get_subscribe_buttons(),
            quote=True
        )

    url = message.text.strip()

    # Detect if user wants MP3 (they can send url + "mp3" or "/mp3")
    mode = 'mp3' if 'mp3' in url.lower() else 'video'
    # Strip any mode keyword from url if present
    url = url.replace('mp3', '').replace('MP3', '').strip()

    status = await message.reply_text("🔎 **Processing link...**", quote=True)

    file_path = None
    try:
        file_path = await download_media(url, mode=mode)
        await status.edit("📤 **Uploading to Telegram...**")

        if mode == 'mp3':
            await message.reply_audio(
                audio=file_path,
                quote=True
            )
        else:
            await message.reply_video(
                video=file_path,
                quote=True
            )

        await update_usage(message.from_user.id)
        await status.delete()

    except Exception as e:
        await status.edit(f"❌ **Error:** `{e}`")

    finally:
        # Always clean up the downloaded file
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# --- ADMIN COMMANDS ---

@app.on_message(filters.command("stats") & filters.user(Config.ADMIN_ID))
async def stats_handler(client, message):
    count = await get_total_users()
    await message.reply_text(f"📊 **Total Users in Database:** `{count}`", quote=True)

@app.on_message(filters.command("logs") & filters.user(Config.ADMIN_ID))
async def logs_handler(client, message):
    if os.path.exists(Config.LOG_FILE):
        await message.reply_document(Config.LOG_FILE, quote=True)
    else:
        await message.reply_text("❌ Log file not found.", quote=True)

@app.on_message(filters.command("broadcast") & filters.user(Config.ADMIN_ID))
async def broadcast_handler(client, message):
    if not message.reply_to_message:
        return await message.reply_text("❌ **Reply to a message** to broadcast it.", quote=True)
    
    progress = await message.reply_text("🚀 **Broadcast starting...**", quote=True)
    users = await get_all_users()
    success, failed = 0, 0
    
    async for user in users:
        try:
            await message.reply_to_message.copy(user['user_id'])
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.3)
    
    await progress.edit(f"✅ **Broadcast Done!**\n\nSuccess: `{success}`\nFailed: `{failed}`")

@app.on_message(filters.command("restart") & filters.user(Config.ADMIN_ID))
async def restart_handler(client, message):
    await message.reply_text("🔄 **Bot is restarting...**", quote=True)
    os.execl(sys.executable, sys.executable, *sys.argv)

# --- CALLBACK HANDLERS ---

@app.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    if query.data == "help":
        await query.message.edit_text(HELP_TXT, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="start_back")]]))
    elif query.data == "about":
        await query.message.edit_text(ABOUT_TXT.format(client.me.mention), reply_markup=ABOUT_BTNS, disable_web_page_preview=True)
    elif query.data == "start_back":
        await query.message.edit_text(START_TXT.format(query.from_user.first_name, get_greeting()), reply_markup=START_BTNS)
    elif query.data == "close":
        await query.message.delete()

# --- RUNNER ---
async def main():
    await start_web_server()
    await app.start()
    print("Bot is successfully running!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
