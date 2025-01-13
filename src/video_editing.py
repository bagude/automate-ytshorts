import os
import json
import pandas as pd
from typing import List, Tuple, Optional
import sys

from moviepy import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip

def create_shorts(
    video_fp: str,
    background_music_fp: str,
    tts_audio_fp: str,
    output_fp: str,
    text: str,
    json_fp: Optional[str] = None,
    font_path: str = "C:/Windows/Fonts/Arial.ttf"  # Adjust based on your system
):
    with VideoFileClip(video_fp) as video:
        width, height = video.size
        target_width = 1080
        target_height = 1920

        # Crop and resize video
        new_width = height * 9 / 16
        x_center = width / 2
        x_start = int(x_center - new_width / 2)
        x_end = int(x_center + new_width / 2)

        cropped_video = video.cropped(x1=x_start, x2=x_end, y1=0, y2=height)
        resized_video = cropped_video.resized(height=target_height)

        with AudioFileClip(background_music_fp) as bg_music, AudioFileClip(tts_audio_fp) as tts_audio:
            if bg_music.duration > resized_video.duration:
                bg_music = bg_music.subclip(0, resized_video.duration)
            else:
                print("Warning: Background music is shorter than video duration.")

            # Combine audio
            final_audio = tts_audio.with_start(0.3)
            resized_video = resized_video.with_audio(final_audio)

            # Handle subtitles
            if json_fp and os.path.isfile(json_fp):
                subtitle_timing = parse_alignment_json(json_fp)
            else:
                subtitle_timing = [(text, 0, resized_video.duration)]

            print(f"Subtitle timing: {subtitle_timing}")

            for i, (start, end) in enumerate(subtitle_timing):
                text_clip = create_subtitle_clip(
                    text=start,
                    start=start,
                    end=end,
                    target_width=target_width,
                    font_path=font_path
                )
                subtitle_timing[i] = text_clip
            

            

            final_clip = CompositeVideoClip([resized_video, *subtitle_timing])
            final_clip.write_videofile(output_fp, codec="libx264", audio_codec="aac", fps=30)


def create_subtitle_clip(
    text: str, start: float, end: float, target_width: int, font_path: str
) -> TextClip:
    return TextClip(
        text,
        font=font_path,
        fontsize=50,
        color="white",
        stroke_color="black",
        stroke_width=2,
        size=(int(target_width * 0.8), None),
        method="caption"
    ).with_start(start).with_end(end).with_position(("center", "bottom"))

def parse_alignment_json(json_fp: str) -> List[Tuple[str, float, float]]:
    with open(json_fp, "r", encoding="utf-8") as f:
        data = json.load(f)

    list_tuples: [((float,float),str)] = []
    for alignment_obj in data:
        text = alignment_obj.get("characters",[])
        start_time = alignment_obj.get("character_start_times_seconds", [])
        end_time = alignment_obj.get("character_end_times_seconds", [])
        
        for i in range(len(text)):
            list_tuples.append(((start_time[i], end_time[i]), text[i]))

    return list_tuples

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
    background_music = r"demo/mp3/background_music.mp3"
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

    print("\nAll videos processed.")

if __name__ == "__main__":
    main()
