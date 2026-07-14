<h1 align="center">Restricted Content Downloader Telegram Bot</h1>

<p align="center">
  <a href="https://github.com/sanjith404/SaveRestricted/stargazers"><img src="https://img.shields.io/github/stars/sanjith404/SaveRestricted?color=blue&style=flat" alt="GitHub Repo stars"></a>
  <a href="https://github.com/sanjith404/SaveRestricted/issues"><img src="https://img.shields.io/github/issues/sanjith404/SaveRestricted" alt="GitHub issues"></a>
  <a href="https://github.com/sanjith404/SaveRestricted/pulls"><img src="https://img.shields.io/github/issues-pr/sanjith404/SaveRestricted" alt="GitHub pull requests"></a>
  <a href="https://github.com/sanjith404/SaveRestricted/graphs/contributors"><img src="https://img.shields.io/github/contributors/sanjith404/SaveRestricted?style=flat" alt="GitHub contributors"></a>
  <a href="https://github.com/sanjith404/SaveRestricted/network/members"><img src="https://img.shields.io/github/forks/sanjith404/SaveRestricted?style=flat" alt="GitHub forks"></a>
</p>

<p align="center">
  <em>Restricted Content Downloader: An advanced Telegram bot script to securely download restricted content such as photos, videos, audio files, or documents from Telegram private chats or channels. This updated version features enhanced media group processing, custom logging, and asynchronous file handling.</em>
</p>
<hr>

## 🚀 Features

- 📥 **Download Media:** Seamlessly fetch photos, videos, audio, and documents.
- ✅ **Advanced Media Groups:** Fully supports downloading from both single media posts and clustered media groups without dropping files.
- 🔄 **Real-Time Tracking:** Interactive progress bar showing live downloading progress.
- ✍️ **Text Extraction:** Copy text messages or captions directly from Telegram posts.
- ⚡ **Optimized Cleanup:** Uses `aiofiles` and asynchronous logic to keep cloud storage clean and efficient.

## 📋 Requirements

Before you begin, ensure you have met the following requirements:

- **Python 3.11** (Highly Recommended)
- Required Libraries: `pyrofork`, `pyleaves`, `tgcrypto`, `aiohttp`, `aiofiles`
- A Telegram bot token (Grab one from [@BotFather](https://t.me/BotFather)).
- **API ID and Hash:** Create an application on [my.telegram.org](https://my.telegram.org) to get these.
- **Session String:** To get your `SESSION_STRING`, open [@ITACHI_404](https://t.me/ITACHI_404) on Telegram, send the `/pyro` command, and follow the instructions.

## 🛠️ Installation

To install all necessary dependencies, run the following command:

Note: If you previously installed pyrogram, you must uninstall it before installing pyrofork to prevent library conflicts.```bash
pip install -r -U requirements.txt

## ⚙️ Configuration

For local hosting, create a config.env file. For cloud deployment (like Kuberns), inject these directly into your Environment Variables panel:

- API_ID: Your API ID from my.telegram.org.

- API_HASH: Your API Hash from my.telegram.org.

- SESSION_STRING: The session string generated via @ITACHI_404.

- BOT_TOKEN: The token you obtained from @BotFather.

```bash
git clone [https://github.com/sanjith404/SaveRestricted](https://github.com/sanjith404/SaveRestricted)
cd SaveRestricted
python main.py
```
## Deploy Using Docker Compose

Make sure you have Docker and Docker Compose installed. The bot will run in a containerized environment with all dependencies automatically managed.

```bash
git clone [https://github.com/sanjith404/SaveRestricted](https://github.com/sanjith404/SaveRestricted)
cd SaveRestricted
docker compose up --build --remove-orphans
```

To stop the Docker container, run: docker compose down

## 📖 Usage

Core Commands

- **`/start – Welcomes you and initializes the bot interface.
- **`/help – Shows detailed instructions and formatting examples.
- **`/dl <post_URL> (or simply paste a link) – Fetch media or documents from that specific post.
- **`/bdl <start_link> <end_link> – Batch-download a range of posts in one go.
- 💡 Example: /bdl https://t.me/mychannel/100 https://t.me/mychannel/120
- **`/killall – Force-cancel any pending or stuck downloads.
- **`/logs – Retrieve the bot’s custom formatted log file for debugging.
- **`/stats – View real-time system status (uptime, disk, memory, network, CPU).
- - **`/setforward <channel_ids>`** – Set one or multiple target channels to automatically forward downloaded media to (separate multiple IDs with commas).
- **`/addforward <channel_id>`** – Add a new channel to your existing forwarding list without overwriting the others.
- **`/getforward`** – View the current list of channels your bot is forwarding files to.
- **`/removeforward`** – Completely disable auto-forwarding and wipe the current routing configuration.

⚠️ Important: Make sure that the account tied to your SESSION_STRING is actually a member of the source chat or channel before attempting to download restricted content!

## 👨‍💻 Author & Credits

- Developer: Sanjith404 | Telegram: @ITACHI_404

- Base Template: Credited to @TheSmartBisnu
