import os
import click
import logging
from typing import Optional, List
from tabulate import tabulate
from datetime import datetime
from threading import Thread
from playsound import playsound

from .db_manager import DatabaseManager, Story
from .story_pipeline import StoryPipeline
from ..video_pipeline.video_manager import VideoManager

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def get_db() -> DatabaseManager:
    """Get database manager instance with default configuration."""
    return DatabaseManager("demo/story_pipeline.db")


def format_story_row(story: Story) -> List[str]:
    """Format a story for tabular display."""
    try:
        created_at = story.created_at.strftime(
            "%Y-%m-%d %H:%M") if isinstance(story.created_at, datetime) else str(story.created_at)
    except (AttributeError, ValueError):
        created_at = "Unknown"

    return [
        story.id[:8] + "...",  # Truncated ID
        story.title[:30] + "..." if len(story.title) > 30 else story.title,
        story.author,
        story.status,
        created_at,
        story.error[:50] + \
        "..." if story.error and len(story.error) > 50 else story.error or ""
    ]


@click.group()
def cli():
    """Story Pipeline CLI - Manage Reddit stories and their processing."""
    pass


@cli.command()
@click.argument('subreddit')
@click.option('--base-dir', default="demo/stories", help="Base directory for story files")
@click.option('--model', default="base", help="Whisper model to use")
@click.option('--single', is_flag=True, help="Process only the first story from the feed")
def crawl(subreddit: str, base_dir: str, model: str, single: bool):
    """Crawl stories from a subreddit and process them. Use --single to process only the first story."""
    config = {
        'subreddit': subreddit,
        'base_dir': base_dir,
        'db_path': 'demo/story_pipeline.db',
        'whisper_model': model,
        'single_story': single
    }

    pipeline = StoryPipeline(config)
    pipeline.run()
    if single:
        click.echo(f"Completed processing first story from r/{subreddit}")
    else:
        click.echo(f"Completed processing stories from r/{subreddit}")


@cli.command(name='list')
@click.option('--status', help="Filter stories by status")
@click.option('--limit', default=10, help="Limit the number of stories shown")
@click.option('--no-errors', is_flag=True, help="Hide error messages")
def list_stories(status: Optional[str], limit: int, no_errors: bool):
    """List stories in the database."""
    with get_db() as db:
        if status:
            stories = db.get_stories_by_status(status)[:limit]
        else:
            stories = db.get_all_stories()[:limit]

        if not stories:
            click.echo("No stories found.")
            return

        headers = ["ID", "Title", "Author", "Status", "Created", "Error"]
        rows = [format_story_row(story) for story in stories]

        click.echo(tabulate(rows, headers=headers, tablefmt="grid"))

        # Add summary of filters applied
        filters = []
        if status:
            filters.append(f"status='{status}'")
        if no_errors:
            filters.append("no-errors")
        filter_text = f" (filtered by {', '.join(filters)})" if filters else ""
        click.echo(f"\nShowing {len(stories)} stories{filter_text}")


@cli.command()
@click.argument('story_id')
def show(story_id: str):
    """Show detailed information about a story."""
    with get_db() as db:
        story = db.get_story(story_id)
        if not story:
            click.echo(f"Story {story_id} not found.")
            return

        click.echo("\nStory Details:")
        click.echo("=" * 50)
        click.echo(f"ID:        {story.id}")
        click.echo(f"Title:     {story.title}")
        click.echo(f"Author:    {story.author}")
        click.echo(f"Subreddit: r/{story.subreddit}")
        click.echo(f"Status:    {story.status}")
        click.echo(f"Created:   {story.created_at}")
        click.echo("\nPaths:")
        click.echo(f"Audio:      {story.audio_path or 'Not generated'}")
        click.echo(f"Timestamps: {story.timestamps_path or 'Not generated'}")
        click.echo(f"Subtitles:  {story.subtitles_path or 'Not generated'}")
        if story.error:
            click.echo(f"\nError:\n{story.error}")
        click.echo("\nText:")
        click.echo("-" * 50)
        click.echo(story.text)


@cli.command()
@click.argument('story_id')
@click.option('--force', is_flag=True, help="Force deletion without confirmation")
def delete(story_id: str, force: bool):
    """Delete a story and its associated files."""
    if not force and not click.confirm(f"Are you sure you want to delete story {story_id}?"):
        return

    with get_db() as db:
        story = db.get_story(story_id)
        if not story:
            click.echo(f"Story {story_id} not found.")
            return

        db.delete_story(story_id)
        click.echo(f"Deleted story {story_id}")


@cli.command()
@click.argument('story_id')
def retry(story_id: str):
    """Retry processing a failed story."""
    with get_db() as db:
        story = db.get_story(story_id)
        if not story:
            click.echo(
                f"Story {story_id} is not in error state (current status: {story.status})")
            return

        if story.status != 'error':
            click.echo(
                f"Story {story_id} is not in error state (current status: {story.status})")
            return

        # Reset story status
        db.update_story_status(story_id, 'new', None)
        click.echo(f"Reset story {story_id} for reprocessing")

        # Create pipeline config
        config = {
            'subreddit': story.subreddit,
            'base_dir': os.path.dirname(os.path.dirname(story.audio_path)) if story.audio_path else "demo/stories",
            'db_path': 'demo/story_pipeline.db',
            'whisper_model': 'base'
        }

        # Run pipeline for this story
        pipeline = StoryPipeline(config)
        pipeline.tts_processor.process([story_id])
        pipeline.subtitle_generator.process([story_id])
        click.echo(f"Completed reprocessing story {story_id}")


@cli.command()
def cleanup():
    """Clean up failed stories and orphaned files."""
    with get_db() as db:
        # Get all error stories
        error_stories = db.get_stories_by_status('error')
        if not error_stories:
            click.echo("No failed stories found.")
            return

        if not click.confirm(f"Found {len(error_stories)} failed stories. Delete them?"):
            return

        for story in error_stories:
            db.delete_story(story.id)
            click.echo(f"Deleted failed story {story.id}")

        click.echo(f"\nDeleted {len(error_stories)} failed stories")


@cli.command()
@click.option('--story-id', help="Create video for a specific story")
@click.option('--all', 'process_all', is_flag=True, help="Process all ready stories")
def create_video(story_id: Optional[str], process_all: bool):
    """Create videos for stories that are ready."""
    if not story_id and not process_all:
        click.echo("Please specify either --story-id or --all")
        return

    with get_db() as db:
        video_manager = VideoManager(db)

        if process_all:
            click.echo("Processing all ready stories...")
            video_manager.process_ready_stories()
        else:
            story = db.get_story(story_id)
            if not story:
                click.echo(f"Story {story_id} not found.")
                return

            click.echo(f"Creating video for story {story_id}")
            click.echo(f"Story status: {story.status}")
            click.echo(f"Audio path: {story.audio_path}")
            click.echo(f"Timestamps path: {story.timestamps_path}")

            try:
                video_manager.create_video_for_story(story)
                click.echo(f"Successfully created video for story {story_id}")
            except Exception as e:
                click.echo(f"Failed to create video: {str(e)}")
                raise  # Re-raise to see the full traceback


@cli.command()
@click.argument('story_id')
def retry_video(story_id: str):
    """Retry video creation for a failed story."""
    with get_db() as db:
        video_manager = VideoManager(db)
        try:
            video_manager.retry_failed_video(story_id)
            click.echo(
                f"Successfully retried video creation for story {story_id}")
        except Exception as e:
            click.echo(f"Failed to retry video creation: {str(e)}")


def _show_banner():
    """Display the ASCII art banner."""
    banner = """
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
"""
    click.echo(banner)


def play_background_music():
    """Play background music in a loop."""
    music_file = "assets/Bit Bit Loop.mp3"  # Our retro menu music
    while True:
        try:
            playsound(music_file)
        except Exception as e:
            click.echo(f"\nNote: Couldn't play background music: {str(e)}")
            break


@cli.command()
def menu():
    """Launch an interactive menu for story pipeline operations."""
    # Start background music in a separate thread
    try:
        music_thread = Thread(target=play_background_music, daemon=True)
        music_thread.start()
    except Exception as e:
        click.echo(f"Note: Background music not available: {str(e)}")

    while True:
        click.clear()
        _show_banner()
        click.echo("\nStory Pipeline Interactive Menu")
        click.echo("=" * 30)
        click.echo("\n1. Story Management")
        click.echo("2. Video Creation")
        click.echo("3. System Status")
        click.echo("\n0. Exit")

        choice = click.prompt("\nSelect an option", type=int, default=0)

        if choice == 0:
            break
        elif choice == 1:
            _show_story_menu()
        elif choice == 2:
            _show_video_menu()
        elif choice == 3:
            _show_status_menu()
        else:
            click.echo("Invalid option")
            click.pause()


def _show_story_menu():
    """Show story management submenu."""
    while True:
        click.clear()
        click.echo("Story Management")
        click.echo("=" * 30)
        click.echo("\n1. List Stories")
        click.echo("2. Show Story Details")
        click.echo("3. Crawl New Stories")
        click.echo("4. Delete Story")
        click.echo("5. Retry Failed Story")
        click.echo("\n0. Back")

        try:
            choice = click.prompt("\nSelect an option", type=int, default=0)

            if choice == 0:
                break
            elif choice == 1:
                try:
                    _handle_list_stories()
                except Exception as e:
                    click.echo(f"Error listing stories: {str(e)}")
            elif choice == 2:
                story_id = click.prompt("Enter story ID", type=str)
                try:
                    ctx = click.get_current_context()
                    ctx.invoke(show, story_id)
                except Exception as e:
                    click.echo(f"Error showing story details: {str(e)}")
                    click.echo(
                        "Please make sure you entered a valid story ID.")
            elif choice == 3:
                subreddit = click.prompt(
                    "Enter subreddit name (e.g., tifu)", type=str)
                single = click.confirm(
                    "Process only the first story?", default=False)
                try:
                    ctx = click.get_current_context()
                    ctx.invoke(crawl, subreddit=subreddit,
                               base_dir="demo/stories", model="base", single=single)
                except Exception as e:
                    click.echo(f"Error crawling stories: {str(e)}")
                    click.echo(
                        "Please make sure you entered a valid subreddit name.")
            elif choice == 4:
                story_id = click.prompt("Enter story ID", type=str)
                try:
                    ctx = click.get_current_context()
                    ctx.invoke(delete, story_id)
                except Exception as e:
                    click.echo(f"Error deleting story: {str(e)}")
                    click.echo(
                        "Please make sure you entered a valid story ID.")
            elif choice == 5:
                story_id = click.prompt("Enter story ID", type=str)
                try:
                    ctx = click.get_current_context()
                    ctx.invoke(retry, story_id)
                except Exception as e:
                    click.echo(f"Error retrying story: {str(e)}")
                    click.echo(
                        "Please make sure you entered a valid story ID.")
            else:
                click.echo("Invalid option")
        except Exception as e:
            click.echo(f"An error occurred: {str(e)}")
            click.echo("Please try again or select a different option.")

        click.pause()


def _show_available_stories(status: Optional[str] = None) -> Optional[str]:
    """Show available stories and let user select one.
    Returns the selected story ID or None if cancelled."""
    with get_db() as db:
        stories = db.get_stories_by_status(
            status) if status else db.get_all_stories()
        if not stories:
            click.echo("No stories found.")
            return None

        click.echo("\nAvailable Stories:")
        click.echo("=" * 50)
        for idx, story in enumerate(stories, 1):
            click.echo(
                f"{idx}. [{story.status}] {story.title[:50]}... (ID: {story.id})")
        click.echo("\n0. Cancel")

        while True:
            try:
                choice = click.prompt(
                    "\nSelect a story number", type=int, default=0)
                if choice == 0:
                    return None
                if 1 <= choice <= len(stories):
                    return stories[choice - 1].id
                click.echo("Invalid selection. Please try again.")
            except ValueError:
                click.echo("Please enter a valid number.")


def _show_video_menu():
    """Show video creation submenu."""
    while True:
        click.clear()
        click.echo("Video Creation")
        click.echo("=" * 30)
        click.echo("\n1. Create Video for Story")
        click.echo("2. Process All Ready Stories")
        click.echo("3. Retry Failed Video")
        click.echo("\n0. Back")

        try:
            choice = click.prompt("\nSelect an option", type=int, default=0)

            if choice == 0:
                break
            elif choice == 1:
                # Show ready stories and let user select one
                click.echo(
                    "\nSelecting from stories ready for video creation:")
                story_id = _show_available_stories('ready')
                if story_id:
                    try:
                        ctx = click.get_current_context()
                        ctx.invoke(create_video, story_id=story_id,
                                   process_all=False)
                    except Exception as e:
                        click.echo(f"Error creating video: {str(e)}")
                        click.echo(
                            "Please make sure the story is ready for video creation.")
            elif choice == 2:
                try:
                    ctx = click.get_current_context()
                    ctx.invoke(create_video, story_id=None, process_all=True)
                except Exception as e:
                    click.echo(f"Error processing videos: {str(e)}")
                    click.echo(
                        "Please make sure there are stories ready for video creation.")
            elif choice == 3:
                # Show failed stories and let user select one
                click.echo(
                    "\nSelecting from stories with failed video creation:")
                story_id = _show_available_stories('video_error')
                if story_id:
                    try:
                        ctx = click.get_current_context()
                        ctx.invoke(retry_video, story_id=story_id)
                    except Exception as e:
                        click.echo(f"Error retrying video: {str(e)}")
                        click.echo(
                            "Please make sure the story had a failed video creation.")
            else:
                click.echo("Invalid option")
        except Exception as e:
            click.echo(f"An error occurred: {str(e)}")
            click.echo("Please try again or select a different option.")

        click.pause()


def _show_status_menu():
    """Show system status submenu."""
    while True:
        click.clear()
        click.echo("System Status")
        click.echo("=" * 30)
        click.echo("\n1. Show Error Stories")
        click.echo("2. Show Ready Stories")
        click.echo("3. Show Processing Stories")
        click.echo("4. Clean Up Failed Stories")
        click.echo("\n0. Back")

        choice = click.prompt("\nSelect an option", type=int, default=0)

        if choice == 0:
            break
        elif choice == 1:
            _handle_list_stories(status='error')
        elif choice == 2:
            _handle_list_stories(status='ready')
        elif choice == 3:
            _handle_list_stories(status='video_processing')
        elif choice == 4:
            ctx = click.get_current_context()
            cleanup.invoke(ctx)

        click.pause()


def _handle_list_stories(status: Optional[str] = None):
    """Handle story listing with optional status filter."""
    ctx = click.get_current_context()
    obj = ctx.ensure_object(dict)
    ctx.invoke(list_stories, status=status, limit=10, no_errors=False)


if __name__ == '__main__':
    cli()
