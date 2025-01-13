import dotenv
import os

def load_env(platform: str) -> tuple:
    dotenv.load_dotenv()
    try:
        if platform == 'youtube-shorts':
            username = os.getenv('YT_USERNAME')
            password = os.getenv('YT_PASSWORD')
            return username, password
        elif platform == 'eleven-labs':
            api_key = os.getenv('ELEVEN_LABS_API_KEY')
            return api_key,
        else:
            return None, None
    except Exception as e:
        raise e