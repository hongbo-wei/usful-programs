import yt_dlp
import os

def download_youtube_video(url):
    # 创建 downloads 文件夹（如果不存在）
    os.makedirs('downloads', exist_ok=True)

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # 下载路径改为 downloads/
        'noplaylist': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

if __name__ == "__main__":
    video_url = input("Enter the YouTube video URL: ")
    if not video_url:
        video_url = "https://www.youtube.com/watch?v=El_We2CrZcg"
        print("Down loading default video 'Beach Weather - Sex, Drugs, Etc. (slowed + reverb)'")
        download_youtube_video(video_url)
    else:
        download_youtube_video(video_url)