
import os
import dotenv

from typing import List, Dict, Any
from src.video_editing import create_shorts
from src.load_env import load_env


class Pipeline:
    def __init__(
        self,
        platform: str, 
        video_fp: str,
        output_fp: str,
        background_music_fp: str,
        tts_audio_fp: str,
        text: str
    ):
    
        self.platform = platform
        self.video_fp = video_fp
        self.output_fp = output_fp
        self.background_music_fp = background_music_fp
        self.tts_audio_fp = tts_audio_fp
        self.text = text

        
    def run(self) -> None:
        try:
            if self.platform == 'youtube-shorts':
                username, password = load_env(self.platform)
                create_shorts(
                    video_fp=self.video_fp,
                    background_music_fp=self.background_music_fp,
                    tts_audio_fp=self.tts_audio_fp,
                    output_fp=self.output_fp,
                    text=self.text
                )
            else:
                raise ValueError('Invalid platform')
        except Exception as e:
            raise e
        
    



def main():

    pipeline = Pipeline(
        platform='youtube-shorts',
        video_fp= r'demo\mp4\13 Minutes Minecraft Parkour Gameplay [Free to Use] [Download].mp4',
        background_music_fp= r'demo\mp3\background_music.mp3',
        tts_audio_fp= r'demo\mp3\tts_audio.mp3',
        text='This is a demo video',
        output_fp= r'demo\mp4\output.mp4',

    )


if __name__ == '__main__':
    main()