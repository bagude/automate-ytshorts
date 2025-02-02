class PipelineError(Exception):
    """Base exception for pipeline-related errors."""
    pass


class StoryProcessingError(PipelineError):
    """Raised when there's an error processing a story."""
    pass


class VideoProcessingError(PipelineError):
    """Raised when there's an error processing a video."""
    pass


class ConfigurationError(Exception):
    """Raised when there's an error with configuration."""
    pass


class DatabaseError(Exception):
    """Raised when there's an error with database operations."""
    pass


class APIError(Exception):
    """Base exception for API-related errors."""
    pass


class ElevenLabsAPIError(APIError):
    """Raised when there's an error with ElevenLabs API."""
    pass


class RedditAPIError(APIError):
    """Raised when there's an error with Reddit API."""
    pass


class ResourceNotFoundError(Exception):
    """Raised when a requested resource is not found."""
    pass


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass
