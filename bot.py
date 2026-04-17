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

# Health Check for Koyeb
async def handle_health(request):
    return web.Response(text="ZeroDev Bot Active")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8080).start()

app = Client("ZeroBot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    user_id = message.from_user.id
    await add_user(user_id, message.from_user.first_name, message.from_user.username)
    
    if not await is_subscribed(client, user_id):
        return await message.reply_text("❌ Join our channels to use me!", reply_markup=get_subscribe_buttons(), quote=True)

    sticker = await message.reply_sticker("CAACAgIAAxkBAAEQZtFpgEdROhGouBVFD3e0K-YjmVHwsgACtCMAAphLKUjeub7NKlvk2TgE", quote=True)
    await asyncio.sleep(2)
    await sticker.delete()

    img_url = f"{random.choice(Config.PICS_URL)}?r={get_random_mix_id()}"
    await message.reply_photo(photo=img_url, caption=START_TXT.format(message.from_user.first_name, get_greeting()), reply_markup=START_BTNS, quote=True)

@app.on_message(filters.regex(r'http') & filters.private)
async def dl_handler(client, message):
    user = await get_user(message.from_user.id)
    if user['plan'] == 'free' and user['usage_count'] >= 5:
        return await message.reply_text("❌ Limit Reached! Contact @Venuboyy", quote=True)

    status = await message.reply_text("🔎 **Processing link...**", quote=True)
    try:
        file_path = await download_media(message.text)
        await status.edit("📤 **Uploading...**")
        await message.reply_document(file_path, quote=True)
        await update_usage(message.from_user.id)
        os.remove(file_path)
        await status.delete()
    except Exception as e:
        await status.edit(f"❌ Error: `{e}`")

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

# Admin commands
@app.on_message(filters.command("stats") & filters.user(Config.ADMIN_ID))
async def stats(c, m):
    count = await get_total_users()
    await m.reply_text(f"📊 Total Users: {count}", quote=True)

async def main():
    await start_web_server()
    await app.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    app.run(main())
