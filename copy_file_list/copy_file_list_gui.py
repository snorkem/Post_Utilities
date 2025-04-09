#!/usr/bin/env python3
"""
File Search and Copy Utility GUI v1.0
=====================================
A PyQt5 GUI frontend for the copy_file_list.py script.
This application provides a user-friendly interface to:
- Select source directories
- Select destination directory
- Choose between file list or EDL file input
- Configure various options
- View console output in real-time
- Track operation progress

Author: Claude
Version: 1.0
"""

import os
import sys
import subprocess
import time
import re
import threading
import queue
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, 
    QCheckBox, QTabWidget, QSpinBox, QProgressBar, QMessageBox,
    QGroupBox, QRadioButton, QButtonGroup, QSplitter, QListWidget,
    QPlainTextEdit, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QProcess
from PyQt5.QtGui import QTextCursor, QFont, QIcon, QTextCharFormat, QColor


class StreamReader(QThread):
    """Thread to read from a stream (stdout/stderr) and emit signals with the content."""
    output_received = pyqtSignal(str)
    progress_update = pyqtSignal(int, int)  # current, total
    file_processed = pyqtSignal(str)
    
    def __init__(self, process):
        super().__init__()
        self.process = process
        self._stop_event = threading.Event()
        
    def run(self):
        """Read from the process and emit signals."""
        while not self._stop_event.is_set():
            # Read all available data
            if self.process.state() == QProcess.Running:
                # Read available data 
                data = self.process.readAllStandardOutput()
                if data.size() > 0:
                    text = bytes(data).decode('utf-8', errors='replace')
                    lines = text.splitlines()
                    
                    for line in lines:
                        if line:
                            self.output_received.emit(line)
                            
                            # Try to extract progress information
                            self._parse_progress_info(line)
                            
                            # Check for file processing info
                            self._parse_file_info(line)
            
            # Small sleep to prevent tight loop
            time.sleep(0.1)
        
        # Final read to catch any remaining output
        while True:
            data = self.process.readAllStandardOutput()
            if data.size() == 0:
                break
            text = bytes(data).decode('utf-8', errors='replace')
            lines = text.splitlines()
            
            for line in lines:
                if line:
                    self.output_received.emit(line)
                    
                    # Try to extract progress information
                    self._parse_progress_info(line)
                    
                    # Check for file processing info
                    self._parse_file_info(line)
    
    def _parse_progress_info(self, line):
        """Parse progress information from the line."""
        # Match progress bar output like: Progress: [####      ] 25% (5/20 files)
        progress_match = re.search(r'Progress:.*?(\d+)%.*?\((\d+)/(\d+)', line)
        if progress_match:
            current = int(progress_match.group(2))
            total = int(progress_match.group(3))
            self.progress_update.emit(current, total)
            return
            
        # Match EDL parsing progress
        edl_match = re.search(r'EDL Parsing Progress.*?\((\d+)/(\d+)', line)
        if edl_match:
            current = int(edl_match.group(1))
            total = int(edl_match.group(2))
            self.progress_update.emit(current, total)
            return
    
    def _parse_file_info(self, line):
        """Parse information about processed files."""
        # Look for "Copied to:" or "WOULD COPY:" lines
        if "Copied to:" in line or "WOULD COPY:" in line:
            # Extract just the filename from the path
            parts = line.split(":", 1)
            if len(parts) > 1:
                filepath = parts[1].strip()
                filename = os.path.basename(filepath)
                self.file_processed.emit(filename)
    
    def stop(self):
        """Stop the thread."""
        self._stop_event.set()
        self.wait()


class ConsoleOutputWidget(QWidget):
    """Widget to display console output with color highlighting."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Create console output text edit
        self.console_output = QPlainTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setLineWrapMode(QPlainTextEdit.NoWrap)
        font = QFont("Courier New", 10)
        self.console_output.setFont(font)
        self.console_output.setMaximumBlockCount(10000)  # Limit to prevent memory issues
        
        # Add to layout
        self.layout.addWidget(self.console_output)
        
        # Format for different message types
        self.normal_format = QTextCharFormat()
        self.error_format = QTextCharFormat()
        self.error_format.setForeground(QColor("red"))
        self.success_format = QTextCharFormat()
        self.success_format.setForeground(QColor("green"))
        self.warning_format = QTextCharFormat()
        self.warning_format.setForeground(QColor("orange"))
        
        # Clear button
        self.clear_button = QPushButton("Clear Console")
        self.clear_button.clicked.connect(self.clear_console)
        self.layout.addWidget(self.clear_button)
    
    def append_text(self, text):
        """Append text to the console with appropriate formatting."""
        # Determine the format based on the text content
        if any(err in text.lower() for err in ["error", "failed", "cannot"]):
            format_to_use = self.error_format
        elif any(warn in text.lower() for warn in ["warning", "caution"]):
            format_to_use = self.warning_format
        elif any(succ in text.lower() for succ in ["copied", "success", "completed"]):
            format_to_use = self.success_format
        else:
            format_to_use = self.normal_format
        
        # Append text with the determined format
        cursor = self.console_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text + '\n')
        self.console_output.setTextCursor(cursor)
        self.console_output.ensureCursorVisible()
    
    def clear_console(self):
        """Clear the console output."""
        self.console_output.clear()


class FileInputDialog(QDialog):
    """Dialog for entering a list of files directly."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter File List")
        self.resize(600, 400)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel("Enter one file pattern per line:")
        layout.addWidget(instructions)
        
        # Text edit for file list
        self.file_list_edit = QPlainTextEdit()
        self.file_list_edit.setPlaceholderText("Example:\n*.jpg\ndoc_*.pdf\nfile_[0-9].txt")
        layout.addWidget(self.file_list_edit)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_file_list(self):
        """Return the entered file list as a list of strings."""
        text = self.file_list_edit.toPlainText()
        if not text:
            return []
        return [line.strip() for line in text.splitlines() if line.strip()]


class CopyFileListGUI(QMainWindow):
    """Main window for the Copy File List GUI application."""
    
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("File Search and Copy Utility")
        self.resize(900, 700)
        
        # Initialize attributes
        self.process = None
        self.temp_file_list_path = None
        self.last_selected_directory = os.path.expanduser("~")
        
        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create a splitter for input controls and output
        self.splitter = QSplitter(Qt.Vertical)
        self.main_layout.addWidget(self.splitter)
        
        # Create input panel
        self.input_panel = QWidget()
        self.input_layout = QVBoxLayout(self.input_panel)
        self.splitter.addWidget(self.input_panel)
        
        # Create directories section
        self.create_directories_section()
        
        # Create input method section (file list or EDL)
        self.create_input_method_section()
        
        # Create options section
        self.create_options_section()
        
        # Create action buttons
        self.create_action_buttons()
        
        # Create progress section
        self.create_progress_section()
        
        # Create output panel with tabs
        self.output_panel = QTabWidget()
        self.splitter.addWidget(self.output_panel)
        
        # Console output
        self.console_widget = ConsoleOutputWidget()
        self.output_panel.addTab(self.console_widget, "Console Output")
        
        # Files processed list
        self.files_list_widget = QListWidget()
        self.output_panel.addTab(self.files_list_widget, "Files Processed")
        
        # Set initial splitter sizes
        self.splitter.setSizes([400, 300])
        
        # Set up timer for periodic UI updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui_state)
        self.update_timer.start(500)  # Update every 500ms
    
    def create_directories_section(self):
        """Create the source and destination directory input section."""
        directories_group = QGroupBox("Directories")
        directories_layout = QVBoxLayout(directories_group)
        
        # Source directories
        source_layout = QHBoxLayout()
        source_label = QLabel("Source Directories:")
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("Comma-separated list of source directories")
        source_browse_button = QPushButton("Browse...")
        source_browse_button.clicked.connect(self.browse_source_directories)
        
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_edit, 1)
        source_layout.addWidget(source_browse_button)
        directories_layout.addLayout(source_layout)
        
        # Destination directory - use the same approach as source directories
        dest_layout = QHBoxLayout()
        dest_label = QLabel("Destination Directories:")
        self.dest_edit = QLineEdit()
        self.dest_edit.setPlaceholderText("Comma-separated list of destination directories")
        dest_browse_button = QPushButton("Browse...")
        dest_browse_button.clicked.connect(self.browse_destination_directories)
        
        dest_layout.addWidget(dest_label)
        dest_layout.addWidget(self.dest_edit, 1)
        dest_layout.addWidget(dest_browse_button)
        directories_layout.addLayout(dest_layout)
        
        # Log file
        log_layout = QHBoxLayout()
        log_label = QLabel("Log File:")
        self.log_edit = QLineEdit()
        self.log_edit.setPlaceholderText("Path to log file")
        log_browse_button = QPushButton("Browse...")
        log_browse_button.clicked.connect(self.browse_log_file)
        
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_edit, 1)
        log_layout.addWidget(log_browse_button)
        directories_layout.addLayout(log_layout)
        
        self.input_layout.addWidget(directories_group)
    
    def create_input_method_section(self):
        """Create the section for selecting input method (file list or EDL)."""
        input_method_group = QGroupBox("Input Method")
        input_method_layout = QVBoxLayout(input_method_group)
        
        # Radio buttons for input method
        self.input_method_buttons = QButtonGroup(self)
        
        file_list_radio = QRadioButton("File List")
        file_list_radio.setChecked(True)
        edl_file_radio = QRadioButton("EDL File")
        
        self.input_method_buttons.addButton(file_list_radio, 0)
        self.input_method_buttons.addButton(edl_file_radio, 1)
        
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(file_list_radio)
        radio_layout.addWidget(edl_file_radio)
        radio_layout.addStretch()
        input_method_layout.addLayout(radio_layout)
        
        # File list input
        file_list_layout = QHBoxLayout()
        self.file_list_edit = QLineEdit()
        self.file_list_edit.setPlaceholderText("Path to file containing list of filenames")
        file_list_browse_button = QPushButton("Browse...")
        file_list_browse_button.clicked.connect(self.browse_file_list)
        file_list_manual_button = QPushButton("Enter List...")
        file_list_manual_button.clicked.connect(self.enter_file_list)
        
        file_list_layout.addWidget(self.file_list_edit, 1)
        file_list_layout.addWidget(file_list_browse_button)
        file_list_layout.addWidget(file_list_manual_button)
        input_method_layout.addLayout(file_list_layout)
        
        # EDL file input
        edl_layout = QHBoxLayout()
        self.edl_edit = QLineEdit()
        self.edl_edit.setPlaceholderText("Path to EDL file")
        self.edl_edit.setEnabled(False)
        edl_browse_button = QPushButton("Browse...")
        edl_browse_button.clicked.connect(self.browse_edl_file)
        edl_browse_button.setEnabled(False)
        
        edl_layout.addWidget(self.edl_edit, 1)
        edl_layout.addWidget(edl_browse_button)
        input_method_layout.addLayout(edl_layout)
        
        # Connect radio button signals
        self.input_method_buttons.buttonClicked.connect(self.input_method_changed)
        
        # Store references to widgets that need to be enabled/disabled
        self.file_list_widgets = [self.file_list_edit, file_list_browse_button, file_list_manual_button]
        self.edl_widgets = [self.edl_edit, edl_browse_button]
        
        self.input_layout.addWidget(input_method_group)
    
    def create_options_section(self):
        """Create the section for additional options."""
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        
        # Create two columns for options
        options_row1 = QHBoxLayout()
        options_row2 = QHBoxLayout()
        options_row3 = QHBoxLayout()  # New row for additional options
        
        # Row 1 options
        self.show_progress_check = QCheckBox("Show Progress")
        self.show_progress_check.setChecked(True)
        options_row1.addWidget(self.show_progress_check)
        
        self.first_match_only_check = QCheckBox("First Match Only")
        self.first_match_only_check.setChecked(True)
        self.first_match_only_check.setToolTip("Stop after finding the first match for each pattern")
        options_row1.addWidget(self.first_match_only_check)

        self.dry_run_check = QCheckBox("Dry Run")
        options_row1.addWidget(self.dry_run_check)
        
        self.verify_check = QCheckBox("Verify Copies")
        options_row1.addWidget(self.verify_check)
        
        options_row1.addStretch()
        
        # Row 2 options
        self.parallel_check = QCheckBox("Parallel Processing")
        options_row2.addWidget(self.parallel_check)
        
        self.use_regex_check = QCheckBox("Use Regex")
        options_row2.addWidget(self.use_regex_check)

        
        max_size_layout = QHBoxLayout()
        max_size_layout.addWidget(QLabel("Max Size (MB):"))
        self.max_size_spin = QSpinBox()
        self.max_size_spin.setRange(0, 100000)
        self.max_size_spin.setSpecialValueText("No Limit")
        max_size_layout.addWidget(self.max_size_spin)
        options_row2.addLayout(max_size_layout)
        
        options_row2.addStretch()
        
        # Row 3 options (moved exclude file here)
        exclude_layout = QHBoxLayout()
        exclude_layout.addWidget(QLabel("Exclude:"))
        self.exclude_edit = QLineEdit()
        self.exclude_edit.setPlaceholderText("Path to exclude file")
        exclude_browse_button = QPushButton("Browse...")
        exclude_browse_button.clicked.connect(self.browse_exclude_file)
        
        exclude_layout.addWidget(self.exclude_edit, 1)
        exclude_layout.addWidget(exclude_browse_button)
        options_row3.addLayout(exclude_layout)
        options_row3.addStretch()
        
        # Add rows to options layout
        options_layout.addLayout(options_row1)
        options_layout.addLayout(options_row2)
        options_layout.addLayout(options_row3)
        
        self.input_layout.addWidget(options_group)
    
    def create_action_buttons(self):
        """Create action buttons (Run, Cancel, etc.)."""
        buttons_layout = QHBoxLayout()
        
        # Run button
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_script)
        buttons_layout.addWidget(self.run_button)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_script)
        self.cancel_button.setEnabled(False)
        buttons_layout.addWidget(self.cancel_button)
        
        # Add to main layout
        self.input_layout.addLayout(buttons_layout)
    
    def create_progress_section(self):
        """Create progress bar and status label."""
        progress_layout = QHBoxLayout()
        
        # Status label
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar, 1)
        
        self.input_layout.addLayout(progress_layout)
    
    def input_method_changed(self, button):
        """Handle input method radio button changes."""
        if self.input_method_buttons.id(button) == 0:  # File List
            for widget in self.file_list_widgets:
                widget.setEnabled(True)
            for widget in self.edl_widgets:
                widget.setEnabled(False)
        else:  # EDL File
            for widget in self.file_list_widgets:
                widget.setEnabled(False)
            for widget in self.edl_widgets:
                widget.setEnabled(True)
    
    def browse_source_directories(self):
        """Open dialog to browse for source directories."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Source Directory", self.last_selected_directory
        )
        if directory:
            self.last_selected_directory = directory
            # Append to existing directories with comma separator
            current_dirs = self.source_edit.text()
            if current_dirs:
                self.source_edit.setText(f"{current_dirs},{directory}")
            else:
                self.source_edit.setText(directory)
    
    def browse_destination_directories(self):
        """Open dialog to browse for destination directories."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Destination Directory", self.last_selected_directory
        )
        if directory:
            self.last_selected_directory = directory
            # Append to existing directories with comma separator
            current_dirs = self.dest_edit.text()
            if current_dirs:
                self.dest_edit.setText(f"{current_dirs},{directory}")
            else:
                self.dest_edit.setText(directory)
    
    def browse_log_file(self):
        """Open dialog to browse for log file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Select Log File", self.last_selected_directory, "Log Files (*.log *.txt);;All Files (*)"
        )
        if file_path:
            self.last_selected_directory = os.path.dirname(file_path)
            self.log_edit.setText(file_path)
    
    def browse_file_list(self):
        """Open dialog to browse for file list."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File List", self.last_selected_directory, "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.last_selected_directory = os.path.dirname(file_path)
            self.file_list_edit.setText(file_path)
    
    def enter_file_list(self):
        """Open dialog to manually enter file list."""
        dialog = FileInputDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            file_list = dialog.get_file_list()
            if file_list:
                # Create a temporary file with the list
                if self.temp_file_list_path:
                    try:
                        os.unlink(self.temp_file_list_path)
                    except OSError:
                        pass
                
                # Generate a new temporary file path
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.temp_file_list_path = os.path.join(
                    os.path.expanduser("~"), f"file_list_{timestamp}.txt"
                )
                
                # Write the list to the temporary file
                with open(self.temp_file_list_path, 'w') as f:
                    f.write('\n'.join(file_list))
                
                # Update the file list edit field
                self.file_list_edit.setText(self.temp_file_list_path)
    
    def browse_edl_file(self):
        """Open dialog to browse for EDL file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select EDL File", self.last_selected_directory, "EDL Files (*.edl);;All Files (*)"
        )
        if file_path:
            self.last_selected_directory = os.path.dirname(file_path)
            self.edl_edit.setText(file_path)
    
    def browse_exclude_file(self):
        """Open dialog to browse for exclude file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Exclude File", self.last_selected_directory, "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.last_selected_directory = os.path.dirname(file_path)
            self.exclude_edit.setText(file_path)
    
    def validate_inputs(self):
        """Validate user inputs before running the script."""
        # Check source directories
        if not self.source_edit.text():
            QMessageBox.warning(self, "Input Error", "Please specify at least one source directory.")
            return False
        
        # Check destination directory
        if not self.dest_edit.text():
            QMessageBox.warning(self, "Input Error", "Please specify at least one destination directory.")
            return False
        
        # Check log file
        if not self.log_edit.text():
            QMessageBox.warning(self, "Input Error", "Please specify a log file.")
            return False
        
        # Check input method
        if self.input_method_buttons.checkedId() == 0:  # File List
            if not self.file_list_edit.text():
                QMessageBox.warning(self, "Input Error", "Please specify a file list.")
                return False
        else:  # EDL File
            if not self.edl_edit.text():
                QMessageBox.warning(self, "Input Error", "Please specify an EDL file.")
                return False
        
        return True
    
    def build_command(self):
        """Build the command to run the copy_file_list.py script."""
        # Base command
        command = ["python3", "copy_file_list.py"]
        
        # Source directories
        command.extend(["-s", self.source_edit.text()])
        
        # Destination directory
        command.extend(["-d", self.dest_edit.text()])
        
        # Log file
        command.extend(["-l", self.log_edit.text()])
        
        # Input method
        if self.input_method_buttons.checkedId() == 0:  # File List
            command.extend(["-f", self.file_list_edit.text()])
        else:  # EDL File
            command.extend(["--edl", self.edl_edit.text()])
        
        # Options
        if self.show_progress_check.isChecked():
            command.append("-p")
        
        if self.use_regex_check.isChecked():
            command.append("-r")
        
        if self.dry_run_check.isChecked():
            command.append("-n")
        
        if self.verify_check.isChecked():
            command.append("--verify")
        
        if self.parallel_check.isChecked():
            command.append("--parallel")
        
        if self.first_match_only_check.isChecked():
            command.append("--first-match-only")
        
        # Max size
        if self.max_size_spin.value() > 0:
            command.extend(["-m", str(self.max_size_spin.value())])
        
        # Exclude file
        if self.exclude_edit.text():
            command.extend(["-x", self.exclude_edit.text()])
        
        return command
    
    def run_script(self):
        """Run the copy_file_list.py script with the specified options."""
        if not self.validate_inputs():
            return
        
        # Build the command
        command = self.build_command()
        
        # Update UI state
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Running...")
        self.files_list_widget.clear()
        self.console_widget.console_output.clear()
        
        # Log the command
        cmd_str = " ".join(command)
        self.console_widget.append_text(f"Running command: {cmd_str}")
        
        # Start the process
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        
        # Create a stream reader
        self.stream_reader = StreamReader(self.process)
        self.stream_reader.output_received.connect(self.console_widget.append_text)
        self.stream_reader.progress_update.connect(self.update_progress)
        self.stream_reader.file_processed.connect(self.add_processed_file)
        
        # Connect process signals
        self.process.started.connect(self.stream_reader.start)
        self.process.finished.connect(self.process_finished)
        self.process.finished.connect(self.stream_reader.stop)
        
        # Start the process
        self.process.start(command[0], command[1:])
    
    def update_progress(self, current, total):
        """Update progress bar with current progress."""
        if total > 0:
            percent = int(current * 100 / total)
            self.progress_bar.setValue(percent)
    
    def add_processed_file(self, filename):
        """Add processed file to the files list."""
        self.files_list_widget.addItem(filename)
        self.files_list_widget.scrollToBottom()
    
    def process_finished(self, exit_code, exit_status):
        """Handle process finished event."""
        # Wait for stream reader to finish
        self.stream_reader.wait(1000)  # Wait up to 1 second
        
        # Reset UI state
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        # Determine status
        if exit_code == 0:
            if self.dry_run_check.isChecked():
                status_text = "Dry run completed successfully"
            else:
                status_text = "Operation completed successfully"
            self.progress_bar.setValue(100)
        else:
            status_text = f"Operation failed with exit code {exit_code}"
        
        # Update status
        self.status_label.setText(status_text)
    
    def cancel_script(self):
        """Cancel the running script."""
        if self.process and self.process.state() == QProcess.Running:
            # Confirm with user
            reply = QMessageBox.question(
                self, "Confirm Cancel", 
                "Are you sure you want to cancel the operation?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Terminate the process
                self.process.terminate()
                
                # If it doesn't terminate, try to kill it
                QTimer.singleShot(2000, self.force_kill_process)
                
                self.status_label.setText("Operation cancelled")
                self.run_button.setEnabled(True)
                self.cancel_button.setEnabled(False)
    
    def force_kill_process(self):
        """Force kill the process if it didn't terminate."""
        if self.process and self.process.state() != QProcess.NotRunning:
            self.process.kill()
    
    def handle_stdout(self):
        """Handle standard output from the process."""
        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        lines = data.splitlines()
        
        for line in lines:
            if line:
                self.console_widget.append_text(line)
                
                # Update progress bar for progress lines
                self.update_progress_from_line(line)
                
                # Update files list for copy lines
                self.update_files_list_from_line(line)
    
    def update_progress_from_line(self, line):
        """Update progress bar based on progress information in the line."""
        # Match progress bar output
        progress_match = re.search(r'Progress:.*?(\d+)%.*?\((\d+)/(\d+)', line)
        if progress_match:
            percent = int(progress_match.group(1))
            self.progress_bar.setValue(percent)
            return
            
        # Match EDL parsing progress
        edl_match = re.search(r'EDL Parsing Progress.*?\((\d+)/(\d+)', line)
        if edl_match:
            current = int(edl_match.group(1))
            total = int(edl_match.group(2))
            percent = int(current * 100 / total)
            self.progress_bar.setValue(percent)
            return
    
    def update_files_list_from_line(self, line):
        """Update files list based on file information in the line."""
        # Look for "Copied to:" or "WOULD COPY:" lines
        if "Copied to:" in line or "WOULD COPY:" in line:
            # Extract just the filename from the path
            parts = line.split(":", 1)
            if len(parts) > 1:
                filepath = parts[1].strip()
                filename = os.path.basename(filepath)
                self.files_list_widget.addItem(filename)
                # Scroll to bottom
                self.files_list_widget.scrollToBottom()
    
    def process_finished(self, exit_code, exit_status):
        """Handle process finished event."""
        if exit_code == 0:
            if self.dry_run_check.isChecked():
                self.status_label.setText("Dry run completed successfully")
            else:
                self.status_label.setText("Operation completed successfully")
        else:
            self.status_label.setText(f"Operation failed with exit code {exit_code}")
        
        # Update UI state
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        # Ensure progress bar is at 100% if successful
        if exit_code == 0:
            self.progress_bar.setValue(100)
    
    def cancel_script(self):
        """Cancel the running script."""
        if self.process and self.process.state() == QProcess.Running:
            # Confirm with user
            reply = QMessageBox.question(
                self, "Confirm Cancel", 
                "Are you sure you want to cancel the operation?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.process.kill()
                self.status_label.setText("Operation cancelled")
                self.run_button.setEnabled(True)
                self.cancel_button.setEnabled(False)
    
    def update_ui_state(self):
        """Update UI state based on current conditions."""
        # Update run/cancel button state based on process running state
        is_process_running = False
        if self.process is not None:
            is_process_running = self.process.state() == QProcess.Running
        
        self.run_button.setEnabled(not is_process_running)
        self.cancel_button.setEnabled(is_process_running)
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Check if a process is running
        is_process_running = False
        if self.process is not None:
            is_process_running = self.process.state() == QProcess.Running
            
        if is_process_running:
            # Confirm with user before closing
            reply = QMessageBox.question(
                self, "Confirm Exit", 
                "A file operation is currently in progress. Are you sure you want to exit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
            else:
                # Try to terminate the process
                if self.process.state() == QProcess.Running:
                    self.process.kill()
        
        # Clean up temporary file if it exists
        if self.temp_file_list_path and os.path.exists(self.temp_file_list_path):
            try:
                os.unlink(self.temp_file_list_path)
            except OSError:
                pass
        
        # Accept the close event
        event.accept()
def main():
    """
    Main entry point for the File Search and Copy Utility GUI application.
    
    Sets up the application, configures global settings, creates the main window,
    and runs the event loop with error handling.
    """
    try:
        # Create the QApplication instance
        app = QApplication(sys.argv)
        
        # Set application metadata
        app.setApplicationName("File Search and Copy Utility")
        app.setApplicationVersion("1.0")
        
        # Set high DPI scaling if supported
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        # Create the main window
        main_window = CopyFileListGUI()
        
        # Style the application with a modern look
        app.setStyle("Fusion")
        
        # Show the main window
        main_window.show()
        
        # Center the window on the screen
        frame_geometry = main_window.frameGeometry()
        center_point = QApplication.desktop().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        main_window.move(frame_geometry.topLeft())
        
        # Run the application event loop and exit with its return code
        return app.exec_()
    
    except Exception as e:
        # Log any unexpected errors
        error_msg = f"Unexpected error during application startup: {e}"
        print(error_msg, file=sys.stderr)
        
        # Show an error message box
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle("Application Error")
        error_dialog.setText("An unexpected error occurred while starting the application.")
        error_dialog.setDetailedText(str(e))
        error_dialog.exec_()
        
        # Return an error code
        return 1

if __name__ == "__main__":
    sys.exit(main())