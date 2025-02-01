import os
import click
import logging
from typing import Optional
from tabulate import tabulate
from datetime import datetime

from .db_manager import DatabaseManager, Story
from .story_pipeline import StoryPipeline

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def get_db() -> DatabaseManager:
    """Get database manager instance with default configuration."""
    return DatabaseManager("demo/story_pipeline.db")


def format_story_row(story: Story) -> list:
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
def crawl(subreddit: str, base_dir: str, model: str):
    """Crawl new stories from a subreddit and process them."""
    config = {
        'subreddit': subreddit,
        'base_dir': base_dir,
        'db_path': 'demo/story_pipeline.db',
        'whisper_model': model
    }

    pipeline = StoryPipeline(config)
    pipeline.run()
    click.echo(f"Completed processing stories from r/{subreddit}")


@cli.command()
@click.option('--status', help="Filter stories by status")
@click.option('--limit', default=10, help="Number of stories to show")
@click.option('--no-errors', is_flag=True, help="Show only stories without errors")
def list(status: Optional[str], limit: int, no_errors: bool):
    """List stories in the database."""
    with get_db() as db:
        if no_errors:
            stories = db.get_stories_without_errors()
        elif status:
            stories = db.get_stories_by_status(status)
        else:
            stories = db.get_all_stories()

        stories = stories[:limit]

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
            click.echo(f"Story {story_id} not found.")
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


if __name__ == '__main__':
    cli()
