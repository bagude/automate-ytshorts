
# Shorts Automated Video Audio Narrator Tool (SAVANT)

```
.·:'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''':·.
: :                                                                                                                                                        : :
: :                                                                                                                                                        : :
: :       ____  _                _        _         _                        _           _  __     ___     _                 _             _ _             : :
: :      / ___|| |__   ___  _ __| |_     / \  _   _| |_ ___  _ __ ___   __ _| |_ ___  __| | \ \   / (_) __| | ___  ___      / \  _   _  __| (_) ___        : :
: :      \___ \| '_ \ / _ \| '__| __|   / _ \| | | | __/ _ \| '_ ` _ \ / _` | __/ _ \/ _` |  \ \ / /| |/ _` |/ _ \/ _ \    / _ \| | | |/ _` | |/ _ \       : :
: :       ___) | | | | (_) | |  | |_   / ___ \ |_| | || (_) | | | | | | (_| | ||  __/ (_| |   \ V / | | (_| |  __/ (_) |  / ___ \ |_| | (_| | | (_) |      : :
: :      |____/|_| |_|\___/|_|   \__| /_/   \_\__,_|\__\___/|_| |_| |_|\__,_|\__\___|\__,_|    \_/  |_|\__,_|\___|\___/  /_/   \_\__,_|\__,_|_|\___/       : :
: :       _   _                      _   _               _____           _            ______    ___     ___    _   _ _______                               : :
: :      | \ | | __ _ _ __ _ __ __ _| |_(_) ___  _ __   |_   _|__   ___ | |          / / ___|  / \ \   / / \  | \ | |_   _\ \                              : :
: :      |  \| |/ _` | '__| '__/ _` | __| |/ _ \| '_ \    | |/ _ \ / _ \| |  _____  | |\___ \ / _ \ \ / / _ \ |  \| | | |  | |                             : :
: :      | |\  | (_| | |  | | | (_| | |_| | (_) | | | |   | | (_) | (_) | | |_____| | | ___) / ___ \ V / ___ \| |\  | | |  | |                             : :
: :      |_| \_|\__,_|_|  |_|  \__,_|\__|_|\___/|_| |_|   |_|\___/ \___/|_|         | ||____/_/   \_\_/_/   \_\_| \_| |_|  | |                             : :
: :                                                                                  \_\                                  /_/                              : :
: :                                                                                                                                                        : :
: :                                                                                                                                                        : :
'·:........................................................................................................................................................:·'
```

An advanced automation pipeline for creating and publishing engaging YouTube Shorts from Reddit stories. This project combines natural language processing, text-to-speech generation, video processing, and automated publishing capabilities to streamline the content creation process.

## 🌟 Key Features

### Story Pipeline

- **Reddit Story Crawling**:
  - Automatically fetches engaging stories from specified subreddits
  - Single story or batch processing options
  - Support for popular subreddits like r/tifu
  - Smart duplicate detection and filtering
- **Text-to-Speech Generation**:
  - High-quality voiceovers using ElevenLabs API
  - Multiple voice options and customization
- **Subtitle Generation**: Creates accurate subtitles using Whisper API for better engagement
- **Database Management**:
  - SQLite-based story tracking system
  - Efficient state management and error handling
  - Story metadata and processing status tracking

### Video Pipeline

- **Dynamic Video Processing**:
  - Creates visually appealing shorts with background videos
  - Smart video scaling and cropping for Shorts format
- **Advanced Audio Processing**:
  - Combines voiceover with background music
  - Intelligent volume normalization
  - Audio effects and enhancements
  - Background music volume auto-adjustment
- **Professional Subtitling**:
  - Smart text segmentation for readability
  - Customizable subtitle styling
  - Fade effects for smooth transitions
  - Dynamic positioning and timing
- **Video Composition**:
  - Automatic video resizing for Shorts format (9:16)
  - Video looping for longer stories
  - Special effects and transitions
  - Progress tracking and error recovery

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- FFmpeg (for video processing)
- Required API keys:
  - ElevenLabs API key
  - Reddit API credentials (optional)


## Demo

https://github.com/user-attachments/assets/dba305d3-9ab1-49da-8f1d-fb7ba12306bd

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
python -m src.cli menu
```

### Enhanced Menu System

1. **Story Management**

   - List Stories: View all stories with advanced filtering options
   - Show Story Details: Get detailed information and processing status
   - Crawl New Stories: Fetch new stories with customizable criteria
   - Delete Story: Remove stories with cleanup
   - Retry Failed Story: Smart retry with error handling

2. **Video Creation**

   - Create Video for Story: Generate videos with progress tracking
   - Process All Ready Stories: Batch video creation with queue management
   - Retry Failed Video: Intelligent retry with error resolution
   - Preview Generated Video: Quick video preview option

3. **System Settings**

   - Configure API Keys: Manage API credentials
   - Update Video Settings: Customize video generation parameters
   - Manage Background Music: Add/remove background tracks
   - Set Processing Preferences: Adjust pipeline behavior

4. **Status and Monitoring**
   - Show Error Stories: Detailed error reporting
   - Show Ready Stories: View stories ready for processing
   - Show Processing Stories: Real-time processing status
   - System Health Check: Verify system requirements
   - Clean Up Failed Stories: Smart cleanup with recovery options

## 🎯 Quick Tutorial

### Creating Your First Video

1. Launch the menu: `python -m src.cli menu`
2. Select "Story Management"
3. Choose "Crawl New Stories"
4. Enter your preferred subreddit (e.g., "tifu")
5. Follow the interactive prompts
6. Monitor progress in the status menu
7. Generate video from the Video Creation menu

### Advanced Features

- **Story Management**:

  - Filter stories by status, subreddit, or date
  - Batch operations for multiple stories
  - Detailed error tracking and resolution

- **Video Creation**:

  - Custom background video selection
  - Subtitle style customization
  - Audio mixing controls
  - Progress monitoring

- **System Management**:
  - Database maintenance tools
  - Resource cleanup utilities
  - Performance optimization options

## 🎵 Extra Features

- **Enhanced CLI Experience**:
  - Color-coded status indicators
  - Progress bars for long operations
  - Interactive menus with keyboard navigation
- **Error Recovery**:
  - Automatic retry mechanisms
  - Detailed error logging
  - Recovery suggestions
- **Resource Management**:
  - Automatic cleanup of temporary files
  - Disk space monitoring
  - Processing queue management

## 💡 Tips

- Start with single story processing to test your setup
- Use the status menu to monitor progress
- Check system requirements before batch processing
- Utilize the preview feature before final rendering
- Keep your API keys updated in the settings

## 🤝 Contributing

Feel free to contribute to this project! Open issues, submit pull requests, or suggest new features.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

Please ensure you comply with Reddit's terms of service and content usage policies when using this tool.
