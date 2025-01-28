# YouTube Shorts Automation Pipeline

An automated pipeline for creating YouTube Shorts with gameplay footage, text-to-speech narration, background music, and synchronized subtitles.

## 1. Core Architecture

The pipeline is built around a modular architecture that processes media assets in a sequential flow:

```python
Video Pipeline
│
├── Input Validation
│   ├── Check file existence (video, audio, JSON)
│   └── Verify duration compatibility
│
├── Audio Processing
│   ├── TTS Audio Normalization
│   ├── Background Music Looping/Fading
│   └── Audio Mixing (Voice + Music)
│
├── Video Processing
│   ├── Resize to 1080x1920 (Vertical Shorts)
│   ├── Gameplay Footage Trimming/Looping
│   └── Background Layer (Fallback if needed)
│
├── Subtitles
│   ├── JSON Timestamp Parsing
│   ├── Fallback Timing System
│   └── Styled TextClip Generation
│
└── Composition
    ├── Layer Stacking (Background → Gameplay → Subtitles)
    └── Final Render
```

## 2. Core Components

- **Input Validation**: Ensures all required files are present and compatible.
- **Audio Processing**: Handles TTS generation, audio normalization, and background music.
- **Video Processing**: Resizes video, handles gameplay footage, and adds background layer.
- **Subtitles**: Generates synchronized subtitles with timestamps.
- **Composition**: Stacks layers and renders the final video.

## 3. How are we doing TTS at the moment?

- We're using the ElevenLabs API to generate TTS audio.

## 4. Development Roadmap

### Phase 1: Core Pipeline (Current)

- [x] Basic video pipeline architecture
- [x] ElevenLabs TTS integration
- [x] Subtitle generation with timestamps
- [] Video composition and rendering
- [x] Basic error handling

### Phase 2: Enhanced Features (In Progress)

- [ ] Advanced audio processing
  - [ ] Dynamic volume normalization
  - [ ] Smart background music mixing
  - [ ] Multiple voice support
- [ ] Improved video processing
  - [ ] Smart video cropping/scaling
  - [ ] Automated B-roll selection
  - [ ] Transition effects library
- [ ] Enhanced subtitle system
  - [ ] Multiple subtitle styles
  - [ ] Animation effects
  - [ ] Smart positioning

### Phase 3: Automation & Scaling

- [ ] Content pipeline automation
  - [x] Reddit post scraping
  - [ ] Automated content filtering
  - [ ] Batch processing system
- [ ] Quality assurance
  - [ ] Automated testing
  - [ ] Quality metrics
  - [ ] Performance monitoring

### Phase 4: Platform Integration

- [ ] YouTube integration
  - [ ] Direct upload capability
  - [ ] Analytics integration
  - [ ] Thumbnail generation
- [ ] Multi-platform support
  - [ ] TikTok export (ban?)
  - [ ] Instagram Reels
  - [ ] Custom aspect ratios

### Phase 5: Advanced Features

- [ ] AI enhancements
  - [ ] Content optimization
  - [ ] Smart video timing
  - [ ] Engagement prediction
