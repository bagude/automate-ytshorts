from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union
from .constants import StoryStatus
import logging


@dataclass
class Story:
    """Data class representing a story and its processing state."""
    id: str
    title: str
    author: str
    subreddit: str
    url: str
    text: str
    created_at: datetime
    status: Union[StoryStatus, str]  # Can be either enum or string
    audio_path: Optional[str] = None
    timestamps_path: Optional[str] = None
    subtitles_path: Optional[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        """Convert status string to enum if needed."""
        if isinstance(self.status, str):
            try:
                # If it's the full enum string (e.g., 'StoryStatus.NEW')
                if self.status.startswith('StoryStatus.'):
                    self.status = getattr(
                        StoryStatus, self.status.split('.')[-1])
                else:
                    # If it's just the value (e.g., 'new')
                    self.status = StoryStatus(self.status)
            except (ValueError, AttributeError) as e:
                # If conversion fails, default to NEW
                logging.warning(
                    f"Invalid status value '{self.status}', defaulting to NEW: {str(e)}")
                self.status = StoryStatus.NEW
