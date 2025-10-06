import os
import json
import logging
from datetime import datetime
from typing import List, Optional

import click
from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt
from rich.table import Table
from rich.text import Text

from ..db import DatabaseManager, Story, StoryStatus
from ..story_pipeline import StoryPipeline
from ..video_pipeline import VideoManager


console = Console()


def _status_style(status: StoryStatus) -> str:
    """Return a rich style string for a given story status."""
    palette = {
        StoryStatus.NEW: "bold blue",
        StoryStatus.AUDIO_GENERATED: "bold green",
        StoryStatus.READY: "bold cyan",
        StoryStatus.VIDEO_PROCESSING: "bold yellow",
        StoryStatus.VIDEO_READY: "bold magenta",
        StoryStatus.VIDEO_ERROR: "bold red",
        StoryStatus.ERROR: "bold red",
    }
    return palette.get(status, "bold white")


def _format_timestamp(value: datetime) -> str:
    """Format a datetime value for display."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def _render_filters(filters: List[str]) -> None:
    """Render a subtle filters badge beneath tables."""
    if not filters:
        return

    badge = Text("Filters:", style="bold dim")
    for item in filters:
        badge.append(" ")
        badge.append(f"[{item}]", style="bold white")
    console.print(Align.center(badge))


def get_db() -> DatabaseManager:
    """Get database manager instance with default configuration."""
    db_path = "demo/story_pipeline.db"
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug(f"Opening database at {db_path}")

    # Ensure the database directory exists
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(f"Creating database directory: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)

    return DatabaseManager(db_path)


@click.group()
def cli():
    """Story Pipeline CLI - Manage Reddit stories and their processing."""
    console.print(Align.center(Text("Automate YT Shorts", style="bold cyan")))
    console.print(Align.center(Text("Story Pipeline CLI", style="dim")))


@cli.command()
@click.argument('subreddit')
@click.option('--base-dir', default="demo/stories", help="Base directory for story files")
@click.option('--model', default="base", help="Whisper model to use")
@click.option('--single', is_flag=True, help="Process only the first story from the feed")
def crawl(subreddit: str, base_dir: str, model: str, single: bool):
    """Crawl stories from a subreddit and process them."""
    config = {
        'subreddit': subreddit,
        'base_dir': base_dir,
        'db_path': 'demo/story_pipeline.db',
        'whisper_model': model,
        'single_story': single
    }

    pipeline = StoryPipeline(config)
    with console.status("Running story pipeline...", spinner="dots"):
        pipeline.run()
    message = (
        f"Completed processing first story from r/{subreddit}"
        if single
        else f"Completed processing stories from r/{subreddit}"
    )
    console.print(
        Panel.fit(
            message,
            border_style="green",
            title="Crawl Complete",
        )
    )


@cli.command(name='list')
@click.option('--status', help="Filter stories by status")
@click.option('--limit', default=10, help="Limit the number of stories shown")
@click.option('--no-errors', is_flag=True, help="Hide error messages")
def list_stories(status: Optional[str], limit: int, no_errors: bool):
    """List stories in the database."""
    logging.info(f"Listing stories with status: {status}")
    with get_db() as db:
        if status:
            try:
                status_enum = StoryStatus(status)
                logging.info(f"Converted status to enum: {status_enum}")
                stories = db.get_stories_by_status(status_enum)[:limit]
            except ValueError as e:
                logging.error(
                    f"Invalid status value: {status}, error: {str(e)}")
                console.print(
                    Panel.fit(
                        f"'{status}' is not a valid status.",
                        title="Invalid Filter",
                        border_style="red",
                    )
                )
                console.print(
                    Align.center(
                        Text(
                            "Valid options: "
                            + ", ".join(s.value for s in StoryStatus),
                            style="dim",
                        )
                    )
                )
                return
        else:
            stories = db.get_all_stories()[:limit]

        if not stories:
            console.print(
                Panel.fit(
                    "No stories found for the selected filters.",
                    border_style="yellow",
                    title="Story Pipeline",
                )
            )
            return

        table = Table(
            title="Stories",
            box=box.MINIMAL_DOUBLE_HEAD,
            header_style="bold cyan",
            show_lines=True,
        )
        table.add_column("ID", style="magenta")
        table.add_column("Title", style="bold white", overflow="fold")
        table.add_column("Author", style="green")
        table.add_column("Status", style="bold")
        table.add_column("Created", style="cyan")
        table.add_column("Error", style="red", overflow="fold")

        for story in stories:
            truncated_id = story.id[:8] + "…" if len(story.id) > 8 else story.id
            title = story.title if len(story.title) <= 60 else story.title[:57] + "…"
            status_style = _status_style(story.status)
            status_value = (
                story.status.value if isinstance(story.status, StoryStatus)
                else str(story.status)
            )
            error_message = "—"
            if story.error and not no_errors:
                error_message = (
                    story.error[:70] + "…" if len(story.error) > 70 else story.error
                )
            elif story.error and no_errors:
                error_message = Text("hidden", style="dim")

            table.add_row(
                truncated_id,
                title,
                story.author or "—",
                f"[{status_style}]{status_value}[/]",
                _format_timestamp(story.created_at),
                error_message,
            )

        console.print(table)

        filters = []
        if status:
            filters.append(f"status={status}")
        if no_errors:
            filters.append("errors=hidden")
        _render_filters(filters)
        console.print(
            Align.center(
                Text(f"Showing {len(stories)} stories", style="dim")
            )
        )


@cli.command()
@click.argument('story_id')
def show(story_id: str):
    """Show detailed information about a story."""
    with get_db() as db:
        story = db.get_story(story_id)
        if not story:
            console.print(
                Panel.fit(
                    f"Story '{story_id}' was not found.",
                    title="Missing Story",
                    border_style="red",
                )
            )
            return

        header = Text(story.title, style="bold white")
        subheader = Text(
            f"u/{story.author} • r/{story.subreddit}", style="dim"
        )
        console.print(Align.center(header))
        console.print(Align.center(subheader))

        details = Table.grid(padding=(0, 2))
        details.add_column(justify="right", style="bold cyan")
        details.add_column(style="white", overflow="fold")
        details.add_row("ID", story.id)
        status_value = (
            story.status.value if isinstance(story.status, StoryStatus)
            else str(story.status)
        )
        details.add_row(
            "Status",
            f"[{_status_style(story.status)}]{status_value}[/]",
        )
        details.add_row("Created", _format_timestamp(story.created_at))

        paths = Table.grid(padding=(0, 2))
        paths.add_column(justify="right", style="bold cyan")
        paths.add_column(style="white", overflow="fold")
        paths.add_row("Audio", story.audio_path or "Not generated")
        paths.add_row("Timestamps", story.timestamps_path or "Not generated")
        paths.add_row("Subtitles", story.subtitles_path or "Not generated")

        console.print(
            Panel.fit(details, title="Story Details", border_style="cyan")
        )
        console.print(
            Panel.fit(paths, title="Asset Paths", border_style="magenta")
        )

        if story.error:
            console.print(
                Panel(
                    story.error,
                    title="Error",
                    border_style="red",
                    padding=(1, 2),
                )
            )

        console.print(
            Panel(
                story.text,
                title="Story Text",
                border_style="green",
                padding=(1, 2),
            )
        )


@cli.command()
@click.argument('story_id')
@click.option('--force', is_flag=True, help="Force deletion without confirmation")
def delete(story_id: str, force: bool):
    """Delete a story and its associated files."""
    if not force:
        if not Confirm.ask(
            f"Delete story [bold]{story_id}[/]?", default=False
        ):
            console.print(Align.center(Text("Deletion cancelled.", style="dim")))
            return

    with get_db() as db:
        story = db.get_story(story_id)
        if not story:
            console.print(
                Panel.fit(
                    f"Story '{story_id}' was not found.",
                    title="Missing Story",
                    border_style="red",
                )
            )
            return

        db.delete_story(story_id)
        console.print(
            Panel.fit(
                f"Story '{story_id}' deleted.",
                title="Removed",
                border_style="green",
            )
        )


@cli.command()
@click.argument('story_id')
def retry(story_id: str):
    """Retry processing a failed story."""
    with get_db() as db:
        story = db.get_story(story_id)
        if not story:
            console.print(
                Panel.fit(
                    f"Story '{story_id}' was not found.",
                    title="Missing Story",
                    border_style="red",
                )
            )
            return

        if story.status != StoryStatus.ERROR:
            console.print(
                Panel.fit(
                    f"Story '{story_id}' is not in an error state.\n"
                    f"Current status: {story.status.value if isinstance(story.status, StoryStatus) else story.status}",
                    border_style="yellow",
                    title="Cannot Retry",
                )
            )
            return

        # Reset story status
        db.update_story_status(story_id, StoryStatus.NEW, None)
        console.print(
            Panel.fit(
                f"Story '{story_id}' reset for reprocessing.",
                border_style="cyan",
                title="Status Reset",
            )
        )

        # Create pipeline config
        config = {
            'subreddit': story.subreddit,
            'base_dir': os.path.dirname(os.path.dirname(story.audio_path)) if story.audio_path else "demo/stories",
            'db_path': 'demo/story_pipeline.db',
            'whisper_model': 'base'
        }

        # Run pipeline for this story
        pipeline = StoryPipeline(config)
        with console.status("Regenerating assets...", spinner="dots"):
            pipeline.tts_processor.process([story_id])
            pipeline.subtitle_generator.process([story_id])

        console.print(
            Panel.fit(
                f"Completed reprocessing for story '{story_id}'.",
                border_style="green",
                title="Success",
            )
        )


@cli.command()
def cleanup():
    """Clean up failed stories and orphaned files."""
    with get_db() as db:
        # Get all error stories
        error_stories = db.get_stories_by_status(StoryStatus.ERROR)
        if not error_stories:
            console.print(
                Panel.fit(
                    "No failed stories found.",
                    border_style="green",
                    title="Cleanup",
                )
            )
            return

        if not Confirm.ask(
            f"Delete {len(error_stories)} failed stories?", default=False
        ):
            console.print(Align.center(Text("Cleanup cancelled.", style="dim")))
            return

        for story in error_stories:
            db.delete_story(story.id)
            console.print(
                f"[bold red]✖[/] Removed failed story [white]{story.id}[/]"
            )

        console.print(
            Panel.fit(
                f"Deleted {len(error_stories)} failed stories.",
                border_style="green",
                title="Cleanup Complete",
            )
        )


@cli.command()
@click.option('--story-id', help="Create video for a specific story")
@click.option('--all', 'process_all', is_flag=True, help="Process all ready stories")
def create_video(story_id: Optional[str], process_all: bool):
    """Create videos for stories that are ready."""
    if not story_id and not process_all:
        console.print(
            Panel.fit(
                "Please specify either --story-id or --all.",
                border_style="red",
                title="Missing Arguments",
            )
        )
        return

    with get_db() as db:
        video_manager = VideoManager(db)

        if process_all:
            with console.status(
                "Processing all video-ready stories...", spinner="dots"
            ):
                video_manager.process_ready_stories()
            console.print(
                Panel.fit(
                    "Processed all ready stories.",
                    border_style="green",
                    title="Video Manager",
                )
            )
        else:
            story = db.get_story(story_id)
            if not story:
                console.print(
                    Panel.fit(
                        f"Story '{story_id}' was not found.",
                        title="Missing Story",
                        border_style="red",
                    )
                )
                return

            summary = Table.grid(padding=(0, 2))
            summary.add_column(justify="right", style="bold cyan")
            summary.add_column(style="white", overflow="fold")
            summary.add_row("Title", story.title)
            summary.add_row(
                "Status",
                f"[{_status_style(story.status)}]{story.status.value if isinstance(story.status, StoryStatus) else story.status}[/]",
            )
            summary.add_row("Audio", story.audio_path or "—")
            summary.add_row("Timestamps", story.timestamps_path or "—")

            console.print(
                Panel.fit(
                    summary,
                    title=f"Story {story_id}",
                    border_style="cyan",
                )
            )

            try:
                with console.status("Rendering video...", spinner="dots"):
                    video_manager.create_video_for_story(story)
                console.print(
                    Panel.fit(
                        f"Successfully created video for story '{story_id}'.",
                        border_style="green",
                        title="Video Complete",
                    )
                )
            except Exception as e:
                console.print(
                    Panel.fit(
                        f"Failed to create video: {str(e)}",
                        border_style="red",
                        title="Video Error",
                    )
                )
                raise


@cli.command()
@click.argument('story_id')
def retry_video(story_id: str):
    """Retry video creation for a failed story."""
    with get_db() as db:
        video_manager = VideoManager(db)
        try:
            with console.status("Retrying video creation...", spinner="dots"):
                video_manager.retry_failed_video(story_id)
            console.print(
                Panel.fit(
                    f"Successfully retried video creation for story '{story_id}'.",
                    border_style="green",
                    title="Video Complete",
                )
            )
        except Exception as e:
            console.print(
                Panel.fit(
                    f"Failed to retry video creation: {str(e)}",
                    border_style="red",
                    title="Video Error",
                )
            )


@cli.command()
@click.option('--keep-files', is_flag=True, help="Keep generated files on disk")
@click.option('--force', is_flag=True, help="Skip confirmation prompt")
def reset(keep_files: bool, force: bool):
    """Reset the database to factory settings.

    This will delete all stories and optionally remove all generated files.
    Use with caution as this operation cannot be undone.
    """
    if not force:
        warning = "⚠️ WARNING: This will delete all stories from the database"
        if not keep_files:
            warning += " and remove all generated files"
        warning += ".\nThis action cannot be undone!"

        console.print(
            Panel(
                warning,
                border_style="red",
                title="Danger Zone",
                padding=(1, 2),
            )
        )
        if not Confirm.ask("Proceed with reset?", default=False):
            console.print(Align.center(Text("Reset cancelled.", style="dim")))
            return

    try:
        with get_db() as db:
            with console.status("Resetting database...", spinner="dots"):
                db.cleanup_database(remove_files=not keep_files)
            console.print(
                Panel.fit(
                    "Database has been reset to factory settings.",
                    border_style="green",
                    title="Reset Complete",
                )
            )
            if not keep_files:
                console.print("[dim]All generated files were removed.[/]")
    except Exception as e:
        console.print(
            Panel.fit(
                f"Error during reset: {str(e)}",
                border_style="red",
                title="Reset Failed",
            )
        )
        raise


@cli.command()
@click.argument('story_id')
def remake_video(story_id: str):
    """Remake video for a story using existing TTS and timestamps files.

    This only runs the video creation step, assuming all required files exist.
    """
    with get_db() as db:
        story = db.get_story(story_id)
        if not story:
            console.print(
                Panel.fit(
                    f"Story '{story_id}' was not found.",
                    title="Missing Story",
                    border_style="red",
                )
            )
            return

        if not story.audio_path or not story.timestamps_path:
            status_table = Table.grid(padding=(0, 2))
            status_table.add_column(justify="right", style="bold cyan")
            status_table.add_column(style="white")
            status_table.add_row("Audio", "✅" if story.audio_path else "❌")
            status_table.add_row(
                "Timestamps", "✅" if story.timestamps_path else "❌"
            )
            console.print(
                Panel.fit(
                    status_table,
                    title="Missing Files",
                    border_style="yellow",
                )
            )
            return

        try:
            from ..video_pipeline.video_pipeline import VideoPipeline, DEFAULT_CONFIG

            # Set up output path
            output_dir = os.path.join("demo", "videos", story.id)
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "final.mp4")

            with console.status("Rendering video...", spinner="dots"):
                with VideoPipeline(DEFAULT_CONFIG) as pipeline:
                    pipeline.execute(
                        output_path=output_path,
                        tts_path=story.audio_path,
                        music_path=os.path.join("demo", "mp3", "bg_music.mp3"),
                        video_path=os.path.join("demo", "mp4", "background.mp4"),
                        text=story.text,
                        subtitle_json=story.timestamps_path
                    )
            console.print(
                Panel.fit(
                    f"Successfully created video: {output_path}",
                    border_style="green",
                    title="Video Complete",
                )
            )

        except Exception as e:
            console.print(
                Panel.fit(
                    f"Failed to create video: {str(e)}",
                    border_style="red",
                    title="Video Error",
                )
            )
            raise


@cli.command()
@click.argument('story_id')
def remake_subtitles(story_id: str):
    """Remake subtitles for a story using existing TTS and timestamps files.

    This only runs the subtitle generation step, assuming the required files exist.
    """
    with get_db() as db:
        story = db.get_story(story_id)
        if not story:
            console.print(
                Panel.fit(
                    f"Story '{story_id}' was not found.",
                    title="Missing Story",
                    border_style="red",
                )
            )
            return

        if not story.audio_path or not story.timestamps_path:
            status_table = Table.grid(padding=(0, 2))
            status_table.add_column(justify="right", style="bold cyan")
            status_table.add_column(style="white")
            status_table.add_row("Audio", "✅" if story.audio_path else "❌")
            status_table.add_row(
                "Timestamps", "✅" if story.timestamps_path else "❌"
            )
            console.print(
                Panel.fit(
                    status_table,
                    title="Missing Files",
                    border_style="yellow",
                )
            )
            return

        try:
            from ..video_pipeline.video_pipeline import SubtitleEngine, DEFAULT_CONFIG

            with console.status("Regenerating subtitles...", spinner="dots"):
                subtitle_engine = SubtitleEngine(DEFAULT_CONFIG)
                subtitle_engine.generate_subtitles(
                    text=story.text,
                    duration=60,
                    subtitle_json=story.timestamps_path
                )
            console.print(
                Panel.fit(
                    "Successfully regenerated subtitles.",
                    border_style="green",
                    title="Subtitles Complete",
                )
            )

            if Confirm.ask(
                "Remake the video with the new subtitles?", default=False
            ):
                ctx = click.get_current_context()
                ctx.invoke(remake_video, story_id=story_id)

        except Exception as e:
            console.print(
                Panel.fit(
                    f"Failed to generate subtitles: {str(e)}",
                    border_style="red",
                    title="Subtitle Error",
                )
            )
            raise


@cli.group()
def files():
    """File management commands."""
    pass


@files.command()
@click.argument('story_id', required=False)
@click.option('--all', 'verify_all', is_flag=True, help="Verify all stories")
def verify(story_id: Optional[str], verify_all: bool):
    """Verify file integrity and show detailed file information.

    If no story_id is provided and --all is not set, shows a menu to select a story.
    """
    with get_db() as db:
        stories = []
        if verify_all:
            stories = db.get_all_stories()
        elif story_id:
            story = db.get_story(story_id)
            if not story:
                console.print(
                    Panel.fit(
                        f"Story '{story_id}' was not found.",
                        title="Missing Story",
                        border_style="red",
                    )
                )
                return
            stories = [story]
        else:
            # Show menu to select story
            story_id = _show_available_stories()
            if not story_id:
                return
            story = db.get_story(story_id)
            if story:
                stories = [story]

        if not stories:
            console.print(
                Panel.fit(
                    "No stories to verify.",
                    border_style="yellow",
                    title="Verification",
                )
            )
            return

        for story in stories:
            console.rule(Text(f"Story {story.id}", style="bold magenta"))
            header = Table.grid(padding=(0, 2))
            header.add_column(justify="right", style="bold cyan")
            header.add_column(style="white", overflow="fold")
            header.add_row("Title", story.title)
            header.add_row(
                "Status",
                f"[{_status_style(story.status)}]{story.status.value if isinstance(story.status, StoryStatus) else story.status}[/]",
            )
            header.add_row("Author", f"u/{story.author}")
            header.add_row("Created", _format_timestamp(story.created_at))
            console.print(Panel.fit(header, border_style="cyan"))

            # Check TTS audio file
            asset_table = Table(
                title="Assets",
                box=box.SIMPLE_HEAVY,
                header_style="bold cyan",
                show_lines=True,
            )
            asset_table.add_column("Asset", style="bold")
            asset_table.add_column("Status", style="white")
            asset_table.add_column("Path", style="dim", overflow="fold")
            asset_table.add_column("Size", justify="right")
            asset_table.add_column("Modified", justify="right")

            def add_asset(label: str, path: Optional[str], unit: str) -> bool:
                if not path:
                    asset_table.add_row(
                        label,
                        "[yellow]No path configured[/]",
                        "—",
                        "—",
                        "—",
                    )
                    return False
                if os.path.exists(path):
                    size_bytes = os.path.getsize(path)
                    if unit == "MB":
                        size_value = size_bytes / 1024 / 1024
                    else:
                        size_value = size_bytes / 1024
                    modified_time = datetime.fromtimestamp(
                        os.path.getmtime(path)
                    ).strftime('%Y-%m-%d %H:%M:%S')
                    asset_table.add_row(
                        label,
                        "[green]Available[/]",
                        path,
                        f"{size_value:.2f} {unit}",
                        modified_time,
                    )
                    return True

                asset_table.add_row(
                    label,
                    "[red]Missing file[/]",
                    path,
                    "—",
                    "—",
                )
                return False

            has_audio = add_asset("TTS Audio", story.audio_path, "KB")
            has_timestamps = add_asset(
                "Timestamps", story.timestamps_path, "KB"
            )
            video_dir = os.path.join("demo", "videos", story.id)
            video_path = os.path.join(video_dir, "final.mp4")
            has_video = add_asset("Video", video_path, "MB")

            console.print(asset_table)

            # Status consistency check
            alerts: List[Text] = []
            status_value = (
                story.status if isinstance(story.status, StoryStatus) else StoryStatus(story.status)
            )
            if status_value == StoryStatus.NEW and (has_audio or has_timestamps or has_video):
                alerts.append(Text("Status is NEW but files exist", style="yellow"))
            elif status_value == StoryStatus.AUDIO_GENERATED and not has_audio:
                alerts.append(Text("Audio generated status but audio file missing", style="red"))
            elif status_value == StoryStatus.READY and (not has_audio or not has_timestamps):
                alerts.append(Text("READY status but required files missing", style="red"))
            elif status_value == StoryStatus.VIDEO_READY and not has_video:
                alerts.append(Text("VIDEO_READY status but video missing", style="red"))
            elif status_value == StoryStatus.VIDEO_PROCESSING and has_video:
                alerts.append(Text("VIDEO_PROCESSING status but video already exists", style="yellow"))

            if alerts:
                summary = Text()
                for alert in alerts:
                    summary.append("• ")
                    summary.append(alert)
                    summary.append("\n")
                console.print(
                    Panel(
                        summary,
                        border_style="yellow",
                        title="Status Check",
                    )
                )
            else:
                console.print(
                    Panel.fit(
                        "Status consistent with files.",
                        border_style="green",
                        title="Status Check",
                    )
                )


@files.command()
@click.argument('story_id', required=False)
@click.option('--file-type', type=click.Choice(['text', 'timestamps', 'all']), default='all',
              help="Type of file to preview")
def preview(story_id: Optional[str], file_type: str):
    """Preview story files (text and timestamps).

    If no story_id is provided, shows a menu to select a story.
    """
    with get_db() as db:
        if not story_id:
            story_id = _show_available_stories()
            if not story_id:
                return

        story = db.get_story(story_id)
        if not story:
            console.print(
                Panel.fit(
                    f"Story '{story_id}' was not found.",
                    title="Missing Story",
                    border_style="red",
                )
            )
            return

        if file_type in ['text', 'all']:
            console.print(
                Panel(
                    story.text,
                    title="Story Text",
                    border_style="green",
                    padding=(1, 2),
                )
            )

        if file_type in ['timestamps', 'all'] and story.timestamps_path:
            if os.path.exists(story.timestamps_path):
                table = Table(
                    title="Timestamps",
                    box=box.SIMPLE_HEAVY,
                    header_style="bold cyan",
                )
                table.add_column("Start", justify="right")
                table.add_column("End", justify="right")
                table.add_column("Text", style="white", overflow="fold")
                try:
                    with open(story.timestamps_path, 'r', encoding='utf-8') as f:
                        timestamps_data = json.load(f)

                    if 'segments' in timestamps_data:  # Whisper format
                        for segment in timestamps_data['segments']:
                            start = segment.get('start', 0)
                            end = segment.get('end', 0)
                            text = segment.get('text', '').strip()
                            table.add_row(
                                f"{start:.2f}s",
                                f"{end:.2f}s",
                                text or "—",
                            )
                    else:  # ElevenLabs format
                        for segment in timestamps_data:
                            if 'characters' in segment and 'character_start_times_seconds' in segment:
                                chars = segment['characters']
                                times = segment['character_start_times_seconds']
                                text = ''.join(chars)
                                start = times[0] if times else 0
                                end = times[-1] if times else 0
                                table.add_row(
                                    f"{start:.2f}s",
                                    f"{end:.2f}s",
                                    text or "—",
                                )
                    console.print(table)
                except json.JSONDecodeError:
                    console.print(
                        Panel.fit(
                            "Invalid JSON format in timestamps file.",
                            border_style="red",
                            title="Timestamps Error",
                        )
                    )
                except Exception as e:
                    console.print(
                        Panel.fit(
                            f"Error reading timestamps: {str(e)}",
                            border_style="red",
                            title="Timestamps Error",
                        )
                    )
            else:
                console.print(
                    Panel.fit(
                        "Timestamps file not found.",
                        border_style="red",
                        title="Timestamps",
                    )
                )


def _show_available_stories() -> Optional[str]:
    """Show a menu of available stories and return the selected story ID."""
    with get_db() as db:
        stories = db.get_all_stories()
        if not stories:
            console.print(
                Panel.fit(
                    "No stories available.",
                    border_style="yellow",
                    title="Stories",
                )
            )
            return None

        table = Table(
            title="Available Stories",
            box=box.SIMPLE_HEAVY,
            header_style="bold cyan",
        )
        table.add_column("#", justify="right")
        table.add_column("Title", style="white", overflow="fold")
        table.add_column("Status", style="bold")
        table.add_column("Author", style="green")
        table.add_column("Created", style="dim")

        for index, story in enumerate(stories, 1):
            title = story.title[:60] + "…" if len(story.title) > 60 else story.title
            created = _format_timestamp(story.created_at)
            status_value = (
                story.status.value if isinstance(story.status, StoryStatus) else str(story.status)
            )
            table.add_row(
                str(index),
                title,
                f"[{_status_style(story.status)}]{status_value}[/]",
                story.author,
                created,
            )

        console.print(table)
        console.print(Align.center(Text("Enter 0 to cancel", style="dim")))

        while True:
            try:
                choice = IntPrompt.ask("Select a story", default=0)
            except (KeyboardInterrupt, EOFError):
                return None

            if choice == 0:
                return None
            if 1 <= choice <= len(stories):
                return stories[choice - 1].id
            console.print(
                Panel.fit(
                    "Invalid choice. Please try again.",
                    border_style="red",
                    title="Selection",
                )
            )


@files.command()
@click.argument('story_id', required=False)
@click.option('--output-dir', default='backups', help="Directory to store backups")
def backup(story_id: Optional[str], output_dir: str):
    """Backup story files to a zip archive.

    If no story_id is provided, shows a menu to select a story.
    """
    import tempfile
    import zipfile
    import shutil

    with get_db() as db:
        if not story_id:
            story_id = _show_available_stories()
            if not story_id:
                return

        story = db.get_story(story_id)
        if not story:
            console.print(
                Panel.fit(
                    f"Story '{story_id}' was not found.",
                    title="Missing Story",
                    border_style="red",
                )
            )
            return

        # Create backup directory
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{story.id}_{timestamp}"
        backup_path = os.path.join(output_dir, f"{backup_name}.zip")
        files_copied = []

        try:
            # Create temporary directory for files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Copy story metadata
                metadata_path = os.path.join(temp_dir, "story.json")
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'id': story.id,
                        'title': story.title,
                        'author': story.author,
                        'subreddit': story.subreddit,
                        'url': story.url,
                        'text': story.text,
                        'created_at': story.created_at.isoformat(),
                        'status': str(story.status)
                    }, f, indent=2)
                files_copied.append(('Story metadata', metadata_path))

                # Copy TTS audio
                if story.audio_path and os.path.exists(story.audio_path):
                    audio_dest = os.path.join(temp_dir, "audio.mp3")
                    shutil.copy2(story.audio_path, audio_dest)
                    files_copied.append(('TTS Audio', story.audio_path))

                # Copy timestamps
                if story.timestamps_path and os.path.exists(story.timestamps_path):
                    timestamps_dest = os.path.join(temp_dir, "timestamps.json")
                    shutil.copy2(story.timestamps_path, timestamps_dest)
                    files_copied.append(('Timestamps', story.timestamps_path))

                # Copy video if exists
                video_path = os.path.join(
                    "demo", "videos", story.id, "final.mp4")
                if os.path.exists(video_path):
                    video_dest = os.path.join(temp_dir, "video.mp4")
                    shutil.copy2(video_path, video_dest)
                    files_copied.append(('Video', video_path))

                if not files_copied:
                    console.print(
                        Panel.fit(
                            "No files found to backup!",
                            border_style="yellow",
                            title="Backup",
                        )
                    )
                    return

                # Create zip archive
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arcname)

            # Show summary
            table = Table(
                title="Files Included",
                box=box.SIMPLE_HEAVY,
                header_style="bold cyan",
            )
            table.add_column("Type", style="bold")
            table.add_column("Path", style="white", overflow="fold")
            table.add_column("Size", justify="right")
            for file_type, path in files_copied:
                size_kb = os.path.getsize(path) / 1024
                table.add_row(
                    file_type,
                    path,
                    f"{size_kb:.2f} KB",
                )

            console.print(
                Panel.fit(
                    f"Created backup: {backup_path}",
                    border_style="green",
                    title="Backup Complete",
                )
            )
            console.print(table)

        except Exception as e:
            if backup_path and os.path.exists(backup_path):
                try:
                    # Clean up partial backup if it exists
                    os.remove(backup_path)
                except:
                    pass
            console.print(
                Panel.fit(
                    f"Error creating backup: {str(e)}",
                    border_style="red",
                    title="Backup Failed",
                )
            )
            raise


@files.command()
@click.argument('backup_path')
@click.option('--force', is_flag=True, help="Overwrite existing files")
def restore(backup_path: str, force: bool):
    """Restore story files from a backup archive."""
    if not os.path.exists(backup_path):
        console.print(
            Panel.fit(
                f"Backup file not found: {backup_path}",
                border_style="red",
                title="Restore",
            )
        )
        return

    try:
        import tempfile
        import zipfile
        import shutil

        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract backup
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)

            # Read story metadata
            metadata_path = os.path.join(temp_dir, "story.json")
            if not os.path.exists(metadata_path):
                console.print(
                    Panel.fit(
                        "Invalid backup: missing story metadata.",
                        border_style="red",
                        title="Restore",
                    )
                )
                return

            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Confirm restoration
            details = Table.grid(padding=(0, 2))
            details.add_column(justify="right", style="bold cyan")
            details.add_column(style="white")
            details.add_row("Title", metadata['title'])
            details.add_row("Author", metadata['author'])
            details.add_row("ID", metadata['id'])
            console.print(Panel.fit(details, title="Restore Preview", border_style="cyan"))

            if not force and not Confirm.ask("Proceed with restore?", default=False):
                console.print(Align.center(Text("Restore cancelled.", style="dim")))
                return

            # Restore files
            story_id = metadata['id']
            files_restored = []

            # Restore TTS audio
            audio_src = os.path.join(temp_dir, "audio.mp3")
            if os.path.exists(audio_src):
                audio_dest = os.path.join(
                    "demo", "stories", story_id, "audio.mp3")
                os.makedirs(os.path.dirname(audio_dest), exist_ok=True)
                shutil.copy2(audio_src, audio_dest)
                files_restored.append(('TTS Audio', audio_dest))

            # Restore timestamps
            timestamps_src = os.path.join(temp_dir, "timestamps.json")
            if os.path.exists(timestamps_src):
                timestamps_dest = os.path.join(
                    "demo", "stories", story_id, "timestamps.json")
                os.makedirs(os.path.dirname(timestamps_dest), exist_ok=True)
                shutil.copy2(timestamps_src, timestamps_dest)
                files_restored.append(('Timestamps', timestamps_dest))

            # Restore video
            video_src = os.path.join(temp_dir, "video.mp4")
            if os.path.exists(video_src):
                video_dest = os.path.join(
                    "demo", "videos", story_id, "final.mp4")
                os.makedirs(os.path.dirname(video_dest), exist_ok=True)
                shutil.copy2(video_src, video_dest)
                files_restored.append(('Video', video_dest))

            # Update database
            with get_db() as db:
                story = Story(
                    id=metadata['id'],
                    title=metadata['title'],
                    author=metadata['author'],
                    subreddit=metadata['subreddit'],
                    url=metadata['url'],
                    text=metadata['text'],
                    created_at=datetime.fromisoformat(metadata['created_at']),
                    status=metadata['status'],
                    audio_path=next(
                        (dest for type_, dest in files_restored if type_ == 'TTS Audio'), None),
                    timestamps_path=next(
                        (dest for type_, dest in files_restored if type_ == 'Timestamps'), None),
                    subtitles_path=next(
                        (dest for type_, dest in files_restored if type_ == 'Video'), None)
                )

                existing_story = db.get_story(story_id)
                if existing_story:
                    if not force and not Confirm.ask(
                        f"Story {story_id} already exists. Update it?",
                        default=True,
                    ):
                        console.print(Align.center(Text("Database update skipped.", style="dim")))
                    else:
                        db.delete_story(story_id)
                        db.add_story(story)
                        console.print(
                            Panel.fit(
                                "Updated existing story in database.",
                                border_style="green",
                                title="Database",
                            )
                        )
                else:
                    db.add_story(story)
                    console.print(
                        Panel.fit(
                            "Added new story to database.",
                            border_style="green",
                            title="Database",
                        )
                    )

            # Show summary
            table = Table(
                title="Files Restored",
                box=box.SIMPLE_HEAVY,
                header_style="bold cyan",
            )
            table.add_column("Type", style="bold")
            table.add_column("Path", style="white", overflow="fold")
            table.add_column("Size", justify="right")
            for file_type, path in files_restored:
                size_kb = os.path.getsize(path) / 1024
                table.add_row(file_type, path, f"{size_kb:.2f} KB")

            console.print(
                Panel.fit(
                    "Restore completed successfully.",
                    border_style="green",
                    title="Restore Complete",
                )
            )
            console.print(table)

    except Exception as e:
        console.print(
            Panel.fit(
                f"Error restoring backup: {str(e)}",
                border_style="red",
                title="Restore Failed",
            )
        )
        raise


if __name__ == '__main__':
    cli()
