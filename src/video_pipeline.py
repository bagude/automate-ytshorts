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


class SubtitleEngine:
    def __init__(self, config: Dict):
        self.config = config
        self._parse_config(config)

    def _parse_config(self, config: Dict) -> None:
        self.font_path = config.get('font_path', 'Arial-Bold')
        self.font_size = config.get('font_size', 70)
        self.subtitle_color = config.get('subtitle_color', 'white')
        self.stroke_color = config.get('stroke_color', 'black')
        self.stroke_width = config.get('stroke_width', 2)
        self.resolution = config.get('vertical_resolution', (1080, 1920))

    def _create_srt_file_from_json(self, subtitle_data: Dict) -> List[Tuple[Tuple[float, float], str]]:
        """Converts JSON timing data into character-accurate subtitle entries with dynamic timing.

        This method implements sophisticated subtitle timing logic:
        1. Processes character-by-character timing data from the JSON input
        2. Groups characters into natural segments based on:
           - Punctuation marks (., !, ?, ,)
           - Time gaps > 0.5s between characters
           - Maximum segment length (40 chars)
           - Natural pauses > 1.5s at spaces
        3. Applies word count-based dynamic duration rules:
           - Base buffer time: 0.2s
           - Word-based buffer: 0.5s per word (capped at 2.5s)
           - Base minimum duration: 0.2s
           - Word-based minimum duration: 0.5s per word (capped at 2.5s)
        4. Special handling for final segment:
           - 20% longer duration than normal segments
           - Base buffer and minimum times increased by 1.2x
           - Maximum buffer time capped at 3.0s
        5. Per-character timing:
           - Each character gets a 0.1s buffer
           - Ensures smooth text display

        Args:
            subtitle_data: Dictionary containing:
                - 'characters': List of individual characters
                - 'character_start_times_seconds': List of start times for each character

        Returns:
            List[Tuple[Tuple[float, float], str]]: List of subtitle entries, each containing:
                - Timing tuple (start_time, end_time) in seconds
                - Subtitle text for that time period

        Raises:
            ValueError: If the JSON format is invalid or there's a mismatch between characters and timings
            KeyError: If required fields are missing from subtitle_data
        """
        char_timings = list(zip(
            subtitle_data['characters'],
            subtitle_data['character_start_times_seconds']
        ))

        subtitle_entries = []
        current_text = []
        segment_start = char_timings[0][1]
        last_char_end = segment_start
        max_segment_chars = 40

        for i, (char, start_time) in enumerate(char_timings):
            current_text.append(char)
            last_char_end = start_time + 0.1  # Per-character buffer

            # Segment break conditions
            break_conditions = [
                char in {'.', '!', '?', ','},
                char == ' ' and (start_time - segment_start) > 1.5,
                len(current_text) >= max_segment_chars,
                i < len(char_timings)-1 and
                char_timings[i+1][1] - start_time > 0.5
            ]

            if any(break_conditions):
                text = ''.join(current_text).strip()
                word_count = len(text.split())

                # Dynamic timing based on word count
                base_buffer = 0.2
                word_based_buffer = 0.5 * word_count
                buffer = min(max(base_buffer, word_based_buffer), 2.5)

                base_min_duration = 0.2
                word_based_min = 0.5 * word_count
                min_duration = min(max(base_min_duration, word_based_min), 2.5)

                end_time = last_char_end + buffer
                if (end_time - segment_start) < min_duration:
                    end_time = segment_start + min_duration

                subtitle_entries.append(((segment_start, end_time), text))

                # Reset segment
                current_text = []
                if i < len(char_timings)-1:
                    segment_start = char_timings[i+1][1]

        # Handle final segment
        if current_text:
            text = ''.join(current_text).strip()
            word_count = len(text.split())

            # Final segment gets 20% longer duration
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

    def generate_subtitles(self, text: str, duration: float, subtitle_json: Optional[str] = None) -> SubtitlesClip:
        """
        Generates a SubtitlesClip for the video using the provided text and timing information.

        If a subtitle JSON file is provided, it is expected to contain data in the following format:
        [
            {
                "characters": ["T", "h", "i", "s", " ", "i", "s", ...],
                "character_start_times_seconds": [0.0, 0.081, 0.151, ...]
            }
            ...
        ]

        The subtitle is built as a progressive(cumulative) text reveal based on character timings.
        For each character, the text is updated from the beginning up to that character.
        The end time for each segment is set to the next character's start time, and for the final
        character it is set to the total duration of the audio.

        If subtitle_json is not provided or fails to load, the entire text is rendered across the entire duration.

        Args:
            text: The complete subtitle text.
            duration: Total duration of the audio/video.
            subtitle_json: Optional path to a JSON file with character timing information.

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
                size=(self.resolution[0], None)
            )

        if subtitle_json is not None:
            try:
                with open(subtitle_json, 'r', encoding='utf-8') as f:
                    subtitle_data_list = json.load(f)

                # Combine all segments into one continuous sequence
                all_characters = []
                all_start_times = []

                for segment in subtitle_data_list:
                    if not all(key in segment for key in ['characters', 'character_start_times_seconds']):
                        raise ValueError("Invalid subtitle JSON format")

                    if len(segment['characters']) != len(segment['character_start_times_seconds']):
                        raise ValueError(
                            "Mismatch between characters and start times")

                    all_characters.extend(segment['characters'])
                    all_start_times.extend(
                        segment['character_start_times_seconds'])

                subtitle_data = {
                    'characters': all_characters,
                    'character_start_times_seconds': all_start_times
                }

                subtitle_entries = self._create_srt_file_from_json(
                    subtitle_data)

                subtitles = SubtitlesClip(
                    subtitle_entries, make_textclip=text_clip_generator, encoding='utf-8')

                subtitles = subtitles.with_position(("center", "bottom"))
                return subtitles

            except (IOError, OSError, ValueError) as e:
                logging.error("Error generating subtitles: %s", str(e))
                raise e
        else:
            return SubtitlesClip([], make_textclip=text_clip_generator, encoding='utf-8')


class VideoCompositor:
    def __init__(self, config: Dict):
        self.config = config
        self._parse_config(config)

    def _parse_config(self, config: Dict) -> None:
        self.output_path = config.get('output_path', 'output.mp4')

    def compose(self, video_clip: VideoFileClip, subtitles_clip: SubtitlesClip, audio_clip: AudioFileClip) -> VideoFileClip:
        """Combines video, subtitles, and audio into a single composite clip.

        Args:
            video_clip: The base video clip
            subtitles_clip: The subtitle overlay clip
            audio_clip: The audio track clip

        Returns:
            VideoFileClip: The final composite video with all elements combined

        """
        video_clip = video_clip.with_audio(audio_clip)

        return CompositeVideoClip([video_clip, subtitles_clip])

    def render(self, clip: VideoFileClip, output_path: str) -> None:
        """Renders the final composite video to a file.

        Args:
            clip: The final composite video clip
            output_path: The path to save the rendered video file

        Note:
            The video is rendered with a fixed FPS of 6 and uses the libx264 codec for
            optimal file size and quality balance in short-form vertical video content.
        """
        clip.write_videofile(output_path, codec='libx264', fps=6)


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
        self.active_clips = []
        logging.info("VideoPipeline initialized successfully")

    def __enter__(self):
        logging.info("Entering VideoPipeline context")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.info("Exiting VideoPipeline context")
        self._cleanup()

    def _cleanup(self):
        logging.info("Starting cleanup of active clips")
        for clip in self.active_clips:
            try:
                clip.close()
            except Exception as e:
                logging.warning("Failed to close clip: %s", str(e))
        logging.info("Cleanup completed")

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
            logging.info("Starting video pipeline execution")
            logging.info(
                f"Processing video with: output={output_path}, tts={tts_path}, music={music_path}, video={video_path}")

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
            self.active_clips.append(audio_clip)
            logging.info(
                f"Audio processing completed. Duration: {audio_clip.duration:.2f} seconds")

            # 3. Video processing
            logging.info("Step 3/6: Processing video file")
            video_clip = self.components['video_processor'].process_video(
                video_path, audio_clip.duration)
            self.active_clips.append(video_clip)
            logging.info(
                f"Video processing completed. Size: {video_clip.size}")

            # 4. Subtitle generation
            logging.info("Step 4/6: Generating subtitles")
            subtitles_clip = self.components['subtitle_engine'].generate_subtitles(
                text, audio_clip.duration, subtitle_json)
            self.active_clips.append(subtitles_clip)
            logging.info("Subtitle generation completed")

            # 5. Composition
            logging.info("Step 5/6: Compositing video, audio, and subtitles")
            final = self.components['compositor'].compose(
                video_clip, subtitles_clip, audio_clip)
            logging.info("Starting video rendering")
            self.components['compositor'].render(final, output_path)
            self.active_clips.append(final)
            logging.info("Video rendering completed")

            # 6. Cleanup
            logging.info("Step 6/6: Performing final cleanup")
            self._cleanup()

            logging.info("✨ Successfully created video: %s", output_path)
        except (IOError, OSError, ValueError, FileNotFoundError, PermissionError, AttributeError) as e:
            logging.error("❌ Pipeline execution failed: %s", str(e))
            raise


DEFAULT_CONFIG = {
    'font_path': r'demo\font_at.ttf',
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
                tts_path=r'demo\mp3\TIFU_by_correcting_my_manager_on_a_phrase_she_was_using.mp3',
                music_path=r'demo\mp3\bg_music.mp3',
                video_path=r'demo\mp4\13 Minutes Minecraft Parkour Gameplay [Free to Use] [Download].mp4',
                text='Hello, world!',
                subtitle_json=r'demo\json\26d5d1bb-c2b2-419d-98dd-bdf5334e5a23.json'
            )
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)
