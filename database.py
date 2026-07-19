# Copyright (C) @ITACHI_404
# Developer: https://t.me/ITACHI_404

import os
from motor.motor_asyncio import AsyncIOMotorClient
from logger import LOGGER

# Initialize Async MongoDB Client 
# The URI will be pulled from Render's Environment Variables
MONGO_URI = os.environ.get("MONGO_URI", "your_mongodb_connection_string_here")
client = AsyncIOMotorClient(MONGO_URI)
db = client["SaveRestrictedBot_DB"]

# Collections
users_col = db["users"]
thumbs_col = db["thumbnails"]
forward_col = db["forward_channels"]

# --- User Management Methods ---
async def add_user(user_id: int):
    """Saves a user ID to the database if it doesn't already exist."""
    try:
        user = await users_col.find_one({"user_id": user_id})
        if not user:
            await users_col.insert_one({"user_id": user_id})
            LOGGER(__name__).info(f"New user {user_id} saved to DB.")
    except Exception as e:
        LOGGER(__name__).error(f"Error adding user to DB: {e}")

async def get_all_users():
    """Returns a list of all registered user IDs."""
    try:
        cursor = users_col.find({}, {"user_id": 1, "_id": 0})
        users = await cursor.to_list(length=None)
        return [user["user_id"] for user in users]
    except Exception as e:
        LOGGER(__name__).error(f"Error fetching users: {e}")
        return []

# --- Thumbnail Management Methods ---
async def set_thumb(user_id: int, file_id: str):
    """Saves or updates a user's custom thumbnail file_id."""
    try:
        await thumbs_col.update_one(
            {"user_id": user_id},
            {"$set": {"file_id": file_id}},
            upsert=True
        )
    except Exception as e:
        LOGGER(__name__).error(f"Error setting thumbnail in DB: {e}")

async def get_thumb(user_id: int):
    """Fetches the custom thumbnail file_id if it exists."""
    try:
        thumb = await thumbs_col.find_one({"user_id": user_id})
        return thumb["file_id"] if thumb else None
    except Exception as e:
        LOGGER(__name__).error(f"Error fetching thumbnail from DB: {e}")
        return None

async def del_thumb(user_id: int):
    """Removes a user's custom thumbnail registration."""
    try:
        result = await thumbs_col.delete_one({"user_id": user_id})
        return result.deleted_count > 0
    except Exception as e:
        LOGGER(__name__).error(f"Error deleting thumbnail from DB: {e}")
        return False

# --- Forward Channel Management Methods ---
async def get_target_channel_ids():
    """Fetches the list of forward channel IDs."""
    try:
        doc = await forward_col.find_one({"_id": "forward_config"})
        return doc.get("channels", []) if doc else []
    except Exception as e:
        LOGGER(__name__).error(f"Error fetching forward channels: {e}")
        return []

async def save_target_channel_ids(channel_ids: list):
    """Saves a new list of forward channel IDs."""
    try:
        await forward_col.update_one(
            {"_id": "forward_config"},
            {"$set": {"channels": channel_ids}},
            upsert=True
        )
        return True
    except Exception as e:
        LOGGER(__name__).error(f"Error saving forward channels: {e}")
        return False

async def remove_target_channel_ids():
    """Removes the forward channel configuration entirely."""
    try:
        await forward_col.delete_one({"_id": "forward_config"})
        return True
    except Exception as e:
        LOGGER(__name__).error(f"Error removing forward channels: {e}")
        return False
