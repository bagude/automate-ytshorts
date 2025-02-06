"""Subtitle generation from audio files."""

import os
import logging
from typing import Dict, Optional

from ..story_pipeline.whisper_api import transcribe_audio, load_whisper_model


class WhisperGenerator:
    """Generates subtitles from audio using Whisper."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the generator.

        Args:
            config: Optional configuration for Whisper model
        """
        self.config = config or {}
        self.model_name = self.config.get('whisper_model', 'base')
        self.model = None

    def _ensure_model_loaded(self):
        """Ensure Whisper model is loaded."""
        if not self.model:
            self.model = load_whisper_model(self.model_name)

    def generate(self, audio_path: str, output_path: str) -> str:
        """Generate subtitles from audio file.

        Args:
            audio_path: Path to the audio file
            output_path: Where to save the generated subtitles

        Returns:
            str: Path to the generated subtitle file
        """
        try:
            self._ensure_model_loaded()
            return transcribe_audio(
                audio_path=audio_path,
                model=self.model,
                json_folder=os.path.dirname(output_path)
            )
        except Exception as e:
            logging.error(f"Failed to generate subtitles: {str(e)}")
            raise
