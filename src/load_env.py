import dotenv
import os
from typing import Tuple, Optional, Union


def load_env(platform: str) -> Union[Tuple[Optional[str], Optional[str]], Tuple[Optional[str],]]:
    """Load environment variables based on the platform.

    Args:
        platform (str): The platform to load credentials for ('youtube-shorts' or 'eleven-labs')

    Returns:
        Union[Tuple[Optional[str], Optional[str]], Tuple[Optional[str],]]: 
            For 'youtube-shorts': (username, password)
            For 'eleven-labs': (api_key,)
            For invalid platform: (None, None)
    """
    dotenv.load_dotenv()
    try:
        if platform == 'youtube-shorts':
            username = os.getenv('YT_USERNAME')
            password = os.getenv('YT_PASSWORD')
            return username, password
        elif platform == 'eleven-labs':
            api_key = os.getenv('ELEVEN_LABS_API_KEY')
            return (api_key,)
        else:
            return None, None
    except Exception as e:
        raise e
