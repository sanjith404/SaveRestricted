# helpers/utils.py
# Copyright (C) @ITACHI_404
# Developer: https://t.me/ITACHI_404

import os
import asyncio
from PIL import Image
from time import time
from pyleaves import Leaves
from helpers.files import fileSizeLimit
from helpers.msg import get_parsed_msg
from logger import LOGGER
from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio
from pyrogram.errors import FloodWait

# Import our new MongoDB database methods
from database import get_thumb, get_target_channel_ids

# Progress bar template
PROGRESS_BAR = "\nPercentage: {percentage:.2f}% | {current}/{total}\nSpeed: {speed}/s\nEstimated Time Left: {est_time}s"

def progressArgs(action, progress_message, start_time):
    return (action, progress_message, start_time, PROGRESS_BAR, "▓", "░")

async def send_media(bot, message, media_path, media_type, caption, progress_message, start_time):
    file_size = os.path.getsize(media_path)
    if not await fileSizeLimit(file_size, message, "upload"): return

    # Get thumbnail ID
    thumb_file_id = await get_thumb(message.from_user.id)
    thumb_path = None
    
    # Safely download the thumbnail if it exists
    if thumb_file_id:
        try:
            thumb_path = await bot.download_media(thumb_file_id)
        except Exception as e:
            LOGGER(__name__).warning(f"Could not download thumbnail: {e}")

    progress_args = progressArgs("📥 Uploading Progress", progress_message, start_time)
    
    # Upload with the thumbnail path (or None if it failed to download)
    try:
        if media_type == "photo":
            sent_msg = await message.reply_photo(media_path, caption=caption or "", progress=Leaves.progress_for_pyrogram, progress_args=progress_args)
        elif media_type == "video":
            sent_msg = await message.reply_video(media_path, thumb=thumb_path, caption=caption or "", progress=Leaves.progress_for_pyrogram, progress_args=progress_args)
        elif media_type == "audio":
            sent_msg = await message.reply_audio(media_path, thumb=thumb_path, caption=caption or "", progress=Leaves.progress_for_pyrogram, progress_args=progress_args)
        else:
            sent_msg = await message.reply_document(media_path, thumb=thumb_path, caption=caption or "", progress=Leaves.progress_for_pyrogram, progress_args=progress_args)
    finally:
        # Cleanup the temp thumbnail file after sending
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)
            
    return sent_msg

async def processMediaGroup(chat_message, bot, message):
    media_group_messages = await chat_message.get_media_group()
    valid_media = []
    downloaded_paths = [] 
    
    # 1. Download all items in the group (Includes photo, video, document, and audio)
    for msg in media_group_messages:
        if msg.photo or msg.video or msg.document or msg.audio:
            path = await msg.download()
            downloaded_paths.append(path)
            
            if msg.photo:
                valid_media.append(InputMediaPhoto(media=path, caption=msg.caption))
            elif msg.video:
                valid_media.append(InputMediaVideo(media=path, caption=msg.caption))
            elif msg.audio:
                valid_media.append(InputMediaAudio(media=path, caption=msg.caption))
            elif msg.document:
                valid_media.append(InputMediaDocument(media=path, caption=msg.caption))
            
    if not valid_media:
        return False

    # 2. Send the media group to the user
    try:
        await bot.send_media_group(chat_id=message.chat.id, media=valid_media)
    except Exception as e:
        LOGGER(__name__).error(f"Error sending media group to user: {e}")

    # 3. Forward the media group to all configured channels with visual tracker status
    channel_ids = await get_target_channel_ids()
    success_count = 0
    if channel_ids:
        for channel_id in channel_ids:
            try:
                await bot.send_media_group(chat_id=channel_id, media=valid_media)
                success_count += 1
                await asyncio.sleep(1) 
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await bot.send_media_group(chat_id=channel_id, media=valid_media)
                success_count += 1
            except Exception as e:
                LOGGER(__name__).error(f"Error forwarding media group to {channel_id}: {e}")
                
        if success_count > 0:
            await message.reply(f"✅ **Forwarded to {success_count} channel(s)**")

    # 4. Clean up downloaded files from disk
    for path in downloaded_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    return True
