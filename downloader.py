import yt_dlp
import os
import asyncio
import glob


async def download_media(url, mode='video'):
    """
    Downloads Reels, Posts, and Videos from Instagram/TikTok/YouTube.
    :param url: The media URL
    :param mode: 'video' for MP4 or 'mp3' for Audio
    :return: Dictionary containing metadata and open binary file object
    """

    os.makedirs('downloads', exist_ok=True)

    ydl_opts = {
        'cookiefile': 'cookies.txt',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'user_agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/123.0.0.0 Safari/537.36'
        ),
        'referer': 'https://www.google.com/',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'format': 'bestvideo+bestaudio/best' if mode == 'video' else 'bestaudio/best',
        # Merge video+audio into a single mp4
        'merge_output_format': 'mp4',
    }

    if mode == 'mp3':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    loop = asyncio.get_event_loop()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(url, download=True)
            )

            # --- FIX: Reliably resolve the actual file path on disk ---
            expected_path = ydl.prepare_filename(info)

            if mode == 'mp3':
                # After FFmpeg post-processing the extension changes to .mp3
                file_path = os.path.splitext(expected_path)[0] + '.mp3'
            else:
                # After merging, yt-dlp always outputs .mp4 (set above)
                file_path = os.path.splitext(expected_path)[0] + '.mp4'

            # Fallback: if the expected path doesn't exist, search downloads/
            if not os.path.exists(file_path):
                ext = 'mp3' if mode == 'mp3' else 'mp4'
                matches = glob.glob(f'downloads/*.{ext}')
                if matches:
                    # Pick the most recently modified file
                    file_path = max(matches, key=os.path.getmtime)
                else:
                    raise FileNotFoundError(
                        f"Downloaded file not found. Expected: {file_path}"
                    )

            # --- FIX: Open in BINARY mode ('rb') — this is what bots expect ---
            binary_file = open(file_path, 'rb')

            metadata = {
                "status": "success",
                "title": info.get('title', 'Unknown Title'),
                "author": info.get('uploader', 'Unknown'),
                "duration": info.get('duration'),
                "views": info.get('view_count'),
                "thumbnail": info.get('thumbnail'),
                "file_path": file_path,       # string path  (for reference)
                "file": binary_file,          # ✅ binary object (pass to bot)
            }
            return metadata

    except Exception as e:
        return {"status": "error", "message": str(e)}


def close_file(result: dict):
    """
    Call this after your bot finishes sending the file to release the handle.
    """
    f = result.get("file")
    if f and not f.closed:
        f.close()


# ─────────────────────────────────────────────
#  BOT USAGE EXAMPLES
# ─────────────────────────────────────────────
#
#  ── python-telegram-bot ──
#  result = await download_media("URL_HERE", mode='video')
#  if result['status'] == 'success':
#      await bot.send_video(chat_id=chat_id, video=result['file'])
#      close_file(result)
#
#  ── Pyrogram ──
#  result = await download_media("URL_HERE", mode='video')
#  if result['status'] == 'success':
#      await client.send_video(chat_id, result['file'])
#      close_file(result)
#
#  ── Audio (MP3) ──
#  result = await download_media("URL_HERE", mode='mp3')
#  if result['status'] == 'success':
#      await bot.send_audio(chat_id=chat_id, audio=result['file'])
#      close_file(result)
#
#  ── If you need the raw bytes instead ──
#  result = await download_media("URL_HERE", mode='video')
#  if result['status'] == 'success':
#      video_bytes = result['file'].read()
#      close_file(result)
