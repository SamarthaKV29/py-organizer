#!/usr/bin/env python3
"""
file_organizer.py - Pure Python file organization engine
Organizes files into year-based folders based on creation/modification dates.
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Callable
from dataclasses import dataclass
from enum import Enum


class DuplicateMode(Enum):
    """How to handle duplicate files"""
    INTERACTIVE = "interactive"
    SKIP = "skip"
    RENAME = "rename"
    OVERWRITE = "overwrite"


@dataclass
class OrganizerStats:
    """Statistics for organization operation"""
    files_moved: int = 0
    files_renamed: int = 0
    files_skipped: int = 0
    dirs_moved: int = 0
    errors: int = 0


@dataclass
class OrganizerConfig:
    """Configuration for file organizer"""
    source_dir: Path
    target_dir: Optional[Path] = None
    dry_run: bool = True
    files_only: bool = False
    verbose: bool = False
    duplicate_mode: DuplicateMode = DuplicateMode.RENAME
    included_folders: Optional[List[str]] = None
    excluded_folders: Optional[List[str]] = None
    target_year: Optional[int] = None
    file_types: Optional[List[str]] = None

    def __post_init__(self):
        """Set target_dir to source_dir if not specified"""
        if self.target_dir is None:
            self.target_dir = self.source_dir


class FileOrganizer:
    """
    Core file organization engine.
    Organizes files into year-based folders based on creation/modification dates.
    """

    def __init__(
        self,
        config: OrganizerConfig,
        log_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        """
        Initialize file organizer.

        Args:
            config: Organizer configuration
            log_callback: Function(message, level) for logging (level: info/success/warning/error)
            progress_callback: Function(current, total) for progress updates
        """
        self.config = config
        self.stats = OrganizerStats()
        self.log_callback = log_callback or self._default_log
        self.progress_callback = progress_callback or self._default_progress
        self._cancelled = False

    def _default_log(self, message: str, level: str = "info"):
        """Default logging (print to console)"""
        print(f"[{level.upper()}] {message}")

    def _default_progress(self, current: int, total: int):
        """Default progress (no-op)"""
        pass

    def cancel(self):
        """Cancel ongoing operation"""
        self._cancelled = True
        self.log("Operation cancelled by user", "warning")

    def log(self, message: str, level: str = "info"):
        """Log a message"""
        self.log_callback(message, level)

    def update_progress(self, current: int, total: int):
        """Update progress"""
        self.progress_callback(current, total)

    def get_item_year(self, path: Path) -> Optional[int]:
        """
        Get year from file/directory modification time (more reliable than creation time).

        Args:
            path: Path to file or directory

        Returns:
            Year as integer, or None if unable to determine
        """
        try:
            # Use modification time (st_mtime) - most reliable across platforms
            # This matches the bash script behavior and user expectations
            stat_info = path.stat()
            timestamp = stat_info.st_mtime

            year = datetime.fromtimestamp(timestamp).year
            return year if 1900 <= year <= 2100 else None

        except Exception as e:
            self.log(f"Could not get year for {path.name}: {str(e)}", "warning")
            return None

    def should_process_item(self, item: Path, is_directory: bool = False) -> bool:
        """
        Check if item should be processed based on filters.

        Args:
            item: Path to check
            is_directory: Whether item is a directory

        Returns:
            True if should process, False otherwise
        """
        name = item.name

        # Skip script files
        if name in ['org_docs.sh', 'org_docs_gui.py', 'file_organizer.py']:
            return False

        # Check if directory should be included/excluded
        if is_directory:
            # Files-only mode: skip all directories
            if self.config.files_only:
                return False

            # Check include list
            if self.config.included_folders:
                return name in self.config.included_folders

            # Check exclude list
            if self.config.excluded_folders and name in self.config.excluded_folders:
                return False

        # Check file type filter
        if not is_directory and self.config.file_types:
            ext = item.suffix.lstrip('.')
            if ext not in self.config.file_types:
                return False

        # Check year filter
        if self.config.target_year:
            year = self.get_item_year(item)
            if year != self.config.target_year:
                return False

        return True

    def handle_duplicate(
        self,
        src: Path,
        dest: Path,
        is_directory: bool = False
    ) -> Tuple[bool, Optional[Path]]:
        """
        Handle duplicate file/directory.

        Args:
            src: Source path
            dest: Destination path that already exists
            is_directory: Whether item is a directory

        Returns:
            Tuple of (should_move, new_dest_path)
            - should_move: False to skip, True to proceed
            - new_dest_path: Modified destination path (for rename), or None
        """
        item_type = "directory" if is_directory else "file"

        # Get file sizes for comparison
        try:
            if not is_directory:
                src_size = src.stat().st_size
                dest_size = dest.stat().st_size
                size_info = f" (Source: {src_size:,} bytes, Existing: {dest_size:,} bytes)"
            else:
                size_info = ""
        except Exception:
            size_info = ""

        self.log(f"Duplicate {item_type}: {dest.name}{size_info}", "warning")

        # Handle based on mode
        if self.config.duplicate_mode == DuplicateMode.SKIP:
            self.log(f"Skipping duplicate {item_type}", "info")
            self.stats.files_skipped += 1
            return False, None

        elif self.config.duplicate_mode == DuplicateMode.OVERWRITE:
            self.log(f"Overwriting existing {item_type}", "warning")
            return True, dest

        elif self.config.duplicate_mode == DuplicateMode.RENAME:
            # Generate unique name with timestamp
            timestamp = datetime.fromtimestamp(src.stat().st_mtime).strftime("%Y%m%d_%H%M%S")
            stem = dest.stem
            suffix = dest.suffix
            new_name = f"{stem}_{timestamp}{suffix}"
            new_dest = dest.parent / new_name

            # Ensure uniqueness
            counter = 1
            while new_dest.exists():
                new_name = f"{stem}_{timestamp}_{counter}{suffix}"
                new_dest = dest.parent / new_name
                counter += 1

            self.log(f"Renaming to: {new_dest.name}", "info")
            self.stats.files_renamed += 1
            return True, new_dest

        # Interactive mode would go here (not implemented for non-blocking operation)
        else:
            self.log(f"Skipping duplicate {item_type} (interactive not supported)", "warning")
            self.stats.files_skipped += 1
            return False, None

    def move_item(
        self,
        item: Path,
        is_directory: bool = False
    ) -> bool:
        """
        Move file or directory to year-based folder.

        Args:
            item: Path to file or directory
            is_directory: Whether item is a directory

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get year
            year = self.get_item_year(item)
            if year is None:
                self.log(f"Skipping {item.name} (no date)", "warning")
                self.stats.files_skipped += 1
                return False

            # Create target directory path
            year_dir = self.config.target_dir / str(year)
            dest = year_dir / item.name

            item_type = "directory" if is_directory else "file"

            # Handle duplicates
            if dest.exists():
                should_move, new_dest = self.handle_duplicate(item, dest, is_directory)
                if not should_move:
                    return False
                if new_dest:
                    dest = new_dest

            # Perform move
            if self.config.dry_run:
                self.log(f"[DRY-RUN] Would move {item_type}: {item.name} → {dest.relative_to(self.config.target_dir)}", "info")
            else:
                # Create year directory
                year_dir.mkdir(parents=True, exist_ok=True)

                # Move (handles both files and directories)
                shutil.move(str(item), str(dest))
                self.log(f"Moved {item_type}: {item.name} → {dest.relative_to(self.config.target_dir)}", "success")

                if is_directory:
                    self.stats.dirs_moved += 1
                else:
                    self.stats.files_moved += 1

            return True

        except Exception as e:
            self.log(f"Error processing {item.name}: {str(e)}", "error")
            self.stats.errors += 1
            return False

    def organize(self) -> OrganizerStats:
        """
        Main organization method. Process all files/directories in source.

        Returns:
            Statistics of the operation
        """
        self._cancelled = False
        self.stats = OrganizerStats()

        self.log(f"Starting file organization...", "info")
        self.log(f"Source: {self.config.source_dir}", "info")
        self.log(f"Target: {self.config.target_dir}", "info")
        if self.config.dry_run:
            self.log("DRY RUN MODE - No changes will be made", "warning")

        # Collect items to process
        try:
            items = list(self.config.source_dir.iterdir())
        except Exception as e:
            self.log(f"Error reading source directory: {str(e)}", "error")
            self.stats.errors += 1
            return self.stats

        # Filter items based on configuration
        items_to_process = []
        for item in items:
            if self._cancelled:
                break

            is_dir = item.is_dir()
            if self.should_process_item(item, is_dir):
                items_to_process.append((item, is_dir))
            elif self.config.verbose:
                self.log(f"Skipping: {item.name}", "info")

        total = len(items_to_process)
        self.log(f"Processing {total} items...", "info")

        # Process items
        for idx, (item, is_dir) in enumerate(items_to_process, 1):
            if self._cancelled:
                self.log("Operation cancelled", "warning")
                break

            self.update_progress(idx, total)

            if self.config.verbose or not self.config.dry_run:
                item_type = "directory" if is_dir else "file"
                self.log(f"[{idx}/{total}] Processing {item_type}: {item.name}", "info")

            self.move_item(item, is_dir)

        # Print summary
        self.log("=" * 60, "info")
        self.log("Summary:", "info")
        self.log("=" * 60, "info")

        if self.stats.files_moved > 0:
            self.log(f"Files moved: {self.stats.files_moved}", "success")
        if self.stats.dirs_moved > 0:
            self.log(f"Directories moved: {self.stats.dirs_moved}", "success")
        if self.stats.files_renamed > 0:
            self.log(f"Files renamed: {self.stats.files_renamed}", "warning")
        if self.stats.files_skipped > 0:
            self.log(f"Files skipped: {self.stats.files_skipped}", "warning")
        if self.stats.errors > 0:
            self.log(f"Errors: {self.stats.errors}", "error")

        self.log("=" * 60, "info")

        if self.config.dry_run:
            self.log("This was a dry run. Uncheck 'Dry Run' to apply changes.", "warning")

        return self.stats
