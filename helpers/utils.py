# helpers/utils.py
import os
from PIL import Image
from time import time
from pyleaves import Leaves
from helpers.files import fileSizeLimit
from helpers.msg import get_parsed_msg
from logger import LOGGER
from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument

# Progress bar template
PROGRESS_BAR = "\nPercentage: {percentage:.2f}% | {current}/{total}\nSpeed: {speed}/s\nEstimated Time Left: {est_time}s"

def progressArgs(action, progress_message, start_time):
    return (action, progress_message, start_time, PROGRESS_BAR, "▓", "░")

async def send_media(bot, message, media_path, media_type, caption, progress_message, start_time):
    file_size = os.path.getsize(media_path)
    if not await fileSizeLimit(file_size, message, "upload"): return

    # Check for Custom Thumbnail
    user_id = message.from_user.id
    custom_thumb = f"thumb/{user_id}.jpg"
    thumb = custom_thumb if os.path.exists(custom_thumb) else None

    progress_args = progressArgs("📥 Uploading Progress", progress_message, start_time)
    
    if media_type == "photo":
        await message.reply_photo(media_path, caption=caption or "", progress=Leaves.progress_for_pyrogram, progress_args=progress_args)
    elif media_type == "video":
        await message.reply_video(media_path, thumb=thumb, caption=caption or "", progress=Leaves.progress_for_pyrogram, progress_args=progress_args)
    elif media_type == "audio":
        await message.reply_audio(media_path, thumb=thumb, caption=caption or "", progress=Leaves.progress_for_pyrogram, progress_args=progress_args)
    else:
        await message.reply_document(media_path, thumb=thumb, caption=caption or "", progress=Leaves.progress_for_pyrogram, progress_args=progress_args)
async def processMediaGroup(chat_message, bot, message):
    media_group_messages = await chat_message.get_media_group()
    valid_media = []
    
    # We must download each item in the group to send them
    for msg in media_group_messages:
        if msg.photo or msg.video or msg.document:
            path = await msg.download()
            if msg.photo:
                valid_media.append(InputMediaPhoto(media=path, caption=msg.caption))
            elif msg.video:
                valid_media.append(InputMediaVideo(media=path, caption=msg.caption))
            elif msg.document:
                valid_media.append(InputMediaDocument(media=path, caption=msg.caption))
            
    if valid_media:
        await bot.send_media_group(chat_id=message.chat.id, media=valid_media)
        return True
    return False
