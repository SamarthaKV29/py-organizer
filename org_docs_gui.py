#!/usr/bin/env python3
"""
org_docs_gui.py - GUI for Python File Organizer
Modern PySide6 interface for organizing files into year-based folders.
Pure Python implementation - no bash dependencies.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QTreeWidget,
    QTreeWidgetItem, QCheckBox, QTextEdit, QGroupBox, QGridLayout,
    QSplitter, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut

from file_organizer import FileOrganizer, OrganizerConfig, DuplicateMode


class OrganizerRunner(QThread):
    """Background thread for running file organization"""
    log_received = Signal(str, str)  # message, level
    progress_updated = Signal(int, int)  # current, total
    finished = Signal(object)  # stats

    def __init__(self, config: OrganizerConfig):
        super().__init__()
        self.config = config
        self.organizer = None
        self._cancelled = False

    def run(self):
        """Execute file organization"""
        try:
            self.organizer = FileOrganizer(
                config=self.config,
                log_callback=self.log_received.emit,
                progress_callback=self.progress_updated.emit
            )
            stats = self.organizer.organize()
            self.finished.emit(stats)
        except Exception as e:
            self.log_received.emit(f"Fatal error: {str(e)}", "error")
            self.finished.emit(None)

    def cancel(self):
        """Cancel the running operation"""
        if self.organizer:
            self.organizer.cancel()


class OrgDocsGUI(QMainWindow):
    """Main GUI window for file organizer"""

    SETTINGS_FILE = Path(__file__).parent / "org_docs_gui.json"

    # Color mapping for log levels
    LOG_COLORS = {
        'info': '#61afef',
        'success': '#4CAF50',
        'warning': '#ff9800',
        'error': '#f44336'
    }

    def __init__(self):
        super().__init__()
        self.runner_thread = None
        self.source_dir = str(Path.home())
        self.splitter = None
        self.zoom_level = 1.0
        self.progress_bar = None

        self.init_ui()
        self.setup_shortcuts()
        self.load_settings()
        self.refresh_tree()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("File Organizer - Year-based Folders (Python)")
        self.setGeometry(100, 100, 950, 750)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create splitter for resizable sections
        self.splitter = QSplitter(Qt.Vertical)

        # Top section
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)

        # Directory selection
        dir_group = QGroupBox("Directories")
        dir_layout = QGridLayout()

        dir_layout.addWidget(QLabel("Source:"), 0, 0)
        self.source_edit = QLineEdit(str(Path.home()))
        dir_layout.addWidget(self.source_edit, 0, 1)
        source_btn = QPushButton("Browse...")
        source_btn.clicked.connect(self.browse_source)
        dir_layout.addWidget(source_btn, 0, 2)

        dir_layout.addWidget(QLabel("Target:"), 1, 0)
        self.target_edit = QLineEdit("")
        self.target_edit.setPlaceholderText("(defaults to source)")
        dir_layout.addWidget(self.target_edit, 1, 1)
        target_btn = QPushButton("Browse...")
        target_btn.clicked.connect(self.browse_target)
        dir_layout.addWidget(target_btn, 1, 2)

        dir_group.setLayout(dir_layout)
        top_layout.addWidget(dir_group)

        # Folder selection tree
        tree_group = QGroupBox("Select Folders to Process (top-level only)")
        tree_layout = QVBoxLayout()

        tree_toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_tree)
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all)
        tree_toolbar.addWidget(refresh_btn)
        tree_toolbar.addWidget(select_all_btn)
        tree_toolbar.addWidget(deselect_all_btn)
        tree_toolbar.addStretch()
        tree_layout.addLayout(tree_toolbar)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("Folders")
        self.tree_widget.setAlternatingRowColors(True)
        self.tree_widget.setMinimumHeight(150)  # Ensure tree is visible
        tree_layout.addWidget(self.tree_widget)

        tree_group.setLayout(tree_layout)
        top_layout.addWidget(tree_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QHBoxLayout()

        self.dry_run_cb = QCheckBox("Dry Run (preview only)")
        self.dry_run_cb.setChecked(True)
        self.interactive_cb = QCheckBox("Interactive")
        self.interactive_cb.setEnabled(False)  # Not supported in GUI mode
        self.interactive_cb.setToolTip("Not supported in GUI mode")
        self.verbose_cb = QCheckBox("Verbose")

        # Checkbox styling
        checkbox_style = """
            QCheckBox {
                spacing: 8px;
                color: #e0e0e0;
                font-size: 10pt;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #666;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #4CAF50;
                background-color: #3d3d3d;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border: 2px solid #4CAF50;
            }
            QCheckBox::indicator:disabled {
                background-color: #1a1a1a;
                border-color: #444;
            }
        """

        for cb in [self.dry_run_cb, self.interactive_cb, self.verbose_cb]:
            cb.setStyleSheet(checkbox_style)

        options_layout.addWidget(self.dry_run_cb)
        options_layout.addWidget(self.interactive_cb)
        options_layout.addWidget(self.verbose_cb)
        options_layout.addStretch()

        options_group.setLayout(options_layout)
        top_layout.addWidget(options_group)

        self.splitter.addWidget(top_widget)

        # Bottom section (log output)
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)

        # Log header with controls
        log_header = QHBoxLayout()
        log_label = QLabel("Log Output")
        log_label.setFont(QFont("Arial", 10, QFont.Bold))
        log_header.addWidget(log_label)

        # Zoom controls
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.setToolTip("Zoom Out (Ctrl+-)")
        zoom_out_btn.clicked.connect(self.zoom_out)
        log_header.addWidget(zoom_out_btn)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet("color: #888; font-size: 9pt;")
        log_header.addWidget(self.zoom_label)

        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.setToolTip("Zoom In (Ctrl++)")
        zoom_in_btn.clicked.connect(self.zoom_in)
        log_header.addWidget(zoom_in_btn)

        zoom_reset_btn = QPushButton("↺")
        zoom_reset_btn.setToolTip("Reset Zoom (Ctrl+0)")
        zoom_reset_btn.clicked.connect(self.zoom_reset)
        log_header.addWidget(zoom_reset_btn)

        log_header.addStretch()

        # Action buttons
        self.run_btn = QPushButton("▶ Run")
        self.run_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;"
        )
        self.run_btn.clicked.connect(self.run_organizer)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setStyleSheet(
            "background-color: #f44336; color: white; font-weight: bold; padding: 8px;"
        )
        self.stop_btn.clicked.connect(self.stop_organizer)
        self.stop_btn.setEnabled(False)

        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_log)

        log_header.addWidget(self.run_btn)
        log_header.addWidget(self.stop_btn)
        log_header.addWidget(clear_btn)

        log_layout.addLayout(log_header)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        log_layout.addWidget(self.progress_bar)

        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Consolas", 9))
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        log_layout.addWidget(self.log_output)

        self.splitter.addWidget(log_widget)
        self.splitter.setSizes([420, 280])

        main_layout.addWidget(self.splitter)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        QShortcut(QKeySequence("Ctrl++"), self).activated.connect(self.zoom_in)
        QShortcut(QKeySequence("Ctrl+="), self).activated.connect(self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self).activated.connect(self.zoom_reset)

    def zoom_in(self):
        """Increase UI zoom level"""
        self.zoom_level = min(self.zoom_level + 0.1, 2.0)
        self.apply_zoom()

    def zoom_out(self):
        """Decrease UI zoom level"""
        self.zoom_level = max(self.zoom_level - 0.1, 0.5)
        self.apply_zoom()

    def zoom_reset(self):
        """Reset zoom to 100%"""
        self.zoom_level = 1.0
        self.apply_zoom()

    def apply_zoom(self):
        """Apply current zoom level to UI elements"""
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
        self.log_output.setFont(QFont("Consolas", int(9 * self.zoom_level)))
        self.tree_widget.setFont(QFont("Arial", int(9 * self.zoom_level)))
        self.save_settings()

    def browse_source(self):
        """Browse for source directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Source Directory", self.source_edit.text()
        )
        if dir_path:
            self.source_edit.setText(dir_path)
            self.source_dir = dir_path
            self.refresh_tree()
            self.save_settings()

    def browse_target(self):
        """Browse for target directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Target Directory",
            self.target_edit.text() or self.source_edit.text()
        )
        if dir_path:
            self.target_edit.setText(dir_path)
            self.save_settings()

    def refresh_tree(self):
        """Refresh the folder tree from source directory"""
        self.tree_widget.clear()
        source_path = Path(self.source_edit.text())

        if not source_path.exists():
            self.append_log(f"Source directory does not exist: {source_path}", "error")
            return

        try:
            subdirs = [d for d in source_path.iterdir() if d.is_dir()]
            subdirs.sort(key=lambda x: x.name.lower())

            for subdir in subdirs:
                # Get directory info
                try:
                    stat_info = subdir.stat()
                    mod_time = datetime.fromtimestamp(stat_info.st_mtime)
                    year = mod_time.year
                    file_count = len([f for f in subdir.iterdir() if f.is_file()])
                    display_text = f"{subdir.name}  [{year}]"
                except Exception:
                    display_text = subdir.name

                item = QTreeWidgetItem([display_text])
                item.setCheckState(0, Qt.Unchecked)
                item.setData(0, Qt.UserRole, subdir.name)

                # Add child folders (one level deep for expandability)
                try:
                    child_dirs = [d for d in subdir.iterdir() if d.is_dir()]
                    child_dirs.sort(key=lambda x: x.name.lower())

                    for child_dir in child_dirs:
                        try:
                            child_stat = child_dir.stat()
                            child_mod = datetime.fromtimestamp(child_stat.st_mtime)
                            child_year = child_mod.year
                            child_text = f"{child_dir.name}  [{child_year}]"
                        except Exception:
                            child_text = child_dir.name

                        child_item = QTreeWidgetItem([child_text])
                        child_item.setData(0, Qt.UserRole, child_dir.name)
                        item.addChild(child_item)
                except Exception:
                    pass  # Skip if can't read subdirectories

                self.tree_widget.addTopLevelItem(item)

            self.append_log(f"Loaded {len(subdirs)} folders from {source_path}", "success")

        except Exception as e:
            self.append_log(f"Error loading folders: {str(e)}", "error")

    def select_all(self):
        """Select all top-level folders"""
        for i in range(self.tree_widget.topLevelItemCount()):
            self.tree_widget.topLevelItem(i).setCheckState(0, Qt.Checked)

    def deselect_all(self):
        """Deselect all top-level folders"""
        for i in range(self.tree_widget.topLevelItemCount()):
            self.tree_widget.topLevelItem(i).setCheckState(0, Qt.Unchecked)

    def get_selected_folders(self):
        """Get list of selected folder names"""
        selected = []
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                folder_name = item.data(0, Qt.UserRole)
                selected.append(folder_name)
        return selected

    def run_organizer(self):
        """Run the file organizer"""
        source_path = Path(self.source_edit.text())
        if not source_path.exists():
            QMessageBox.critical(
                self,
                "Invalid Source",
                f"Source directory does not exist:\n{source_path}"
            )
            return

        # Get configuration
        selected_folders = self.get_selected_folders()
        files_only = len(selected_folders) == 0

        if files_only:
            reply = QMessageBox.question(
                self,
                "No Folders Selected",
                "No folders are selected. This will process ONLY FILES (directories will be skipped).\n\nContinue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Build configuration
        target_path = Path(self.target_edit.text()) if self.target_edit.text() else None

        config = OrganizerConfig(
            source_dir=source_path,
            target_dir=target_path,
            dry_run=self.dry_run_cb.isChecked(),
            files_only=files_only,
            verbose=self.verbose_cb.isChecked(),
            duplicate_mode=DuplicateMode.RENAME,
            included_folders=selected_folders if selected_folders else None
        )

        # Clear log and show progress
        self.log_output.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Log configuration
        self.append_log(f"Starting file organization...", "info")
        self.append_log(f"Source: {config.source_dir}", "info")
        self.append_log(f"Target: {config.target_dir}", "info")
        if config.dry_run:
            self.append_log("DRY RUN MODE - No changes will be made", "warning")
        if files_only:
            self.append_log("FILES ONLY mode - Directories will be skipped", "info")
        self.append_log("─" * 80, "info")

        # Disable run button, enable stop button
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # Start runner thread
        self.runner_thread = OrganizerRunner(config)
        self.runner_thread.log_received.connect(self.append_log)
        self.runner_thread.progress_updated.connect(self.update_progress)
        self.runner_thread.finished.connect(self.on_finished)
        self.runner_thread.start()

    def stop_organizer(self):
        """Stop the running organizer"""
        if self.runner_thread and self.runner_thread.isRunning():
            self.stop_btn.setEnabled(False)
            self.runner_thread.cancel()
            self.append_log("Cancelling operation...", "warning")

    def append_log(self, message: str, level: str = "info"):
        """Append message to log output with color coding"""
        color = self.LOG_COLORS.get(level, self.LOG_COLORS['info'])
        html = f"<span style='color: {color};'>{message}</span>"
        self.log_output.append(html)

        # Auto-scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_progress(self, current: int, total: int):
        """Update progress bar"""
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
            percentage = int((current / total) * 100)
            self.progress_bar.setFormat(f"{current}/{total} ({percentage}%)")

    def on_finished(self, stats):
        """Handle organizer completion"""
        self.append_log("─" * 80, "info")

        if stats:
            self.append_log("✓ Operation completed", "success")
        else:
            self.append_log("✗ Operation failed", "error")

        # Hide progress bar
        self.progress_bar.setVisible(False)

        # Re-enable run button, disable stop button
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def clear_log(self):
        """Clear the log output"""
        self.log_output.clear()

    def load_settings(self):
        """Load settings from JSON file"""
        if not self.SETTINGS_FILE.exists():
            return

        try:
            with open(self.SETTINGS_FILE, 'r') as f:
                settings = json.load(f)

            if 'source_dir' in settings and settings['source_dir']:
                self.source_edit.setText(settings['source_dir'])
                self.source_dir = settings['source_dir']

            if 'target_dir' in settings:
                self.target_edit.setText(settings['target_dir'])

            # Checkboxes (dry_run intentionally NOT restored - always defaults to ON)
            if 'verbose' in settings:
                self.verbose_cb.setChecked(settings['verbose'])

            if 'splitter_sizes' in settings and self.splitter:
                self.splitter.setSizes(settings['splitter_sizes'])

            if 'zoom_level' in settings:
                self.zoom_level = settings['zoom_level']
                self.apply_zoom()

            self.append_log("✓ Settings loaded", "success")

        except Exception as e:
            self.append_log(f"Warning: Could not load settings: {str(e)}", "warning")

    def save_settings(self):
        """Save settings to JSON file"""
        try:
            settings = {
                'source_dir': self.source_edit.text(),
                'target_dir': self.target_edit.text(),
                'verbose': self.verbose_cb.isChecked(),
                'splitter_sizes': self.splitter.sizes() if self.splitter else [420, 280],
                'zoom_level': self.zoom_level
            }

            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=2)

        except Exception as e:
            print(f"Warning: Could not save settings: {str(e)}")

    def closeEvent(self, event):
        """Save settings when window closes"""
        if self.runner_thread and self.runner_thread.isRunning():
            self.runner_thread.cancel()
            if not self.runner_thread.wait(3000):
                self.runner_thread.terminate()
                self.runner_thread.wait()

        self.save_settings()
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = OrgDocsGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
