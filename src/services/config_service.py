from typing import Dict, Optional
import os
import json
from pathlib import Path


class ConfigService:
    def __init__(self, config_path: str = "config/settings.json"):
        self.config_path = config_path
        self._ensure_config_dir()
        self.config = self._load_config()

    def _ensure_config_dir(self) -> None:
        """Ensures the configuration directory exists."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

    def _load_config(self) -> Dict:
        """Loads configuration from file or creates default."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return self._create_default_config()

    def _create_default_config(self) -> Dict:
        """Creates and saves default configuration."""
        default_config = {
            'story_pipeline': {
                'base_dir': 'demo/stories',
                'db_path': 'demo/story_pipeline.db',
                'whisper_model': 'base'
            },
            'video_pipeline': {
                'output_dir': 'demo/videos',
                'background_dir': 'assets/backgrounds',
                'music_dir': 'assets/music'
            }
        }
        self.save_config(default_config)
        return default_config

    def save_config(self, config: Dict) -> None:
        """Saves configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=4)

    def get_story_pipeline_config(self, subreddit: str, single_story: bool = False) -> Dict:
        """Gets configuration for story pipeline."""
        config = self.config['story_pipeline'].copy()
        config.update({
            'subreddit': subreddit,
            'single_story': single_story
        })
        return config

    def get_video_pipeline_config(self) -> Dict:
        """Gets configuration for video pipeline."""
        return self.config['video_pipeline'].copy()

    def update_config(self, section: str, key: str, value: any) -> None:
        """Updates a specific configuration value."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save_config(self.config)
