import os
import time
import logging
from typing import Dict, Optional
from threading import Lock

logger = logging.getLogger(__name__)


class TempFileManager:
    """
    Manages temporary files with automatic cleanup based on age.

    This class provides functionality to register temporary files, track their creation time,
    and clean up files that exceed a specified maximum age. It ensures thread-safe operations
    for file registration and cleanup.

    Attributes:
        base_dir (str): Base directory for temporary files.
        max_age (int): Maximum age of temporary files in seconds.
        files (Dict[str, float]): Dictionary mapping file paths to their creation timestamps.
        lock (Lock): Thread lock for safe concurrent access.
    """

    def __init__(self, base_dir: str, max_age: int = 3600):
        """
        Initialize the TempFileManager.

        Args:
            base_dir (str): Base directory for temporary files.
            max_age (int, optional): Maximum age of temporary files in seconds. Defaults to 3600 (1 hour).
        """
        self.base_dir = base_dir
        self.max_age = max_age
        self.files: Dict[str, float] = {}
        self.lock = Lock()

        # Ensure base directory exists
        os.makedirs(self.base_dir, exist_ok=True)
        logger.info(f"Initialized TempFileManager with base_dir: {self.base_dir}, max_age: {self.max_age} seconds")

    def register_file(self, file_path: str) -> None:
        """
        Register a temporary file with its creation timestamp.

        Args:
            file_path (str): Path to the temporary file.
        """
        abs_path = os.path.abspath(file_path)
        if not os.path.isfile(abs_path):
            logger.warning(f"Attempted to register non-existent file: {abs_path}")
            return

        with self.lock:
            self.files[abs_path] = time.time()
            logger.debug(f"Registered temporary file: {abs_path}")

    def cleanup(self, force: bool = False) -> int:
        """
        Clean up temporary files older than max_age or all files if force is True.

        Args:
            force (bool, optional): If True, remove all registered files regardless of age. Defaults to False.

        Returns:
            int: Number of files removed.
        """
        current_time = time.time()
        removed_count = 0

        with self.lock:
            files_to_remove = []
            for file_path, creation_time in self.files.items():
                age = current_time - creation_time
                if force or age > self.max_age:
                    files_to_remove.append(file_path)
                    removed_count += 1

            for file_path in files_to_remove:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.debug(f"Removed temporary file: {file_path}")
                    del self.files[file_path]
                except Exception as e:
                    logger.error(f"Failed to remove temporary file {file_path}: {e}")
                    # Keep the file in the registry if removal fails to retry
                    # later

        logger.info(f"Cleaned up {removed_count} temporary files (force={force})")
        return removed_count

    def get_file_age(self, file_path: str) -> Optional[float]:
        """
        Get the age of a registered temporary file in seconds.

        Args:
            file_path (str): Path to the temporary file.

        Returns:
            Optional[float]: Age of the file in seconds if registered, None otherwise.
        """
        abs_path = os.path.abspath(file_path)
        if abs_path in self.files:
            return time.time() - self.files[abs_path]
        return None

    def is_temp_file(self, file_path: str) -> bool:
        """
        Check if a file is a registered temporary file.

        Args:
            file_path (str): Path to check.

        Returns:
            bool: True if the file is registered as temporary, False otherwise.
        """
        abs_path = os.path.abspath(file_path)
        return abs_path in self.files

    def clear_all(self) -> int:
        """
        Remove all registered temporary files.

        Returns:
            int: Number of files removed.
        """
        return self.cleanup(force=True)
