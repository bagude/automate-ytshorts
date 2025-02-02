import os
from typing import Dict


def get_story_folder_path(story_id: str, base_dir: str = "demo/stories") -> str:
    """Get the folder path for a story.

    Args:
        story_id (str): ID of the story
        base_dir (str): Base directory for stories

    Returns:
        str: Path to the story folder
    """
    folder_path = os.path.join(base_dir, story_id)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def get_story_file_paths(story_id: str, base_dir: str = "demo/stories") -> Dict[str, str]:
    """Get the file paths for a story's assets.

    Args:
        story_id (str): ID of the story
        base_dir (str): Base directory for stories

    Returns:
        Dict[str, str]: Dictionary containing paths for story assets
    """
    folder_path = get_story_folder_path(story_id, base_dir)
    return {
        "audio": os.path.join(folder_path, "audio.mp3"),
        "timestamps": os.path.join(folder_path, "timestamps.json"),
        "subtitles": os.path.join(folder_path, "subtitles.srt"),
        "story_json": os.path.join(folder_path, f"{story_id}.json")
    }
