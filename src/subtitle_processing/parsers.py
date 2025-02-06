"""Subtitle parser implementations for different subtitle formats."""

import json
import logging
from abc import ABC, abstractmethod
from typing import List, Tuple


class SubtitleParser(ABC):
    """Abstract base class for subtitle parsers."""

    @abstractmethod
    def parse(self, file_path: str) -> List[Tuple[Tuple[float, float], str]]:
        """Parse subtitle data from a file.

        Args:
            file_path: Path to the subtitle file

        Returns:
            List of tuples containing timing information and subtitle text
            Each tuple is ((start_time, end_time), text)
        """
        pass


class WhisperSubtitleParser(SubtitleParser):
    """Parser for Whisper-format JSON subtitle files."""

    def parse(self, file_path: str) -> List[Tuple[Tuple[float, float], str]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'segments' not in data:
                raise ValueError("Invalid Whisper format: missing segments")

            return [
                ((segment['start'], segment['end']), segment['text'].strip())
                for segment in data['segments']
                if all(key in segment for key in ['start', 'end', 'text'])
            ]
        except Exception as e:
            logging.error(f"Error parsing Whisper subtitle file: {str(e)}")
            raise


class ElevenLabsSubtitleParser(SubtitleParser):
    """Parser for ElevenLabs-format JSON subtitle files."""

    def parse(self, file_path: str) -> List[Tuple[Tuple[float, float], str]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise ValueError("Invalid ElevenLabs format")

            entries = []
            for segment in data:
                if not all(key in segment for key in ['characters', 'character_start_times_seconds']):
                    continue

                chars = segment['characters']
                times = segment['character_start_times_seconds']

                if len(chars) != len(times):
                    continue

                # Group characters into words
                text = ''.join(chars)
                start_time = times[0]
                end_time = times[-1] + 0.1  # Add small buffer

                entries.append(((start_time, end_time), text))

            return entries
        except Exception as e:
            logging.error(f"Error parsing ElevenLabs subtitle file: {str(e)}")
            raise


class SubtitleParserFactory:
    """Factory for creating appropriate subtitle parser based on file format."""

    @staticmethod
    def create_parser(file_path: str) -> SubtitleParser:
        """Create appropriate parser based on file content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, dict) and 'segments' in data:
                return WhisperSubtitleParser()
            elif isinstance(data, list) and data and 'characters' in data[0]:
                return ElevenLabsSubtitleParser()
            else:
                raise ValueError("Unsupported subtitle format")
        except Exception as e:
            logging.error(f"Error creating subtitle parser: {str(e)}")
            raise
