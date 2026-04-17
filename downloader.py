import yt_dlp
import os
import asyncio

async def download_media(url, mode='video'):
    """
    Downloads Reels, Posts, and Videos from Instagram/TikTok/YouTube.
    :param url: The media URL
    :param mode: 'video' for MP4 or 'mp3' for Audio
    :return: Dictionary containing metadata and the binary file path
    """
    
    # Ensure the downloads folder exists
    os.makedirs('downloads', exist_ok=True)

    ydl_opts = {
        # 1. AUTHENTICATION: Essential for Instagram/TikTok blocks
        # Place your exported cookies.txt in the same folder as this script
        'cookiefile': 'cookies.txt', 
        
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
        
        # 2. OUTPUT & FORMAT
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'format': 'bestvideo+bestaudio/best' if mode == 'video' else 'bestaudio/best',
    }

    # 3. MP3 CONVERSION LOGIC
    if mode == 'mp3':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    # Running the extraction in a thread to keep it async-friendly
    loop = asyncio.get_event_loop()
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info and download
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            
            # Get the final filename (handles the extension change for MP3)
            file_path = ydl.prepare_filename(info)
            if mode == 'mp3':
                file_path = os.path.splitext(file_path)[0] + ".mp3"

            # 4. VIDEO INFORMATION (Metadata)
            metadata = {
                "status": "success",
                "title": info.get('title', 'Unknown Title'),
                "author": info.get('uploader', 'Unknown'),
                "duration": info.get('duration'),
                "views": info.get('view_count'),
                "thumbnail": info.get('thumbnail'),
                "file_path": file_path # Use this for your bot
            }
            return metadata

    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- HOW TO USE WITH A BOT ---
# result = await download_media("URL_HERE", mode='video')
# if result['status'] == 'success':
#     with open(result['file_path'], 'rb') as f:
#         # bot.send_video(chat_id, f) <--- This fixes the "Invalid File" error
