import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", "12345"))
    API_HASH = os.environ.get("API_HASH", "your_api_hash")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")
    MONGO_URL = os.environ.get("MONGO_URL", "your_mongodb_url")
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "12345678"))
    
    CHANNELS = ["zerodev2", "mvxyoffcail"]
    PICS_URL = ["https://api.aniwallpaper.workers.dev/random?type=girl"]
    LOG_FILE = "logs.txt"
    SOURCE_LINK = "https://ouo.io/nBFMfH" # Update this
