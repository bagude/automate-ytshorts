from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, BarColumn, TextColumn
from rich.console import Console
from rich.live import Live
from rich.table import Table
from typing import Dict, Optional
from ..db import StoryStatus
import time


class PipelineProgress:
    def __init__(self):
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        )
        self._story_status: Dict[str, Dict] = {}

    def track_story(self, story_id: str, title: str):
        """Start tracking progress for a story."""
        self._story_status[story_id] = {
            'crawl': self.progress.add_task(f"[green]Crawling: {title}", total=100),
            'tts': self.progress.add_task(f"[yellow]Generating audio: {title}", total=100, visible=False),
            'subtitle': self.progress.add_task(f"[blue]Creating subtitles: {title}", total=100, visible=False),
            'video': self.progress.add_task(f"[red]Rendering video: {title}", total=100, visible=False)
        }

    def update_progress(self, story_id: str, status: StoryStatus, progress: float):
        """Update progress for a story based on its status."""
        if story_id not in self._story_status:
            return

        tasks = self._story_status[story_id]

        # Show/hide tasks based on status
        if status == StoryStatus.NEW:
            self.progress.update(tasks['crawl'], completed=int(progress * 100))
        elif status == StoryStatus.AUDIO_PROCESSING:
            self.progress.update(tasks['crawl'], completed=100, visible=False)
            self.progress.update(
                tasks['tts'], visible=True, completed=int(progress * 100))
        elif status == StoryStatus.AUDIO_GENERATED:
            self.progress.update(tasks['tts'], completed=100, visible=False)
            self.progress.update(
                tasks['subtitle'], visible=True, completed=int(progress * 100))
        elif status == StoryStatus.READY:
            self.progress.update(
                tasks['subtitle'], completed=100, visible=False)
            self.progress.update(
                tasks['video'], visible=True, completed=int(progress * 100))
        elif status == StoryStatus.VIDEO_READY:
            self.progress.update(tasks['video'], completed=100)

    def start(self):
        """Start the progress display."""
        return self.progress

    def stop(self):
        """Stop tracking all stories."""
        self._story_status.clear()
        self.progress.stop()
