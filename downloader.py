import yt_dlp
import asyncio
import os

async def download_media(url, download_type='video'):
    """
    download_type can be 'video' or 'mp3'
    """
    
    # Check if the cookies file exists to prevent silent errors
    if not os.path.exists('cookies.txt'):
        print("⚠️ Warning: cookies.txt not found! Platform might block the download.")

    ydl_opts = {
        # 1. AUTHENTICATION: Use the exported cookies file
        'cookiefile': 'cookies.txt', 
        
        'quiet': False,
        'no_warnings': False,
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        
        # 2. FORMATTING: Logic for Video vs Audio
        'format': 'bestvideo+bestaudio/best' if download_type == 'video' else 'bestaudio/best',
        
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }] if download_type == 'mp3' else [],

        # 3. SPOOFING & BYPASS
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
        'geo_bypass': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Extract info first
            info = ydl.extract_info(url, download=True)
            
            # Gather useful information
            metadata = {
                "title": info.get('title'),
                "author": info.get('uploader'),
                "views": info.get('view_count'),
                "duration": info.get('duration'),
                "description": info.get('description'),
                "filename": ydl.prepare_filename(info)
            }
            
            return metadata
            
        except yt_dlp.utils.DownloadError as e:
            return {"error": str(e)}

# --- How to run it ---
# async def main():
#     # Make sure the 'downloads' folder exists
#     os.makedirs('downloads', exist_ok=True)
#     
#     # For Video
#     result = await download_media("YOUR_LINK_HERE", 'video')
#     print(result)
#
# asyncio.run(main())
