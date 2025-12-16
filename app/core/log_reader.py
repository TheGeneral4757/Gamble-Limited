from pathlib import Path
from typing import List


def get_log_lines(log_file: Path, lines: int = 100, level: str = "all") -> List[str]:
    """
    Reads recent log lines from a given log file.

    Note: This implementation reads the entire file into memory. For very large
    log files, a more memory-efficient approach (e.g., reading the file
    backwards) would be better.

    Args:
        log_file: The Path object for the log file.
        lines: The number of lines to retrieve from the end of the file.
        level: The log level to filter by. 'all' returns all levels.

    Returns:
        A list of strings, where each string is a log line.
        Returns a message list if the file doesn't exist or an error occurs.
    """
    logs = []
    try:
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()

            # Filter by level if specified
            if level.lower() != "all":
                level_upper = level.upper()
                all_lines = [line for line in all_lines if level_upper in line]

            # Get last N lines
            logs = all_lines[-lines:]
            logs = [line.strip() for line in logs]
        else:
            logs = [
                "Log file not found. Enable file logging in config: logging.log_to_file = true"
            ]
    except Exception as e:
        logs = [f"Error reading logs: {e}"]

    return logs
