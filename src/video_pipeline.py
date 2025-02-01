import os
import math
import json
import logging
import sys
from types import TracebackType
from typing import List, Tuple, Optional, Dict, Union, Type
from moviepy import *
from moviepy.video.tools.subtitles import SubtitlesClip
from abc import ABC, abstractmethod

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
            audio_duration: Duration of the audio clip in seconds
            video_duration: Duration of the video clip in seconds

        Raises:
            ValueError: If audio_duration is greater than video_duration, with a detailed error message
                      containing both durations
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
        2. If music is shorter than target duration: Loops the music using moviepy's AudioLoop
           effect to seamlessly fill the entire duration without abrupt transitions

        Args:
            music_clip: The background music clip to process
            target_duration: The desired final duration in seconds

        Returns:
            AudioFileClip: A new audio clip that exactly matches the target duration, either
                         trimmed or seamlessly looped using AudioLoop effect
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
        4. Normalizes both TTS and background music using AudioNormalize effect
        5. Adjusts the volume levels of both clips according to configured settings
        6. Adapts the background music to match the TTS duration through looping or trimming
        7. Combines both audio streams into a final composite clip

        Args:
            tts_path: Path to the text-to-speech audio file that will drive the timing
            music_path: Path to the background music file that will be adapted

        Returns:
            AudioFileClip: A composite audio clip containing both the TTS and
                background music, synchronized, normalized and volume-adjusted according to
                configuration settings

        Raises:
            FileNotFoundError: If either the TTS or music file cannot be found
            IOError: If there are issues reading or processing the audio files
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


class VideoProcessor:
    def __init__(self, config: Dict):
        self.config = config
        self._parse_config(config)

        self.w_detail = None
        self.h_detail = None
        self.duration = None

    def _parse_config(self, config: Dict) -> None:
        """Extracts relevant configuration values with defaults."""
        self.fade_duration = config.get('fade_duration', 0.5)
        self.resolution = config.get('vertical_resolution', (1080, 1920))
        self.loop_overlap = config.get('loop_overlap_duration', 1.0)

    def _resize_video(self, clip: VideoFileClip) -> VideoFileClip:
        """Resizes video to match target resolution while maintaining aspect ratio."""
        return clip.with_effects([vfx.Resize(height=self.resolution[0])])

    def _loop_video_to_duration(self, clip: VideoFileClip, target_duration: float) -> VideoFileClip:
        """Loops or trims video to match target duration.

        If video is shorter than target, makes it loopable with a smooth transition
        using the configured loop_overlap duration (default 1.0s) to avoid abrupt cuts.
        If video is longer than target, subclips it to the exact duration.

        Args:
            clip: The video clip to process
            target_duration: Target duration in seconds

        Returns:
            VideoFileClip: A video clip matching the target duration, either trimmed
                         or smoothly looped with overlap transitions
        """
        if clip.duration >= target_duration:
            return clip.subclipped(0, target_duration)

        # Make the clip loopable with a smooth transition
        loopable = clip.with_effects([vfx.MakeLoopable(self.loop_overlap)])
        # Loop it to reach target duration
        return loopable.loop(n=None, duration=target_duration)

    def _apply_video_effects(self, clip: VideoFileClip) -> VideoFileClip:
        """Applies fade in/out effects to video."""
        return clip.with_effects([vfx.CrossFadeIn(self.fade_duration), vfx.CrossFadeOut(self.fade_duration)])

    def _report_dimensions(self, clip: VideoFileClip) -> None:
        """Reports the dimensions of the video."""
        self.w_detail = clip.size[0]
        self.h_detail = clip.size[1]
        self.duration = clip.duration

        logging.info("Video dimensions: %dx%d", self.w_detail, self.h_detail)
        logging.info("Video duration: %s", self.duration)

    def process_video(self, video_path: str, target_duration: float) -> VideoFileClip:
        """Processes video by loading, resizing, applying effects, and adjusting duration.

        Args:
            video_path: Path to input video file
            target_duration: Target duration to match (usually from audio)

        Returns:
            VideoFileClip: Processed video clip ready for composition

        Raises:
            FileNotFoundError: If video file doesn't exist
            IOError: If there are issues processing the video
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        try:
            # Load video
            video_clip = VideoFileClip(video_path)
            self._report_dimensions(video_clip)
            # Process the video
            video_clip = self._resize_video(video_clip)
            video_clip = self._loop_video_to_duration(
                video_clip, target_duration)
            video_clip = self._apply_video_effects(video_clip)
            self._report_dimensions(video_clip)

            return video_clip

        except (IOError, OSError) as e:
            try:
                video_clip.close()
            except (IOError, OSError):
                pass
            raise IOError(f"Error processing video file: {str(e)}") from e


class SubtitleParser(ABC):
    """Abstract base class for subtitle parsers."""

    @abstractmethod
    def parse(self, json_path: str) -> List[Tuple[Tuple[float, float], str]]:
        """Parse subtitle data from a JSON file.

        Args:
            json_path: Path to the JSON file containing subtitle data

        Returns:
            List of tuples containing timing information and subtitle text
            Each tuple is ((start_time, end_time), text)
        """
        pass


class WhisperSubtitleParser(SubtitleParser):
    """Parser for Whisper-format JSON subtitle files."""

    def _subdivide_segment(self, text: str, start_time: float, end_time: float, max_chars: int = 50) -> List[Tuple[Tuple[float, float], str]]:
        """Subdivides a Whisper segment into smaller chunks based on text length and punctuation."""
        text = text.strip()
        if not text:
            return []

        if len(text) <= max_chars:
            return [((start_time, end_time), text)]

        # Define punctuation hierarchy for splitting
        strong_breaks = {'.', '!', '?'}
        medium_breaks = {';', ':', '—', '--'}
        weak_breaks = {',', ')', ']', '}', '"'}

        def find_best_split_point(text: str, max_length: int) -> int:
            if len(text) <= max_length:
                return len(text)

            for i in range(max_length, 0, -1):
                if text[i-1] in strong_breaks:
                    return i

            min_length_for_medium = int(max_length * 0.7)
            for i in range(max_length, min_length_for_medium, -1):
                if text[i-1] in medium_breaks:
                    return i

            min_length_for_weak = int(max_length * 0.8)
            for i in range(max_length, min_length_for_weak, -1):
                if text[i-1] in weak_breaks:
                    return i

            last_space = text[:max_length].rfind(' ')
            if last_space > 0:
                return last_space

            return max_length

        chunks = []
        current_pos = 0
        text_length = len(text)

        while current_pos < text_length:
            remaining_text = text[current_pos:]
            split_point = find_best_split_point(remaining_text, max_chars)

            chunk = remaining_text[:split_point].strip()
            if chunk:
                chunks.append(chunk)
            current_pos += split_point

        num_chunks = len(chunks)
        total_duration = end_time - start_time
        result = []
        total_chars = sum(len(chunk) for chunk in chunks)
        current_time = start_time

        for i, chunk in enumerate(chunks):
            chunk_weight = 1.0
            if chunk[-1] in strong_breaks:
                chunk_weight = 1.2
            elif chunk[-1] in medium_breaks:
                chunk_weight = 1.1

            char_ratio = len(chunk) / total_chars
            this_duration = (total_duration * char_ratio) * chunk_weight

            if current_time + this_duration > end_time:
                this_duration = end_time - current_time

            chunk_end = current_time + this_duration

            if i < num_chunks - 1:
                chunk_end -= 0.1

            result.append(((current_time, chunk_end), chunk))
            current_time = chunk_end + 0.1

        return result

    def parse(self, json_path: str) -> List[Tuple[Tuple[float, float], str]]:
        """Parse Whisper JSON output to create subtitle entries."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'segments' not in data:
                raise ValueError(
                    "Invalid Whisper JSON format: missing 'segments' key")

            subtitle_entries = []
            for segment in data['segments']:
                if all(key in segment for key in ['start', 'end', 'text']):
                    start_time = segment['start']
                    end_time = segment['end']
                    text = segment['text'].strip()

                    if text:
                        subdivided_entries = self._subdivide_segment(
                            text=text,
                            start_time=start_time,
                            end_time=end_time
                        )
                        subtitle_entries.extend(subdivided_entries)
                else:
                    logging.warning("Skipping invalid segment in Whisper JSON")

            return subtitle_entries

        except FileNotFoundError:
            logging.error("Whisper JSON file not found: %s", json_path)
            raise
        except json.JSONDecodeError as e:
            logging.error("Invalid JSON format in %s: %s", json_path, str(e))
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            logging.error("Error processing Whisper JSON: %s", str(e))
            raise


class ElevenLabsSubtitleParser(SubtitleParser):
    """Parser for ElevenLabs-format JSON subtitle files."""

    def parse(self, json_path: str) -> List[Tuple[Tuple[float, float], str]]:
        """Parse ElevenLabs JSON output to create subtitle entries with character-level timing."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                subtitle_data_list = json.load(f)

            all_characters = []
            all_start_times = []

            for segment in subtitle_data_list:
                if not all(key in segment for key in ['characters', 'character_start_times_seconds']):
                    raise ValueError("Invalid ElevenLabs JSON format")

                if len(segment['characters']) != len(segment['character_start_times_seconds']):
                    raise ValueError(
                        "Mismatch between characters and start times")

                all_characters.extend(segment['characters'])
                all_start_times.extend(
                    segment['character_start_times_seconds'])

            char_timings = list(zip(all_characters, all_start_times))

            subtitle_entries = []
            current_text = []
            segment_start = char_timings[0][1]
            last_char_end = segment_start
            max_segment_chars = 60

            for i, (char, start_time) in enumerate(char_timings):
                current_text.append(char)
                last_char_end = start_time + 0.1

                break_conditions = [
                    char in {'.', '!', '?', ','},
                    char == ' ' and (start_time - segment_start) > 1.5,
                    len(current_text) >= max_segment_chars,
                    i < len(char_timings) -
                    1 and char_timings[i+1][1] - start_time > 0.5
                ]

                if any(break_conditions):
                    text = ''.join(current_text).strip()
                    if len(current_text) >= max_segment_chars:
                        text += '...'

                    word_count = len(text.split())

                    base_buffer = 0.8
                    word_based_buffer = 1 * word_count
                    buffer = min(max(base_buffer, word_based_buffer), 3.5)

                    base_min_duration = 0.8
                    word_based_min = 1 * word_count
                    min_duration = min(
                        max(base_min_duration, word_based_min), 3.5)

                    end_time = last_char_end + buffer
                    if (end_time - segment_start) < min_duration:
                        end_time = segment_start + min_duration

                    subtitle_entries.append(((segment_start, end_time), text))

                    current_text = []
                    if i < len(char_timings)-1:
                        segment_start = char_timings[i+1][1]

            if current_text:
                text = ''.join(current_text).strip()
                word_count = len(text.split())

                base_buffer = 0.2 * 1.2
                word_based_buffer = 0.5 * word_count * 1.2
                buffer = min(max(base_buffer, word_based_buffer), 3.0)

                base_min_duration = 0.2 * 1.2
                word_based_min = 0.5 * word_count * 1.2
                min_duration = min(max(base_min_duration, word_based_min), 3.0)

                end_time = last_char_end + buffer
                if (end_time - segment_start) < min_duration:
                    end_time = segment_start + min_duration

                subtitle_entries.append(((segment_start, end_time), text))

            # Add smooth transitions between segments
            for i in range(len(subtitle_entries)-1):
                current_end = subtitle_entries[i][0][1]
                next_start = subtitle_entries[i+1][0][0]
                if next_start > current_end:
                    overlap = (next_start - current_end) * 0.3
                    subtitle_entries[i] = (
                        (subtitle_entries[i][0][0], current_end + overlap),
                        subtitle_entries[i][1]
                    )

            return subtitle_entries

        except Exception as e:
            logging.error("Error processing ElevenLabs JSON: %s", str(e))
            raise


class SubtitleParserFactory:
    """Factory class for creating subtitle parsers based on JSON format."""

    @staticmethod
    def detect_format(json_path: str) -> str:
        """Detect the format of the JSON file.

        Args:
            json_path: Path to the JSON file

        Returns:
            str: 'whisper' or 'elevenlabs'

        Raises:
            ValueError: If JSON format cannot be determined
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'segments' in data and isinstance(data['segments'], list):
                if data['segments'] and all(key in data['segments'][0] for key in ['start', 'end', 'text']):
                    return 'whisper'

            if isinstance(data, list) and data:
                first_item = data[0]
                if all(key in first_item for key in ['characters', 'character_start_times_seconds']):
                    return 'elevenlabs'

            raise ValueError(
                "Unknown JSON format - neither Whisper nor ElevenLabs format detected")

        except Exception as e:
            logging.error("Error detecting JSON format: %s", str(e))
            raise

    @classmethod
    def create_parser(cls, json_path: str) -> SubtitleParser:
        """Create and return appropriate parser based on JSON format.

        Args:
            json_path: Path to the JSON file

        Returns:
            SubtitleParser: Instance of appropriate parser class

        Raises:
            ValueError: If JSON format cannot be determined
        """
        format_type = cls.detect_format(json_path)
        if format_type == 'whisper':
            return WhisperSubtitleParser()
        elif format_type == 'elevenlabs':
            return ElevenLabsSubtitleParser()
        else:
            raise ValueError(f"Unsupported subtitle format: {format_type}")


class SubtitleEngine:
    def __init__(self, config: Dict, parser_factory: Optional[Type[SubtitleParserFactory]] = None):
        """Initialize the SubtitleEngine.

        Args:
            config: Configuration dictionary
            parser_factory: Optional custom parser factory class. If None, uses default SubtitleParserFactory.
        """
        self.config = config
        self._parse_config(config)
        self.parser_factory = parser_factory or SubtitleParserFactory

    def _parse_config(self, config: Dict) -> None:
        self.font_path = config.get('font_path', 'Arial-Bold')
        self.font_size = config.get('font_size', 70)
        self.subtitle_color = config.get('subtitle_color', 'white')
        self.stroke_color = config.get('stroke_color', 'black')
        self.stroke_width = config.get('stroke_width', 2)
        self.resolution = config.get('vertical_resolution', (1080, 1920))

    def _effect_subtitles(self, subtitles: SubtitlesClip) -> SubtitlesClip:
        # Add a fade in and fade out effect to the subtitles
        return subtitles.with_effects([vfx.CrossFadeIn(0.1), vfx.CrossFadeOut(0.1)])

    def generate_subtitles(self, text: str, duration: float, subtitle_json: Optional[str] = None) -> SubtitlesClip:
        """
        Generates a SubtitlesClip for the video using the provided text and timing information.

        Args:
            text: The complete subtitle text.
            duration: Total duration of the audio/video.
            subtitle_json: Optional path to a JSON file with timing information.

        Returns:
            SubtitlesClip: A moviepy SubtitlesClip generated based on the timing data.
        """
        def text_clip_generator(txt):
            return TextClip(
                text=txt,
                font=self.font_path,
                font_size=self.font_size,
                color=self.subtitle_color,
                stroke_color=self.stroke_color,
                stroke_width=self.stroke_width,
                method="caption",
                size=(self.resolution[0], None),
                text_align="center"
            )

        if subtitle_json is not None:
            try:
                # Use the parser factory to get the appropriate parser
                parser = self.parser_factory.create_parser(subtitle_json)
                subtitle_entries = parser.parse(subtitle_json)

                subtitles = SubtitlesClip(
                    subtitle_entries,
                    make_textclip=text_clip_generator
                )

                subtitles = subtitles.with_position(
                    ("center", 0.70), relative=True)

                return self._effect_subtitles(subtitles)

            except Exception as e:
                logging.error(
                    "Error generating subtitles from JSON: %s", str(e))
                raise
        else:
            return SubtitlesClip([], make_textclip=text_clip_generator, encoding='utf-8')


class VideoCompositor:
    def __init__(self, config: Dict):
        self.config = config
        self._parse_config(config)

    def _parse_config(self, config: Dict) -> None:
        self.output_path = config.get('output_path', 'output.mp4')
        self.panic_mode = config.get('panic_mode', False)

    def _apply_panic_effects(self, clip: VideoFileClip) -> VideoFileClip:
        """Applies a series of attention-grabbing effects to the video when in panic mode."""

        clip = clip.with_effects([
            vfx.AccelDecel(new_duration=clip.duration * 2,
                           abruptness=0.5, soonness=0.5)
        ])

        return clip

    def compose(self, video_clip: VideoFileClip, subtitles_clip: SubtitlesClip, audio_clip: AudioFileClip) -> VideoFileClip:
        """Combines video, subtitles, and audio into a single composite clip.

        Args:
            video_clip: The base video clip
            subtitles_clip: The subtitle overlay clip
            audio_clip: The audio track clip

        Returns:
            VideoFileClip: The final composite video with all elements combined
        """
        # Apply audio
        video_clip = video_clip.with_audio(audio_clip)

        # Apply panic mode effects if enabled
        if self.panic_mode:
            logging.info(
                "🚨 PANIC MODE ACTIVATED! Applying chaotic video effects 🚨")
            video_clip = self._apply_panic_effects(video_clip)

        # Combine with subtitles
        return CompositeVideoClip([video_clip, subtitles_clip])

    def render(self, clip: VideoFileClip, output_path: str, fps: int = 30) -> None:
        """Renders the final composite video to a file.

        Args:
            clip: The final composite video clip
            output_path: The path to save the rendered video file
            fps: The frame rate of the output video (default: 30)

        Note:
            The video is rendered using the libx264 codec for optimal file size
            and quality balance in short-form vertical video content.
        """
        clip.write_videofile(output_path, codec='libx264', fps=fps)


class VideoPipeline:
    def __init__(self, config: Dict):
        logging.info("Initializing VideoPipeline with configuration")
        self.config = config
        self.components = {
            'validator': InputValidator(),
            'audio_processor': AudioProcessor(config),
            'video_processor': VideoProcessor(config),
            'subtitle_engine': SubtitleEngine(config),
            'compositor': VideoCompositor(config)
        }
        self._active_clips: Dict[str, Union[VideoFileClip,
                                            AudioFileClip, SubtitlesClip]] = {}
        self._cleanup_status = {'initialized': False, 'cleaned': False}
        logging.info("VideoPipeline initialized successfully")

    def __enter__(self) -> 'VideoPipeline':
        """Enter the context manager.

        Sets up the pipeline and marks it as initialized for proper cleanup tracking.

        Returns:
            VideoPipeline: The pipeline instance
        """
        logging.info("Entering VideoPipeline context")
        self._cleanup_status['initialized'] = True
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]],
                 exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None:
        """Exit the context manager and ensure proper cleanup.

        Args:
            exc_type: The type of the exception that occurred, if any
            exc_val: The instance of the exception that occurred, if any
            exc_tb: The traceback of the exception that occurred, if any
        """
        logging.info("Exiting VideoPipeline context")
        try:
            self._cleanup()
        except Exception as e:
            logging.error("Error during cleanup in context exit: %s", str(e))
            # If we had an original exception, preserve it
            if exc_type is not None:
                raise exc_val
            # Otherwise, raise the cleanup error
            raise
        finally:
            # Mark as cleaned even if there were errors
            self._cleanup_status['cleaned'] = True

        # Log any exception that occurred during pipeline execution
        if exc_type is not None:
            logging.error("Pipeline execution failed with %s: %s",
                          exc_type.__name__, str(exc_val))

    def _register_clip(self, clip_id: str, clip: Union[VideoFileClip, AudioFileClip, SubtitlesClip]) -> None:
        """Register a clip for cleanup tracking.

        Args:
            clip_id: Unique identifier for the clip
            clip: The clip to register
        """
        self._active_clips[clip_id] = clip
        logging.debug("Registered clip: %s", clip_id)

    def _cleanup(self) -> None:
        """Clean up all active media clips and resources.

        This method ensures proper closure of all video, audio, and subtitle clips
        that were created during pipeline execution.
        """
        if not self._cleanup_status['initialized']:
            logging.warning("Cleanup called before pipeline initialization")
            return

        if self._cleanup_status['cleaned']:
            logging.info("Cleanup already performed")
            return

        logging.info("Starting cleanup of %d active clips",
                     len(self._active_clips))

        cleanup_errors = []
        for clip_id, clip in self._active_clips.items():
            try:
                if clip is not None:
                    clip.close()
                    logging.debug("Successfully closed clip: %s", clip_id)
            except Exception as e:
                error_msg = f"Failed to close clip {clip_id}: {str(e)}"
                cleanup_errors.append(error_msg)
                logging.error(error_msg)

        # Clear the clips dictionary
        self._active_clips.clear()

        if cleanup_errors:
            raise RuntimeError(
                f"Cleanup completed with {len(cleanup_errors)} errors: {'; '.join(cleanup_errors)}")

        logging.info("Cleanup completed successfully")

    def execute(
            self,
            output_path: str,
            tts_path: str,
            music_path: str,
            video_path: str,
            text: str,
            subtitle_json: Optional[str] = None,
            fps: int = 30
    ) -> None:
        try:
            logging.info("Starting video pipeline execution")
            logging.info(
                f"Processing video with: output={output_path}, tts={tts_path}, music={music_path}, video={video_path}, fps={fps}")

            # 1. Input validation
            logging.info("Step 1/6: Validating input files and paths")
            self.components['validator'].validate_inputs(
                output_path,
                tts_path,
                music_path,
                video_path
            )
            logging.info("Input validation completed successfully")

            # 2. Audio processing
            logging.info(
                "Step 2/6: Processing audio files (TTS and background music)")
            audio_clip = self.components['audio_processor'].process_audio(
                tts_path, music_path)
            self._register_clip('audio', audio_clip)
            logging.info(
                f"Audio processing completed. Duration: {audio_clip.duration:.2f} seconds")

            # 3. Video processing
            logging.info("Step 3/6: Processing video file")
            video_clip = self.components['video_processor'].process_video(
                video_path, audio_clip.duration)
            self._register_clip('video', video_clip)
            logging.info(
                f"Video processing completed. Size: {video_clip.size}")

            # 4. Subtitle generation
            logging.info("Step 4/6: Generating subtitles")
            subtitles_clip = self.components['subtitle_engine'].generate_subtitles(
                text, audio_clip.duration, subtitle_json)
            self._register_clip('subtitles', subtitles_clip)
            logging.info("Subtitle generation completed")

            # 5. Composition
            logging.info("Step 5/6: Compositing video, audio, and subtitles")
            final = self.components['compositor'].compose(
                video_clip, subtitles_clip, audio_clip)
            self._register_clip('final', final)
            logging.info("Starting video rendering")
            self.components['compositor'].render(final, output_path, fps=fps)
            logging.info("Video rendering completed")

            logging.info("✨ Successfully created video: %s", output_path)
        except Exception as e:
            logging.error("❌ Pipeline execution failed: %s", str(e))
            raise


DEFAULT_CONFIG = {
    'font_path': r'demo\font_at.ttf',
    'font_size': 75,
    'subtitle_color': 'white',
    'stroke_color': 'black',
    'stroke_width': 10,
    'vertical_resolution': (1080, 1920),
    'subtitle_position': ('center', 0.85),
    'music_volume': 0.3,
    'tts_volume': 1.2,
    'audio_master_duration_sec': 60,
    'panic_mode': False
}

if __name__ == "__main__":
    try:
        with VideoPipeline(DEFAULT_CONFIG) as pipeline:
            pipeline.execute(
                output_path='test_output.mp4',
                tts_path=r'demo\mp3\TIFU_by_correcting_my_manager_on_a_phrase_she_was_using.mp3',
                music_path=r'demo\mp3\bg_music.mp3',
                video_path=r'demo\mp4\13 Minutes Minecraft Parkour Gameplay [Free to Use] [Download].mp4',
                text='Hello, world!',
                subtitle_json=r'demo\json\TIFU_by_correcting_my_manager_on_a_phrase_she_was_using.json',
                fps=2  # Example FPS setting
            )
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)
