import os
import click
import logging
from typing import Optional, List
from tabulate import tabulate
from datetime import datetime
import json

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
                click.echo(f"Story {story_id} not found.")
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
            click.echo("No stories to verify.")
            return

        for story in stories:
            click.echo(f"\nVerifying story: {story.id}")
            click.echo("=" * 50)
            click.echo(f"Title: {story.title}")
            click.echo(f"Status: {story.status}")

            # Check TTS audio file
            if story.audio_path:
                if os.path.exists(story.audio_path):
                    size = os.path.getsize(story.audio_path) / 1024  # KB
                    modified = os.path.getmtime(story.audio_path)
                    modified_time = datetime.fromtimestamp(
                        modified).strftime('%Y-%m-%d %H:%M:%S')
                    click.echo(f"\n📁 TTS Audio:")
                    click.echo(f"  Path: {story.audio_path}")
                    click.echo(f"  Size: {size:.2f} KB")
                    click.echo(f"  Modified: {modified_time}")
                else:
                    click.echo(
                        f"\n❌ TTS Audio file missing: {story.audio_path}")
            else:
                click.echo("\n⚠️ No TTS audio path in database")

            # Check timestamps file
            if story.timestamps_path:
                if os.path.exists(story.timestamps_path):
                    size = os.path.getsize(story.timestamps_path) / 1024  # KB
                    modified = os.path.getmtime(story.timestamps_path)
                    modified_time = datetime.fromtimestamp(
                        modified).strftime('%Y-%m-%d %H:%M:%S')
                    click.echo(f"\n📁 Timestamps:")
                    click.echo(f"  Path: {story.timestamps_path}")
                    click.echo(f"  Size: {size:.2f} KB")
                    click.echo(f"  Modified: {modified_time}")
                else:
                    click.echo(
                        f"\n❌ Timestamps file missing: {story.timestamps_path}")
            else:
                click.echo("\n⚠️ No timestamps path in database")

            # Check video file
            video_dir = os.path.join("demo", "videos", story.id)
            video_path = os.path.join(video_dir, "final.mp4")
            if os.path.exists(video_path):
                size = os.path.getsize(video_path) / 1024 / 1024  # MB
                modified = os.path.getmtime(video_path)
                modified_time = datetime.fromtimestamp(
                    modified).strftime('%Y-%m-%d %H:%M:%S')
                click.echo(f"\n📁 Video:")
                click.echo(f"  Path: {video_path}")
                click.echo(f"  Size: {size:.2f} MB")
                click.echo(f"  Modified: {modified_time}")
            else:
                click.echo("\n⚠️ No video file found")

            # Status consistency check
            has_audio = story.audio_path and os.path.exists(story.audio_path)
            has_timestamps = story.timestamps_path and os.path.exists(
                story.timestamps_path)
            has_video = os.path.exists(video_path)

            click.echo("\n🔍 Status Check:")
            if story.status == StoryStatus.NEW and (has_audio or has_timestamps or has_video):
                click.echo("  ⚠️ Status is NEW but files exist")
            elif story.status == StoryStatus.AUDIO_GENERATED and not has_audio:
                click.echo(
                    "  ❌ Status is AUDIO_GENERATED but audio file missing")
            elif story.status == StoryStatus.READY and (not has_audio or not has_timestamps):
                click.echo("  ❌ Status is READY but required files missing")
            elif story.status == StoryStatus.VIDEO_READY and not has_video:
                click.echo("  ❌ Status is VIDEO_READY but video file missing")
            elif story.status == StoryStatus.VIDEO_PROCESSING and has_video:
                click.echo("  ⚠️ Status is VIDEO_PROCESSING but video exists")
            else:
                click.echo("  ✅ Status consistent with files")


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
            click.echo(f"Story {story_id} not found.")
            return

        if file_type in ['text', 'all']:
            click.echo("\n📝 Story Text:")
            click.echo("=" * 50)
            click.echo(story.text)

        if file_type in ['timestamps', 'all'] and story.timestamps_path:
            if os.path.exists(story.timestamps_path):
                click.echo("\n⏱️ Timestamps:")
                click.echo("=" * 50)
                try:
                    with open(story.timestamps_path, 'r', encoding='utf-8') as f:
                        timestamps_data = json.load(f)

                    if 'segments' in timestamps_data:  # Whisper format
                        for segment in timestamps_data['segments']:
                            start = segment.get('start', 0)
                            end = segment.get('end', 0)
                            text = segment.get('text', '').strip()
                            click.echo(f"{start:.2f} → {end:.2f}: {text}")
                    else:  # ElevenLabs format
                        for segment in timestamps_data:
                            if 'characters' in segment and 'character_start_times_seconds' in segment:
                                chars = segment['characters']
                                times = segment['character_start_times_seconds']
                                text = ''.join(chars)
                                start = times[0] if times else 0
                                end = times[-1] if times else 0
                                click.echo(f"{start:.2f} → {end:.2f}: {text}")
                except json.JSONDecodeError:
                    click.echo("❌ Invalid JSON format in timestamps file")
                except Exception as e:
                    click.echo(f"❌ Error reading timestamps: {str(e)}")
            else:
                click.echo("\n❌ Timestamps file not found")


def _show_available_stories() -> Optional[str]:
    """Show a menu of available stories and return the selected story ID."""
    with get_db() as db:
        stories = db.get_all_stories()
        if not stories:
            click.echo("No stories available.")
            return None

        click.echo("\nAvailable Stories")
        click.echo("=" * 50 + "\n")

        for i, story in enumerate(stories, 1):
            title = story.title[:50] + \
                "..." if len(story.title) > 50 else story.title
            created = story.created_at.strftime('%Y-%m-%d %H:%M')
            click.echo(f"{i}. {title}")
            click.echo(f"   Status: {story.status}")
            click.echo(f"   Author: {story.author}")
            click.echo(f"   Created: {created}\n")

        click.echo("0. Cancel\n")

        while True:
            try:
                choice = click.prompt(
                    "Select a story number", type=int, default=0)
                if choice == 0:
                    return None
                if 1 <= choice <= len(stories):
                    return stories[choice - 1].id
                click.echo("Invalid choice. Please try again.")
            except (ValueError, click.Abort):
                return None


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
            click.echo(f"Story {story_id} not found.")
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
                    click.echo("⚠️ No files found to backup!")
                    return

                # Create zip archive
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arcname)

            # Show summary
            click.echo(f"\n✨ Created backup: {backup_path}")
            click.echo("\nFiles included:")
            for file_type, path in files_copied:
                size = os.path.getsize(path) / 1024  # KB
                click.echo(
                    f"  • {file_type}: {os.path.basename(path)} ({size:.2f} KB)")

        except Exception as e:
            if backup_path and os.path.exists(backup_path):
                try:
                    # Clean up partial backup if it exists
                    os.remove(backup_path)
                except:
                    pass
            click.echo(f"❌ Error creating backup: {str(e)}")
            raise


@files.command()
@click.argument('backup_path')
@click.option('--force', is_flag=True, help="Overwrite existing files")
def restore(backup_path: str, force: bool):
    """Restore story files from a backup archive."""
    if not os.path.exists(backup_path):
        click.echo(f"Backup file not found: {backup_path}")
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
                click.echo("❌ Invalid backup: missing story metadata")
                return

            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Confirm restoration
            click.echo("\nRestore the following story?")
            click.echo(f"Title: {metadata['title']}")
            click.echo(f"Author: {metadata['author']}")
            click.echo(f"ID: {metadata['id']}")

            if not force and not click.confirm("\nProceed with restore?"):
                click.echo("Restore cancelled.")
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
                    if not force and not click.confirm(f"\nStory {story_id} already exists. Update it?"):
                        click.echo("Database update skipped.")
                    else:
                        db.delete_story(story_id)
                        db.add_story(story)
                        click.echo("Updated existing story in database.")
                else:
                    db.add_story(story)
                    click.echo("Added new story to database.")

            # Show summary
            click.echo("\n✨ Restore completed successfully")
            click.echo("\nFiles restored:")
            for file_type, path in files_restored:
                size = os.path.getsize(path) / 1024  # KB
                click.echo(f"  • {file_type}: {path} ({size:.2f} KB)")

    except Exception as e:
        click.echo(f"❌ Error restoring backup: {str(e)}")
        raise


if __name__ == '__main__':
    cli()
