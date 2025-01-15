import os
import json
import pandas as pd
from typing import List, Tuple, Optional
import sys

from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeAudioClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip


def create_shorts(
    video_fp: str,
    background_music_fp: str,
    tts_audio_fp: str,
    output_fp: str,
    text: str,
    json_fp: Optional[str] = None,
    font_path: str = "C:/Windows/Fonts/Arial.ttf"  # Adjust based on your system
):
    
    srt_file = parse_alignment_json(json_fp) if json_fp else None
    generator = lambda text: TextClip(text = text, font = font_path, font_size = 48, color = 'white', method = 'caption', size = (1000, 400)).with_duration(5)
    subtitles = SubtitlesClip(srt_file, make_textclip=generator, encoding = 'utf-8')

    tts_audio = AudioFileClip(tts_audio_fp)
    tts_audio = tts_audio.with_volume_scaled(1.2)

    clip = VideoFileClip(video_fp)
    clip = clip.subclipped(0, tts_audio.duration)

    background_music = AudioFileClip(background_music_fp)
    background_music = background_music.subclipped(0, None)
    background_music = background_music.with_volume_scaled(0.2)

    composite_audio = CompositeAudioClip([tts_audio, background_music])

    final_video = CompositeVideoClip([clip, subtitles.with_position((0.5,0.5), relative=True)])
    final_video = final_video.with_audio(composite_audio)

    with final_video as video:
        video.write_videofile(output_fp, codec="libx264", audio_codec="aac", fps=24)

    

def parse_alignment_json(json_fp: str) -> List[Tuple[Tuple[float,float], str]]:
    with open(json_fp, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Create list for timestamp pairs and text
    segments: List[Tuple[Tuple[float,float], str]] = []

    for alignment_obj in data:
        # Join characters into a single string
        text = ''.join(alignment_obj.get("characters", []))
        
        # Get start and end times
        start_times = alignment_obj.get("character_start_times_seconds", [])
        end_times = alignment_obj.get("character_end_times_seconds", [])

        if start_times and end_times:
            # Create timestamp tuple ((start, end), text)
            start = min(start_times)
            end = max(end_times)
            print(text, start, end)
            
            segments.append(((start, end), text))  # Changed order to match required format

    return segments



def find_json_by_id(json_id: str, folder: str) -> str:
    if not json_id:
        return ""
    target_filename = f"{json_id}.json"
    for filename in os.listdir(folder):
        if filename == target_filename:
            return os.path.join(os.path.abspath(folder), filename)
    return ""

def main():
    csv_file = "tifu_posts_output.csv"
    df = pd.read_csv(csv_file)
    df.dropna(subset=["Text"], inplace=True)

    example_video = r"demo\mp4\13 Minutes Minecraft Parkour Gameplay [Free to Use] [Download].mp4"
    background_music = r"demo/mp3/bg_music.mp3"
    json_folder = r"demo/json"

    for index, row in df.iterrows():
        text_content = row["Text"]
        tts_mp3_path = row["output_mp3_path"]
        json_id = row.get("json_id", "")
        alignment_json_path = find_json_by_id(json_id, json_folder)

        output_fp = os.path.join("demo", "mp4", f"short_{index}.mp4")
        print(f"\nProcessing row {index} -> {output_fp}")

        create_shorts(
            video_fp=example_video,
            background_music_fp=background_music,
            tts_audio_fp=tts_mp3_path,
            output_fp=output_fp,
            text=text_content,
            json_fp=alignment_json_path if alignment_json_path else None,
            font_path="C:/Windows/Fonts/Arial.ttf"  # Ensure the font path is valid
        )
        sys.exit()

    print("\nAll videos processed.")

if __name__ == "__main__":
    main()
