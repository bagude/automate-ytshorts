import logging
from typing import Dict, Optional
from moviepy.video.tools.subtitles import SubtitlesClip

from ..subtitle_processing.parsers import SubtitleParserFactory
from ..subtitle_processing.subtitle_generator import WhisperGenerator
from ..subtitle_processing.subtitle_styler import SubtitleStyler

logging.basicConfig(level=logging.INFO,
                    format='%(filename)s - %(lineno)d - %(asctime)s - %(levelname)s - %(message)s')


class SubtitleService:
    """Service for handling subtitle operations.

    This service provides high-level operations for subtitle generation,
    styling, and video integration. It abstracts away the implementation
    details of parsing, processing, and rendering subtitles.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the subtitle service.

        Args:
            config: Optional configuration dictionary for customizing subtitle
                   generation and styling.
        """
        self.config = config or {}
        self.styler = SubtitleStyler(self.config)
        self.generator = WhisperGenerator(self.config)

    def generate_from_audio(self, audio_path: str, output_path: str) -> str:
        """Generate subtitles from an audio file.

        Args:
            audio_path: Path to the audio file
            output_path: Where to save the generated subtitles

        Returns:
            str: Path to the generated subtitle file
        """
        try:
            return self.generator.generate(audio_path, output_path)
        except Exception as e:
            logging.error(f"Failed to generate subtitles: {str(e)}")
            raise

    def create_subtitle_clip(self, subtitle_path: str, duration: Optional[float] = None) -> SubtitlesClip:
        """Create a subtitle clip for video rendering.

        Args:
            subtitle_path: Path to the subtitle file
            duration: Optional video duration for synchronization

        Returns:
            SubtitlesClip: Ready-to-use subtitle clip for video
        """
        try:
            parser = SubtitleParserFactory.create_parser(subtitle_path)
            subtitle_data = parser.parse(subtitle_path)
            return self.styler.create_clip(subtitle_data, duration)
        except Exception as e:
            logging.error(f"Failed to create subtitle clip: {str(e)}")
            raise

    def update_style(self, **style_options) -> None:
        """Update subtitle styling options.

        Args:
            **style_options: Style parameters to update (font, size, color, etc.)
        """
        self.styler.update_style(**style_options)

    def get_current_style(self) -> Dict:
        """Get current subtitle style settings.

        Returns:
            Dict: Current style configuration
        """
        return self.styler.get_current_style()
