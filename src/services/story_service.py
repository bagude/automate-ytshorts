from typing import List, Dict, Optional
from ..db.manager import DatabaseManager
from ..story_pipeline.story_pipeline import StoryPipeline
from ..db import Story, StoryStatus


class StoryService:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def create_pipeline(self, config: Dict) -> StoryPipeline:
        """Creates and configures a story pipeline instance."""
        return StoryPipeline(config)

    def get_all_stories(self, limit: Optional[int] = None) -> List[Story]:
        """Retrieves all stories with optional limit."""
        stories = self.db_manager.get_all_stories()
        if limit:
            return stories[:limit]
        return stories

    def get_story(self, story_id: str) -> Optional[Story]:
        """Retrieves a single story by ID."""
        return self.db_manager.get_story(story_id)

    def process_subreddit(self, config: Dict) -> List[str]:
        """Processes stories from a subreddit.

        Args:
            config: Configuration dictionary for story pipeline

        Returns:
            List[str]: List of story IDs that were processed

        Raises:
            ValueError: If subreddit configuration is invalid
            Exception: If story processing fails
        """
        try:
            pipeline = self.create_pipeline(config)
            story_ids = pipeline.run()

            if not story_ids:
                return []

            # Update status for all processed stories
            for story_id in story_ids:
                self.db_manager.update_story_status(story_id, StoryStatus.NEW)

            return story_ids

        except Exception as e:
            # If we have story IDs but processing failed, update their status
            if 'story_ids' in locals():
                for story_id in story_ids:
                    self.db_manager.update_story_status(
                        story_id,
                        StoryStatus.ERROR,
                        f"Story processing failed: {str(e)}"
                    )
            raise

    def update_story_status(self, story_id: str, status: StoryStatus, error: Optional[str] = None) -> None:
        """Updates the status of a story."""
        self.db_manager.update_story_status(story_id, status, error)
