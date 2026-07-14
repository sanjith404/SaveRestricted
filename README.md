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

```bash
pip install -r -U requirements.txt
