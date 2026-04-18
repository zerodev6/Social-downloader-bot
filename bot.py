import asyncio
import os
import sys
import random
from aiohttp import web
from pyrogram import Client, filters, enums
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from script import START_TXT, HELP_TXT, ABOUT_TXT
from database import add_user, update_usage, get_total_users, get_all_users
from utils import (
    get_greeting,
    get_random_mix_id,
    is_subscribed,
    get_subscribe_buttons,
    START_BTNS,
    ABOUT_BTNS,
)
from downloader import download_media, is_youtube

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────
async def handle_health(request):
    return web.Response(text="ZeroDev Bot is Online 🚀")


async def start_web_server():
    app_web = web.Application()
    app_web.router.add_get("/", handle_health)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()


# ─────────────────────────────────────────────────────────────────────────────
# BOT CLIENT
# ─────────────────────────────────────────────────────────────────────────────
app = Client(
    "ZeroBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    parse_mode=enums.ParseMode.HTML,
)

# ─────────────────────────────────────────────────────────────────────────────
# AUTO REACTION — your logic, translated to Pyrogram
# ─────────────────────────────────────────────────────────────────────────────
@app.on_message(filters.all & ~filters.bot, group=-1)
async def auto_react_handler(client, message):
    # Skip album/media group messages
    if message.media_group_id:
        message.continue_propagation()
        return

    try:
        a = ["❤️", "🥰", "🔥", "💋", "😍", "😘", "☺️"]
        b = random.choice(a)

        await client.send_reaction(
            chat_id=message.chat.id,
            message_id=message.id,
            emoji=b,
            big=True,
        )
    except Exception:
        pass

    message.continue_propagation()


# ─────────────────────────────────────────────────────────────────────────────
# YOUTUBE QUALITY KEYBOARD
# ─────────────────────────────────────────────────────────────────────────────
YT_QUALITIES = ["144", "240", "360", "480", "720", "1080", "1440", "2160"]
yt_pending: dict = {}


def yt_quality_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, q in enumerate(YT_QUALITIES):
        label = f"{'🔵' if q in ('720', '1080') else '⚪'} {q}p"
        row.append(InlineKeyboardButton(label, callback_data=f"ytdl|{q}"))
        if (i + 1) % 4 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🎵 MP3 Only", callback_data="ytdl|mp3")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="close")])
    return InlineKeyboardMarkup(buttons)


# ─────────────────────────────────────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────────────────────────────────────
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    user_id = message.from_user.id
    await add_user(user_id, message.from_user.first_name, message.from_user.username)

    if not await is_subscribed(client, user_id):
        return await message.reply_text(
            "⚠️ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ! 📢 ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ᴜsɪɴɢ ᴛʜᴇ ʙᴏᴛ.",
            reply_markup=get_subscribe_buttons(),
            quote=True,
        )

    sticker = await message.reply_sticker(
        "CAACAgQAAxkBAAEQqAVppTbJHAjruWesm0z6g7MZOPQjLQACUAEAAqghIQaxvfG1zemEojoE",
        quote=True,
    )
    await asyncio.sleep(2)
    await sticker.delete()

    img_url = f"{random.choice(Config.PICS_URL)}?r={get_random_mix_id()}"
    await message.reply_photo(
        photo=img_url,
        caption=START_TXT.format(message.from_user.first_name, get_greeting()),
        reply_markup=START_BTNS,
        quote=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# /info
# ─────────────────────────────────────────────────────────────────────────────
@app.on_message(filters.command("info") & filters.private)
async def info_handler(client, message):
    user = message.from_user
    photos = [p async for p in client.get_chat_photos(user.id, limit=1)]

    info_caption = (
        f"<b>👤 ᴜsᴇʀ ɪɴғᴏ</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>ɴᴀᴍᴇ:</b> {user.first_name}\n"
        f"<b>ʟᴀsᴛ ɴᴀᴍᴇ:</b> {user.last_name or 'ɴ/ᴀ'}\n"
        f"<b>ᴛᴇʟᴇɢʀᴀᴍ ɪᴅ:</b> <code>{user.id}</code>\n"
        f"<b>ᴅᴄ ɪᴅ:</b> {user.dc_id or 'ᴜɴᴋɴᴏᴡɴ'}\n"
        f"<b>ᴜsᴇʀɴᴀᴍᴇ:</b> @{user.username or 'ɴᴏɴᴇ'}\n"
        f"<b>ᴘʀᴏғɪʟᴇ:</b> <a href='tg://user?id={user.id}'>ᴄʟɪᴄᴋ ʜᴇʀᴇ</a>"
    )

    if photos:
        await message.reply_photo(photos[0].file_id, caption=info_caption, quote=True)
    else:
        await message.reply_text(info_caption, quote=True)


# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD HANDLER
# ─────────────────────────────────────────────────────────────────────────────
@app.on_message(filters.regex(r'https?://') & filters.private)
async def dl_handler(client, message):
    user_id = message.from_user.id

    if not await is_subscribed(client, user_id):
        return await message.reply_text(
            "⚠️ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ! 📢 ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ᴜsɪɴɢ ᴛʜᴇ ʙᴏᴛ.",
            reply_markup=get_subscribe_buttons(),
            quote=True,
        )

    raw = message.text.strip()
    force_mp3 = 'mp3' in raw.lower()
    url = raw.replace('mp3', '').replace('MP3', '').strip()

    if is_youtube(url) and not force_mp3:
        yt_pending[message.chat.id] = url
        await message.reply_text(
            "🎬 ʏᴏᴜᴛᴜʙᴇ ᴅᴇᴛᴇᴄᴛᴇᴅ! ᴄʜᴏᴏsᴇ ʏᴏᴜʀ ᴘʀᴇғᴇʀʀᴇᴅ ǫᴜᴀʟɪᴛʏ:",
            reply_markup=yt_quality_keyboard(),
            quote=True,
        )
        return

    await _do_download(client, message, url, mode='mp3' if force_mp3 else 'video')


# ─────────────────────────────────────────────────────────────────────────────
# CORE DOWNLOAD + UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
async def _do_download(client, message, url, mode='video', quality='best', reply_to=None, edit_msg=None):
    target = reply_to or message
    file_path = None

    try:
        upload_action = (
            enums.ChatAction.UPLOAD_AUDIO if mode == 'mp3'
            else enums.ChatAction.UPLOAD_VIDEO
        )

        stop_action = asyncio.Event()

        async def keep_action():
            while not stop_action.is_set():
                try:
                    await client.send_chat_action(message.chat.id, upload_action)
                except Exception:
                    pass
                await asyncio.sleep(4)

        action_task = asyncio.create_task(keep_action())

        try:
            file_path, caption = await download_media(url, mode=mode, quality=quality)
        finally:
            stop_action.set()
            action_task.cancel()
            try:
                await action_task
            except asyncio.CancelledError:
                pass

        await client.send_chat_action(message.chat.id, upload_action)

        if edit_msg:
            try:
                await edit_msg.delete()
            except Exception:
                pass

        if mode == 'mp3':
            await target.reply_audio(audio=file_path, caption=caption or None, quote=True)
        else:
            await target.reply_video(video=file_path, caption=caption or None, supports_streaming=True, quote=True)

        await update_usage(message.from_user.id)

    except Exception as e:
        err_msg = str(e)
        if len(err_msg) > 200:
            err_msg = err_msg[:200] + '…'
        await target.reply_text(f"❌ <b>Download failed:</b>\n<code>{err_msg}</code>", quote=True)

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK HANDLER
# ─────────────────────────────────────────────────────────────────────────────
@app.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    data = query.data

    if data == "check_sub":
        if await is_subscribed(client, query.from_user.id):
            await query.answer("✅ ᴀᴄᴄᴇss ɢʀᴀɴᴛᴇᴅ!", show_alert=True)
            await query.message.delete()
        else:
            await query.answer("❌ ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ ᴊᴏɪɴᴇᴅ ᴀʟʟ ᴄʜᴀɴɴᴇʟs ʏᴇᴛ!", show_alert=True)
        return

    if data.startswith("ytdl|"):
        _, choice = data.split("|", 1)
        url = yt_pending.get(query.message.chat.id)

        if not url:
            await query.answer("⚠️ sᴇssɪᴏɴ ᴇxᴘɪʀᴇᴅ. sᴇɴᴅ ᴛʜᴇ ʟɪɴᴋ ᴀɢᴀɪɴ.", show_alert=True)
            return

        await query.answer(f"{'🎵 MP3' if choice == 'mp3' else f'📥 {choice}p'} selected!")

        mode    = 'mp3' if choice == 'mp3' else 'video'
        quality = 'best' if choice == 'mp3' else choice

        try:
            await query.message.edit_text("⏳ <b>Starting download…</b>")
        except Exception:
            pass

        yt_pending.pop(query.message.chat.id, None)

        await _do_download(
            client, query.message, url,
            mode=mode, quality=quality,
            reply_to=query.message, edit_msg=query.message,
        )
        return

    if data == "help":
        await query.message.edit_text(
            HELP_TXT,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⌂ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ", callback_data="start_back")]]),
        )
    elif data == "about":
        await query.message.edit_text(
            ABOUT_TXT.format(client.me.mention),
            reply_markup=ABOUT_BTNS,
            disable_web_page_preview=True,
        )
    elif data == "start_back":
        await query.message.edit_text(
            START_TXT.format(query.from_user.first_name, get_greeting()),
            reply_markup=START_BTNS,
        )
    elif data == "close":
        await query.message.delete()


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN COMMANDS
# ─────────────────────────────────────────────────────────────────────────────
@app.on_message(filters.command("stats") & filters.user(Config.ADMIN_ID))
async def stats_handler(client, message):
    count = await get_total_users()
    await message.reply_text(f"📊 <b>Total Users:</b> <code>{count}</code>", quote=True)


@app.on_message(filters.command("logs") & filters.user(Config.ADMIN_ID))
async def logs_handler(client, message):
    if os.path.exists(Config.LOG_FILE):
        await message.reply_document(Config.LOG_FILE, quote=True)
    else:
        await message.reply_text("❌ Log file not found.", quote=True)


@app.on_message(filters.command("broadcast") & filters.user(Config.ADMIN_ID))
async def broadcast_handler(client, message):
    if not message.reply_to_message:
        return await message.reply_text("❌ <b>Reply to a message</b> to broadcast it.", quote=True)

    progress = await message.reply_text("🚀 <b>Broadcast starting…</b>", quote=True)
    users = await get_all_users()
    success, failed = 0, 0

    async for user in users:
        try:
            await message.reply_to_message.copy(user['user_id'])
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.3)

    await progress.edit(
        f"✅ <b>Broadcast Done!</b>\n\nSuccess: <code>{success}</code>\nFailed: <code>{failed}</code>"
    )


@app.on_message(filters.command("restart") & filters.user(Config.ADMIN_ID))
async def restart_handler(client, message):
    await message.reply_text("🔄 <b>Bot is restarting…</b>", quote=True)
    os.execl(sys.executable, sys.executable, *sys.argv)


# ─────────────────────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────────────────────
async def main():
    await start_web_server()
    await app.start()
    print("✅ ZeroDev Bot is successfully running!")
    await asyncio.Event().wait()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
