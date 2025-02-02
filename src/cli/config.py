import logging

# Global debug flag
DEBUG = False


def configure_logging(debug: bool = False):
    """Configure logging based on debug mode.

    Args:
        debug (bool): Whether to enable debug mode
    """
    global DEBUG
    DEBUG = debug

    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(filename)s - %(lineno)d - %(asctime)s - %(levelname)s - %(message)s'
        )
    else:
        logging.basicConfig(
            level=logging.WARNING,
            format='%(levelname)s: %(message)s'
        )
