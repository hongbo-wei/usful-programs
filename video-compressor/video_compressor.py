import sys
import os
from moviepy import VideoFileClip

# Usage: python video_compressor.py input_video output_video [bitrate]
def compress_video(input_path, output_path, bitrate="800k"):
    clip = VideoFileClip(input_path)
    clip.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        bitrate=bitrate,
        threads=4,
        preset="medium"
    )
    clip.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python video_compressor.py input_video output_video [bitrate]")
        sys.exit(1)
    input_video = sys.argv[1]
    output_video = sys.argv[2]
    bitrate = sys.argv[3] if len(sys.argv) > 3 else "800k"
    compress_video(input_video, output_video, bitrate)
    print(f"Compressed video saved to {output_video}")
