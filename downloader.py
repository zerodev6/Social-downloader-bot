import yt_dlp
import asyncio
import os

async def download_media(url, download_type='video'):
    """
    Downloads media from Instagram, TikTok, YouTube, etc.
    download_type can be 'video' or 'mp3'
    """
    
    # 1. Ensure downloads directory exists
    os.makedirs('downloads', exist_ok=True)

    # 2. Check for cookies file to bypass bot protection
    if not os.path.exists('cookies.txt'):
        print("⚠️ Warning: cookies.txt not found! Create this file to bypass Instagram/TikTok logins.")

    ydl_opts = {
        'cookiefile': 'cookies.txt', # Reads cookies to authenticate
        'quiet': True,
        'no_warnings': True,
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        
        # Determine format based on user request
        'format': 'bestvideo+bestaudio/best' if download_type == 'video' else 'bestaudio/best',
        
        # Convert to mp3 if requested
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }] if download_type == 'mp3' else [],

        # Spoof headers
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
        'geo_bypass': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Extract info and download
            info = ydl.extract_info(url, download=True)
            
            # Important: If it's an MP3, yt-dlp changes the extension AFTER downloading.
            # We need to get the exact final filename.
            filename = ydl.prepare_filename(info)
            if download_type == 'mp3':
                filename = filename.rsplit('.', 1)[0] + '.mp3'

            metadata = {
                "title": info.get('title', 'Unknown Title'),
                "author": info.get('uploader', 'Unknown Author'),
                "filename": filename
            }
            
            return metadata
            
        except Exception as e:
            return {"error": str(e)}

# ==========================================
# HOW TO FIX YOUR BOT ERROR (The Crucial Part)
# ==========================================

async def main():
    test_url = "YOUR_LINK_HERE" # Put a TikTok or Insta link here
    
    # 1. Get the downloaded file data
    result = await download_media(test_url, 'video')
    
    if "error" in result:
        print(f"Failed to download: {result['error']}")
        return

    filepath = result["filename"]
    print(f"Successfully downloaded: {filepath}")

    # 2. THE FIX FOR YOUR ERROR:
    # You MUST open the file using 'rb' (read binary) before sending it via a bot.
    
    try:
        with open(filepath, 'rb') as binary_file:
            print("File successfully opened in binary mode. It is ready to send!")
            
            # Example for Telegram:
            # bot.send_video(chat_id, binary_file, caption=result["title"])
            
            # Example for Discord:
            # await channel.send(file=discord.File(binary_file))
            
    except Exception as e:
        print(f"Error opening file: {e}")
        
    finally:
        # 3. Clean up the file after sending so your server doesn't run out of storage
        if os.path.exists(filepath):
            os.remove(filepath)
            print("Deleted local file to save space.")

# Run the test
# asyncio.run(main())
