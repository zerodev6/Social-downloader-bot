import yt_dlp
import os
import asyncio
import glob


async def download_media(url, mode='video'):
    """
    Downloads Reels, Posts, and Videos from Instagram/TikTok/YouTube.
    :param url: The media URL
    :param mode: 'video' for MP4 or 'mp3' for Audio
    :return: Absolute file path string — raises Exception on failure
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
        'merge_output_format': 'mp4',
    }

    if mode == 'mp3':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    loop = asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await loop.run_in_executor(
            None, lambda: ydl.extract_info(url, download=True)
        )

        expected_path = ydl.prepare_filename(info)

        if mode == 'mp3':
            file_path = os.path.splitext(expected_path)[0] + '.mp3'
        else:
            file_path = os.path.splitext(expected_path)[0] + '.mp4'

        # Fallback: search downloads folder for most recent file
        if not os.path.exists(file_path):
            ext = 'mp3' if mode == 'mp3' else 'mp4'
            matches = glob.glob(f'downloads/*.{ext}')
            if matches:
                file_path = max(matches, key=os.path.getmtime)
            else:
                raise FileNotFoundError(f"Downloaded file not found. Expected: {file_path}")

        return os.path.abspath(file_path)
