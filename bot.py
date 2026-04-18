import os, asyncio, time, shutil, logging, sys
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from pyrogram.errors import UserNotParticipant
from config import Config
from database import db
from script import *
from utils import get_greeting, get_random_mix_id, humanbytes
from progress import progress_for_pyrogram
import extractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ── Force Sub Config ──────────────────────────────────────────────────────────
FSUB_1, FSUB_2 = -1002444390757, -1002302324905
CH_LINK_1 = "https://t.me/zerodev2"
CH_LINK_2 = "https://t.me/mvxyoffcail"

# ── In-memory state ───────────────────────────────────────────────────────────
user_selections: dict   = {}   # msg_id  -> {path, files, page}
rename_waiting: dict    = {}   # user_id -> {path, original_name, proc_msg}
upload_type_waiting: dict = {} # user_id -> {path, new_name}

FILES_PER_PAGE = 10

# ── Clients ───────────────────────────────────────────────────────────────────
bot = Client(
    "UnzipBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
)
user_bot = (
    Client("UserSession", session_string=Config.SESSION_STRING)
    if Config.SESSION_STRING else None
)

# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

async def is_subscribed(client, message):
    unsubscribed = []
    for chat_id, link in [(FSUB_1, CH_LINK_1), (FSUB_2, CH_LINK_2)]:
        try:
            await client.get_chat_member(chat_id, message.from_user.id)
        except UserNotParticipant:
            unsubscribed.append(InlineKeyboardButton("📢 Join Channel", url=link))
        except Exception:
            pass
    if unsubscribed:
        me = await client.get_me()
        btn = [
            unsubscribed,
            [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{me.username}?start=start")],
        ]
        await message.reply_text(
            "<b>❌ Access Denied! Join our channels to continue.</b>",
            reply_markup=InlineKeyboardMarkup(btn),
        )
        return False
    return True

def main_menu_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Premium", callback_data="premium")],
        [
            InlineKeyboardButton("📑 About", callback_data="about"),
            InlineKeyboardButton("ℹ️ Help",  callback_data="help"),
        ],
    ])

def generate_file_menu(msg_id: int):
    data = user_selections.get(msg_id)
    if not data:
        return None
    files   = list(data["files"].items())
    page    = data.get("page", 0)
    total   = len(files)
    start   = page * FILES_PER_PAGE
    end     = min(start + FILES_PER_PAGE, total)
    buttons = []
    for i, (filename, is_checked) in enumerate(files[start:end], start=start):
        icon  = "✅" if is_checked else "⬜"
        short = filename if len(filename) <= 35 else filename[:32] + "…"
        buttons.append([InlineKeyboardButton(f"{icon} {short}", callback_data=f"toggle|{msg_id}|{i}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"page|{msg_id}|{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{max(1, -(-total // FILES_PER_PAGE))}", callback_data="noop"))
    if end < total:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"page|{msg_id}|{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([
        InlineKeyboardButton("✔️ All",  callback_data=f"all|{msg_id}"),
        InlineKeyboardButton("✖️ None", callback_data=f"none|{msg_id}"),
    ])
    buttons.append([InlineKeyboardButton("📤 Upload Selected", callback_data=f"upload|{msg_id}")])
    buttons.append([InlineKeyboardButton("🗑️ Cancel",          callback_data=f"close|{msg_id}")])
    return InlineKeyboardMarkup(buttons)

def upload_type_buttons(user_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 As File",  callback_data=f"uptype|file|{user_id}"),
            InlineKeyboardButton("🎬 As Video", callback_data=f"uptype|video|{user_id}"),
        ],
        [InlineKeyboardButton("🗑️ Cancel", callback_data=f"uptype|cancel|{user_id}")],
    ])

def _cleanup_entry(msg_id: int):
    entry = user_selections.pop(msg_id, None)
    if entry:
        path = entry.get("path")
        if path and os.path.exists(path):
            try:
                shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
            except Exception as e:
                logger.warning(f"Cleanup failed for {path}: {e}")

# ═════════════════════════════════════════════════════════════════════════════
# GENERAL COMMANDS
# ═════════════════════════════════════════════════════════════════════════════

@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    if not await is_subscribed(client, message):
        return
    await db.add_user(
        message.from_user.id,
        message.from_user.first_name,
        message.from_user.username,
    )
    # Show "please wait", wait 1 second, then show welcome
    wait_msg = await message.reply_text("⏳ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ…")
    await asyncio.sleep(1)
    try:
        await wait_msg.delete()
    except Exception:
        pass
    await message.reply_photo(
        f"{Config.PICS_URL[0]}?r={get_random_mix_id()}",
        caption=START_TXT.format(message.from_user.first_name, get_greeting()),
        reply_markup=main_menu_buttons(),
    )

@bot.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message):
    await message.reply_text(
        HELP_TXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Back to Menu", callback_data="home")]
        ]),
    )

@bot.on_message(filters.command("about") & filters.private)
async def about_cmd(client, message):
    await message.reply_text(
        ABOUT_TXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Back to Menu", callback_data="home")]
        ]),
    )

@bot.on_message(filters.command("info") & filters.private)
async def info_handler(client, message):
    user   = message.from_user
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

# ═════════════════════════════════════════════════════════════════════════════
# THUMBNAIL MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

@bot.on_message(filters.command("addthumb") & filters.private & filters.reply)
async def add_thumb(client, message):
    if not message.reply_to_message.photo:
        return await message.reply_text("❌ Please reply to a **Photo** to set it as thumbnail.")
    msg     = await message.reply_text("🔄 **Saving Thumbnail...**")
    file_id = message.reply_to_message.photo.file_id
    await db.set_thumbnail(message.from_user.id, file_id)
    await msg.edit("✅ **Custom Thumbnail Saved Successfully!**")

@bot.on_message(filters.command("delthumb") & filters.private)
async def del_thumb(client, message):
    await db.set_thumbnail(message.from_user.id, None)
    await message.reply_text("🗑️ **Thumbnail Removed.**")

@bot.on_message(filters.command("viewthumb") & filters.private)
async def view_thumb(client, message):
    user  = await db.get_user(message.from_user.id)
    thumb = user.get("thumbnail") if user else None
    if thumb:
        await message.reply_photo(thumb, caption="🖼️ **Your Current Thumbnail**")
    else:
        await message.reply_text("❌ No custom thumbnail set.")

# ═════════════════════════════════════════════════════════════════════════════
# ADMIN COMMANDS  (Config.ADMINS only — invisible to regular users)
# ═════════════════════════════════════════════════════════════════════════════

@bot.on_message(filters.command("stats") & filters.user(Config.ADMINS))
async def stats_cmd(client, message):
    users_count   = await db.total_users_count()
    premium_count = await db.total_premium_count() if hasattr(db, "total_premium_count") else "N/A"
    await message.reply_text(
        f"📊 **Bot Statistics**\n\n"
        f"👥 Total Users: `{users_count}`\n"
        f"💎 Premium Users: `{premium_count}`"
    )

@bot.on_message(filters.command("add_premium") & filters.user(Config.ADMINS))
async def add_premium(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/add_premium user_id`")
    try:
        user_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ Invalid user ID.")
    await db.update_user(user_id, {"is_premium": True})
    await message.reply_text(f"✅ User `{user_id}` promoted to Premium.")
    try:
        await bot.send_message(user_id, "🎊 **Congratulations! You have been granted Premium access.**")
    except Exception:
        pass

@bot.on_message(filters.command("remove_premium") & filters.user(Config.ADMINS))
async def remove_premium(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/remove_premium user_id`")
    try:
        user_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ Invalid user ID.")
    await db.update_user(user_id, {"is_premium": False})
    await message.reply_text(f"❌ User `{user_id}` removed from Premium.")
    try:
        await bot.send_message(user_id, "⚠️ **Your Premium access has been revoked.**")
    except Exception:
        pass

@bot.on_message(filters.command("ban") & filters.user(Config.ADMINS))
async def ban_user(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/ban user_id`")
    try:
        user_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ Invalid user ID.")
    await db.update_user(user_id, {"is_banned": True})
    await message.reply_text(f"🚫 User `{user_id}` has been banned.")

@bot.on_message(filters.command("unban") & filters.user(Config.ADMINS))
async def unban_user(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/unban user_id`")
    try:
        user_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ Invalid user ID.")
    await db.update_user(user_id, {"is_banned": False})
    await message.reply_text(f"✅ User `{user_id}` has been unbanned.")

@bot.on_message(filters.command("broadcast") & filters.user(Config.ADMINS) & filters.reply)
async def broadcast(client, message):
    users = await db.get_all_users()
    msg   = await message.reply_text("🚀 **Broadcast Started...**")
    count, failed = 0, 0
    for user in users:
        try:
            await message.reply_to_message.copy(user["id"])
            count += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.1)
    await msg.edit(
        f"✅ **Broadcast Completed!**\n\n"
        f"📨 Sent: `{count}`\n❌ Failed: `{failed}`"
    )

@bot.on_message(filters.command("logs") & filters.user(Config.ADMINS))
async def send_logs(client, message):
    try:
        await message.reply_document("bot.log", caption="📋 **Bot Logs**")
    except FileNotFoundError:
        await message.reply_text("❌ No log file found.")

@bot.on_message(filters.command("restart") & filters.user(Config.ADMINS))
async def restart_bot(client, message):
    await message.reply_text("🔄 **Restarting Bot...**")
    os.execl(sys.executable, sys.executable, *sys.argv)

# ═════════════════════════════════════════════════════════════════════════════
# ARCHIVE HANDLING
# ═════════════════════════════════════════════════════════════════════════════

SUPPORTED_EXT = (".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tar.gz", ".tar.bz2")

ALL_COMMANDS = [
    "start","help","about","info","addthumb","delthumb","viewthumb",
    "stats","add_premium","remove_premium","ban","unban","broadcast","logs","restart","skip"
]

@bot.on_message(filters.private & (filters.document | filters.video))
async def handle_archive(client, message):
    if not await is_subscribed(client, message):
        return

    file  = message.document or message.video
    fname = (file.file_name or "").lower()
    if not any(fname.endswith(ext) for ext in SUPPORTED_EXT):
        return

    user = await db.get_user(message.from_user.id)
    if user and user.get("is_banned"):
        return await message.reply_text("🚫 You are banned from using this bot.")

    proc = await message.reply_text("🔎 **Scanning Archive...**")
    path = await client.download_media(
        message,
        file_name=f"downloads/{message.from_user.id}_{message.id}_{file.file_name}",
        progress=progress_for_pyrogram,
        progress_args=("🔽 Downloading", proc, time.time()),
    )

    if not path or not os.path.exists(path):
        return await proc.edit("❌ **Download failed. Please try again.**")

    # ── RAR: ask for new filename first ───────────────────────────────────
    if fname.endswith(".rar"):
        rename_waiting[message.from_user.id] = {
            "path":          path,
            "original_name": file.file_name,
            "proc_msg":      proc,
        }
        await proc.edit(
            f"📦 **RAR file received!**\n\n"
            f"📄 Original name: `{file.file_name}`\n\n"
            f"✏️ Please send the **new filename** (without extension).\n"
            f"Or send /skip to keep original names."
        )
        return

    # ── Other formats: show file picker ──────────────────────────────────
    try:
        files = await extractor.get_archive_list(path)
        if not files:
            os.remove(path)
            return await proc.edit("❌ **Archive is empty or unsupported.**")

        user_selections[message.id] = {"path": path, "files": {f: True for f in files}, "page": 0}
        await proc.edit(
            f"📂 **Archive Scanned!**\n\n"
            f"📦 Files found: `{len(files)}`\n"
            f"✅ Selected: `{len(files)}`\n\n"
            f"Toggle files below, then press **Upload Selected**.",
            reply_markup=generate_file_menu(message.id),
        )
    except Exception as e:
        logger.exception("Archive scan error")
        if os.path.exists(path): os.remove(path)
        await proc.edit(f"❌ **Error scanning archive:**\n`{e}`")

# ── User sends new name for RAR ───────────────────────────────────────────────
@bot.on_message(filters.private & filters.text & ~filters.command(ALL_COMMANDS))
async def handle_rename_reply(client, message):
    uid = message.from_user.id
    if uid not in rename_waiting:
        return   # not in rename flow — ignore

    entry    = rename_waiting.pop(uid)
    new_name = message.text.strip()
    path     = entry["path"]
    proc     = entry["proc_msg"]

    upload_type_waiting[uid] = {"path": path, "new_name": new_name}

    await proc.edit(f"✅ **New name set:** `{new_name}`\n\n📤 How would you like to upload?")
    await message.reply_text("Choose upload type:", reply_markup=upload_type_buttons(uid))

# ── /skip keeps original filenames ───────────────────────────────────────────
@bot.on_message(filters.command("skip") & filters.private)
async def skip_rename(client, message):
    uid = message.from_user.id
    if uid not in rename_waiting:
        return await message.reply_text("❌ Nothing to skip.")

    entry = rename_waiting.pop(uid)
    path  = entry["path"]
    proc  = entry["proc_msg"]

    upload_type_waiting[uid] = {"path": path, "new_name": None}
    await proc.edit("⏭️ **Keeping original filenames.**\n\n📤 How would you like to upload?")
    await message.reply_text("Choose upload type:", reply_markup=upload_type_buttons(uid))

# ═════════════════════════════════════════════════════════════════════════════
# CALLBACK QUERIES
# ═════════════════════════════════════════════════════════════════════════════

@bot.on_callback_query()
async def callbacks(client, query):
    data = query.data
    uid  = query.from_user.id

    if data == "noop":
        return await query.answer()

    # ── Navigation ────────────────────────────────────────────────────────
    if data == "home":
        await query.answer()
        await query.message.edit_text(
            START_TXT.format(query.from_user.first_name, get_greeting()),
            reply_markup=main_menu_buttons(),
        )
        return

    if data == "about":
        await query.answer()
        await query.message.edit_text(
            ABOUT_TXT,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back", callback_data="home")]]),
        )
        return

    if data == "help":
        await query.answer()
        await query.message.edit_text(
            HELP_TXT,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back", callback_data="home")]]),
        )
        return

    if data == "premium":
        await query.answer()
        user_db    = await db.get_user(uid)
        is_premium = user_db.get("is_premium") if user_db else False
        text = (
            "💎 **You already have Premium access!**\n\nEnjoy unlimited extractions with priority support."
            if is_premium else
            "💎 **Premium Access**\n\n"
            "• Unlimited archive extractions\n"
            "• Priority processing speed\n"
            "• Custom thumbnails\n"
            "• Priority support\n\n"
            "Contact the admin to upgrade!"
        )
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📩 Contact Admin",
                    url=f"https://t.me/{Config.ADMINS[0]}" if Config.ADMINS else "https://t.me/")],
                [InlineKeyboardButton("🏠 Back", callback_data="home")],
            ]),
        )
        return

    # ── Upload type (RAR rename flow) ─────────────────────────────────────
    if data.startswith("uptype|"):
        _, utype, target_uid_str = data.split("|")
        target_uid = int(target_uid_str)

        if utype == "cancel":
            entry = upload_type_waiting.pop(target_uid, None)
            if entry and os.path.exists(entry["path"]):
                os.remove(entry["path"])
            await query.answer("🗑️ Cancelled.")
            await query.message.edit_text("🗑️ **Operation cancelled.**")
            return

        entry = upload_type_waiting.pop(target_uid, None)
        if not entry:
            return await query.answer("⚠️ Session expired.", show_alert=True)

        await query.answer(f"📤 Uploading as {'Video' if utype == 'video' else 'File'}…")
        await query.message.edit_text("⏳ **Extracting & uploading...**")

        archive_path = entry["path"]
        new_name     = entry.get("new_name")
        extract_dir  = archive_path + "_extracted"
        os.makedirs(extract_dir, exist_ok=True)

        try:
            all_files = await extractor.get_archive_list(archive_path)
            await extractor.extract_files(archive_path, extract_dir, all_files)
        except Exception as e:
            shutil.rmtree(extract_dir, ignore_errors=True)
            if os.path.exists(archive_path): os.remove(archive_path)
            return await query.message.edit_text(f"❌ **Extraction failed:**\n`{e}`")

        user_db    = await db.get_user(target_uid)
        thumb_id   = user_db.get("thumbnail") if user_db else None
        thumb_path = None
        if thumb_id:
            try:
                thumb_path = await bot.download_media(thumb_id, file_name=f"downloads/thumb_{target_uid}.jpg")
            except Exception:
                thumb_path = None

        success, failed = 0, 0
        for idx, fname in enumerate(all_files, 1):
            fpath = os.path.join(extract_dir, fname)
            if not os.path.exists(fpath):
                fpath = os.path.join(extract_dir, os.path.basename(fname))
            if not os.path.exists(fpath):
                failed += 1
                continue

            # Rename if user provided a new name
            if new_name:
                ext       = os.path.splitext(fname)[1]
                new_fname = f"{new_name}{ext}" if len(all_files) == 1 else f"{new_name}_{idx}{ext}"
                new_fpath = os.path.join(os.path.dirname(fpath), new_fname)
                os.rename(fpath, new_fpath)
                fpath = new_fpath

            try:
                size_str   = humanbytes(os.path.getsize(fpath))
                upload_msg = await query.message.reply_text(
                    f"📤 **Uploading:** `{os.path.basename(fpath)}`\n📦 Size: `{size_str}`"
                )
                if utype == "video":
                    await client.send_video(
                        query.message.chat.id,
                        video=fpath,
                        thumb=thumb_path,
                        caption=f"🎬 `{os.path.basename(fpath)}`\n📦 `{size_str}`",
                        supports_streaming=True,
                        progress=progress_for_pyrogram,
                        progress_args=("📤 Uploading", upload_msg, time.time()),
                    )
                else:
                    await client.send_document(
                        query.message.chat.id,
                        document=fpath,
                        thumb=thumb_path,
                        caption=f"📄 `{os.path.basename(fpath)}`\n📦 `{size_str}`",
                        progress=progress_for_pyrogram,
                        progress_args=("📤 Uploading", upload_msg, time.time()),
                    )
                await upload_msg.delete()
                success += 1
            except Exception:
                logger.exception(f"Upload failed for {fpath}")
                failed += 1

        shutil.rmtree(extract_dir, ignore_errors=True)
        if os.path.exists(archive_path): os.remove(archive_path)
        if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)

        await query.message.edit_text(
            f"✅ **Upload Complete!**\n\n📨 Uploaded: `{success}`\n❌ Failed: `{failed}`"
        )
        return

    # ── File-picker: toggle ───────────────────────────────────────────────
    if data.startswith("toggle|"):
        _, msg_id, idx = data.split("|")
        msg_id, idx = int(msg_id), int(idx)
        entry = user_selections.get(msg_id)
        if not entry:
            return await query.answer("⚠️ Session expired.", show_alert=True)
        files = list(entry["files"].keys())
        if idx >= len(files):
            return await query.answer()
        fname = files[idx]
        entry["files"][fname] = not entry["files"][fname]
        selected = sum(v for v in entry["files"].values())
        await query.answer(f"{'✅' if entry['files'][fname] else '⬜'} {fname[:40]}")
        await query.message.edit_text(
            f"📂 **Select files to upload**\n\n✅ Selected: `{selected}` / `{len(files)}`",
            reply_markup=generate_file_menu(msg_id),
        )
        return

    if data.startswith("all|"):
        msg_id = int(data.split("|")[1])
        entry  = user_selections.get(msg_id)
        if not entry: return await query.answer("⚠️ Session expired.", show_alert=True)
        for k in entry["files"]: entry["files"][k] = True
        n = len(entry["files"])
        await query.answer("✅ All selected!")
        await query.message.edit_text(
            f"📂 **Select files to upload**\n\n✅ Selected: `{n}` / `{n}`",
            reply_markup=generate_file_menu(msg_id),
        )
        return

    if data.startswith("none|"):
        msg_id = int(data.split("|")[1])
        entry  = user_selections.get(msg_id)
        if not entry: return await query.answer("⚠️ Session expired.", show_alert=True)
        for k in entry["files"]: entry["files"][k] = False
        await query.answer("⬜ All deselected!")
        await query.message.edit_text(
            f"📂 **Select files to upload**\n\n✅ Selected: `0` / `{len(entry['files'])}`",
            reply_markup=generate_file_menu(msg_id),
        )
        return

    if data.startswith("page|"):
        _, msg_id, page = data.split("|")
        msg_id, page = int(msg_id), int(page)
        entry = user_selections.get(msg_id)
        if not entry: return await query.answer("⚠️ Session expired.", show_alert=True)
        entry["page"] = page
        selected = sum(v for v in entry["files"].values())
        await query.answer()
        await query.message.edit_text(
            f"📂 **Select files to upload**\n\n✅ Selected: `{selected}` / `{len(entry['files'])}`",
            reply_markup=generate_file_menu(msg_id),
        )
        return

    if data.startswith("close|"):
        msg_id = int(data.split("|")[1])
        _cleanup_entry(msg_id)
        await query.answer("🗑️ Cancelled.")
        await query.message.edit_text("🗑️ **Operation cancelled and files cleaned up.**")
        return

    if data.startswith("upload|"):
        msg_id = int(data.split("|")[1])
        entry  = user_selections.get(msg_id)
        if not entry:
            return await query.answer("⚠️ Session expired.", show_alert=True)
        selected_files = [f for f, checked in entry["files"].items() if checked]
        if not selected_files:
            return await query.answer("⚠️ No files selected!", show_alert=True)

        await query.answer("📤 Starting upload…")
        await query.message.edit_text(
            f"⏳ **Extracting & uploading `{len(selected_files)}` file(s)...**"
        )

        archive_path = entry["path"]
        extract_dir  = archive_path + "_extracted"
        os.makedirs(extract_dir, exist_ok=True)

        try:
            await extractor.extract_files(archive_path, extract_dir, selected_files)
        except Exception as e:
            logger.exception("Extraction error")
            _cleanup_entry(msg_id)
            shutil.rmtree(extract_dir, ignore_errors=True)
            return await query.message.edit_text(f"❌ **Extraction failed:**\n`{e}`")

        user_db    = await db.get_user(uid)
        thumb_id   = user_db.get("thumbnail") if user_db else None
        thumb_path = None
        if thumb_id:
            try:
                thumb_path = await bot.download_media(thumb_id, file_name=f"downloads/thumb_{uid}.jpg")
            except Exception:
                thumb_path = None

        success, failed = 0, 0
        for fname in selected_files:
            fpath = os.path.join(extract_dir, fname)
            if not os.path.exists(fpath):
                fpath = os.path.join(extract_dir, os.path.basename(fname))
            if not os.path.exists(fpath):
                failed += 1
                continue
            try:
                size_str   = humanbytes(os.path.getsize(fpath))
                upload_msg = await query.message.reply_text(
                    f"📤 **Uploading:** `{os.path.basename(fname)}`\n📦 Size: `{size_str}`"
                )
                await client.send_document(
                    query.message.chat.id,
                    document=fpath,
                    thumb=thumb_path,
                    caption=f"📄 `{os.path.basename(fname)}`\n📦 `{size_str}`",
                    progress=progress_for_pyrogram,
                    progress_args=("📤 Uploading", upload_msg, time.time()),
                )
                await upload_msg.delete()
                success += 1
            except Exception:
                logger.exception(f"Upload failed for {fname}")
                failed += 1

        _cleanup_entry(msg_id)
        shutil.rmtree(extract_dir, ignore_errors=True)
        if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)

        await query.message.edit_text(
            f"✅ **Upload Complete!**\n\n📨 Uploaded: `{success}`\n❌ Failed: `{failed}`"
        )
        return

    await query.answer("⚠️ Unknown action.", show_alert=True)

# ═════════════════════════════════════════════════════════════════════════════
# WEB SERVER & ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

async def web_server():
    app = web.Application()
    app.add_routes([
        web.get("/",       lambda r: web.json_response({"status": "Bot Active 🚀"})),
        web.get("/health", lambda r: web.json_response({"ok": True})),
    ])
    return app

async def main():
    os.makedirs("downloads", exist_ok=True)
    runner = web.AppRunner(await web_server())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8080).start()
    logger.info("Web server started on :8080")
    if user_bot:
        await user_bot.start()
        logger.info("UserBot started ✅")
    await bot.start()
    logger.info("Bot started successfully ✅")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
