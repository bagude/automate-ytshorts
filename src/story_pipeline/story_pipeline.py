import os
import logging
import uuid
from typing import Dict, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime

from .reddit_crawl import get_posts, parse_text
from .elevenlabs_api import process_csv
from .whisper_api import transcribe_audio, load_whisper_model
from ..db import DatabaseManager, Story, get_story_file_paths
from ..load_env import load_env
from ..db import StoryStatus

logging.basicConfig(level=logging.INFO,
                    format='%(filename)s - %(lineno)d - %(asctime)s - %(levelname)s - %(message)s')


class InputValidator:
    """Validates input parameters and configurations for the story pipeline processing."""

    @staticmethod
    def validate_directories(output_dirs: Dict[str, str]) -> None:
        """Validates and creates necessary output directories.

        Args:
            output_dirs (Dict[str, str]): Dictionary of directory paths to validate/create
        """
        for dir_name, dir_path in output_dirs.items():
            if not os.path.exists(dir_path):
                logging.info(f"Creating {dir_name} directory: {dir_path}")
                os.makedirs(dir_path, exist_ok=True)
            elif not os.path.isdir(dir_path):
                raise ValueError(
                    f"{dir_name} path exists but is not a directory: {dir_path}")

    @staticmethod
    def validate_subreddit(subreddit: str) -> None:
        """Validates subreddit name.

        Args:
            subreddit (str): Name of the subreddit to validate
        """
        if not subreddit or not isinstance(subreddit, str):
            raise ValueError("Subreddit name must be a non-empty string")


class StoryProcessor(ABC):
    """Abstract base class for story processing steps."""

    @abstractmethod
    def process(self, *args, **kwargs):
        """Process the story data."""
        pass


class RedditStoryProcessor(StoryProcessor):
    """Handles Reddit story crawling and processing."""

    def __init__(self, subreddit: str, db_manager: DatabaseManager, single_story: bool = False):
        self.subreddit = subreddit
        self.db_manager = db_manager
        self.single_story = single_story

    def process(self) -> List[str]:
        """Crawls Reddit for stories and saves them to database.

        Returns:
            List[str]: List of story IDs that were processed
        """
        logging.info(f"Crawling stories from r/{self.subreddit}")
        posts = get_posts(self.subreddit, single=self.single_story)
        story_ids = []

        for title, post_data in posts.items():
            story_id = str(uuid.uuid4())
            story = Story(
                id=story_id,
                title=title,
                author=post_data['author'],
                subreddit=self.subreddit,
                url=post_data['permalink'],
                text=parse_text(post_data['text']),
                created_at=datetime.now(),
                status=StoryStatus.NEW
            )
            self.db_manager.add_story(story)
            story_ids.append(story_id)

        if self.single_story:
            logging.info("Saved first story to database")
        else:
            logging.info(f"Saved {len(story_ids)} stories to database")
        return story_ids


class TextToSpeechProcessor(StoryProcessor):
    """Handles text-to-speech conversion using ElevenLabs API."""

    def __init__(self, db_manager: DatabaseManager, base_dir: str = "demo/stories"):
        self.db_manager = db_manager
        self.base_dir = base_dir
        self.api_key = load_env("eleven-labs")[0]
        self.voice_id = "YFpUSo240svj7tcmDapZ"

    def process(self, story_ids: List[str]) -> None:
        """Converts text to speech using ElevenLabs API.

        Args:
            story_ids (List[str]): List of story IDs to process
        """
        logging.info("Starting text-to-speech conversion")

        for story_id in story_ids:
            story = self.db_manager.get_story(story_id)
            if not story:
                continue

            try:
                # Get paths for this story
                story_dir = os.path.join(self.base_dir, story_id)
                os.makedirs(story_dir, exist_ok=True)

                audio_path = os.path.join(story_dir, "audio.mp3")

                # Process TTS
                from .elevenlabs_api import _make_headers, _make_payload, _handle_timestamps_mode
                headers = _make_headers(self.api_key)
                payload = _make_payload(story.text)

                json_id = _handle_timestamps_mode(
                    self.voice_id,
                    headers,
                    payload,
                    audio_path,
                    story_dir  # Pass the story directory
                )

                if json_id:
                    # Update database with new paths, including the actual JSON file path
                    json_path = os.path.join(story_dir, f"{json_id}.json")
                    self.db_manager.update_story_paths(
                        story_id,
                        audio_path=audio_path,
                        timestamps_path=json_path  # Use the actual JSON file path
                    )
                    self.db_manager.update_story_status(
                        story_id, 'audio_generated')
                else:
                    self.db_manager.update_story_status(
                        story_id,
                        'error',
                        'Failed to generate audio timestamps'
                    )
            except Exception as e:
                self.db_manager.update_story_status(
                    story_id,
                    'error',
                    f'TTS generation failed: {str(e)}'
                )


class SubtitleGenerator(StoryProcessor):
    """Handles subtitle generation using Whisper API."""

    def __init__(self, db_manager: DatabaseManager, model_name: str = "base"):
        self.db_manager = db_manager
        self.model_name = model_name
        self.model = None

    def process(self, story_ids: List[str]) -> None:
        """Generates subtitles for stories.

        Args:
            story_ids (List[str]): List of story IDs to process
        """
        logging.info("Starting subtitle generation")

        # Load Whisper model once for all files
        if not self.model:
            self.model = load_whisper_model(self.model_name)

        for story_id in story_ids:
            story = self.db_manager.get_story(story_id)
            if not story or not story.audio_path or story.status != 'audio_generated':
                continue

            logging.info(f"Generating subtitles for story: {story.title}")
            try:
                transcribe_audio(
                    audio_path=story.audio_path,
                    model=self.model,
                    json_folder=os.path.dirname(story.timestamps_path)
                )
                self.db_manager.update_story_status(story_id, 'ready')
            except Exception as e:
                self.db_manager.update_story_status(
                    story_id,
                    'error',
                    f'Subtitle generation failed: {str(e)}'
                )


class StoryPipeline:
    """Main pipeline for processing Reddit stories into audio with subtitles."""

    def __init__(self, config: Dict):
        """Initialize the story pipeline with configuration.

        Args:
            config (Dict): Configuration dictionary containing:
                - subreddit: Name of subreddit to crawl
                - base_dir: Base directory for story files
                - db_path: Path to SQLite database
                - whisper_model: Name of Whisper model to use
                - single_story: Whether to process only one story
        """
        self.config = config
        self.validate_config()

        # Initialize database manager
        self.db_manager = DatabaseManager(
            config.get('db_path', 'demo/story_pipeline.db'))

        # Create processors
        self.reddit_processor = RedditStoryProcessor(
            config['subreddit'],
            self.db_manager,
            config.get('single_story', False)
        )

        self.tts_processor = TextToSpeechProcessor(
            self.db_manager,
            config.get('base_dir', 'demo/stories')
        )

        self.subtitle_generator = SubtitleGenerator(
            self.db_manager,
            config.get('whisper_model', 'base')
        )

    def validate_config(self) -> None:
        """Validates the pipeline configuration."""
        InputValidator.validate_subreddit(self.config.get('subreddit'))
        base_dir = self.config.get('base_dir', 'demo/stories')
        InputValidator.validate_directories({'base_dir': base_dir})

    def run(self) -> None:
        """Runs the complete story processing pipeline."""
        try:
            logging.info("Starting story pipeline")

            # Step 1: Crawl Reddit for stories
            story_ids = self.reddit_processor.process()

            # Step 2: Convert text to speech
            self.tts_processor.process(story_ids)

            # Step 3: Generate subtitles
            self.subtitle_generator.process(story_ids)

            logging.info("Story pipeline completed successfully")

        except Exception as e:
            logging.error(f"Pipeline failed: {str(e)}")
            raise
        finally:
            self.db_manager.close()


def main():
    """Entry point for the story pipeline."""
    # Example configuration
    config = {
        'subreddit': 'tifu',
        'base_dir': 'demo/stories',
        'db_path': 'demo/story_pipeline.db',
        'whisper_model': 'base',
        'single_story': False
    }

    pipeline = StoryPipeline(config)
    pipeline.run()


if __name__ == "__main__":
    main()
