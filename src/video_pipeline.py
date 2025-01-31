import os
import json
import logging
import sys
from typing import List, Tuple, Optional, Dict
from moviepy import *
from moviepy.video.tools.subtitles import SubtitlesClip

logging.basicConfig(level=logging.INFO,
                    format='%(filename)s - %(lineno)d - %(asctime)s - %(levelname)s - %(message)s')


class InputValidator:
    """Validates input files and parameters for the video pipeline processing.

    Handles validation of input/output paths and duration compatibility checks."""

    def validate_inputs(self, output_path: str, tts_path: str, music_path: str, video_path: str):
        """Validates existence and accessibility of all required input and output files.

        Args:
            output_path: Path where output video will be saved
            tts_path: Path to text-to-speech audio file
            music_path: Path to background music file
            video_path: Path to input video file
        """
        self._validate_file(tts_path, "TTS file")
        self._validate_file(music_path, "Music file")
        self._validate_file(video_path, "Video file")
        self._validate_output_dir(output_path)

    def validate_durations(self, audio_duration: float, video_duration: float) -> None:
        """Validates that audio duration does not exceed video duration.

        Args:
            audio_duration: Duration of the audio clip
            video_duration: Duration of the video clip
        """
        if audio_duration > video_duration:
            raise ValueError(
                f"Audio duration ({audio_duration}s) exceeds video duration ({video_duration}s)"
            )

    def _validate_file(self, path: str, file_desc: str):
        """Validates that a file exists and is accessible.

        Args:
            path: Path to the file to validate
            file_desc: Description of the file (e.g., "TTS file", "Music file", "Video file")
        """
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"{file_desc} not found at {path}")
        if not os.path.isfile(path):
            raise ValueError(f"{file_desc} is not a file")

    def _validate_output_dir(self, output_path: str):
        """Validates that the output directory exists and is writable.

        Args:
            output_path: Path to the output video file
        """
        output_dir = os.path.dirname(output_path) or "."
        if not os.path.exists(output_dir):
            raise FileNotFoundError(
                f"Output directory not found at {output_dir}")
        if not os.access(output_dir, os.W_OK):
            raise PermissionError(f"No write access to {output_dir}")


class AudioProcessor:

    def __init__(self, config: Dict):
        self.config = config
        self._parse_config(config)

    def _parse_config(self, config: Dict) -> None:
        self.tts_volume = config.get('tts_volume', 1.0)
        self.music_volume = config.get('music_volume', 0.3)
        self.fade_duration = config.get('fade_duration', 0.5)

    def _adjust_volume(self, clip: AudioFileClip, volume: float) -> AudioFileClip:
        """Adjusts the volume of an audio clip.

        Args:
            clip: The audio clip to adjust
            volume: The volume level to set (1.0 is normal, 0.5 is half volume)

        Returns:
            AudioFileClip: Volume-adjusted audio clip
        """
        return clip.with_volume_scaled(volume)

    def _create_master_audio(self, duration: float) -> AudioClip:
        """Creates a master audio clip with the specified duration and no audio.

        Args:
            duration: The duration in seconds for the master audio clip

        Returns:
            AudioClip: A silent audio clip of the specified duration
        """
        return AudioClip(duration=duration)

    def _loop_music_to_duration(self, music_clip: AudioFileClip, target_duration: float) -> AudioFileClip:
        """Loops or trims the background music to match the target duration.

        This method handles two scenarios:
        1. If music is longer than target duration: Trims the music to fit
        2. If music is shorter than target duration: Loops the music using AudioLoop
           effect to fill the entire duration

        Args:
            music_clip: The background music clip to process
            target_duration: The desired final duration in seconds

        Returns:
            AudioFileClip: A new audio clip that exactly matches the target duration
        """
        if music_clip.duration >= target_duration:
            return music_clip.subclipped(0, target_duration)

        # Use AudioLoop effect to loop the music
        return music_clip.with_effects([afx.AudioLoop(duration=target_duration)])

    def _apply_tts_effects(self, tts_clip: AudioFileClip) -> AudioFileClip:
        """Applies fade in/out effects to the TTS audio.

        Adds a subtle fade in at the start and fade out at the end of the TTS
        to create smoother transitions and avoid abrupt audio changes.

        Args:
            tts_clip: The TTS audio clip to process

        Returns:
            AudioFileClip: TTS clip with fade effects applied
        """
        return tts_clip.with_effects([
            afx.AudioFadeIn(self.fade_duration),
            afx.AudioFadeOut(self.fade_duration)
        ])

    def _normalize_volume(self, clip: AudioFileClip) -> AudioFileClip:
        """ Normalizes the volume of an audio clip based on the afx.AudioNormalize module from moviepy.

        Args:
            clip: The audio clip to normalize

        Returns:
            AudioFileClip: Normalized audio clip
        """
        return clip.with_effects([afx.AudioNormalize()])

    def process_audio(self, tts_path: str, music_path: str) -> AudioFileClip:
        """Creates a synchronized audio composition from TTS and background music.

        This method implements a multi-step audio processing pipeline:
        1. Loads the TTS and background music clips from their respective paths
        2. Uses the TTS duration as the master duration for the final composition
        3. Applies fade in/out effects to the TTS audio for smooth transitions
        4. Adjusts the volume levels of both clips according to configured settings
        5. Adapts the background music to match the TTS duration through looping or trimming
        6. Combines both audio streams into a final composite clip

        Args:
            tts_path: Path to the text-to-speech audio file that will drive the timing
            music_path: Path to the background music file that will be adapted

        Returns:
            AudioFileClip: A composite audio clip containing both the TTS and
                background music, synchronized and volume-adjusted according to
                configuration settings

        Raises:
            FileNotFoundError: If either the TTS or music file cannot be found
            IOError: If there are issues reading the audio files
        """
        # Verify files exist before attempting to load them
        if not os.path.exists(tts_path):
            raise FileNotFoundError(f"TTS audio file not found: {tts_path}")
        if not os.path.exists(music_path):
            raise FileNotFoundError(
                f"Background music file not found: {music_path}")

        try:
            # Load the audio clips
            tts_clip = AudioFileClip(tts_path)
            music_clip = AudioFileClip(music_path)

            # Use TTS duration as the master duration
            master_duration = tts_clip.duration

            # Apply fade effects to TTS
            tts_clip = self._apply_tts_effects(tts_clip)

            # Normalize all audio clips
            tts_clip = self._normalize_volume(tts_clip)
            music_clip = self._normalize_volume(music_clip)

            # Adjust volumes
            tts_clip = self._adjust_volume(tts_clip, self.tts_volume)
            music_clip = self._adjust_volume(music_clip, self.music_volume)

            # Loop music to match TTS duration
            music_clip = self._loop_music_to_duration(
                music_clip, master_duration)

            # Merge audio and return
            return CompositeAudioClip([tts_clip, music_clip])
        except (IOError, OSError, ValueError) as e:
            # Clean up any open clips important to avoid memory leaks
            try:
                tts_clip.close()
                music_clip.close()
            except (IOError, OSError):
                pass
            raise IOError(f"Error processing audio files: {str(e)}") from e


class VideoProcessor():
    def __init__(self, config: Dict):
        self.config = config

    def process_video(self, *args):
        pass


class SubtitleEngine:
    def generate_subtitles(self, *args):
        pass


class VideoCompositor:
    def compose(self, *args):
        pass


class VideoPipeline:
    def __init__(self, config: Dict):
        self.config = config
        self.components = {
            'validator': InputValidator(),
            'audio_processor': AudioProcessor(config),
            # 'video_processor': VideoProcessor(config),
            # 'subtitle_engine': SubtitleEngine(config),
            # 'compositor': VideoCompositor(config)
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
                logging.warning("Failed to close clip: %s", str(e))

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
            audio_clip = self.components['audio_processor'].process_audio(
                tts_path, music_path)
            self.active_clips.append(audio_clip)

            sys.exit(0)

            # 3. Video processing
            video_clip = self.components['video_processor'].process_video(
                video_path, audio_clip.duration)
            self.active_clips.append(video_clip)

            # Validate curation compatibility
            self.components['validator'].validate_durations(
                audio_clip.duration, video_clip.duration)

            # 4. Subtitle generation
            subtitles_clip = self.components['subtitle_engine'].generate_subtitles(
                text, audio_clip.duration, subtitle_json)
            self.active_clips.append(subtitles_clip)

            # 5. Composition
            final = self.components['compositor'].compose(
                video_clip, subtitles_clip, audio_clip)
            self.components['compositor'].render(final, output_path)

            logging.info("Successfully created video: %s", output_path)
        except (IOError, OSError, ValueError, FileNotFoundError, PermissionError, AttributeError) as e:
            logging.error("An error occurred: %s", str(e))
            sys.exit(1)


DEFAULT_CONFIG = {
    'font_path': 'Arial-Bold',
    'font_size': 70,
    'subtitle_color': 'white',
    'stroke_color': 'black',
    'stroke_width': 2,
    'vertical_resolution': (1080, 1920),
    'subtitle_position': ('center', 0.85),
    'music_volume': 0.3,
    'tts_volume': 1.2,
    'audio_master_duration_sec': 60
}

if __name__ == "__main__":
    try:
        with VideoPipeline(DEFAULT_CONFIG) as pipeline:
            pipeline.execute(
                output_path='test_output.mp4',
                tts_path=r'demo\mp3\TIFU_by_sending_a_spicy_text_to_my_boss.mp3',
                music_path=r'demo\mp3\bg_music.mp3',
                video_path=r'demo\mp4\13 Minutes Minecraft Parkour Gameplay [Free to Use] [Download].mp4',
                text='Hello, world!',
                subtitle_json='subtitle.json'
            )
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)
