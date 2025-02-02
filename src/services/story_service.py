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
        """Processes stories from a subreddit."""
        pipeline = self.create_pipeline(config)
        return pipeline.run()

    def update_story_status(self, story_id: str, status: StoryStatus, error: Optional[str] = None) -> None:
        """Updates the status of a story."""
        self.db_manager.update_story_status(story_id, status, error)
