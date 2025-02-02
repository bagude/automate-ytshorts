from enum import Enum
from typing import List


class StoryStatus(str, Enum):
    """Enumeration of possible story statuses."""
    NEW = 'new'
    AUDIO_GENERATED = 'audio_generated'
    READY = 'ready'
    VIDEO_PROCESSING = 'video_processing'
    VIDEO_READY = 'video_ready'
    VIDEO_ERROR = 'video_error'
    ERROR = 'error'

    @classmethod
    def get_video_ready_statuses(cls) -> List['StoryStatus']:
        """Get statuses that indicate a story is ready for video creation."""
        return [cls.READY, cls.AUDIO_GENERATED]  # Also include AUDIO_GENERATED as a valid status

    @classmethod
    def get_error_statuses(cls) -> List['StoryStatus']:
        """Get statuses that indicate a story is in an error state."""
        return [cls.ERROR, cls.VIDEO_ERROR]

    @classmethod
    def get_processing_statuses(cls) -> List['StoryStatus']:
        """Get statuses that indicate a story is being processed."""
        return [cls.VIDEO_PROCESSING]
