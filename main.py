# Copyright (C) @ITACHI_404
# Developer: https://t.me/ITACHI_404

import os
import shutil
import psutil
import asyncio
import json
from time import time
from aiohttp import web

from pyleaves import Leaves
from pyrogram.enums import ParseMode
from pyrogram import Client, filters
from pyrogram.errors import PeerIdInvalid, BadRequest, FloodWait
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from helpers.utils import (
    processMediaGroup,
    progressArgs,
    send_media
)

from helpers.files import (
    get_download_path,
    fileSizeLimit,
    get_readable_file_size,
    get_readable_time,
    cleanup_download
)

from helpers.msg import (
    getChatMsgID,
    get_file_name,
    get_parsed_msg
)

from config import PyroConf
from logger import LOGGER
from database import (
    add_user, get_all_users, 
    set_thumb, get_thumb, del_thumb,
    get_target_channel_ids, save_target_channel_ids, remove_target_channel_ids
)

# Initialize the bot client
bot = Client(
    "SaveRestricted_Bot",
    api_id=PyroConf.API_ID,
    api_hash=PyroConf.API_HASH,
    bot_token=PyroConf.BOT_TOKEN,
    workers=40,
    parse_mode=ParseMode.MARKDOWN,
)

# Client for user session
user = Client("user_session", workers=40, session_string=PyroConf.SESSION_STRING)

RUNNING_TASKS = set()

def track_task(coro):
    task = asyncio.create_task(coro)
    RUNNING_TASKS.add(task)
    
    def remove_task():
        try:
            RUNNING_TASKS.discard(task)
        except:
            pass
    
    task.add_done_callback(lambda _: remove_task())
    return task


@bot.on_message(filters.command("start") & filters.private)
async def start(_, message: Message):
    await add_user(message.from_user.id)

    welcome_text = (
        "👋 **Welcome to SaveRestricted Bot!**\n\n"
        "I can grab photos, videos, audio, and documents from any Telegram post.\n"
        "Just send me a link (paste it directly or use `/dl <link>`),\n"
        "or reply to a message with `/dl`.\n\n"
        "ℹ️ Use `/help` to view all commands and examples.\n"
        "🔒 Make sure the user client is part of the chat.\n\n"
        "Ready? Send me a Telegram post link!"
    )
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("Update Channel", url="https://t.me/ITACHI_404")]])
    await message.reply(welcome_text, reply_markup=markup, disable_web_page_preview=True)


@bot.on_message(filters.command("help") & filters.private)
async def help_command(_, message: Message):
    help_text = (
        "💡 **SaveRestricted Bot Help**\n\n"
        "➤ **Download Media**\n"
        "   – Send `/dl <post_URL>` **or** just paste a Telegram post link to fetch photos, videos, audio, or documents.\n"
        "   – Send `/rdl <post_URL> <new_name>` to download and rename individual files.\n\n"
        "➤ **Batch Download**\n"
        "   – Send `/bdl start_link end_link` to grab a series of posts in one go.\n"
        "      💡 Example: `/bdl https://t.me/mychannel/100 https://t.me/mychannel/120`\n"
        "**It will download all posts from ID 100 to 120.**\n\n"
        "➤ **Thumbnail Management**\n"
        "   – Reply to an image with `/setthumb` to set it as a custom thumbnail.\n"
        "   – Send `/thumb` to see your current custom thumbnail.\n"
        "   – Send `/delthumb` to remove your custom thumbnail.\n\n"
        "➤ **Forward Settings**\n"
        "   – Send `/setforward -1001234,-1009876` to set target channels (comma-separated).\n"
        "   – Send `/addforward -1005555` to add a channel.\n"
        "   – Send `/getforward` to check current forward channels.\n"
        "   – Send `/removeforward` to disable auto-forwarding.\n\n"
        "➤ **Admin / Broadcaster**\n"
        "   – Reply to a message with `/broadcast` to send it to all users.\n"
        "   – Send `/killall` to cancel pending downloads.\n\n"
        "➤ **Logs & Stats**\n"
        "   – Send `/logs` to download the bot's logs file.\n"
        "   – Send `/stats` to view current status:\n\n"
        "**Example**:\n"
        "  • `/dl https://telegram.me/ITACHI_404/547`\n"
        "  • `https://telegram.me/ITACHI_404/547`"
    )
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("Update Channel", url="https://t.me/ITACHI_404")]])
    await message.reply(help_text, reply_markup=markup, disable_web_page_preview=True)


@bot.on_message(filters.command("setforward") & filters.private)
async def set_forward_command(_, message: Message):
    if len(message.command) < 2:
        return await message.reply("**Usage:** `/setforward -1001234567890,-1009876543210`\nSeparate multiple channel IDs with commas.")
    try:
        channel_ids = [int(cid.strip()) for cid in message.command[1].split(',')]
        if await save_target_channel_ids(channel_ids):
            channels_list = "\n".join([f"• `{cid}`" for cid in channel_ids])
            await message.reply(f"✅ **Forward channels set to:**\n{channels_list}")
        else:
            await message.reply("❌ **Failed to save channel IDs to database.**")
    except ValueError:
        await message.reply("❌ **Invalid channel ID. Must be an integer.**")


@bot.on_message(filters.command("addforward") & filters.private)
async def add_forward_command(_, message: Message):
    if len(message.command) < 2:
        return await message.reply("**Usage:** `/addforward -1001234567890`")
    try:
        new_channel_id = int(message.command[1])
        current_channel_ids = await get_target_channel_ids()
        
        if new_channel_id in current_channel_ids:
            return await message.reply(f"ℹ️ **Channel `{new_channel_id}` is already in the list.**")
            
        current_channel_ids.append(new_channel_id)
        if await save_target_channel_ids(current_channel_ids):
            channels_list = "\n".join([f"• `{cid}`" for cid in current_channel_ids])
            await message.reply(f"✅ **Channel added! Current forward channels:**\n{channels_list}")
        else:
            await message.reply("❌ **Failed to save to database.**")
    except ValueError:
        await message.reply("❌ **Invalid channel ID. Must be an integer.**")


@bot.on_message(filters.command("getforward") & filters.private)
async def get_forward_command(_, message: Message):
    channel_ids = await get_target_channel_ids()
    if channel_ids:
        channels_list = "\n".join([f"• `{cid}`" for cid in channel_ids])
        await message.reply(f"📢 **Current forward channels:**\n{channels_list}")
    else:
        await message.reply("❌ **No forward channels set.**")


@bot.on_message(filters.command("removeforward") & filters.private)
async def remove_forward_command(_, message: Message):
    if await remove_target_channel_ids():
        await message.reply("✅ **Forward channels removed. Auto-forwarding disabled.**")
    else:
        await message.reply("❌ **Error removing forward channels or none were set.**")


@bot.on_message(filters.command("rdl") & filters.private)
async def rdl_command(_, message: Message):
    if len(message.command) < 3: 
        return await message.reply("Usage: `/rdl <link> <new_name>`")
    message.custom_name = message.command[2]
    await track_task(handle_download(bot, message, message.command[1]))


@bot.on_message(filters.command("setthumb") & filters.private)
async def set_thumb_command(_, message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply("❌ **Please reply to an image to set it as a custom thumbnail.**")
    
    file_id = message.reply_to_message.photo.file_id
    await set_thumb(message.from_user.id, file_id)
    await message.reply("✅ **Custom thumbnail saved successfully to cloud database!**")


@bot.on_message(filters.command("thumb") & filters.private)
async def get_thumb_command(_, message: Message):
    file_id = await get_thumb(message.from_user.id)
    if file_id:
        await message.reply_photo(file_id, caption="📷 **Your current custom thumbnail.**")
    else:
        await message.reply("❌ **You haven't set a custom thumbnail yet.**")


@bot.on_message(filters.command("delthumb") & filters.private)
async def del_thumb_command(_, message: Message):
    if await del_thumb(message.from_user.id):
        await message.reply("✅ **Custom thumbnail deleted successfully!**")
    else:
        await message.reply("❌ **No custom thumbnail found to delete.**")


@bot.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(_, message: Message):
    if not message.reply_to_message:
        return await message.reply("❌ **Reply to a message to broadcast it.**")
    
    users = await get_all_users()
    if not users:
        return await message.reply("❌ **No user logs found in the database.**")
        
    sent = 0
    for uid in users:
        try:
            await message.reply_to_message.copy(int(uid))
            sent += 1
            await asyncio.sleep(0.3)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await message.reply_to_message.copy(int(uid))
            sent += 1
        except:
            continue
    await message.reply(f"✅ **Broadcast complete! Sent to {sent} users.**")


async def forward_to_channels(bot: Client, message: Message, media_path: str, media_type: str, caption: str):
    channel_ids = await get_target_channel_ids()
    if not channel_ids:
        return
    
    filename = os.path.basename(media_path)
    success_count = 0
    
    for channel_id in channel_ids:
        try:
            # Attempt to send the media
            if media_type == "photo":
                await bot.send_photo(channel_id, media_path, caption=caption)
            elif media_type == "video":
                await bot.send_video(channel_id, media_path, caption=caption)
            elif media_type == "audio":
                await bot.send_audio(channel_id, media_path, caption=caption)
            elif media_type == "document":
                await bot.send_document(channel_id, media_path, caption=caption)
            
            success_count += 1
            await asyncio.sleep(0.5)

        except FloodWait as e:
            # Handle FloodWait specifically
            await asyncio.sleep(e.value)
            try:
                if media_type == "photo": await bot.send_photo(channel_id, media_path, caption=caption)
                elif media_type == "video": await bot.send_video(channel_id, media_path, caption=caption)
                elif media_type == "audio": await bot.send_audio(channel_id, media_path, caption=caption)
                elif media_type == "document": await bot.send_document(channel_id, media_path, caption=caption)
                success_count += 1
            except Exception as e:
                LOGGER(__name__).error(f"Retry failed for {channel_id}: {e}")

        except Exception as e:
            # Handle all other errors
            LOGGER(__name__).error(f"Error forwarding to {channel_id}: {e}")
            
    if success_count > 0:
        await message.reply(f"✅ **{filename} forwarded to {success_count} channel(s)**")

async def forward_text_to_channels(bot: Client, message: Message, text: str):
    channel_ids = await get_target_channel_ids()
    if not channel_ids:
        return
        
    success_count = 0
    for channel_id in channel_ids:
        try:
            await bot.send_message(channel_id, text)
            success_count += 1
            await asyncio.sleep(0.5)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            LOGGER(__name__).error(f"Error forwarding text to {channel_id}: {e}")
            
    if success_count > 0:
        # Message for forwarded text content
        await message.reply(f"✅ **Text message forwarded to {success_count} channel(s)**")


async def handle_download(bot: Client, message: Message, post_url: str):
    if "?" in post_url: 
        post_url = post_url.split("?", 1)[0]
    
    media_path = None
    progress_message = None
    
    try:
        chat_id, message_id = getChatMsgID(post_url)
        chat_message = await user.get_messages(chat_id=chat_id, message_ids=message_id)
        LOGGER(__name__).info(f"Downloading media from URL: {post_url}")
        
        if chat_message.media_group_id:
            await processMediaGroup(chat_message, bot, message)
            return
            
        if chat_message.media:
            start_time = time()
            progress_message = await message.reply("**📥 Downloading Progress...**")
            filename = getattr(message, "custom_name", get_file_name(message_id, chat_message))
            download_path = get_download_path(message.id, filename)
            
            media_path = await chat_message.download(
                file_name=download_path,
                progress=Leaves.progress_for_pyrogram,
                progress_args=progressArgs("📥 Downloading Progress", progress_message, start_time),
            )
            
            media_type = "photo" if chat_message.photo else "video" if chat_message.video else "audio" if chat_message.audio else "document"
            parsed_caption = await get_parsed_msg(chat_message.caption or "", chat_message.caption_entities)
            
            # Send to the user who requested it
            await send_media(
                bot, message, media_path, media_type, 
                parsed_caption, 
                progress_message, start_time
            )
            
            # Forward to configured channels with status reply tracking
            await forward_to_channels(bot, message, media_path, media_type, parsed_caption)
            
        elif chat_message.text or chat_message.caption:
            parsed_text = await get_parsed_msg(chat_message.text or chat_message.caption or "", chat_message.entities or chat_message.caption_entities)
            await message.reply(parsed_text)
            
            text_content = f"**From {post_url}:**\n\n{parsed_text}"
            await forward_text_to_channels(bot, message, text_content)
            
    except FloodWait as e:
        await message.reply(f"⚠️ **Telegram limits reached. Waiting {e.value} seconds...**")
        await asyncio.sleep(e.value)
    except (PeerIdInvalid, BadRequest, KeyError):
        await message.reply("**Make sure the user client is part of the chat.**")
    except Exception as e:
        await message.reply(f"**❌ {str(e)}**")
    finally:
        if media_path:
            cleanup_download(media_path)
        if progress_message:
            try:
                await progress_message.delete()
            except:
                pass


@bot.on_message(filters.command("dl") & filters.private)
async def download_media(bot: Client, message: Message):
    if len(message.command) < 2: 
        return await message.reply("**Provide a post URL after the /dl command.**")
    await track_task(handle_download(bot, message, message.command[1]))


@bot.on_message(filters.command("bdl") & filters.private)
async def download_range(bot: Client, message: Message):
    args = message.text.split()
    if len(args) != 3 or not all("telegram.me/" in arg or "t.me/" in arg for arg in args[1:]):
        return await message.reply("🚀 **Batch Download**\n`/bdl start_link end_link`")
        
    try:
        start_chat, start_id = getChatMsgID(args[1])
        end_chat, end_id = getChatMsgID(args[2])
    except Exception as e: 
        return await message.reply(f"**❌ Error parsing links:\n{e}**")
    
    prefix = args[1].rsplit("/", 1)[0]
    loading = await message.reply(f"📥 **Downloading posts {start_id}–{end_id}…**")
    
    downloaded = skipped = failed = 0
    current_task = asyncio.current_task()
    processed_groups = set() 
    
    for msg_id in range(start_id, end_id + 1):
        if current_task.cancelled():
            break
            
        url = f"{prefix}/{msg_id}"
        try:
            chat_msg = await user.get_messages(chat_id=start_chat, message_ids=msg_id)
            if not chat_msg or not (chat_msg.media or chat_msg.text or chat_msg.caption):
                skipped += 1
                continue
            
            if chat_msg.media_group_id:
                if chat_msg.media_group_id in processed_groups:
                    skipped += 1
                    continue
                processed_groups.add(chat_msg.media_group_id)
                
            await handle_download(bot, message, url)
            downloaded += 1
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await handle_download(bot, message, url)
            downloaded += 1
        except: 
            failed += 1
            
        await asyncio.sleep(2)
        try:
            progress = f"📥 **Processing {msg_id-start_id+1}/{end_id-start_id+1}\nDownloaded: {downloaded} | Skipped: {skipped} | Failed: {failed}**"
            await loading.edit_text(progress)
        except:
            pass
            
    await loading.delete()
    await message.reply(
        "**✅ Batch Process Complete!**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📥 **Downloaded** : `{downloaded}` post(s)\n"
        f"⏭️ **Skipped**    : `{skipped}` (already processed or empty)\n"
        f"❌ **Failed**     : `{failed}` error(s)"
    )


@bot.on_message(filters.private & ~filters.command(["start", "help", "dl", "stats", "logs", "killall", "bdl", "rdl", "setthumb", "thumb", "delthumb", "broadcast", "setforward", "addforward", "getforward", "removeforward"]))
async def handle_any_message(bot: Client, message: Message):
    if message.text and ("telegram.me/" in message.text or "t.me/" in message.text):
        await track_task(handle_download(bot, message, message.text))


@bot.on_message(filters.command("stats") & filters.private)
async def stats(_, message: Message):
    currentTime = get_readable_time(time() - PyroConf.BOT_START_TIME)
    process = psutil.Process(os.getpid())
    stats_msg = (
        "**≧◉◡◉≦ Bot is Up and Running successfully.**\n\n"
        f"**➜ Bot Uptime:** `{currentTime}`\n"
        f"**➜ Memory Usage:** `{round(process.memory_info()[0] / 1024**2)} MiB`\n"
        f"**➜ CPU:** `{psutil.cpu_percent(interval=0.5)}%`"
    )
    await message.reply(stats_msg)


@bot.on_message(filters.command("logs") & filters.private)
async def logs(_, message: Message):
    if os.path.exists("logs.txt"): 
        await message.reply_document(document="logs.txt", caption="**Logs**")
    else: 
        await message.reply("**Not exists**")


@bot.on_message(filters.command("killall") & filters.private)
async def cancel_all_tasks(_, message: Message):
    cancelled = 0
    for task in list(RUNNING_TASKS):
        if not task.done():
            task.cancel()
            cancelled += 1
    await message.reply(f"**Cancelled {cancelled} running task(s).**")


async def start_health_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    LOGGER(__name__).info(f"Health check web server active on port {port}")

if __name__ == "__main__":
    try:
        LOGGER(__name__).info("Starting SaveRestricted Bot initialization...")
        loop = asyncio.get_event_loop()
        loop.create_task(start_health_server())
        user.start()
        bot.run()
    except Exception as err: 
        LOGGER(__name__).error(err)
