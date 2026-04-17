from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

client = AsyncIOMotorClient(Config.MONGO_URL)
db = client["downloader_bot"]
users_col = db["users"]

async def add_user(user_id, first_name, username):
    user = await users_col.find_one({"user_id": user_id})
    if not user:
        await users_col.insert_one({
            "user_id": user_id,
            "first_name": first_name,
            "username": username,
            "plan": "free",
            "usage_count": 0
        })

async def get_user(user_id):
    return await users_col.find_one({"user_id": user_id})

async def update_usage(user_id):
    await users_col.update_one({"user_id": user_id}, {"$inc": {"usage_count": 1}})

async def get_total_users():
    return await users_col.count_documents({})

async def get_all_users():
    return users_col.find({})
  
