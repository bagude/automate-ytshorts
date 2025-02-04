import click
import logging
from threading import Thread
from playsound import playsound
from typing import Optional
import os
from datetime import datetime

from .commands import cli, list_stories, show, crawl, delete, retry, cleanup, create_video, retry_video, remake_video, remake_subtitles, verify, preview, backup, restore
from .formatters import show_banner
from .settings import get_music_enabled, set_music_enabled
from ..db import StoryStatus


def play_background_music():
    """Play background music in a loop."""
    if not get_music_enabled():
        return

    music_file = "assets/bit_bit_loop.mp3"  # Our retro menu music
    while True:
        try:
            playsound(music_file)
        except Exception as e:
            logging.error(f"Couldn't play background music: {str(e)}")
            break


def _show_available_stories(status: Optional[str] = None) -> Optional[str]:
    """Show available stories and let user select one.
    Returns the selected story ID or None if cancelled."""
    from .commands import get_db
    logging.info(
        f"Fetching stories with status: {status if status else 'all'}")

    with get_db() as db:
        if status:
            try:
                if status == 'ready':
                    # For video creation, get all video-ready stories
                    ready_statuses = StoryStatus.get_video_ready_statuses()
                    logging.info(
                        f"Getting stories with video-ready statuses: {[str(s) for s in ready_statuses]}")
                    stories = db.get_stories_by_multiple_statuses(
                        ready_statuses)
                    logging.info(
                        f"Found {len(stories)} stories ready for video creation")

                    # Debug: show what's in the database
                    cursor = db.conn.execute("SELECT id, status FROM stories")
                    all_stories = cursor.fetchall()
                    logging.info(
                        f"All stories in database: {[(row[0], row[1]) for row in all_stories]}")
                else:
                    status_enum = StoryStatus(status)
                    logging.info(
                        f"Converting status '{status}' to enum: {status_enum}, enum value: {status_enum.value}")
                    stories = db.get_stories_by_status(status_enum)
                    logging.info(
                        f"Found {len(stories)} stories with status '{status}'")

                if len(stories) == 0:
                    # Debug query to see what statuses exist in the database
                    cursor = db.conn.execute(
                        "SELECT DISTINCT status FROM stories")
                    existing_statuses = [row[0] for row in cursor.fetchall()]
                    logging.info(
                        f"Existing status values in database: {existing_statuses}")
            except ValueError as e:
                logging.error(
                    f"Invalid status value: {status}, error: {str(e)}")
                click.echo(f"Invalid status: {status}")
                click.echo(
                    f"Valid statuses are: {', '.join(s.value for s in StoryStatus)}")
                return None
            except Exception as e:
                logging.error(f"Error fetching stories: {str(e)}")
                raise
        else:
            stories = db.get_all_stories()
            logging.info(f"Found {len(stories)} total stories")

        if not stories:
            logging.info("No stories found")
            click.echo("No stories found.")
            return None

        # Clear screen and show header
        click.clear()
        click.echo("\nAvailable Stories")
        click.echo("=" * 50)

        # Show stories in a more readable format
        for idx, story in enumerate(stories, 1):
            # Truncate title if too long
            title = story.title[:50] + \
                "..." if len(story.title) > 50 else story.title
            # Format creation date
            created = story.created_at.strftime("%Y-%m-%d %H:%M")

            # Log story details
            logging.debug(f"Story {idx}: ID={story.id}, Status={story.status}, " +
                          f"Audio={'✓' if story.audio_path else '✗'}, " +
                          f"Timestamps={'✓' if story.timestamps_path else '✗'}")

            click.echo(f"\n{idx}. {title}")
            click.echo(f"   Status: {story.status}")
            click.echo(f"   Author: u/{story.author}")
            click.echo(f"   Created: {created}")
            if story.error:
                error_msg = story.error[:100] + \
                    "..." if len(story.error) > 100 else story.error
                click.echo(f"   Error: {error_msg}")

        click.echo("\n0. Cancel")

        while True:
            try:
                choice = click.prompt(
                    "\nSelect a story number", type=int, default=0)
                if choice == 0:
                    logging.debug("User cancelled story selection")
                    return None
                if 1 <= choice <= len(stories):
                    selected_id = stories[choice - 1].id
                    logging.debug(
                        f"User selected story {choice} with ID: {selected_id}")
                    return selected_id
                logging.debug(f"Invalid selection: {choice}")
                click.echo("Invalid selection. Please try again.")
            except ValueError:
                logging.debug("Invalid input: not a number")
                click.echo("Please enter a valid number.")


def _handle_list_stories(status: Optional[str] = None):
    """Handle story listing with optional status filter."""
    ctx = click.get_current_context()
    try:
        if status:
            # Don't convert to enum here, just pass the status value directly
            ctx.invoke(list_stories, status=status, limit=10, no_errors=False)
        else:
            ctx.invoke(list_stories, status=None, limit=10, no_errors=False)
    except ValueError:
        click.echo(f"Invalid status: {status}")
        click.echo(
            f"Valid statuses are: {', '.join(s.value for s in StoryStatus)}")
        return


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
                try:
                    # Show list of stories and let user select one
                    story_id = _show_available_stories()
                    if story_id:
                        ctx = click.get_current_context()
                        ctx.invoke(show, story_id=story_id)
                except Exception as e:
                    click.echo(f"Error showing story details: {str(e)}")
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
            elif choice == 4:
                try:
                    # Show list of stories and let user select one
                    story_id = _show_available_stories()
                    if story_id:
                        ctx = click.get_current_context()
                        ctx.invoke(delete, story_id=story_id, force=False)
                except Exception as e:
                    click.echo(f"Error deleting story: {str(e)}")
            elif choice == 5:
                try:
                    # Show list of error stories and let user select one
                    story_id = _show_available_stories('error')
                    if story_id:
                        ctx = click.get_current_context()
                        ctx.invoke(retry, story_id=story_id)
                except Exception as e:
                    click.echo(f"Error retrying story: {str(e)}")
            else:
                click.echo("Invalid option")
        except Exception as e:
            click.echo(f"An error occurred: {str(e)}")

        click.pause()


def _show_video_menu():
    """Show video creation submenu."""
    while True:
        click.clear()
        click.echo("Video Creation")
        click.echo("=" * 30)
        click.echo("\n1. Create Video for Story")
        click.echo("2. Process All Ready Stories")
        click.echo("3. Retry Failed Video")
        click.echo("4. Remake Video (using existing files)")
        click.echo("5. Remake Subtitles")
        click.echo("\n0. Back")

        try:
            choice = click.prompt("\nSelect an option", type=int, default=0)

            if choice == 0:
                break
            elif choice == 1:
                logging.info("Starting video creation for selected story")
                try:
                    # Show ready stories and let user select one
                    logging.debug("Getting stories ready for video creation")
                    story_id = _show_available_stories('ready')
                    if story_id:
                        logging.info(f"Selected story ID: {story_id}")
                        ctx = click.get_current_context()
                        ctx.invoke(create_video, story_id=story_id,
                                   process_all=False)
                    else:
                        logging.info(
                            "No story selected or no stories available")
                except Exception as e:
                    logging.error(f"Error creating video: {str(e)}")
                    click.echo(f"Error creating video: {str(e)}")
            elif choice == 2:
                logging.info("Processing all ready stories")
                try:
                    ctx = click.get_current_context()
                    ctx.invoke(create_video, story_id=None, process_all=True)
                except Exception as e:
                    logging.error(f"Error processing videos: {str(e)}")
                    click.echo(f"Error processing videos: {str(e)}")
            elif choice == 3:
                logging.info("Starting retry of failed video")
                try:
                    # Show failed stories and let user select one
                    story_id = _show_available_stories('video_error')
                    if story_id:
                        logging.info(
                            f"Selected story ID for retry: {story_id}")
                        ctx = click.get_current_context()
                        ctx.invoke(retry_video, story_id=story_id)
                    else:
                        logging.info(
                            "No story selected or no failed stories available")
                except Exception as e:
                    logging.error(f"Error retrying video: {str(e)}")
                    click.echo(f"Error retrying video: {str(e)}")
            elif choice == 4:
                logging.info("Starting video remake")
                try:
                    # Show all stories and let user select one
                    story_id = _show_available_stories()
                    if story_id:
                        logging.info(
                            f"Selected story ID for remake: {story_id}")
                        ctx = click.get_current_context()
                        ctx.invoke(remake_video, story_id=story_id)
                    else:
                        logging.info("No story selected")
                except Exception as e:
                    logging.error(f"Error remaking video: {str(e)}")
                    click.echo(f"Error remaking video: {str(e)}")
            elif choice == 5:
                logging.info("Starting subtitle remake")
                try:
                    # Show all stories and let user select one
                    story_id = _show_available_stories()
                    if story_id:
                        logging.info(
                            f"Selected story ID for subtitle remake: {story_id}")
                        ctx = click.get_current_context()
                        ctx.invoke(remake_subtitles, story_id=story_id)
                    else:
                        logging.info("No story selected")
                except Exception as e:
                    logging.error(f"Error remaking subtitles: {str(e)}")
                    click.echo(f"Error remaking subtitles: {str(e)}")
            else:
                click.echo("Invalid option")
        except Exception as e:
            logging.error(f"An error occurred in video menu: {str(e)}")
            click.echo(f"An error occurred: {str(e)}")

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
            _handle_list_stories(status=StoryStatus.ERROR.value)
        elif choice == 2:
            _handle_list_stories(status=StoryStatus.READY.value)
        elif choice == 3:
            _handle_list_stories(status=StoryStatus.VIDEO_PROCESSING.value)
        elif choice == 4:
            ctx = click.get_current_context()
            ctx.invoke(cleanup)

        click.pause()


def _show_settings_menu():
    """Show settings menu."""
    while True:
        click.clear()
        click.echo("Settings")
        click.echo("=" * 30)
        click.echo(
            f"\n1. Background Music: {'ON' if get_music_enabled() else 'OFF'}")
        click.echo("\n0. Back")

        try:
            choice = click.prompt("\nSelect an option", type=int, default=0)

            if choice == 0:
                break
            elif choice == 1:
                new_state = not get_music_enabled()
                set_music_enabled(new_state)
                if new_state:
                    click.echo(
                        "Music enabled. Will start on next menu launch.")
                else:
                    click.echo("Music disabled.")
                click.pause()
        except Exception as e:
            click.echo(f"An error occurred: {str(e)}")
            click.pause()


def _show_file_menu():
    """Show file management submenu."""
    while True:
        click.clear()
        click.echo("File Management")
        click.echo("=" * 30)
        click.echo("\n1. Verify Files")
        click.echo("2. Preview Files")
        click.echo("3. Backup Story")
        click.echo("4. Restore from Backup")
        click.echo("\n0. Back")

        try:
            choice = click.prompt("\nSelect an option", type=int, default=0)

            if choice == 0:
                break
            elif choice == 1:
                logging.info("Starting file verification")
                try:
                    # Show all stories and let user select one
                    story_id = _show_available_stories()
                    if story_id:
                        logging.info(
                            f"Selected story ID for verification: {story_id}")
                        ctx = click.get_current_context()
                        ctx.invoke(verify, story_id=story_id, verify_all=False)
                    else:
                        logging.info("No story selected")
                except Exception as e:
                    logging.error(f"Error verifying files: {str(e)}")
                    click.echo(f"Error verifying files: {str(e)}")
            elif choice == 2:
                logging.info("Starting file preview")
                try:
                    # Show all stories and let user select one
                    story_id = _show_available_stories()
                    if story_id:
                        logging.info(
                            f"Selected story ID for preview: {story_id}")
                        ctx = click.get_current_context()
                        ctx.invoke(preview, story_id=story_id, file_type='all')
                    else:
                        logging.info("No story selected")
                except Exception as e:
                    logging.error(f"Error previewing files: {str(e)}")
                    click.echo(f"Error previewing files: {str(e)}")
            elif choice == 3:
                logging.info("Starting backup")
                try:
                    # Show all stories and let user select one
                    story_id = _show_available_stories()
                    if story_id:
                        logging.info(
                            f"Selected story ID for backup: {story_id}")
                        ctx = click.get_current_context()
                        ctx.invoke(backup, story_id=story_id,
                                   output_dir='backups')
                    else:
                        logging.info("No story selected")
                except Exception as e:
                    logging.error(f"Error creating backup: {str(e)}")
                    click.echo(f"Error creating backup: {str(e)}")
            elif choice == 4:
                logging.info("Starting restore")
                try:
                    # List available backups
                    backup_dir = 'backups'
                    if not os.path.exists(backup_dir):
                        click.echo("No backups found.")
                        continue

                    backups = [f for f in os.listdir(
                        backup_dir) if f.endswith('.zip')]
                    if not backups:
                        click.echo("No backup files found.")
                        continue

                    click.echo("\nAvailable backups:")
                    for idx, backup in enumerate(backups, 1):
                        backup_path = os.path.join(backup_dir, backup)
                        size = os.path.getsize(backup_path) / 1024  # KB
                        modified = datetime.fromtimestamp(
                            os.path.getmtime(backup_path))
                        click.echo(
                            f"{idx}. {backup} ({size:.2f} KB) - {modified}")

                    click.echo("\n0. Cancel")
                    choice = click.prompt(
                        "\nSelect a backup to restore", type=int, default=0)

                    if choice == 0:
                        continue
                    if 1 <= choice <= len(backups):
                        backup_path = os.path.join(
                            backup_dir, backups[choice - 1])
                        ctx = click.get_current_context()
                        ctx.invoke(
                            restore, backup_path=backup_path, force=False)
                    else:
                        click.echo("Invalid selection.")
                except Exception as e:
                    logging.error(f"Error restoring backup: {str(e)}")
                    click.echo(f"Error restoring backup: {str(e)}")
            else:
                click.echo("Invalid option")
        except Exception as e:
            logging.error(f"An error occurred in file menu: {str(e)}")
            click.echo(f"An error occurred: {str(e)}")

        click.pause()


def _show_main_menu():
    """Show main menu."""
    while True:
        click.clear()
        click.echo(show_banner())
        click.echo("\nStory Pipeline Interactive Menu")
        click.echo("=" * 30)
        click.echo("\n1. Story Management")
        click.echo("2. Video Creation")
        click.echo("3. System Status")
        click.echo("4. File Management")
        click.echo("5. Settings")
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
        elif choice == 4:
            _show_file_menu()
        elif choice == 5:
            _show_settings_menu()
        else:
            click.echo("Invalid option")
            click.pause()


@cli.command()
@click.option('--debug', is_flag=True, help='Enable debug logging')
def menu(debug: bool):
    """Interactive menu for managing the story pipeline."""
    from .config import configure_logging
    configure_logging(debug)

    # Start background music in a separate thread if enabled
    if get_music_enabled():
        try:
            music_thread = Thread(target=play_background_music, daemon=True)
            music_thread.start()
        except Exception as e:
            logging.error(f"Couldn't start background music: {str(e)}")

    _show_main_menu()
