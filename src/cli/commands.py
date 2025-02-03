import os
import click
import logging
from typing import Optional, List
from tabulate import tabulate

from ..db import DatabaseManager, Story, StoryStatus
from ..story_pipeline import StoryPipeline
from ..video_pipeline import VideoManager
from .formatters import format_story_row


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
    pass


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
                click.echo(f"Invalid status: {status}")
                click.echo(
                    f"Valid statuses are: {', '.join(s.value for s in StoryStatus)}")
                return
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
            click.echo(f"Story {story_id} not found.")
            return

        if story.status != StoryStatus.ERROR:
            click.echo(
                f"Story {story_id} is not in error state (current status: {story.status})")
            return

        # Reset story status
        db.update_story_status(story_id, StoryStatus.NEW, None)
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
        error_stories = db.get_stories_by_status(StoryStatus.ERROR)
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
                raise


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

        if not click.confirm(f"\n{warning}\n\nAre you absolutely sure you want to continue?"):
            click.echo("Operation cancelled.")
            return

    try:
        with get_db() as db:
            click.echo("Starting database reset...")
            db.cleanup_database(remove_files=not keep_files)
            click.echo("✨ Database has been reset to factory settings.")
            if not keep_files:
                click.echo("📂 All generated files have been removed.")
    except Exception as e:
        click.echo(f"❌ Error during reset: {str(e)}")
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
            click.echo(f"Story {story_id} not found.")
            return

        if not story.audio_path or not story.timestamps_path:
            click.echo(f"Story {story_id} is missing required files:")
            click.echo(f"Audio path: {'✓' if story.audio_path else '✗'}")
            click.echo(
                f"Timestamps path: {'✓' if story.timestamps_path else '✗'}")
            return

        try:
            from ..video_pipeline.video_pipeline import VideoPipeline, DEFAULT_CONFIG

            # Set up output path
            output_dir = os.path.join("demo", "videos", story.id)
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "final.mp4")

            click.echo("Starting video creation...")
            with VideoPipeline(DEFAULT_CONFIG) as pipeline:
                pipeline.execute(
                    output_path=output_path,
                    tts_path=story.audio_path,
                    music_path=os.path.join("demo", "mp3", "bg_music.mp3"),
                    video_path=os.path.join("demo", "mp4", "background.mp4"),
                    text=story.text,
                    subtitle_json=story.timestamps_path
                )
            click.echo(f"✨ Successfully created video: {output_path}")

        except Exception as e:
            click.echo(f"❌ Failed to create video: {str(e)}")
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
            click.echo(f"Story {story_id} not found.")
            return

        if not story.audio_path or not story.timestamps_path:
            click.echo(f"Story {story_id} is missing required files:")
            click.echo(f"Audio path: {'✓' if story.audio_path else '✗'}")
            click.echo(
                f"Timestamps path: {'✓' if story.timestamps_path else '✗'}")
            return

        try:
            from ..video_pipeline.video_pipeline import SubtitleEngine, DEFAULT_CONFIG

            click.echo("Starting subtitle generation...")
            subtitle_engine = SubtitleEngine(DEFAULT_CONFIG)
            subtitles = subtitle_engine.generate_subtitles(
                text=story.text,
                duration=60,  # This duration doesn't matter for subtitle generation from timestamps
                subtitle_json=story.timestamps_path
            )
            click.echo("✨ Successfully regenerated subtitles")

            if click.confirm("Would you like to remake the video with the new subtitles?"):
                ctx = click.get_current_context()
                ctx.invoke(remake_video, story_id=story_id)

        except Exception as e:
            click.echo(f"❌ Failed to generate subtitles: {str(e)}")
            raise


if __name__ == '__main__':
    cli()
