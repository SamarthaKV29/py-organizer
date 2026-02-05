#!/usr/bin/env python3
"""
org_docs_gui.py - GUI wrapper for org_docs.sh script
Simple and elegant PySide6 interface for organizing files into year-based folders.
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QTreeWidget,
    QTreeWidgetItem, QCheckBox, QTextEdit, QGroupBox, QGridLayout,
    QSplitter, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QProcess
from PySide6.QtGui import QIcon, QFont


class ScriptRunner(QThread):
    """Background thread for running the bash script"""
    output_received = Signal(str)
    process_finished = Signal(int)

    def __init__(self, script_path, args):
        super().__init__()
        self.script_path = script_path
        self.args = args
        self.process = None

    def run(self):
        """Execute the bash script and stream output"""
        try:
            # Use Git Bash on Windows
            if sys.platform == "win32":
                cmd = ["bash", str(self.script_path)] + self.args
            else:
                cmd = [str(self.script_path)] + self.args

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Stream output line by line
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.output_received.emit(line.rstrip())

            self.process.wait()
            self.process_finished.emit(self.process.returncode)

        except Exception as e:
            self.output_received.emit(f"Error: {str(e)}")
            self.process_finished.emit(1)

    def stop(self):
        """Terminate the running process"""
        if self.process:
            self.process.terminate()


class OrgDocsGUI(QMainWindow):
    """Main GUI window for org_docs.sh"""

    SETTINGS_FILE = Path(__file__).parent / "org_docs_gui.json"

    def __init__(self):
        super().__init__()
        self.script_path = Path(__file__).parent / "org_docs.sh"
        self.runner_thread = None
        self.source_dir = str(Path.home())
        self.splitter = None  # Will be set in init_ui

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("File Organizer - Year-based Folders")
        self.setGeometry(100, 100, 900, 700)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create splitter for resizable sections
        self.splitter = QSplitter(Qt.Vertical)

        # Top section (directory selection + tree + options)
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
        tree_layout.addWidget(self.tree_widget)

        tree_group.setLayout(tree_layout)
        top_layout.addWidget(tree_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QHBoxLayout()

        self.dry_run_cb = QCheckBox("Dry Run (preview only)")
        self.dry_run_cb.setChecked(True)
        self.interactive_cb = QCheckBox("Interactive")
        self.verbose_cb = QCheckBox("Verbose")

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

        log_header = QHBoxLayout()
        log_label = QLabel("Log Output")
        log_label.setFont(QFont("Arial", 10, QFont.Bold))
        log_header.addWidget(log_label)
        log_header.addStretch()

        self.run_btn = QPushButton("▶ Run")
        self.run_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.run_btn.clicked.connect(self.run_script)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        self.stop_btn.clicked.connect(self.stop_script)
        self.stop_btn.setEnabled(False)

        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_log)

        log_header.addWidget(self.run_btn)
        log_header.addWidget(self.stop_btn)
        log_header.addWidget(clear_btn)

        log_layout.addLayout(log_header)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Consolas", 9))
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        log_layout.addWidget(self.log_output)

        self.splitter.addWidget(log_widget)

        # Set splitter sizes (60% top, 40% bottom)
        self.splitter.setSizes([420, 280])

        main_layout.addWidget(self.splitter)

        # Initial tree load
        self.refresh_tree()

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
            self, "Select Target Directory", self.target_edit.text() or self.source_edit.text()
        )
        if dir_path:
            self.target_edit.setText(dir_path)
            self.save_settings()

    def refresh_tree(self):
        """Refresh the folder tree from source directory"""
        self.tree_widget.clear()
        source_path = Path(self.source_edit.text())

        if not source_path.exists():
            self.log_output.append(f"<span style='color: #f44336;'>Source directory does not exist: {source_path}</span>")
            return

        try:
            # Get all top-level subdirectories
            subdirs = [d for d in source_path.iterdir() if d.is_dir()]
            subdirs.sort(key=lambda x: x.name.lower())

            for subdir in subdirs:
                # Get directory date
                try:
                    mod_time = subdir.stat().st_mtime
                    date_str = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d')
                    year = datetime.fromtimestamp(mod_time).strftime('%Y')
                except:
                    date_str = 'unknown'
                    year = '?'

                # Create top-level item with checkbox
                item = QTreeWidgetItem(self.tree_widget)
                item.setText(0, f"{subdir.name}  [{year}]")
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                item.setData(0, Qt.UserRole, str(subdir))
                item.setToolTip(0, f"Modified: {date_str}")

                # Add child items (not checkable, just for preview)
                try:
                    children = list(subdir.iterdir())[:50]  # Limit to 50 items
                    for child in children:
                        child_item = QTreeWidgetItem(item)
                        child_item.setText(0, f"{'📁' if child.is_dir() else '📄'} {child.name}")
                        child_item.setFlags(child_item.flags() & ~Qt.ItemIsUserCheckable)
                        child_item.setForeground(0, Qt.gray)

                    if len(list(subdir.iterdir())) > 50:
                        more_item = QTreeWidgetItem(item)
                        more_item.setText(0, "... (more items)")
                        more_item.setForeground(0, Qt.gray)
                except PermissionError:
                    pass

            self.log_output.append(f"<span style='color: #4CAF50;'>Loaded {len(subdirs)} folders from {source_path}</span>")

        except Exception as e:
            self.log_output.append(f"<span style='color: #f44336;'>Error loading folders: {str(e)}</span>")

    def select_all(self):
        """Select all top-level folders"""
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            item.setCheckState(0, Qt.Checked)

    def deselect_all(self):
        """Deselect all top-level folders"""
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            item.setCheckState(0, Qt.Unchecked)

    def get_selected_folders(self):
        """Get list of selected folder names"""
        selected = []
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                selected.append(item.text(0))
        return selected

    def build_command_args(self):
        """Build command line arguments for the script"""
        args = []

        # Source directory
        source = self.source_edit.text()
        if source:
            args.extend(["--source-dir", source])

        # Target directory
        target = self.target_edit.text()
        if target:
            args.extend(["--target-dir", target])

        # Options
        if self.dry_run_cb.isChecked():
            args.append("--dry-run")

        if self.interactive_cb.isChecked():
            args.append("--interactive")

        if self.verbose_cb.isChecked():
            args.append("--verbose")

        # Selected folders
        selected_folders = self.get_selected_folders()
        if selected_folders:
            for folder in selected_folders:
                args.extend(["--include", folder])

        return args

    def run_script(self):
        """Run the org_docs.sh script"""
        if not self.script_path.exists():
            QMessageBox.critical(
                self,
                "Script Not Found",
                f"Cannot find org_docs.sh at:\n{self.script_path}\n\nPlease ensure the script is in the same directory as this GUI."
            )
            return

        selected_folders = self.get_selected_folders()
        if not selected_folders:
            reply = QMessageBox.question(
                self,
                "No Folders Selected",
                "No folders are selected. This will process ALL top-level items.\n\nContinue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        args = self.build_command_args()

        self.log_output.clear()
        self.log_output.append(f"<span style='color: #61afef;'>Running: bash {self.script_path.name} {' '.join(args)}</span>")
        self.log_output.append("<span style='color: #61afef;'>{'─' * 80}</span>")

        # Disable run button, enable stop button
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # Start runner thread
        self.runner_thread = ScriptRunner(self.script_path, args)
        self.runner_thread.output_received.connect(self.append_log)
        self.runner_thread.process_finished.connect(self.on_process_finished)
        self.runner_thread.start()

    def stop_script(self):
        """Stop the running script"""
        if self.runner_thread:
            self.runner_thread.stop()
            self.log_output.append("<span style='color: #f44336;'>Process terminated by user</span>")

    def append_log(self, text):
        """Append text to log output with color coding"""
        # Simple color coding based on content
        if "error" in text.lower() or "failed" in text.lower():
            text = f"<span style='color: #f44336;'>{text}</span>"
        elif "success" in text.lower() or "moved" in text.lower():
            text = f"<span style='color: #4CAF50;'>{text}</span>"
        elif "warning" in text.lower() or "skip" in text.lower():
            text = f"<span style='color: #ff9800;'>{text}</span>"
        elif "dry-run" in text.lower():
            text = f"<span style='color: #2196F3;'>{text}</span>"
        else:
            text = f"<span style='color: #d4d4d4;'>{text}</span>"

        self.log_output.append(text)

        # Auto-scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_process_finished(self, exit_code):
        """Handle process completion"""
        self.log_output.append("<span style='color: #61afef;'>{'─' * 80}</span>")
        if exit_code == 0:
            self.log_output.append("<span style='color: #4CAF50;'>✓ Process completed successfully</span>")
        else:
            self.log_output.append(f"<span style='color: #f44336;'>✗ Process exited with code {exit_code}</span>")

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

            # Restore paths
            if 'source_dir' in settings and settings['source_dir']:
                self.source_edit.setText(settings['source_dir'])
                self.source_dir = settings['source_dir']

            if 'target_dir' in settings:
                self.target_edit.setText(settings['target_dir'])

            # Restore checkboxes
            if 'dry_run' in settings:
                self.dry_run_cb.setChecked(settings['dry_run'])

            if 'interactive' in settings:
                self.interactive_cb.setChecked(settings['interactive'])

            if 'verbose' in settings:
                self.verbose_cb.setChecked(settings['verbose'])

            # Restore splitter sizes
            if 'splitter_sizes' in settings and self.splitter:
                self.splitter.setSizes(settings['splitter_sizes'])

            self.log_output.append("<span style='color: #4CAF50;'>✓ Settings loaded</span>")

        except Exception as e:
            self.log_output.append(f"<span style='color: #ff9800;'>Warning: Could not load settings: {str(e)}</span>")

    def save_settings(self):
        """Save settings to JSON file"""
        try:
            settings = {
                'source_dir': self.source_edit.text(),
                'target_dir': self.target_edit.text(),
                'dry_run': self.dry_run_cb.isChecked(),
                'interactive': self.interactive_cb.isChecked(),
                'verbose': self.verbose_cb.isChecked(),
                'splitter_sizes': self.splitter.sizes() if self.splitter else [420, 280]
            }

            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=2)

        except Exception as e:
            print(f"Warning: Could not save settings: {str(e)}")

    def closeEvent(self, event):
        """Save settings when window closes"""
        self.save_settings()
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern cross-platform style

    window = OrgDocsGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
