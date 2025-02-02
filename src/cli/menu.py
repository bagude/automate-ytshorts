import click
import logging
from ..db.manager import DatabaseManager, get_db
from ..crawler.reddit import RedditCrawler
from ..constants import StoryStatus
from ..pipeline.audio import AudioGenerator
from ..pipeline.subtitles import SubtitlesGenerator
from ..pipeline.video import VideoGenerator


def configure_logging(debug: bool):
    """Configure logging level based on debug flag."""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


@click.group()
def cli():
    """CLI for managing the story pipeline."""
    pass


@cli.command()
@click.option('--debug', is_flag=True, help='Enable debug logging')
def menu(debug):
    """Interactive menu for managing the story pipeline."""
    configure_logging(debug)
    while True:
        click.clear()
        click.echo("Story Pipeline Menu")
        click.echo("1. List stories")
        click.echo("2. Crawl new stories")
        click.echo("3. Generate audio")
        click.echo("4. Generate subtitles")
        click.echo("5. Generate video")
        click.echo("6. Exit")

        choice = click.prompt("Enter your choice", type=int)

        try:
            if choice == 1:
                _show_available_stories()
            elif choice == 2:
                _crawl_new_stories()
            elif choice == 3:
                _generate_audio()
            elif choice == 4:
                _generate_subtitles()
            elif choice == 5:
                _generate_video()
            elif choice == 6:
                click.echo("Goodbye!")
                break
            else:
                click.echo("Invalid choice")

            if choice != 6:
                click.pause()
        except Exception as e:
            click.echo(f"Error: {str(e)}")
            click.pause()
