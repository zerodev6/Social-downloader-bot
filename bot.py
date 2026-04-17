import asyncio
import logging
import os
import sys
import random
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from config import Config
from database import add_user, get_user, update_usage, get_total_users, get_all_users
from utils import get_greeting, get_random_mix_id, is_subscribed, get_subscribe_buttons, START_BTNS, get_greeting
from downloader import download_media

# Logging
logging.basicConfig(level=logging.INFO, filename=Config.LOG_FILE, filemode='a', 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Client("DownloaderBot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)

# Strings provided in prompt
START_TXT = "<b>ʜᴇʏ, {}! {}</b>\n\nɪ'ᴍ ᴀɴ <b>ᴀʟʟ-ɪɴ-ᴏɴᴇ sᴏᴄɪᴀʟ ᴍᴇᴅɪᴀ ᴅᴏᴡɴʟᴏᴀᴅᴇʀ ʙᴏᴛ</b> 📥..."
# (Include other strings here as defined in your request)

@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    await add_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    
    if not await is_subscribed(client, message.from_user.id):
        return await message.reply_text("❌ **Access Denied!**\nPlease join our channels to use this bot.", 
                                        reply_markup=get_subscribe_buttons())

    sticker = await message.reply_sticker("CAACAgIAAxkBAAEQZtFpgEdROhGouBVFD3e0K-YjmVHwsgACtCMAAphLKUjeub7NKlvk2TgE")
    await asyncio.sleep(2)
    await sticker.delete()

    welcome_img = f"{random.choice(Config.PICS_URL)}?r={get_random_mix_id()}"
    greeting = get_greeting()
    
    await message.reply_photo(
        photo=welcome_img,
        caption=START_TXT.format(message.from_user.first_name, greeting),
        reply_markup=START_BTNS
    )

@bot.on_message(filters.regex(r'http') & filters.private)
async def link_handler(client, message):
    user = await get_user(message.from_user.id)
    if user['plan'] == 'free' and user['usage_count'] >= 5:
        return await message.reply_text("⚠️ **Limit Reached!** Upgrade to Premium for unlimited downloads.")
    
    # Download Logic Placeholder
    status = await message.reply_text("🔄 **Processing link...**", quote=True)
    try:
        # Quality buttons would be sent here
        file_path = await download_media(message.text)
        await message.reply_document(file_path)
        await update_usage(message.from_user.id)
        await status.delete()
        os.remove(file_path)
    except Exception as e:
        await status.edit(f"❌ **Error:** {str(e)}")

@bot.on_message(filters.command("stats") & filters.user(Config.ADMIN_ID))
async def stats_handler(client, message):
    total = await get_total_users()
    await message.reply_text(f"📊 **Total Users:** {total}")

@bot.on_message(filters.command("broadcast") & filters.user(Config.ADMIN_ID))
async def broadcast_handler(client, message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to a message to broadcast.")
    
    users = await get_all_users()
    success, failed = 0, 0
    msg = await message.reply_text("🚀 **Starting Broadcast...**")
    
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
    
    await msg.edit(f"✅ **Broadcast Completed!**\n\nTotal: {success + failed}\nSuccess: {success}\nFailed: {failed}")

@bot.on_message(filters.command("logs") & filters.user(Config.ADMIN_ID))
async def send_logs(client, message):
    await message.reply_document(Config.LOG_FILE)

@bot.on_message(filters.command("restart") & filters.user(Config.ADMIN_ID))
async def restart_bot(client, message):
    await message.reply_text("🔄 **Restarting...**")
    os.execl(sys.executable, sys.executable, *sys.argv)

if __name__ == "__main__":
    bot.run()
