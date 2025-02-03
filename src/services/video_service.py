import os
from typing import List, Dict, Optional
from ..db.manager import DatabaseManager
from ..video_pipeline.video_pipeline import VideoPipeline
from ..db import Story, StoryStatus


class VideoService:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def create_pipeline(self, config: Dict) -> VideoPipeline:
        """Creates and configures a video pipeline instance."""
        return VideoPipeline(config)

    def get_pending_videos(self) -> List[Story]:
        """Retrieves stories ready for video generation."""
        return self.db_manager.get_stories_by_status(StoryStatus.READY)

    def process_video(self, story_id: str, config: Dict) -> None:
        """Processes a single story into a video.

        Args:
            story_id: ID of the story to process
            config: Configuration dictionary for video pipeline

        Raises:
            ValueError: If story is not found
        """
        story = self.db_manager.get_story(story_id)
        if not story:
            raise ValueError(f"Story not found: {story_id}")

        # Update story status to processing
        self.db_manager.update_story_status(
            story_id, StoryStatus.VIDEO_PROCESSING)

        try:
            pipeline = self.create_pipeline(config)

            # Generate output path
            output_dir = os.path.normpath(
                os.path.join("demo", "videos", story.id))
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.normpath(
                os.path.join(output_dir, "final.mp4"))

            # Normalize paths for consistency
            music_path = os.path.normpath(
                os.path.join("demo", "mp3", "bg_music.mp3"))
            video_path = os.path.normpath(
                os.path.join("demo", "mp4", "background.mp4"))

            # Execute video pipeline
            pipeline.execute(
                output_path=output_path,
                tts_path=story.audio_path,  # This path comes from DB and should already be normalized
                music_path=music_path,
                video_path=video_path,
                text=story.text,
                # This path comes from DB and should already be normalized
                subtitle_json=story.timestamps_path
            )

            # Update story status to ready and save output path
            self.db_manager.update_story_status(
                story_id, StoryStatus.VIDEO_READY)
            self.db_manager.update_story_paths(
                story_id, subtitles_path=output_path)

        except Exception as e:
            # Update story status to error if something goes wrong
            self.db_manager.update_story_status(
                story_id, StoryStatus.VIDEO_ERROR, str(e))
            raise

    def get_video_status(self, story_id: str) -> Optional[StoryStatus]:
        """Gets the video processing status for a story."""
        story = self.db_manager.get_story(story_id)
        return story.status if story else None
