
import os
import dotenv


class Pipeline:
    def __init__(
        self,
        platform: str, 
        video_fp: str,
        *args,
        **kwargs  
    ):
    
        self.platform = platform
        self.video_fp = video_fp
        self.args = args
        self.kwargs = kwargs

    def load_env(self) -> tuple:
        dotenv.load_dotenv()
        try:
            if self.platform == 'youtube-shorts':
                username = os.getenv('YT_USERNAME')
                password = os.getenv('YT_PASSWORD')
                return username, password
            else:
                return None, None
        except Exception as e:
            raise e
        
    



def main():

    pipeline = Pipeline(
        platform='youtube-shorts',
        video_fp='path/to/video.mp4'
    )
    print(pipeline.platform, pipeline.video_fp)

if __name__ == '__main__':
    main()