# Copyright (C) @ITACHI_404
# Developer : https://t.me/ITACHI_404

import os
import shutil
import psutil
import asyncio
import json
import threading
from time import time

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

# Initialize the bot client
bot = Client(
    "media_bot",
    api_id=PyroConf.API_ID,
    api_hash=PyroConf.API_HASH,
    bot_token=PyroConf.BOT_TOKEN,
    workers=10,
    parse_mode=ParseMode.MARKDOWN,
)

# Client for user session
user = Client("user_session", workers=10, session_string=PyroConf.SESSION_STRING)

RUNNING_TASKS = set()

# Configuration file path
CONFIG_FILE = "forward_config.json"

# Load target channel IDs from config file
def load_forward_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('target_channel_ids', [])
        return []
    except Exception as e:
        LOGGER(__name__).error(f"Error loading config: {e}")
        return []

# Save target channel IDs to config file
def save_forward_config(channel_ids):
    try:
        config = {'target_channel_ids': channel_ids}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        return True
    except Exception as e:
        LOGGER(__name__).error(f"Error saving config: {e}")
        return False

# Get target channel IDs
def get_target_channel_ids():
    return load_forward_config()

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
    welcome_text = (
        "👋 **Welcome to Media Downloader Bot!**\n\n"
        "I can grab photos, videos, audio, and documents from any Telegram post.\n"
        "Just send me a link (paste it directly or use `/dl <link>`),\n"
        "or reply to a message with `/dl`.\n\n"
        "ℹ️ Use `/help` to view all commands and examples.\n"
        "🔒 Make sure the user client is part of the chat.\n\n"
        "Ready? Send me a Telegram post link!"
    )

    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Update Channel", url="https://t.me/ITACHI_404")]]
    )
    await message.reply(welcome_text, reply_markup=markup, disable_web_page_preview=True)


@bot.on_message(filters.command("help") & filters.private)
async def help_command(_, message: Message):
    help_text = (
        "💡 **Media Downloader Bot Help**\n\n"
        "➤ **Download Media**\n"
        "   – Send `/dl <post_URL>` **or** just paste a Telegram post link to fetch photos, videos, audio, or documents.\n\n"
        "➤ **Batch Download**\n"
        "   – Send `/bdl start_link end_link` to grab a series of posts in one go.\n"
        "      💡 Example: `/bdl https://t.me/mychannel/100 https://t.me/mychannel/120`\n"
        "**It will download all posts from ID 100 to 120.**\n\n"
        "➤ **Forward Settings**\n"
        "   – Send `/setforward -1001234567890,-1009876543210` to set multiple target channels\n"
        "   – Send `/addforward -1005555555555` to add a channel to existing list\n"
        "   – Send `/getforward` to check current forward channels\n"
        "   – Send `/removeforward` to disable auto-forwarding\n\n"
        "➤ **Requirements**\n"
        "   – Make sure the user client is part of the chat.\n\n"
        "➤ **If the bot hangs**\n"
        "   – Send `/killall` to cancel any pending downloads.\n\n"
        "➤ **Logs**\n"
        "   – Send `/logs` to download the bot's logs file.\n\n"
        "➤ **Stats**\n"
        "   – Send `/stats` to view current status:\n\n"
        "**Example**:\n"
        "  • `/dl https://t.me/ITACHI_404/547`\n"
        "  • `https://t.me/ITACHI_404/547`"
    )
    
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Update Channel", url="https://t.me/ITACHI_404")]]
    )
    await message.reply(help_text, reply_markup=markup, disable_web_page_preview=True)


@bot.on_message(filters.command("setforward") & filters.private)
async def set_forward_command(_, message: Message):
    if len(message.command) < 2:
        await message.reply(
            "**Usage:** `/setforward -1001234567890,-1009876543210`\n\n"
            "To get your channel ID, use @username_to_id_bot\n"
            "Separate multiple channel IDs with commas"
        )
        return
    
    try:
        channel_ids_str = message.command[1]
        channel_ids = []
        
        for channel_id_str in channel_ids_str.split(','):
            channel_id = int(channel_id_str.strip())
            channel_ids.append(channel_id)
        
        if save_forward_config(channel_ids):
            channels_list = "\n".join([f"• `{cid}`" for cid in channel_ids])
            await message.reply(f"✅ **Forward channels set to:**\n{channels_list}")
        else:
            await message.reply("❌ **Failed to save channel IDs**")
    except ValueError:
        await message.reply("❌ **Invalid channel ID. Must be an integer.**")


@bot.on_message(filters.command("addforward") & filters.private)
async def add_forward_command(_, message: Message):
    if len(message.command) < 2:
        await message.reply(
            "**Usage:** `/addforward -1001234567890`\n\n"
            "To get your channel ID, use @username_to_id_bot"
        )
        return
    
    try:
        new_channel_id = int(message.command[1])
        current_channel_ids = get_target_channel_ids()
        
        if new_channel_id in current_channel_ids:
            await message.reply(f"ℹ️ **Channel `{new_channel_id}` is already in the list.**")
            return
            
        current_channel_ids.append(new_channel_id)
        
        if save_forward_config(current_channel_ids):
            channels_list = "\n".join([f"• `{cid}`" for cid in current_channel_ids])
            await message.reply(f"✅ **Channel added! Current forward channels:**\n{channels_list}")
        else:
            await message.reply("❌ **Failed to save channel IDs**")
    except ValueError:
        await message.reply("❌ **Invalid channel ID. Must be an integer.**")


@bot.on_message(filters.command("getforward") & filters.private)
async def get_forward_command(_, message: Message):
    channel_ids = get_target_channel_ids()
    if channel_ids:
        channels_list = "\n".join([f"• `{cid}`" for cid in channel_ids])
        await message.reply(f"📢 **Current forward channels:**\n{channels_list}")
    else:
        await message.reply("❌ **No forward channels set. Use `/setforward -1001234567890,-1009876543210`**")


@bot.on_message(filters.command("removeforward") & filters.private)
async def remove_forward_command(_, message: Message):
    try:
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
            await message.reply("✅ **Forward channels removed. Auto-forwarding disabled.**")
        else:
            await message.reply("ℹ️ **No forward channels were set.**")
    except Exception as e:
        await message.reply(f"❌ **Error removing forward channels:** {str(e)}")


async def forward_to_channels(bot: Client, media_path: str, media_type: str, caption: str, original_message: Message = None):
    """Forward media to all configured channels"""
    channel_ids = get_target_channel_ids()
    if not channel_ids:
        return
    
    success_count = 0
    failed_channels = []
    
    for channel_id in channel_ids:
        try:
            if media_type == "photo":
                await bot.send_photo(
                    channel_id,
                    media_path,
                    caption=caption
                )
            elif media_type == "video":
                await bot.send_video(
                    channel_id,
                    media_path,
                    caption=caption
                )
            elif media_type == "audio":
                await bot.send_audio(
                    channel_id,
                    media_path,
                    caption=caption
                )
            elif media_type == "document":
                await bot.send_document(
                    channel_id,
                    media_path,
                    caption=caption
                )
            success_count += 1
            LOGGER(__name__).info(f"Forwarded to channel: {channel_id}")
        except FloodWait as e:
            LOGGER(__name__).warning(f"Hit floodwait. Sleeping for {e.value} seconds...")
            await asyncio.sleep(e.value)
            try:
                if media_type == "photo": await bot.send_photo(channel_id, media_path, caption=caption)
                elif media_type == "video": await bot.send_video(channel_id, media_path, caption=caption)
                elif media_type == "audio": await bot.send_audio(channel_id, media_path, caption=caption)
                elif media_type == "document": await bot.send_document(channel_id, media_path, caption=caption)
                success_count += 1
            except Exception as retry_err:
                failed_channels.append(f"`{channel_id}`: {str(retry_err)}")
        except Exception as e:
            LOGGER(__name__).error(f"Error forwarding to channel {channel_id}: {e}")
            failed_channels.append(f"`{channel_id}`: {str(e)}")
    
    # Report results if we have an original message to reply to
    if original_message and (success_count > 0 or failed_channels):
        if success_count > 0 and not failed_channels:
            await original_message.reply(f"✅ **Forwarded to {success_count} channel(s)**")
        elif success_count > 0 and failed_channels:
            failed_list = "\n".join(failed_channels)
            await original_message.reply(
                f"⚠️ **Partially forwarded:**\n"
                f"✅ Success: {success_count} channel(s)\n"
                f"❌ Failed: {len(failed_channels)} channel(s)\n\n"
                f"**Failed channels:**\n{failed_list}"
            )
        else:
            failed_list = "\n".join(failed_channels)
            await original_message.reply(
                f"❌ **Failed to forward to all channels:**\n{failed_list}"
            )


async def forward_text_to_channels(bot: Client, text: str, original_message: Message = None):
    """Forward text to all configured channels"""
    channel_ids = get_target_channel_ids()
    if not channel_ids:
        return
    
    success_count = 0
    failed_channels = []
    
    for channel_id in channel_ids:
        try:
            await bot.send_message(channel_id, text)
            success_count += 1
            LOGGER(__name__).info(f"Forwarded text to channel: {channel_id}")
        except Exception as e:
            LOGGER(__name__).error(f"Error forwarding text to channel {channel_id}: {e}")
            failed_channels.append(f"`{channel_id}`: {str(e)}")
    
    # Report results if we have an original message to reply to
    if original_message and (success_count > 0 or failed_channels):
        if success_count > 0 and not failed_channels:
            await original_message.reply(f"✅ **Forwarded text to {success_count} channel(s)**")
        elif success_count > 0 and failed_channels:
            failed_list = "\n".join(failed_channels)
            await original_message.reply(
                f"⚠️ **Partially forwarded text:**\n"
                f"✅ Success: {success_count} channel(s)\n"
                f"❌ Failed: {len(failed_channels)} channel(s)\n\n"
                f"**Failed channels:**\n{failed_list}"
            )
        else:
            failed_list = "\n".join(failed_channels)
            await original_message.reply(
                f"❌ **Failed to forward text to all channels:**\n{failed_list}"
            )


async def handle_download(bot: Client, message: Message, post_url: str):
    # Cut off URL at '?' if present
    if "?" in post_url:
        post_url = post_url.split("?", 1)[0]

    try:
        chat_id, message_id = getChatMsgID(post_url)
        chat_message = await user.get_messages(chat_id=chat_id, message_ids=message_id)

        LOGGER(__name__).info(f"Downloading media from URL: {post_url}")

        if chat_message.document or chat_message.video or chat_message.audio:
            file_size = (
                chat_message.document.file_size
                if chat_message.document
                else chat_message.video.file_size
                if chat_message.video
                else chat_message.audio.file_size
            )

            if not await fileSizeLimit(
                file_size, message, "download", user.me.is_premium
            ):
                return

        parsed_caption = await get_parsed_msg(
            chat_message.caption or "", chat_message.caption_entities
        )
        parsed_text = await get_parsed_msg(
            chat_message.text or "", chat_message.entities
        )

        if chat_message.media_group_id:
            if not await processMediaGroup(chat_message, bot, message):
                await message.reply(
                    "**Could not extract any valid media from the media group.**"
                )
            return

        elif chat_message.media:
            start_time = time()
            progress_message = await message.reply("**📥 Downloading Progress...**")

            filename = get_file_name(message_id, chat_message)
            download_path = get_download_path(message.id, filename)

            media_path = await chat_message.download(
                file_name=download_path,
                progress=Leaves.progress_for_pyrogram,
                progress_args=progressArgs(
                    "📥 Downloading Progress", progress_message, start_time
                ),
            )

            LOGGER(__name__).info(f"Downloaded: {os.path.basename(media_path)}")

            if chat_message.photo:
                media_type = "photo"
            elif chat_message.video:
                media_type = "video"
            elif chat_message.audio:
                media_type = "audio"
            else:
                media_type = "document"

            await send_media(
                bot,
                message,
                media_path,
                media_type,
                parsed_caption,
                progress_message,
                start_time,
            )

            # Forward to all configured channels (only once)
            await forward_to_channels(bot, media_path, media_type, parsed_caption, message)

            cleanup_download(media_path)
            await progress_message.delete()

        elif chat_message.text or chat_message.caption:
            await message.reply(parsed_text or parsed_caption)
            
            # Forward text to all configured channels (only once)
            text_content = f"**From {post_url}:**\n\n{parsed_text or parsed_caption}"
            await forward_text_to_channels(bot, text_content, message)

        else:
            await message.reply("**No media or text found in the post URL.**")

    except (PeerIdInvalid, BadRequest, KeyError):
        await message.reply("**Make sure the user client is part of the chat.**")
    except Exception as e:
        error_message = f"**❌ {str(e)}**"
        await message.reply(error_message)
        LOGGER(__name__).error(e)


async def process_single_message(bot: Client, original_message: Message, chat_msg, url: str, loading_message: Message):
    """Process a single message from batch download"""
    media_path = None
    filename = get_file_name(chat_msg.id, chat_msg) if chat_msg else "Unknown file"
    already_forwarded = False  # Track if we've already forwarded this file
    
    for attempt in range(3):  # Retry up to 3 times
        try:
            parsed_caption = await get_parsed_msg(
                chat_msg.caption or "", chat_msg.caption_entities
            )
            parsed_text = await get_parsed_msg(
                chat_msg.text or "", chat_msg.entities
            )

            if chat_msg.media_group_id:
                # 1. Process and upload the media group to the user session
                if not await processMediaGroup(chat_msg, bot, original_message):
                    await original_message.reply(
                        f"**Could not extract any valid media from the media group at {url}.**"
                    )
                    return False
                
                # 2. Fix forwarding drop for continuous loops
                if not already_forwarded:
                    if parsed_caption or parsed_text:
                        text_content = f"**From {url}:**\n\n{parsed_text or parsed_caption}"
                        await forward_text_to_channels(bot, text_content, original_message)
                    else:
                        await forward_text_to_channels(bot, f"✅ **Forwarded media group from {url}**", original_message)
                    already_forwarded = True
                
                return True

            elif chat_msg.media:
                start_time = time()
                progress_message = await original_message.reply(f"**📥 Downloading {filename} from {url} (Attempt {attempt+1}/3)...**")

                download_path = get_download_path(original_message.id, filename)

                media_path = await chat_msg.download(
                    file_name=download_path,
                    progress=Leaves.progress_for_pyrogram,
                    progress_args=progressArgs(
                        f"📥 Downloading {filename}", progress_message, start_time
                    ),
                )

                LOGGER(__name__).info(f"Downloaded: {os.path.basename(media_path)}")

                if chat_msg.photo:
                    media_type = "photo"
                elif chat_msg.video:
                    media_type = "video"
                elif chat_msg.audio:
                    media_type = "audio"
                else:
                    media_type = "document"
                
                # Send to user
                await send_media(
                    bot,
                    original_message,
                    media_path,
                    media_type,
                    parsed_caption,
                    progress_message,
                    start_time,
                )
                
                # Forward to channels only if not already forwarded
                if not already_forwarded:
                    await forward_to_channels(bot, media_path, media_type, parsed_caption, original_message)
                    already_forwarded = True

                cleanup_download(media_path)
                await progress_message.delete()
                
                return True  # Successfully processed, exit function

            elif chat_msg.text or chat_msg.caption:
                await original_message.reply(f"**From {url}:**\n\n{parsed_text or parsed_caption}")
                
                # Forward text only if not already forwarded
                if not already_forwarded:
                    text_content = f"**From {url}:**\n\n{parsed_text or parsed_caption}"
                    await forward_text_to_channels(bot, text_content, original_message)
                    already_forwarded = True
                
                return True  # Successfully processed text, exit function
            else:
                await original_message.reply(f"**No media or text found in {url}.**")
                return False  # No content, don't retry

        except Exception as e:
            error_message = f"**❌ Attempt {attempt+1}/3 failed for {filename} from {url}: {str(e)}**"
            await original_message.reply(error_message)
            LOGGER(__name__).error(f"Attempt {attempt+1}/3 failed for {filename} from {url}: {e}")
            
            # Clean up if media_path was created
            if media_path and os.path.exists(media_path):
                cleanup_download(media_path)
            
            # Wait before retry (except on last attempt)
            if attempt < 2:
                await asyncio.sleep(2)
            else:
                # Last attempt failed, return False
                return False
    
    return False


@bot.on_message(filters.command("dl") & filters.private)
async def download_media(bot: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("**Provide a post URL after the /dl command.**")
        return

    post_url = message.command[1]
    await track_task(handle_download(bot, message, post_url))


@bot.on_message(filters.command("bdl") & filters.private)
async def download_range(bot: Client, message: Message):
    args = message.text.split()

    if len(args) != 3 or not all(arg.startswith("https://t.me/") for arg in args[1:]):
        await message.reply(
            "🚀 **Batch Download Process**\n"
            "`/bdl start_link end_link`\n\n"
            "💡 **Example:**\n"
            "`/bdl https://t.me/mychannel/100 https://t.me/mychannel/120`"
        )
        return

    try:
        start_chat, start_id = getChatMsgID(args[1])
        end_chat, end_id = getChatMsgID(args[2])
    except Exception as e:
        return await message.reply(f"**❌ Error parsing links:\n{e}**")

    if start_chat != end_chat:
        return await message.reply("**❌ Both links must be from the same channel.**")
    if start_id > end_id:
        return await message.reply("**❌ Invalid range: start ID cannot exceed end ID.**")

    try:
        await user.get_chat(start_chat)
    except Exception:
        pass

    prefix = args[1].rsplit("/", 1)[0]
    loading = await message.reply(f"📥 **Downloading posts {start_id}–{end_id}…**")

    downloaded = skipped = failed = 0

    # Process messages sequentially to maintain order
    for msg_id in range(start_id, end_id + 1):
        url = f"{prefix}/{msg_id}"
        try:
            chat_msg = await user.get_messages(chat_id=start_chat, message_ids=msg_id)
            if not chat_msg:
                skipped += 1
                continue

            has_media = bool(chat_msg.media_group_id or chat_msg.media)
            has_text = bool(chat_msg.text or chat_msg.caption)
            if not (has_media or has_text):
                skipped += 1
                continue

            # Process the message with retries
            success = await process_single_message(bot, message, chat_msg, url, loading)
            
            if success:
                downloaded += 1
            else:
                failed += 1
                LOGGER(__name__).error(f"All attempts failed for {url}")

        except Exception as e:
            failed += 1
            LOGGER(__name__).error(f"Error at {url}: {e}")
            await message.reply(f"**❌ Error processing {url}: {str(e)}**")

        # Update loading message with progress
        progress = f"📥 **Processing {msg_id-start_id+1}/{end_id-start_id+1} - Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}**"
        try:
            await loading.edit_text(progress)
        except:
            pass

        # Padding cushion for flood restrictions
        await asyncio.sleep(2)

    await loading.delete()
    await message.reply(
        "**✅ Batch Process Complete!**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📥 **Downloaded** : `{downloaded}` post(s)\n"
        f"⏭️ **Skipped** : `{skipped}` (no content)\n"
        f"❌ **Failed** : `{failed}` error(s)"
    )


@bot.on_message(filters.private & ~filters.command(["start", "help", "dl", "stats", "logs", "killall", "bdl", "setforward", "getforward", "removeforward", "addforward"]))
async def handle_any_message(bot: Client, message: Message):
    if message.text and not message.text.startswith("/"):
        await track_task(handle_download(bot, message, message.text))


@bot.on_message(filters.command("stats") & filters.private)
async def stats(_, message: Message):
    currentTime = get_readable_time(time() - PyroConf.BOT_START_TIME)
    total, used, free = shutil.disk_usage(".")
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(psutil.net_io_counters().bytes_sent)
    recv = get_readable_file_size(psutil.net_io_counters().bytes_recv)
    cpuUsage = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    process = psutil.Process(os.getpid())

    stats = (
        "**≧◉◡◉≦ Bot is Up and Running successfully.**\n\n"
        "➜ Bot Uptime: `{currentTime}`\n"
        "➜ Total Disk Space: `{total}`\n"
        "➜ Used: `{used}`\n"
        "➜ Free: `{free}`\n"
        "➜ Memory Usage: `{round(process.memory_info()[0] / 1024**2)} MiB`\n\n"
        "➜ Upload: `{sent}`\n"
        "➜ Download: `{recv}`\n\n"
        "➜ CPU: `{cpuUsage}%` | "
        "➜ RAM: `{memory}%` | "
        "➜ DISK: `{disk}%`"
    )
    await message.reply(stats)


@bot.on_message(filters.command("logs") & filters.private)
async def logs(_, message: Message):
    if os.path.exists("logs.txt"):
        await message.reply_document(document="logs.txt", caption="**Logs**")
    else:
        await message.reply("**Not exists**")


@bot.on_message(filters.command("killall") & filters.private)
async def cancel_all_tasks(_, message: Message):
    cancelled = 0
    current_tasks = list(RUNNING_TASKS)
    
    if not current_tasks:
        await message.reply("**No running tasks to cancel.**")
        return
    
    for task in current_tasks:
        if not task.done():
            task.cancel()
            cancelled += 1
            try:
                await asyncio.sleep(0.1)  # Small delay to allow cancellation
            except:
                pass
    
    # Clear the set after cancellation
    RUNNING_TASKS.clear()
    
    await message.reply(f"**Cancelled {cancelled} running task(s).**")


def start_health_server():
    """Starts a minimal web server for Render health checks."""
    from aiohttp import web
    async def health(request):
        return web.Response(text="OK", status=200)
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    
    async def run_server():
        await runner.setup()
        port = int(os.environ.get("PORT", 8000))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        LOGGER(__name__).info(f"Health server running on port {port}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_server())
    loop.run_forever()


if __name__ == "__main__":
    try:
        # Start the health server in a background thread
        threading.Thread(target=start_health_server, daemon=True).start()
        
        LOGGER(__name__).info("Bot Started!")
        user.start()
        bot.run()
    except KeyboardInterrupt:
        pass
    except Exception as err:
        LOGGER(__name__).error(err)
    finally:
        LOGGER(__name__).info("Bot Stopped")
