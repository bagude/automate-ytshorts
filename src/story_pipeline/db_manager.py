import os
import sqlite3
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logging.basicConfig(level=logging.INFO,
                    format='%(filename)s - %(lineno)d - %(asctime)s - %(levelname)s - %(message)s')


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
    status: str  # 'new', 'audio_generated', 'subtitles_generated', 'ready'
    audio_path: Optional[str] = None
    timestamps_path: Optional[str] = None
    subtitles_path: Optional[str] = None
    error: Optional[str] = None


class DatabaseManager:
    """Manages SQLite database operations for story pipeline."""

    def __init__(self, db_path: str = "demo/story_pipeline.db"):
        """Initialize database connection and create tables if they don't exist.

        Args:
            db_path (str): Path to SQLite database file
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    subreddit TEXT NOT NULL,
                    url TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'new',
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
                story.url, story.text, story.created_at, story.status,
                story.audio_path, story.timestamps_path, story.subtitles_path,
                story.error
            ))

    def update_story_status(self, story_id: str, status: str, error: Optional[str] = None) -> None:
        """Update the processing status of a story.

        Args:
            story_id (str): ID of the story to update
            status (str): New status
            error (Optional[str]): Error message if any
        """
        with self.conn:
            self.conn.execute("""
                UPDATE stories
                SET status = ?, error = ?
                WHERE id = ?
            """, (status, error, story_id))

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

    def get_stories_by_status(self, status: str) -> List[Story]:
        """Retrieve all stories with a given status.

        Args:
            status (str): Status to filter by

        Returns:
            List[Story]: List of matching stories
        """
        cursor = self.conn.execute("""
            SELECT * FROM stories WHERE status = ?
            ORDER BY created_at DESC
        """, (status,))
        stories = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # Convert created_at string to datetime
            if isinstance(row_dict['created_at'], str):
                row_dict['created_at'] = self._parse_datetime(
                    row_dict['created_at'])
            stories.append(Story(**row_dict))
        return stories

    def get_all_stories(self) -> List[Story]:
        """Retrieve all stories.

        Returns:
            List[Story]: List of all stories
        """
        cursor = self.conn.execute(
            "SELECT * FROM stories ORDER BY created_at DESC")
        stories = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # Convert created_at string to datetime
            if isinstance(row_dict['created_at'], str):
                row_dict['created_at'] = self._parse_datetime(
                    row_dict['created_at'])
            stories.append(Story(**row_dict))
        return stories

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
            WHERE error IS NULL 
                AND status != 'error'
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

    def get_stories_by_multiple_statuses(self, statuses: List[str]) -> List[Story]:
        """Retrieve all stories with any of the given statuses.

        Args:
            statuses (List[str]): List of statuses to filter by

        Returns:
            List[Story]: List of matching stories
        """
        placeholders = ','.join('?' * len(statuses))
        cursor = self.conn.execute(f"""
            SELECT * FROM stories 
            WHERE status IN ({placeholders})
            ORDER BY created_at DESC
        """, statuses)
        stories = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # Convert created_at string to datetime
            if isinstance(row_dict['created_at'], str):
                row_dict['created_at'] = self._parse_datetime(
                    row_dict['created_at'])
            stories.append(Story(**row_dict))
        return stories


def get_story_folder_path(story_id: str, base_dir: str = "demo/stories") -> str:
    """Get the folder path for a story's files.

    Args:
        story_id (str): ID of the story
        base_dir (str): Base directory for story files

    Returns:
        str: Full path to the story's folder
    """
    folder_path = os.path.join(base_dir, story_id)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def get_story_file_paths(story_id: str, base_dir: str = "demo/stories") -> Dict[str, str]:
    """Get the file paths for a story's assets.

    Args:
        story_id (str): ID of the story
        base_dir (str): Base directory for story files

    Returns:
        Dict[str, str]: Dictionary containing paths for audio, timestamps, and subtitles
    """
    folder_path = get_story_folder_path(story_id, base_dir)
    return {
        'audio_path': os.path.join(folder_path, "audio.mp3"),
        'timestamps_path': os.path.join(folder_path, "timestamps.json"),
        'subtitles_path': os.path.join(folder_path, "subtitles.srt")
    }
