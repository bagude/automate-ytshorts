import os
import logging
from typing import Dict, Optional, List
from ..story_pipeline.db_manager import DatabaseManager, Story
from .video_pipeline import VideoPipeline, DEFAULT_CONFIG

logging.basicConfig(level=logging.INFO,
                    format='%(filename)s - %(lineno)d - %(asctime)s - %(levelname)s - %(message)s')


class VideoManager:
    """Manages video creation for stories using VideoPipeline."""

    # Story status constants
    STATUS_READY = 'ready'  # Initial ready state (audio and subtitles done)
    STATUS_VIDEO_PROCESSING = 'video_processing'  # Video is being created
    STATUS_VIDEO_READY = 'video_ready'  # Video creation completed
    STATUS_VIDEO_ERROR = 'video_error'  # Video creation failed

    def __init__(self, db_manager: DatabaseManager, video_config: Optional[Dict] = None):
        """Initialize the video manager.

        Args:
            db_manager: Database manager instance
            video_config: Optional configuration for video pipeline
        """
        self.db_manager = db_manager
        self.video_config = video_config or DEFAULT_CONFIG

    def get_stories_ready_for_video(self) -> List[Story]:
        """Get all stories that are ready for video creation.

        Returns:
            List[Story]: List of stories that can have videos created
        """
        # Get stories that are either ready for first processing or already have videos
        return self.db_manager.get_stories_by_multiple_statuses([
            self.STATUS_READY,
            self.STATUS_VIDEO_READY
        ])

    def create_video_for_story(self, story: Story, output_path: Optional[str] = None) -> None:
        """Create a video for a specific story.

        Args:
            story: Story object to create video for
            output_path: Optional custom output path for the video
        """
        if story.status not in [self.STATUS_READY, self.STATUS_VIDEO_READY]:
            raise ValueError(
                f"Story {story.id} is not ready for video creation (status: {story.status})")

        if not all([story.audio_path, story.timestamps_path]):
            raise ValueError(f"Story {story.id} is missing required files")

        try:
            # Generate output path if not provided
            if not output_path:
                output_dir = os.path.join("demo", "videos", story.id)
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, "final.mp4")

            # Update story status
            self.db_manager.update_story_status(
                story.id, self.STATUS_VIDEO_PROCESSING)

            # Create video using pipeline
            with VideoPipeline(self.video_config) as pipeline:
                pipeline.execute(
                    output_path=output_path,
                    tts_path=story.audio_path,
                    # Default background music
                    music_path=os.path.join("demo", "mp3", "bg_music.mp3"),
                    # Default background video
                    video_path=os.path.join("demo", "mp4", "background.mp4"),
                    text=story.text,
                    subtitle_json=story.timestamps_path
                )

            # Update story status and path
            self.db_manager.update_story_status(
                story.id, self.STATUS_VIDEO_READY)
            self.db_manager.update_story_paths(
                story.id, subtitles_path=output_path)

            logging.info(f"Successfully created video for story {story.id}")

        except Exception as e:
            error_msg = f"Failed to create video: {str(e)}"
            logging.error(error_msg)
            self.db_manager.update_story_status(
                story.id, self.STATUS_VIDEO_ERROR, error_msg)
            raise

    def process_ready_stories(self) -> None:
        """Process all stories that are ready for video creation."""
        stories = self.get_stories_ready_for_video()
        if not stories:
            logging.info("No stories ready for video creation")
            return

        logging.info(f"Found {len(stories)} stories ready for video creation")
        for story in stories:
            try:
                self.create_video_for_story(story)
            except Exception as e:
                logging.error(f"Failed to process story {story.id}: {str(e)}")
                continue

    def retry_failed_video(self, story_id: str) -> None:
        """Retry video creation for a failed story.

        Args:
            story_id: ID of the story to retry
        """
        story = self.db_manager.get_story(story_id)
        if not story:
            raise ValueError(f"Story {story_id} not found")

        if story.status not in [self.STATUS_VIDEO_ERROR, self.STATUS_VIDEO_PROCESSING]:
            raise ValueError(
                f"Story {story_id} is not in a failed video state (status: {story.status})")

        # Reset status and retry
        self.db_manager.update_story_status(story_id, self.STATUS_READY)
        self.create_video_for_story(story)
