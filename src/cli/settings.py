import json
import logging
from typing import Dict


def load_settings() -> Dict:
    """Load settings from file or return defaults."""
    try:
        with open('assets/settings.json', 'r') as f:
            return json.load(f)
    except:
        return {'music_enabled': True}


def save_settings(settings: Dict) -> None:
    """Save settings to file.

    Args:
        settings (Dict): Settings to save
    """
    try:
        with open('assets/settings.json', 'w') as f:
            json.dump(settings, f)
    except Exception as e:
        logging.error(f"Couldn't save settings: {str(e)}")


def get_music_enabled() -> bool:
    """Get whether background music is enabled."""
    return load_settings().get('music_enabled', True)


def set_music_enabled(enabled: bool) -> None:
    """Set whether background music is enabled.

    Args:
        enabled (bool): Whether to enable background music
    """
    settings = load_settings()
    settings['music_enabled'] = enabled
    save_settings(settings)
