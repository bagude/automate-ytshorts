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
        """Processes a single story into a video."""
        story = self.db_manager.get_story(story_id)
        if not story:
            raise ValueError(f"Story not found: {story_id}")

        pipeline = self.create_pipeline(config)
        pipeline.process_story(story)

    def get_video_status(self, story_id: str) -> Optional[StoryStatus]:
        """Gets the video processing status for a story."""
        story = self.db_manager.get_story(story_id)
        return story.status if story else None
