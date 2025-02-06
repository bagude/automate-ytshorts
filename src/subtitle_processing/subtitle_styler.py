"""Subtitle styling and rendering for video."""

import logging
from typing import Dict, List, Tuple, Optional
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.video.VideoClip import TextClip
from moviepy.video import vfx


class SubtitleStyler:
    """Handles subtitle styling and rendering."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the styler.

        Args:
            config: Optional configuration for styling
        """
        self.config = config or {}
        self._setup_defaults()

    def _setup_defaults(self):
        """Set up default style values."""
        self.font = self.config.get('font_path', 'Arial-Bold')
        self.font_size = self.config.get('font_size', 70)
        self.color = self.config.get('subtitle_color', 'white')
        self.stroke_color = self.config.get('stroke_color', 'black')
        self.stroke_width = self.config.get('stroke_width', 2)
        self.resolution = self.config.get('vertical_resolution', (1080, 1920))
        self.position = self.config.get('subtitle_position', ('center', 0.70))

    def _create_text_clip(self, txt: str) -> TextClip:
        """Create a TextClip with current style settings."""
        return TextClip(
            text=txt,
            font=self.font,
            font_size=self.font_size,
            color=self.color,
            stroke_color=self.stroke_color,
            stroke_width=self.stroke_width,
            method="caption",
            size=(self.resolution[0], None),
            text_align="center"
        )

    def _add_effects(self, subtitles: SubtitlesClip) -> SubtitlesClip:
        """Add visual effects to subtitles."""
        return subtitles.with_effects([vfx.CrossFadeIn(0.1), vfx.CrossFadeOut(0.1)])

    def create_clip(self, subtitle_data: List[Tuple[Tuple[float, float], str]], duration: Optional[float] = None) -> SubtitlesClip:
        """Create a styled subtitle clip.

        Args:
            subtitle_data: List of subtitle entries (timing, text)
            duration: Optional video duration for sync check

        Returns:
            SubtitlesClip: Styled subtitle clip
        """
        try:
            subtitles = SubtitlesClip(
                subtitle_data,
                make_textclip=self._create_text_clip
            )

            subtitles = subtitles.with_position(self.position, relative=True)

            if duration and abs(subtitles.duration - duration) > 0.1:
                logging.warning(
                    f"Subtitle duration ({subtitles.duration}) differs from video duration ({duration})"
                )

            return self._add_effects(subtitles)

        except Exception as e:
            logging.error(f"Failed to create subtitle clip: {str(e)}")
            raise

    def update_style(self, **style_options):
        """Update style settings.

        Args:
            **style_options: Style parameters to update
        """
        valid_params = {
            'font', 'font_size', 'color', 'stroke_color',
            'stroke_width', 'resolution', 'position'
        }

        for param, value in style_options.items():
            if param in valid_params:
                setattr(self, param, value)
            else:
                logging.warning(f"Ignoring invalid style parameter: {param}")

    def get_current_style(self) -> Dict:
        """Get current style settings.

        Returns:
            Dict: Current style configuration
        """
        return {
            'font': self.font,
            'font_size': self.font_size,
            'color': self.color,
            'stroke_color': self.stroke_color,
            'stroke_width': self.stroke_width,
            'resolution': self.resolution,
            'position': self.position
        }
