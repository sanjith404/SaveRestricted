# Copyright (C) @ITACHI_404
# Developer: https://t.me/ITACHI_404

import os
import shutil
import psutil
import asyncio
import threading
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

# Initialize the bot client as SaveRestricted_Bot
bot = Client(
    "SaveRestricted_Bot",
    api_id=PyroConf.API_ID,
    api_hash=PyroConf.API_HASH,
    bot_token=PyroConf.BOT_TOKEN,
    workers=10,
    parse_mode=ParseMode.MARKDOWN,
)

# Client for user session
user = Client("user_session", workers=10, session_string=PyroConf.SESSION_STRING)

RUNNING_TASKS = set()
CONFIG_FILE = "forward_config.json"

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
    if not os.path.exists("users.txt"):
        open("users.txt", "w").close()
    with open("users.txt", "a+") as f:
        f.seek(0)
        if str(message.from_user.id) not in f.read():
            f.write(f"{message.from_user.id}\n")

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
        "   – Send `/setforward <ids>` to set target channels (comma-separated).\n"
        "   – Send `/addforward <id>` to add a channel.\n"
        "   – Send `/getforward` to check current forward channels.\n"
        "   – Send `/removeforward` to disable auto-forwarding.\n\n"
        "➤ **Admin / Broadcaster**\n"
        "   – Reply to a message with `/broadcast` to send it to all users.\n\n"
        "➤ **Logs & Stats**\n"
        "   – Send `/logs` to download the bot's logs file.\n"
        "   – Send `/stats` to view current status:\n\n"
        "**Example**:\n"
        "  • `/dl https://telegram.me/ITACHI_404/547`\n"
        "  • `https://telegram.me/ITACHI_404/547`"
    )
    
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Update Channel", url="https://t.me/ITACHI_404")]]
    )
    await message.reply(help_text, reply_markup=markup, disable_web_page_preview=True)

@bot.on_message(filters.command("rdl") & filters.private)
async def rdl_command(_, message: Message):
    if len(message.command) < 3: return await message.reply("Usage: `/rdl <link> <new_name>`")
    message.custom_name = message.command[2]
    await track_task(handle_download(bot, message, message.command[1]))

@bot.on_message(filters.command("setthumb") & filters.private)
async def set_thumb_command(_, message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply("❌ **Please reply to an image to set it as custom thumbnail.**")
    os.makedirs("thumb", exist_ok=True)
    await message.reply_to_message.download(file_name=f"thumb/{message.from_user.id}.jpg")
    await message.reply("✅ **Custom thumbnail saved successfully!**")

@bot.on_message(filters.command("thumb") & filters.private)
async def get_thumb_command(_, message: Message):
    path = f"thumb/{message.from_user.id}.jpg"
    if os.path.exists(path):
        await message.reply_photo(path, caption="📷 **Your current custom thumbnail.**")
    else:
        await message.reply("❌ **You haven't set a custom thumbnail yet.**")

@bot.on_message(filters.command("delthumb") & filters.private)
async def del_thumb_command(_, message: Message):
    path = f"thumb/{message.from_user.id}.jpg"
    if os.path.exists(path):
        os.remove(path)
        await message.reply("✅ **Custom thumbnail deleted successfully!**")
    else:
        await message.reply("❌ **No custom thumbnail found to delete.**")

@bot.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(_, message: Message):
    if not message.reply_to_message:
        return await message.reply("❌ **Reply to a message to broadcast it.**")
    if not os.path.exists("users.txt"):
        return await message.reply("❌ **No user logs found.**")
    with open("users.txt", "r") as f:
        users = f.read().splitlines()
    sent = 0
    for uid in users:
        try:
            await message.reply_to_message.copy(int(uid))
            sent += 1
        except:
            continue
    await message.reply(f"✅ **Broadcast complete! Sent to {sent} users.**")

async def handle_download(bot: Client, message: Message, post_url: str):
    if "?" in post_url: post_url = post_url.split("?", 1)[0]
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
            await send_media(bot, message, media_path, media_type, await get_parsed_msg(chat_message.caption or "", chat_message.caption_entities), progress_message, start_time)
            cleanup_download(media_path)
            await progress_message.delete()
        elif chat_message.text or chat_message.caption:
            await message.reply(await get_parsed_msg(chat_message.text or chat_message.caption or "", chat_message.entities or chat_message.caption_entities))
    except (PeerIdInvalid, BadRequest, KeyError):
        await message.reply("**Make sure the user client is part of the chat.**")
    except Exception as e:
        await message.reply(f"**❌ {str(e)}**")

@bot.on_message(filters.command("dl") & filters.private)
async def download_media(bot: Client, message: Message):
    if len(message.command) < 2: return await message.reply("**Provide a post URL after the /dl command.**")
    await track_task(handle_download(bot, message, message.command[1]))

@bot.on_message(filters.command("bdl") & filters.private)
async def download_range(bot: Client, message: Message):
    args = message.text.split()
    if len(args) != 3 or not all("telegram.me/" in arg or "t.me/" in arg for arg in args[1:]):
        return await message.reply("🚀 **Batch Download**\n`/bdl start_link end_link`")
    try:
        start_chat, start_id = getChatMsgID(args[1])
        end_chat, end_id = getChatMsgID(args[2])
    except Exception as e: return await message.reply(f"**❌ Error parsing links:\n{e}**")
    
    prefix = args[1].rsplit("/", 1)[0]
    loading = await message.reply(f"📥 **Downloading posts {start_id}–{end_id}…**")
    downloaded = skipped = failed = 0
    for msg_id in range(start_id, end_id + 1):
        url = f"{prefix}/{msg_id}"
        try:
            chat_msg = await user.get_messages(chat_id=start_chat, message_ids=msg_id)
            if not chat_msg or not (chat_msg.media or chat_msg.text or chat_msg.caption):
                skipped += 1
                continue
            task = track_task(handle_download(bot, message, url))
            await task
            downloaded += 1
        except: failed += 1
        await asyncio.sleep(3)
    await loading.delete()
    await message.reply(
        "**✅ Batch Process Complete!**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📥 **Downloaded** : `{downloaded}` post(s)\n"
        f"⏭️ **Skipped**    : `{skipped}` (no content)\n"
        f"❌ **Failed**     : `{failed}` error(s)"
    )

@bot.on_message(filters.private & ~filters.command(["start", "help", "dl", "stats", "logs", "killall", "bdl", "rdl", "setthumb", "thumb", "delthumb", "broadcast"]))
async def handle_any_message(bot: Client, message: Message):
    if message.text and ("telegram.me/" in message.text or "t.me/" in message.text):
        await track_task(handle_download(bot, message, message.text))

@bot.on_message(filters.command("stats") & filters.private)
async def stats(_, message: Message):
    currentTime = get_readable_time(time() - PyroConf.BOT_START_TIME)
    total, used, free = shutil.disk_usage(".")
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
    if os.path.exists("logs.txt"): await message.reply_document(document="logs.txt", caption="**Logs**")
    else: await message.reply("**Not exists**")

@bot.on_message(filters.command("killall") & filters.private)
async def cancel_all_tasks(_, message: Message):
    cancelled = 0
    for task in list(RUNNING_TASKS):
        if not task.done():
            task.cancel()
            cancelled += 1
    await message.reply(f"**Cancelled {cancelled} running task(s).**")

def start_health_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(runner.setup())
    loop.run_until_complete(web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8000))).start())
    loop.run_forever()

if __name__ == "__main__":
    try:
        os.makedirs("thumb", exist_ok=True)
        threading.Thread(target=start_health_server, daemon=True).start()
        LOGGER(__name__).info("Bot Started!")
        user.start()
        bot.run()
    except Exception as err: LOGGER(__name__).error(err)
