import os
import sqlite3
import logging
from typing import Dict, List, Optional
from datetime import datetime
from .models import Story
from .constants import StoryStatus

logging.basicConfig(level=logging.INFO,
                    format='%(filename)s - %(lineno)d - %(asctime)s - %(levelname)s - %(message)s')


class DatabaseManager:
    """Manages SQLite database operations for story pipeline."""

    def __init__(self, db_path: str = "demo/story_pipeline.db"):
        """Initialize database connection and create tables if they don't exist.

        Args:
            db_path (str): Path to SQLite database file
        """
        self.db_path = db_path
        logging.debug(f"Initializing database connection to {db_path}")
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            logging.debug("Database connection established")
            self._create_tables()
        except Exception as e:
            logging.error(f"Failed to initialize database: {str(e)}")
            raise

    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        default_status = str(StoryStatus.NEW)
        with self.conn:
            self.conn.execute(f"""
                CREATE TABLE IF NOT EXISTS stories (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    subreddit TEXT NOT NULL,
                    url TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT '{default_status}',
                    audio_path TEXT,
                    timestamps_path TEXT,
                    subtitles_path TEXT,
                    error TEXT
                )
            """)

    def add_story(self, story: Story) -> None:
        """Add a new story to the database.

        Args:
            story (Story): Story object to add
        """
        with self.conn:
            self.conn.execute("""
                INSERT INTO stories (
                    id, title, author, subreddit, url, text, created_at,
                    status, audio_path, timestamps_path, subtitles_path, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                story.id, story.title, story.author, story.subreddit,
                story.url, story.text, story.created_at, str(story.status),
                story.audio_path, story.timestamps_path, story.subtitles_path,
                story.error
            ))

    def update_story_status(self, story_id: str, status: StoryStatus, error: Optional[str] = None) -> None:
        """Update the processing status of a story.

        Args:
            story_id (str): ID of the story to update
            status (StoryStatus): New status
            error (Optional[str]): Error message if any
        """
        with self.conn:
            self.conn.execute("""
                UPDATE stories
                SET status = ?, error = ?
                WHERE id = ?
            """, (str(status), error, story_id))

    def update_story_paths(
        self,
        story_id: str,
        audio_path: Optional[str] = None,
        timestamps_path: Optional[str] = None,
        subtitles_path: Optional[str] = None
    ) -> None:
        """Update file paths for a story.

        Args:
            story_id (str): ID of the story to update
            audio_path (Optional[str]): Path to audio file
            timestamps_path (Optional[str]): Path to timestamps file
            subtitles_path (Optional[str]): Path to subtitles file
        """
        updates = []
        values = []
        if audio_path is not None:
            updates.append("audio_path = ?")
            values.append(audio_path)
        if timestamps_path is not None:
            updates.append("timestamps_path = ?")
            values.append(timestamps_path)
        if subtitles_path is not None:
            updates.append("subtitles_path = ?")
            values.append(subtitles_path)

        if updates:
            values.append(story_id)
            with self.conn:
                self.conn.execute(f"""
                    UPDATE stories
                    SET {', '.join(updates)}
                    WHERE id = ?
                """, values)

    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime string from SQLite into datetime object.

        Args:
            dt_str (str): Datetime string from SQLite

        Returns:
            datetime: Parsed datetime object
        """
        try:
            # Try parsing with microseconds
            return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                # Try parsing without microseconds
                return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                # If all else fails, return current datetime
                logging.warning(f"Could not parse datetime: {dt_str}")
                return datetime.now()

    def get_story(self, story_id: str) -> Optional[Story]:
        """Retrieve a story by its ID.

        Args:
            story_id (str): ID of the story to retrieve

        Returns:
            Optional[Story]: Story object if found, None otherwise
        """
        cursor = self.conn.execute("""
            SELECT * FROM stories WHERE id = ?
        """, (story_id,))
        row = cursor.fetchone()
        if row:
            row_dict = dict(row)
            # Convert created_at string to datetime
            if isinstance(row_dict['created_at'], str):
                row_dict['created_at'] = self._parse_datetime(
                    row_dict['created_at'])
            return Story(**row_dict)
        return None

    def get_stories_by_status(self, status: StoryStatus) -> List[Story]:
        """Retrieve all stories with a given status.

        Args:
            status (StoryStatus): Status to filter by

        Returns:
            List[Story]: List of matching stories
        """
        try:
            # Get the actual value from the enum
            status_str = str(status.value)
            query = "SELECT * FROM stories WHERE status = ? ORDER BY created_at DESC"
            params = (status_str,)
            logging.debug(f"Executing query: {query} with params: {params}")

            # Debug: show what's in the database
            cursor = self.conn.execute("SELECT DISTINCT status FROM stories")
            statuses = [row[0] for row in cursor.fetchall()]
            logging.debug(f"All status values in database: {statuses}")

            cursor = self.conn.execute(query, params)
            stories = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                if isinstance(row_dict['created_at'], str):
                    row_dict['created_at'] = self._parse_datetime(
                        row_dict['created_at'])
                stories.append(Story(**row_dict))
            logging.debug(
                f"Found {len(stories)} stories with status {status_str}")
            return stories
        except Exception as e:
            logging.error(f"Error in get_stories_by_status: {str(e)}")
            raise

    def get_stories_by_multiple_statuses(self, statuses: List[StoryStatus]) -> List[Story]:
        """Retrieve all stories with any of the given statuses.

        Args:
            statuses (List[StoryStatus]): List of statuses to filter by

        Returns:
            List[Story]: List of matching stories
        """
        try:
            # Convert enum values to strings
            status_strings = [str(status.value) for status in statuses]
            placeholders = ','.join(['?' for _ in status_strings])
            query = f"SELECT * FROM stories WHERE status IN ({placeholders}) ORDER BY created_at DESC"

            logging.debug(
                f"Executing query: {query} with statuses: {status_strings}")
            cursor = self.conn.execute(query, status_strings)

            stories = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                if isinstance(row_dict['created_at'], str):
                    row_dict['created_at'] = self._parse_datetime(
                        row_dict['created_at'])
                stories.append(Story(**row_dict))

            logging.debug(
                f"Found {len(stories)} stories with statuses {status_strings}")
            return stories
        except Exception as e:
            logging.error(
                f"Error in get_stories_by_multiple_statuses: {str(e)}")
            raise

    def get_all_stories(self) -> List[Story]:
        """Retrieve all stories.

        Returns:
            List[Story]: List of all stories
        """
        try:
            query = "SELECT * FROM stories ORDER BY created_at DESC"
            logging.debug(f"Executing query: {query}")
            cursor = self.conn.execute(query)
            stories = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                if isinstance(row_dict['created_at'], str):
                    row_dict['created_at'] = self._parse_datetime(
                        row_dict['created_at'])
                stories.append(Story(**row_dict))
            logging.debug(f"Found {len(stories)} stories")
            return stories
        except Exception as e:
            logging.error(f"Error in get_all_stories: {str(e)}")
            raise

    def delete_story(self, story_id: str) -> None:
        """Delete a story and its associated files.

        Args:
            story_id (str): ID of the story to delete
        """
        story = self.get_story(story_id)
        if story:
            # Delete associated files
            for path in [story.audio_path, story.timestamps_path, story.subtitles_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError as e:
                        logging.error(f"Failed to delete file {path}: {e}")

            # Delete from database
            with self.conn:
                self.conn.execute(
                    "DELETE FROM stories WHERE id = ?", (story_id,))

    def close(self):
        """Close the database connection."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_stories_without_errors(self) -> List[Story]:
        """Retrieve all stories that don't have errors.

        Returns:
            List[Story]: List of stories without errors
        """
        cursor = self.conn.execute("""
            SELECT * FROM stories 
            WHERE error IS NULL OR error = ''
            ORDER BY created_at DESC
        """)
        stories = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # Convert created_at string to datetime
            if isinstance(row_dict['created_at'], str):
                row_dict['created_at'] = self._parse_datetime(
                    row_dict['created_at'])
            stories.append(Story(**row_dict))
        return stories
