# 🚀 ZeroDev Social Media Downloader Bot

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Framework](https://img.shields.io/badge/Framework-Pyrogram-orange?style=for-the-badge&logo=telegram)
![Database](https://img.shields.io/badge/Database-MongoDB-green?style=for-the-badge&logo=mongodb)
![Build](https://img.shields.io/badge/Build-v2.0_Ultra-gold?style=for-the-badge)
![Hosting](https://img.shields.io/badge/Deploy-Koyeb-black?style=for-the-badge&logo=koyeb)

A premium, high-speed Telegram bot designed to download media from **TikTok, Instagram, YouTube, Facebook, and Pinterest** with ease. Featuring a sleek UI, auto-detect capabilities, and a robust admin dashboard.

---

## 🔥 Key Features

* 📥 **Multi-Platform Support:** TikTok (No Watermark), Instagram Reels, YouTube, and more.
* ⚡ **High Performance:** Fully asynchronous logic handling 500+ concurrent users.
* 🛡️ **Force Subscribe:** Restrict access until users join your specified channels.
* 💎 **Premium UI:** Animated stickers, random welcome images, and clean inline buttons.
* 📊 **Admin Suite:** Real-time stats, broadcast system, and remote log access.
* 🐳 **Docker Ready:** Optimized for containerized deployment.

---

## 🛠 Commands

### User Commands
| Command | Action |
| :--- | :--- |
| `/start` | Start the bot and get the welcome menu |
| `/info` | View your Telegram profile & DC details |
| `Link Paste` | Just send any URL to start downloading |

### Admin Commands
| Command | Action |
| :--- | :--- |
| `/stats` | View total user database count |
| `/broadcast` | Send a message to all users (Reply to a message) |
| `/logs` | Get the current session logs |
| `/restart` | Restart the bot remotely |

---

## 🚀 Deployment Guide

### 1. Requirements
* Python 3.10 or higher
* MongoDB URI
* Telegram API ID & Hash (from [my.telegram.org](https://my.telegram.org))

### 2. Environment Variables
Set these variables in your hosting panel (Koyeb/Heroku) or a `.env` file:

```env
API_ID=123456
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
MONGO_URL=your_mongodb_url
ADMIN_ID=your_telegram_id
PORT=8080
