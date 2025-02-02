# Automate YTShorts

An advanced automation pipeline for creating and publishing engaging YouTube Shorts from Reddit stories. This project combines natural language processing, text-to-speech generation, video processing, and automated publishing capabilities to streamline the content creation process.

## 🌟 Key Features

### Story Pipeline

- **Reddit Story Crawling**:
  - Automatically fetches engaging stories from specified subreddits
  - Single story or batch processing options
  - Support for popular subreddits like r/tifu
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

## 📖 Interactive Menu Usage

Launch the interactive menu with:

```bash
python -m src.story_pipeline.cli menu
```

### Main Menu Options

1. **Story Management**

   - List Stories: View all stories in the database
   - Show Story Details: Get detailed information about a specific story
   - Crawl New Stories: Fetch new stories from Reddit
   - Delete Story: Remove a story from the database
   - Retry Failed Story: Retry processing a failed story

2. **Video Creation**

   - Create Video for Story: Generate a video for a specific story
   - Process All Ready Stories: Create videos for all stories marked as ready
   - Retry Failed Video: Retry video creation for a failed story

3. **System Status**
   - Show Error Stories: List stories with errors
   - Show Ready Stories: List stories ready for video creation
   - Show Processing Stories: List stories currently being processed
   - Clean Up Failed Stories: Remove failed stories from the database

## 🎯 Quick Tutorial

### Creating Your First Video

1. Launch the menu: `python -m src.story_pipeline.cli menu`
2. Select "Story Management" (Option 1)
3. Choose "Crawl New Stories" (Option 3)
4. Enter "tifu" as the subreddit
5. Choose "yes" to process only one story (recommended for testing)
6. Wait for the story to be processed
7. Go back to main menu and select "Video Creation" (Option 2)
8. Choose "Create Video for Story" (Option 1)
9. Select your story from the list
10. Wait for video creation to complete

### Managing Stories

- Use the Story Management menu to:
  - View all stories with `List Stories`
  - Check story details including status and error messages
  - Delete unwanted stories
  - Retry failed stories

### Creating Videos

- Use the Video Creation menu to:
  - Create videos for individual stories
  - Batch process all ready stories
  - Retry failed video creations

### Monitoring Status

- Use the System Status menu to:
  - Track story processing status
  - Identify and fix errors
  - Clean up failed stories

## 🎵 Extra Features

- **Retro Menu Music**: Enjoy a nostalgic bit-tune while navigating the menus
- **Interactive Story Selection**: Easy-to-use numbered menu for story selection
- **Error Handling**: Graceful error handling with helpful messages
- **Status Tracking**: Comprehensive status tracking for all processing stages

## 💡 Tips

- Start with single story processing to test your setup
- Use the status menu to monitor story processing
- Check story details before video creation to ensure all required files are present
- Use the retry options if processing fails

## 🤝 Contributing

Feel free to contribute to this project! Open issues, submit pull requests, or suggest new features.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

Please ensure you comply with Reddit's terms of service and content usage policies when using this tool.
