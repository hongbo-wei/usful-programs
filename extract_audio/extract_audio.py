from moviepy import VideoFileClip

def extract_audio(video_path, output_audio_path):
    # Load the video file
    video = VideoFileClip(video_path)

    # Extract and write the audio
    if video.audio:
        video.audio.write_audiofile(output_audio_path)
        print(f"Audio extracted to: {output_audio_path}")
    else:
        print("No audio stream found in the video.")

# Example usage
video_file = "input_video.mp4"
audio_output = "extracted_audio.mp3"  # Can also use .wav
extract_audio(video_file, audio_output)
