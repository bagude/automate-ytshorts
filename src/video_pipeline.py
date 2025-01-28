import os
import json
import logging
from typing import List, Tuple, Optional, Dict
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ColorClip
)
from moviepy.video.tools.subtitles import SubtitlesClip

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VideoPipeline:
    def __init__(self, config: Dict):
        self.config = config
        self.components = {
            'validator': InputValidator(),
            'audio_processor': AudioProcessor(config),
            'video_processor': VideoProcessor(config),
            'subtitle_engine': SubtitleEngine(config),
            'compositor': VideoCompositor(config)
        }
        self.active_clips = []

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()

    def _cleanup(self):
        for clip in self.active_clips:
            try:
                clip.close()
            except Exception as e:
                logging.warning(f"Failed to close clip: {e}")

    def execute(
            self,
            output_path: str,
            tts_path: str,
            music_path: str,
            video_path: str,
            text: str,
            subtitle_json: Optional[str] = None
    ) -> None:
        
        try:
            # 1. Input validation
            self.components['validator'].validate_inputs(
                output_path,
                tts_path,
                music_path,
                video_path
            )

            # 2. Audio processing
            audio_clip = self.components['audio_processor'].process_audio(tts_path, music_path)
            self.active_clips.append(audio_clip)

            # 3. Video processing
            video_clip = self.components['video_processor'].process_video(video_path, audio_clip.duration)
            self.active_clips.append(video_clip)

            # Validate curation compatibility
            self.components['validator'].validate_durations(audio_clip.duration, video_clip.duration)

            # 4. Subtitle generation
            subtitles_clip = self.components['subtitle_engine'].generate_subtitles(text, audio_clip.duration, subtitle_json)
            self.active_clips.append(subtitles_clip)

            # 5. Composition
            final = self.components['compositor'].compose(video_clip, subtitles_clip, audio_clip)
            self.components['compositor'].render(final, output_path)
            
            logging.info(f"Successfully created video: {output_path}")
        except Exception as e:
            logging.error(f"Pipeline failed: {str(e)}")
            

            


DEFAULT_CONFIG = {
    'font_path': 'Arial-Bold',
    'font_size': 70,
    'subtitle_color': 'white',
    'stroke_color': 'black',
    'stroke_width': 2,
    'vertical_resolution': (1080, 1920),
    'subtitle_position': ('center', 0.85),
    'music_volume': 0.3,
    'tts_volume': 1.2
}

if __name__ == "__main__":
    try:
        with VideoPipeline(DEFAULT_CONFIG) as pipeline:
            pipeline.execute(
                output_path = 'output.mp4',
                tts_path = 'tts.mp3',
                music_path = 'music.mp3',
                video_path = 'video.mp4',
                text = 'Hello, world!',
                subtitle_json = 'subtitle.json'
            )
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        exit(1)
