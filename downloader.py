import yt_dlp
import os
import asyncio
import glob
import subprocess
import shutil
import time
import re
import aiohttp
import json

# ─────────────────────────────────────────────────────────────────────────────
# COOKIES & AUTH SETUP
# ─────────────────────────────────────────────────────────────────────────────

def _write_cookie_file(env_var: str, filename: str) -> str | None:
    content = os.environ.get(env_var, '').strip()
    if not content:
        # Check if the file already exists manually in the cookies/ folder
        path = f'cookies/{filename}'
        return path if os.path.exists(path) else None
        
    os.makedirs('cookies', exist_ok=True)
    path = f'cookies/{filename}'
    with open(path, 'w') as f:
        if not content.startswith('# Netscape'):
            f.write('# Netscape HTTP Cookie File\n')
        f.write(content)
    return path

# Updated Cookie Path Logic
_YT_COOKIE_FILE  = _write_cookie_file('YOUTUBE_COOKIES',   'youtube.txt')
_IG_COOKIE_FILE  = _write_cookie_file('INSTAGRAM_COOKIES', 'instagram.txt')
_FB_COOKIE_FILE  = _write_cookie_file('FACEBOOK_COOKIES',  'facebook.txt')
_TT_COOKIE_FILE  = _write_cookie_file('TIKTOK_COOKIES',    'tiktok.txt')

# ─────────────────────────────────────────────────────────────────────────────
# TIKTOK PHOTO EXTRACTOR (Hardened)
# ─────────────────────────────────────────────────────────────────────────────

async def download_tiktok_photo(url: str) -> tuple:
    """Downloads all images from a TikTok slideshow post."""
    os.makedirs('downloads', exist_ok=True)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, allow_redirects=True) as resp:
            html = await resp.text()

    image_urls = []
    # Attempt to find the JSON data in the script tag
    data_match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"([^>]+)>(.*?)</script>', html)
    if data_match:
        try:
            raw_json = data_match.group(2)
            data = json.loads(raw_json)
            # Traverse the nested TikTok JSON structure
            item_struct = data.get('__DEFAULT_SCOPE__', {}).get('webapp.video-detail', {}).get('itemInfo', {}).get('itemStruct', {})
            images = item_struct.get('imagePost', {}).get('images', [])
            for img in images:
                # Use the highest quality thumbnail or image URL available
                u = img.get('imageURL', {}).get('urlList', [None])[0]
                if u: image_urls.append(u)
        except Exception as e:
            print(f"JSON Parse Error: {e}")

    # Fallback to Regex if JSON parsing fails
    if not image_urls:
        image_urls = re.findall(r'https://p[0-9]+(?:-sign)?\.tiktokcdn\.com/[^\s"\'\\]+\.(?:jpg|jpeg|png|webp)', html)
        image_urls = list(dict.fromkeys(image_urls)) # Deduplicate

    if not image_urls:
        raise ValueError("Could not find any images in this TikTok post. It might be private or a standard video.")

    downloaded = []
    async with aiohttp.ClientSession(headers=headers) as session:
        for i, img_url in enumerate(image_urls):
            path = f"downloads/tiktok_img_{int(time.time())}_{i}.jpg"
            async with session.get(img_url) as img_resp:
                if img_resp.status == 200:
                    with open(path, 'wb') as f:
                        f.write(await img_resp.read())
                    downloaded.append(os.path.abspath(path))

    caption = f"<b>🎵 TikTok</b> | 🖼 Slideshow ({len(downloaded)} images)\n\n<i>⚡ @FullSaveMe_z_Bot</i>"
    return (downloaded if len(downloaded) > 1 else downloaded[0]), caption

# ─────────────────────────────────────────────────────────────────────────────
# CORE DOWNLOAD LOGIC
# ─────────────────────────────────────────────────────────────────────────────

async def download_media(url: str, mode: str = 'video', quality: str = 'best') -> tuple:
    os.makedirs('downloads', exist_ok=True)

    # 1. IMMEDIATE INTERCEPT for TikTok Photos
    if 'tiktok.com' in url and '/photo/' in url:
        return await download_tiktok_photo(url)

    # 2. INTERCEPT for Spotify
    if 'spotify.com' in url:
        return await download_spotify(url)

    # 3. CONFIGURE YT-DLP
    ydl_opts = build_ydl_opts(url, mode=mode, quality=quality)
    
    # Critical: Use cookies for YouTube if available
    if 'youtube.com' in url or 'youtu.be' in url:
        if _YT_COOKIE_FILE:
            ydl_opts['cookiefile'] = _YT_COOKIE_FILE
        # Injecting more aggressive player clients
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web', 'mweb', 'tv_embedded']}}

    loop = asyncio.get_event_loop()
    min_mtime = time.time() - 2

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # We use extract_info with download=True
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            
            # Get the actual file path
            filename = ydl.prepare_filename(info)
            # Handle post-processed extensions (like mp3)
            if mode == 'mp3':
                filename = os.path.splitext(filename)[0] + ".mp3"
            
            # Check for multi-file results (like galleries)
            files = collect_downloaded_files(mode, filename, min_mtime)
            caption = build_caption(info, mode, quality, url)
            
            result = [os.path.abspath(f) for f in files]
            return (result if len(result) > 1 else result[0]), caption

    except Exception as e:
        # Final Error catch for the bot
        raise Exception(f"Download error: {str(e)}")
