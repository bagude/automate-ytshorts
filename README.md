# Automate YTShorts

An advanced automation pipeline for creating and publishing engaging YouTube Shorts from Reddit stories. This project combines natural language processing, text-to-speech generation, video processing, and automated publishing capabilities to streamline the content creation process.

## 🌟 Key Features

### Story Pipeline

- **Reddit Story Crawling**: Automatically fetches engaging stories from specified subreddits
- **Text-to-Speech Generation**: Converts stories into natural-sounding voiceovers using ElevenLabs API
- **Subtitle Generation**: Creates accurate subtitles using Whisper API for better engagement
- **Database Management**: Efficiently tracks and manages processed stories

### Video Pipeline

- **Dynamic Video Processing**: Creates visually appealing shorts with background videos
- **Advanced Audio Processing**:
  - Combines voiceover with background music
  - Intelligent volume normalization
  - Audio effects and enhancements
- **Professional Subtitling**:
  - Smart text segmentation for readability
  - Customizable subtitle styling
  - Fade effects for smooth transitions
- **Video Composition**:
  - Automatic video resizing for Shorts format
  - Video looping for longer stories
  - Special effects and transitions

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Required API keys:
  - ElevenLabs API key
  - Reddit API credentials (optional)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/automate-ytshorts.git
cd automate-ytshorts
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up your environment variables in `.env`:

```
ELEVENLABS_API_KEY=your_key_here
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=your_user_agent
```

## 📖 Usage

### Story Pipeline

```python
from story_pipeline.story_pipeline import StoryPipeline

config = {
    "subreddit": "tifu",  # or any other subreddit
    "output_dirs": {
        "json": "demo/json",
        "mp3": "demo/mp3"
    }
}

pipeline = StoryPipeline(config)
pipeline.run()
```

### Video Pipeline

```python
from video_pipeline.video_pipeline import VideoPipeline

config = {
    "video": {
        "width": 1080,
        "height": 1920
    },
    "subtitle": {
        "font": "demo/font_at.ttf",
        "font_size": 40,
        "color": "white"
    }
}

with VideoPipeline(config) as pipeline:
    pipeline.execute(
        output_path="output.mp4",
        tts_path="demo/mp3/story.mp3",
        music_path="background.mp3",
        video_path="background.mp4",
        text="Story text for subtitles"
    )
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues and pull requests.

## ⚠️ Disclaimer

Please ensure you comply with Reddit's terms of service and content usage policies when using this tool.
