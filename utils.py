import random
import string
import pytz
from datetime import datetime
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from config import Config

def get_greeting():
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    hour = now.hour
    if 5 <= hour < 12: return "Good Morning 🌅"
    elif 12 <= hour < 17: return "Good Afternoon ☀️"
    elif 17 <= hour < 21: return "Good Evening 🌆"
    else: return "Good Night 🌙"

def get_random_mix_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

async def is_subscribed(client, user_id):
    for channel in Config.CHANNELS:
        try:
            await client.get_chat_member(channel, user_id)
        except UserNotParticipant:
            return False
        except:
            pass
    return True

def get_subscribe_buttons():
    btns = [[InlineKeyboardButton(f"Join {c}", url=f"https://t.me/{c}")] for c in Config.CHANNELS]
    btns.append([InlineKeyboardButton("🔄 Try Again", callback_data="check_sub")])
    return InlineKeyboardMarkup(btns)

START_BTNS = InlineKeyboardMarkup([
    [InlineKeyboardButton("Help ✨", callback_data="help"), InlineKeyboardButton("About ℹ️", callback_data="about")],
    [InlineKeyboardButton("Close ✖️", callback_data="close")]
])

ABOUT_BTNS = InlineKeyboardMarkup([
    [InlineKeyboardButton("Source Code 📁", url=Config.SOURCE_LINK)],
    [InlineKeyboardButton("⬅️ Back", callback_data="start_back")]
])
