import logging
import pandas as pd
import inspect


# Define ANSI escape codes for colors
class LogColors:
    RESET = "\033[0m"
    INFO = "\033[32m"      # Green
    DEBUG = "\033[34m"     # Blue
    WARNING = "\033[33m"   # Yellow
    ERROR = "\033[31m"     # Red
    CRITICAL = "\033[41m"  # Red background


# Custom Formatter with Colors
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        log_colors = {
            logging.INFO: LogColors.INFO,
            logging.DEBUG: LogColors.DEBUG,
            logging.WARNING: LogColors.WARNING,
            logging.ERROR: LogColors.ERROR,
            logging.CRITICAL: LogColors.CRITICAL,
        }
        color = log_colors.get(record.levelno, LogColors.RESET)
        message = super().format(record)
        return f"{color}{message}{LogColors.RESET}"


def configure_logging():
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)

    # Use the custom formatter
    formatter = ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)


def log_dataframe_info(df: pd.DataFrame, df_name: str = "DataFrame"):
    """
    Logs the shape and column names of a DataFrame, dynamically reflecting the caller's class name.

    Args:
        df (pd.DataFrame): The DataFrame to log information about.
        df_name (str): Name of the DataFrame for logging.
    """
    # Dynamically get the caller's class name
    frame = inspect.currentframe().f_back
    class_name = frame.f_locals.get('self', None).__class__.__name__ if 'self' in frame.f_locals else "UnknownClass"

    # Create a logger dynamically for the caller's class
    logger = logging.getLogger(class_name)

    logger.info(f"{df_name} shape: {df.shape}")
    logger.info(f"{df_name} columns: {list(df.columns)}")

