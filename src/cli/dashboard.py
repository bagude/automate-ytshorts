from rich.live import Live
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from datetime import datetime
from typing import List, Optional
from ..db import Story, StoryStatus, DatabaseManager


class PipelineDashboard:
    def __init__(self, db_manager: DatabaseManager):
        self.console = Console()
        self.db_manager = db_manager

    def generate_status_table(self, stories: List[Story]) -> Table:
        """Generate a table showing story statuses."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim", width=12)
        table.add_column("Title", width=30)
        table.add_column("Status", justify="center", width=15)
        table.add_column("Progress", justify="right", width=10)
        table.add_column("Created", justify="right", width=20)

        status_colors = {
            StoryStatus.NEW: "blue",
            StoryStatus.AUDIO_GENERATED: "green",
            StoryStatus.READY: "cyan",
            StoryStatus.VIDEO_PROCESSING: "yellow",
            StoryStatus.VIDEO_READY: "green",
            StoryStatus.VIDEO_ERROR: "red",
            StoryStatus.ERROR: "red"
        }

        for story in stories:
            color = status_colors.get(story.status, "white")
            progress = self._get_progress_bar(story.status)

            table.add_row(
                story.id[:8],
                story.title[:27] +
                "..." if len(story.title) > 30 else story.title,
                f"[{color}]{story.status.value}[/{color}]",
                f"[{color}]{progress}[/{color}]",
                story.created_at.strftime("%Y-%m-%d %H:%M")
            )

        return table

    def generate_metrics_panel(self) -> Panel:
        """Generate a panel showing pipeline metrics."""
        total_stories = len(self.db_manager.get_all_stories())
        error_stories = len(
            self.db_manager.get_stories_by_status(StoryStatus.ERROR))
        ready_stories = len(
            self.db_manager.get_stories_by_status(StoryStatus.READY))
        processing_stories = len(
            self.db_manager.get_stories_by_status(StoryStatus.VIDEO_PROCESSING))

        metrics = f"""[bold]Pipeline Metrics[/bold]
        
Total Stories: {total_stories}
Ready for Video: {ready_stories}
Processing: {processing_stories}
Errors: {error_stories}"""

        return Panel(metrics, title="Metrics", border_style="green")

    def _get_progress_bar(self, status: StoryStatus) -> str:
        """Generate a progress bar based on story status."""
        progress_map = {
            StoryStatus.NEW: "▓░░░░",
            StoryStatus.AUDIO_GENERATED: "▓▓▓░░",
            StoryStatus.READY: "▓▓▓▓░",
            StoryStatus.VIDEO_PROCESSING: "▓▓▓▓░",
            StoryStatus.VIDEO_READY: "▓▓▓▓▓",
            StoryStatus.VIDEO_ERROR: "✗✗✗✗✗",
            StoryStatus.ERROR: "✗✗✗✗✗"
        }
        return progress_map.get(status, "░░░░░")

    def show_dashboard(self):
        """Show a live dashboard of pipeline status."""
        layout = Layout()

        def generate_layout():
            stories = self.db_manager.get_all_stories()
            layout.split_column(
                Layout(self.generate_metrics_panel(), size=10),
                Layout(self.generate_status_table(stories))
            )
            return layout

        with Live(generate_layout(), refresh_per_second=2, screen=True) as live:
            while True:
                live.update(generate_layout())
