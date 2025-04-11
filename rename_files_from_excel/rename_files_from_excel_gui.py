import os
import sys
import re
import logging
import pandas as pd
from pathlib import Path
import threading
import traceback
import subprocess
import datetime
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QListWidget, QTextEdit, 
                            QGroupBox, QGridLayout, QFileDialog, QMessageBox, QStatusBar,
                            QScrollArea, QCheckBox)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot


class TextRedirector(QObject):
    """Class to redirect stdout to a QTextEdit widget."""
    text_written = pyqtSignal(str)
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.text_written.connect(self.update_text)
        self.buffer = ""
        
    def write(self, string):
        self.buffer += string
        self.text_written.emit(string)
        
    def flush(self):
        pass
        
    @pyqtSlot(str)
    def update_text(self, text):
        self.text_widget.moveCursor(self.text_widget.textCursor().End)
        self.text_widget.insertPlainText(text)
        self.text_widget.ensureCursorVisible()


class FileRenamerApp(QMainWindow):
    """GUI application for renaming files based on Excel data."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Renamer Tool")
        self.setMinimumSize(800, 800)
        self.resize(800, 1200)
        
        # Column names in Excel
        self.master_name_col = "Master Original Name"
        self.proxy_name_col = "Avid Proxy Name"
        self.master_suffix = "_M"
        
        # File and directory paths
        self.excel_path = ""
        self.target_dirs = []
        
        # Processing options
        self.recursive_search = True
        self.force_overwrite = False
        self.dry_run = False
        
        # Setup logger
        self.logger = self.setup_logger()
        
        # Create UI components
        self.init_ui()
        
        # Store backup of stdout for redirection
        self.stdout_backup = sys.stdout
    
    def setup_logger(self, logname='renames.log'):
        """Set up and return a logger with appropriate configuration."""
        # Store the log file path as an instance variable for easy access
        self.log_file_path = os.path.abspath(logname)
        
        logging.basicConfig(
            filename=self.log_file_path,
            filemode='a',
            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
            datefmt="%Y-%m-%d %H:%M:%S",
            level=logging.DEBUG
        )
        return logging.getLogger('File Renamer Tool')
    
    def init_ui(self):
        """Initialize the user interface."""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Brief explanation at the top
        explanation_frame = QGroupBox()
        explanation_layout = QVBoxLayout(explanation_frame)
        explanation_text = "This tool renames files based on an Excel spreadsheet. It looks for files with names matching the 'Master Original Name' column\nand renames them to the corresponding name in the 'Avid Proxy Name' column, adding the suffix at the end."
        explanation_label = QLabel(explanation_text)
        explanation_label.setAlignment(Qt.AlignLeft)
        explanation_layout.addWidget(explanation_label)
        main_layout.addWidget(explanation_frame)
        
        # Excel file selection section
        excel_frame = QGroupBox("Excel File Selection")
        excel_layout = QGridLayout(excel_frame)
        
        excel_label = QLabel("Excel File:")
        excel_layout.addWidget(excel_label, 0, 0)
        
        self.excel_path_edit = QLineEdit()
        excel_layout.addWidget(self.excel_path_edit, 0, 1)
        
        excel_browse_btn = QPushButton("Browse...")
        excel_browse_btn.clicked.connect(self.browse_excel_file)
        excel_layout.addWidget(excel_browse_btn, 0, 2)
        
        main_layout.addWidget(excel_frame)
        
        # Directory selection section
        dir_frame = QGroupBox("Target Directories")
        dir_layout = QVBoxLayout(dir_frame)
        
        dir_button_frame = QWidget()
        dir_button_layout = QHBoxLayout(dir_button_frame)
        
        dir_label = QLabel("Directory:")
        dir_button_layout.addWidget(dir_label)
        
        self.dir_entry = QLineEdit()
        dir_button_layout.addWidget(self.dir_entry)
        
        dir_browse_btn = QPushButton("Browse...")
        dir_browse_btn.clicked.connect(self.browse_directory)
        dir_button_layout.addWidget(dir_browse_btn)
        
        add_dir_btn = QPushButton("Add Directory")
        add_dir_btn.clicked.connect(self.add_directory)
        dir_button_layout.addWidget(add_dir_btn)
        
        remove_dir_btn = QPushButton("Remove Selected")
        remove_dir_btn.clicked.connect(self.remove_directory)
        dir_button_layout.addWidget(remove_dir_btn)
        
        dir_layout.addWidget(dir_button_frame)
        
        # Directory listbox
        self.dir_listbox = QListWidget()
        dir_layout.addWidget(self.dir_listbox)
        
        main_layout.addWidget(dir_frame)
        
        # Excel column configuration section
        config_frame = QGroupBox("Excel Configuration")
        config_layout = QGridLayout(config_frame)
        
        master_label = QLabel("Master Original Name Column:")
        config_layout.addWidget(master_label, 0, 0)
        
        self.master_col_edit = QLineEdit(self.master_name_col)
        config_layout.addWidget(self.master_col_edit, 0, 1)
        
        master_desc = QLabel("(Column containing original filenames to search for)")
        config_layout.addWidget(master_desc, 0, 2)
        
        proxy_label = QLabel("Avid Proxy Name Column:")
        config_layout.addWidget(proxy_label, 1, 0)
        
        self.proxy_col_edit = QLineEdit(self.proxy_name_col)
        config_layout.addWidget(self.proxy_col_edit, 1, 1)
        
        proxy_desc = QLabel("(Column containing new filenames to rename to)")
        config_layout.addWidget(proxy_desc, 1, 2)
        
        suffix_label = QLabel("Master File Suffix:")
        config_layout.addWidget(suffix_label, 2, 0)
        
        self.suffix_edit = QLineEdit(self.master_suffix)
        config_layout.addWidget(self.suffix_edit, 2, 1)
        
        suffix_desc = QLabel("(Added to the end of each renamed file)")
        config_layout.addWidget(suffix_desc, 2, 2)
        
        main_layout.addWidget(config_frame)
        
        # Options section
        options_frame = QGroupBox("Options")
        options_layout = QVBoxLayout(options_frame)
        
        self.recursive_checkbox = QCheckBox("Search files recursively in subdirectories")
        self.recursive_checkbox.setChecked(self.recursive_search)
        options_layout.addWidget(self.recursive_checkbox)
        
        self.force_checkbox = QCheckBox("Force overwrite (create backup of existing destination files)")
        self.force_checkbox.setChecked(self.force_overwrite)
        options_layout.addWidget(self.force_checkbox)
        
        self.dry_run_checkbox = QCheckBox("Dry run (show what would be renamed without making changes)")
        self.dry_run_checkbox.setChecked(self.dry_run)
        options_layout.addWidget(self.dry_run_checkbox)
        
        main_layout.addWidget(options_frame)
        
        # Action buttons
        button_frame = QWidget()
        button_layout = QHBoxLayout(button_frame)
        
        log_button = QPushButton("View Log File")
        log_button.clicked.connect(self.open_log_file)
        button_layout.addWidget(log_button)
        
        button_layout.addStretch()
        
        rename_button = QPushButton("RENAME FILES")
        rename_button.setStyleSheet("font-weight: bold; font-size: 14px;")
        rename_button.clicked.connect(self.start_renaming)
        button_layout.addWidget(rename_button)
        
        main_layout.addWidget(button_frame)
        
        # Output console
        console_frame = QGroupBox("Console Output")
        console_layout = QVBoxLayout(console_frame)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        console_layout.addWidget(self.console)
        
        main_layout.addWidget(console_frame)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def browse_excel_file(self):
        """Browse for Excel file and update the path field."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Excel File", "", "Excel Files (*.xlsx *.xls)")
            
            if file_path:
                self.excel_path_edit.setText(file_path)
                self.status_bar.showMessage(f"Excel file selected: {os.path.basename(file_path)}")
        
        except Exception as e:
            error_msg = f"Error browsing for file: {str(e)}"
            self.logger.error(error_msg)
            QMessageBox.critical(self, "Error", f"Could not browse for file: {str(e)}")
    
    def browse_directory(self):
        """Browse for directory and update the path field."""
        try:
            dir_path = QFileDialog.getExistingDirectory(
                self, "Select Target Directory", "")
            
            if dir_path:
                self.dir_entry.setText(dir_path)
                self.status_bar.showMessage(f"Directory selected: {dir_path}")
        
        except Exception as e: 
            error_msg = f"Error browsing for directory: {str(e)}"
            self.logger.error(error_msg)
            QMessageBox.critical(self, "Error", f"Could not browse for directory: {str(e)}")
    
    def open_log_file(self):
        """Open the log file in the default system text editor."""
        try:
            if not os.path.exists(self.log_file_path):
                # Create an empty log file if it doesn't exist yet
                with open(self.log_file_path, 'w') as f:
                    f.write("Log file created on {}\n".format(
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                
            # Open the log file with the system's default text editor
            if sys.platform == "win32":
                # Windows
                os.startfile(self.log_file_path)
            elif sys.platform == "darwin":
                # macOS
                subprocess.Popen(["open", self.log_file_path])
            else:
                # Linux and other Unix-like
                subprocess.Popen(["xdg-open", self.log_file_path])
                
            self.status_bar.showMessage(f"Opened log file: {self.log_file_path}")
        except Exception as e:
            error_msg = f"Error opening log file: {str(e)}"
            self.logger.error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
            
            # Fallback: Show the log file path so the user can find it manually
            QMessageBox.information(self, "Log File Location", 
                               f"The log file is located at:\n{self.log_file_path}\n\n"
                               f"Please open it manually with a text editor.")
    
    def add_directory(self):
        """Add a directory to the list."""
        dir_path = self.dir_entry.text().strip()
        if not dir_path:
            QMessageBox.information(self, "Input Required", "Please enter a directory path.")
            return
            
        if dir_path not in self.target_dirs:
            self.target_dirs.append(dir_path)
            self.dir_listbox.addItem(dir_path)
            self.dir_entry.clear()  # Clear the entry
            self.status_bar.showMessage(f"Added directory: {dir_path}")
        else:
            QMessageBox.warning(self, "Duplicate Directory", "This directory is already in the list.")
    
    def remove_directory(self):
        """Remove selected directory from the list."""
        selected_items = self.dir_listbox.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Selection Required", "Please select a directory to remove.")
            return
            
        for item in selected_items:
            row = self.dir_listbox.row(item)
            self.dir_listbox.takeItem(row)
            self.target_dirs.remove(item.text())
            
        self.status_bar.showMessage("Directory removed")
    
    def check_single_sheet(self, excel_file):
        """Check if the Excel file contains only a single sheet."""
        try:
            # Use pandas ExcelFile to get sheet names
            xls = pd.ExcelFile(excel_file)
            sheet_names = xls.sheet_names
            
            if len(sheet_names) > 1:
                error_msg = f"Excel file contains multiple sheets: {', '.join(sheet_names)}. Only single-sheet files are supported."
                print(error_msg)
                self.logger.error(error_msg)
                return False, sheet_names[0]
            
            return True, sheet_names[0]
            
        except Exception as e:
            error_msg = f"Error checking Excel sheets: {str(e)}"
            print(error_msg)
            self.logger.error(error_msg)
            return False, None
    
    def validate_inputs(self):
        """Validate all user inputs before running the renaming process."""
        excel_path = self.excel_path_edit.text()
        if not excel_path:
            QMessageBox.critical(self, "Input Error", "Please enter an Excel file path.")
            return False
            
        # Verify the Excel file has the correct extension
        if not excel_path.lower().endswith(('.xlsx', '.xls')):
            QMessageBox.critical(self, "Input Error", "The specified file is not an Excel file (.xlsx or .xls).")
            return False
            
        if not os.path.exists(excel_path):
            QMessageBox.critical(self, "Input Error", "The specified Excel file does not exist.")
            return False
            
        # Check if Excel has only one sheet
        single_sheet, sheet_name = self.check_single_sheet(excel_path)
        if not single_sheet:
            QMessageBox.critical(self, "Excel Error", "This tool only supports Excel files with a single sheet.")
            return False
            
        if not self.target_dirs:
            QMessageBox.critical(self, "Input Error", "Please add at least one target directory.")
            return False
            
        for dir_path in self.target_dirs:
            if not os.path.exists(dir_path):
                QMessageBox.critical(self, "Input Error", f"Directory does not exist: {dir_path}")
                return False
                
        if not self.master_col_edit.text() or not self.proxy_col_edit.text():
            QMessageBox.critical(self, "Input Error", "Please provide column names for Master and Proxy names.")
            return False
            
        return True
    
    def start_renaming(self):
        """Start the file renaming process in a separate thread."""
        if not self.validate_inputs():
            return
            
        # Update configuration values from UI
        self.master_name_col = self.master_col_edit.text()
        self.proxy_name_col = self.proxy_col_edit.text()
        self.master_suffix = self.suffix_edit.text()
        self.excel_path = self.excel_path_edit.text()
        self.recursive_search = self.recursive_checkbox.isChecked()
        self.force_overwrite = self.force_checkbox.isChecked()
        self.dry_run = self.dry_run_checkbox.isChecked()
            
        # Disable UI during processing
        self.disable_ui()
        
        # Redirect stdout to console
        sys.stdout = TextRedirector(self.console)
        
        # Start processing in a separate thread
        thread = threading.Thread(target=self.rename_files_process)
        thread.daemon = True
        thread.start()
    
    def disable_ui(self):
        """Disable UI controls during processing."""
        central_widget = self.centralWidget()
        for child in central_widget.findChildren(QPushButton):
            child.setEnabled(False)
        
        for child in central_widget.findChildren(QLineEdit):
            child.setEnabled(False)
            
        for child in central_widget.findChildren(QCheckBox):
            child.setEnabled(False)
            
        self.dir_listbox.setEnabled(False)
        self.status_bar.showMessage("Processing... Please wait.")
    
    def enable_ui(self):
        """Re-enable UI controls after processing."""
        central_widget = self.centralWidget()
        for child in central_widget.findChildren(QPushButton):
            child.setEnabled(True)
        
        for child in central_widget.findChildren(QLineEdit):
            child.setEnabled(True)
            
        for child in central_widget.findChildren(QCheckBox):
            child.setEnabled(True)
            
        self.dir_listbox.setEnabled(True)
        self.status_bar.showMessage("Ready")
    
    def rename_files_process(self):
        """Main file renaming process."""
        try:
            # Get configuration values
            excel_file = Path(os.path.abspath(self.excel_path))
            target_dirs = [Path(os.path.abspath(dir_path)) for dir_path in self.target_dirs]
            master_col = self.master_name_col
            proxy_col = self.proxy_name_col
            suffix = self.master_suffix
            recursive = self.recursive_search
            force = self.force_overwrite
            dry_run = self.dry_run
            
            # Clear console
            self.console.clear()
            
            print(f"Starting file renaming process:")
            print(f"Excel file: {excel_file}")
            print(f"Target directories: {', '.join(str(d) for d in target_dirs)}")
            print(f"Master column: {master_col}")
            print(f"Proxy column: {proxy_col}")
            print(f"Suffix: {suffix}")
            print(f"Recursive search: {recursive}")
            print(f"Force overwrite: {force}")
            print(f"Dry run: {dry_run}")
            print("-" * 50)
            
            # Log the configuration
            self.logger.info("Configuration: excel=%s, dirs=%s, master_col=%s, proxy_col=%s, "
                           "suffix=%s, recursive=%s, force=%s, dry_run=%s",
                           excel_file, target_dirs, master_col, proxy_col,
                           suffix, recursive, force, dry_run)
            
            # Read Excel file
            try:
                # Get sheet name first
                _, sheet_name = self.check_single_sheet(excel_file)
                
                df = pd.read_excel(excel_file, sheet_name=0)  # Always use first sheet
                print(f"Successfully read Excel file with {len(df)} rows from sheet '{sheet_name}'")
                self.logger.info(f"Successfully read Excel file with {len(df)} rows from sheet '{sheet_name}'")
            except Exception as e:
                print(f"Error reading Excel file: {str(e)}")
                self.logger.error(f"Error reading Excel file: {str(e)}")
                QApplication.instance().processEvents()  # Process pending events
                QMessageBox.critical(self, "Excel Error", f"Error reading Excel file: {str(e)}")
                QApplication.instance().processEvents()  # Process pending events
                self.enable_ui()
                return
                
            # Verify required columns exist
            if master_col not in df.columns:
                error_msg = f"Required column not found: '{master_col}'"
                print(error_msg)
                self.logger.error(error_msg)
                QApplication.instance().processEvents()  # Process pending events
                QMessageBox.critical(self, "Column Error", error_msg)
                QApplication.instance().processEvents()  # Process pending events
                self.enable_ui()
                return
                
            if proxy_col not in df.columns:
                error_msg = f"Required column not found: '{proxy_col}'"
                print(error_msg)
                self.logger.error(error_msg)
                QApplication.instance().processEvents()  # Process pending events
                QMessageBox.critical(self, "Column Error", error_msg)
                QApplication.instance().processEvents()  # Process pending events
                self.enable_ui()
                return
                
            # Extract data from Excel
            proxy_names = df[proxy_col]
            master_file_names = df[master_col]
            
            # Validate filenames
            invalid_rows = []
            for index, (master_name, proxy_name) in enumerate(zip(master_file_names, proxy_names)):
                if not self.validate_filename(master_name, index, master_col) or \
                   not self.validate_filename(proxy_name, index, proxy_col):
                    invalid_rows.append(index + 2)  # +2 for Excel row number
            
            if invalid_rows:
                error_msg = f"Invalid filenames found in rows: {', '.join(map(str, invalid_rows))}"
                print(error_msg)
                self.logger.error(error_msg)
                QApplication.instance().processEvents()  # Process pending events
                QMessageBox.critical(self, "Validation Error", error_msg)
                QApplication.instance().processEvents()  # Process pending events
                self.enable_ui()
                return
            
            # Check for duplicates
            master_dups = master_file_names.duplicated()
            proxy_dups = proxy_names.duplicated()
            
            if master_dups.any() or proxy_dups.any():
                master_dup_rows = [i+2 for i, is_dup in enumerate(master_dups) if is_dup]
                proxy_dup_rows = [i+2 for i, is_dup in enumerate(proxy_dups) if is_dup]
                
                error_parts = []
                if master_dup_rows:
                    error_parts.append(f"Duplicate master names in rows: {', '.join(map(str, master_dup_rows))}")
                if proxy_dup_rows:
                    error_parts.append(f"Duplicate proxy names in rows: {', '.join(map(str, proxy_dup_rows))}")
                    
                error_msg = " and ".join(error_parts)
                print(error_msg)
                self.logger.error(error_msg)
                QApplication.instance().processEvents()  # Process pending events
                QMessageBox.critical(self, "Duplicate Error", error_msg)
                QApplication.instance().processEvents()  # Process pending events
                self.enable_ui()
                return
            
            # Collect files to process from all target directories
            files_to_rename = []
            for target_dir in target_dirs:
                print(f"Collecting files from: {target_dir}")
                dir_files = self.collect_files_recursively(target_dir, recursive)
                files_to_rename.extend(dir_files)
                print(f"Found {len(dir_files)} files in {target_dir}")
            
            print(f"Total files collected from all directories: {len(files_to_rename)}")
            
            if not files_to_rename:
                print("No files found to rename.")
                self.logger.info("No files found to rename.")
                QApplication.instance().processEvents()  # Process pending events
                QMessageBox.information(self, "No Files", "No files found to rename in the specified directories.")
                QApplication.instance().processEvents()  # Process pending events
                self.enable_ui()
                return
            
            # Perform renaming
            renamed = self.rename_files_efficiently(
                files_to_rename, 
                master_file_names, 
                proxy_names, 
                suffix,
                force,
                dry_run
            )
            
            # Show completion message
            dry_run_prefix = "Dry run - " if dry_run else ""
            completion_msg = f"{dry_run_prefix}Successfully {'' if dry_run else ''}renamed {renamed} files out of {len(files_to_rename)} files processed."
            print(completion_msg)
            print("See 'renames.log' for complete details.")
            self.logger.info(completion_msg)
            QApplication.instance().processEvents()  # Process pending events
            QMessageBox.information(self, "Process Complete", completion_msg)
            QApplication.instance().processEvents()  # Process pending events
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.logger.exception(error_msg)
            QApplication.instance().processEvents()  # Process pending events
            QMessageBox.critical(self, "Error", error_msg)
            QApplication.instance().processEvents()  # Process pending events
            
        finally:
            # Restore stdout
            sys.stdout = self.stdout_backup
            
            # Re-enable UI
            self.enable_ui()
    
    def validate_filename(self, filename, index, column_name):
        """Check if filename contains valid characters and is not empty."""
        if pd.isna(filename):
            error_msg = f"Empty cell in {column_name} on row {index+2}"
            print(error_msg)
            self.logger.error(error_msg)
            return False
            
        # Check for invalid path characters
        invalid_chars_pattern = re.compile(r"[<>/{}[\]~`]")
        if invalid_chars_pattern.search(str(filename)):
            error_msg = f"Invalid path character detected in {column_name} on row {index+2}"
            print(error_msg)
            self.logger.error(error_msg)
            return False
            
        # Check for non-ASCII characters
        try:
            str(filename).encode('ascii')
            return True
        except UnicodeEncodeError:
            error_msg = f"Non-ASCII character in {column_name} '{filename}' on row {index+2}"
            print(error_msg)
            self.logger.error(error_msg)
            return False
    
    def collect_files_recursively(self, directory, recursive=True):
        """Recursively collect all non-hidden files from directory and subdirectories."""
        files_list = []
        
        if not directory.is_dir():
            error_msg = f"Target is not a directory: {directory}"
            print(error_msg)
            self.logger.error(error_msg)
            return files_list
            
        print(f"Target is directory: {directory}. Collecting files...")
        
        try:
            if recursive:
                # Use rglob for recursive search
                for path in directory.rglob('*'):
                    if path.is_file() and not path.name.startswith('.'):
                        files_list.append(path)
            else:
                # Use iterdir for non-recursive search
                for path in directory.iterdir():
                    if path.is_file() and not path.name.startswith('.'):
                        files_list.append(path)
                        
        except Exception as e:
            error_msg = f"Error collecting files from {directory}: {str(e)}"
            print(error_msg)
            self.logger.error(error_msg)
        
        return files_list
    
    def rename_files_efficiently(self, target_files, master_names, proxy_names, suffix, force=False, dry_run=False):
        """Rename files using an efficient lookup approach."""
        # Create a lookup dictionary for faster access
        rename_map = {}
        for index, master_name in master_names.items():
            if pd.notna(master_name) and pd.notna(proxy_names[index]):
                rename_map[str(master_name)] = str(proxy_names[index])
        
        rename_count = 0
        skipped_count = 0
        errors_count = 0
        
        # Process each file
        for file_path in target_files:
            file_name = file_path.stem
            file_ext = file_path.suffix
            
            if file_name in rename_map:
                new_name = rename_map[file_name] + suffix + file_ext
                new_path = file_path.parent / new_name
                
                try:
                    # Check if destination exists
                    if new_path.exists():
                        if force and not dry_run:
                            # If force flag is true, create a backup before overwriting
                            backup_path = new_path.with_name(f"{new_path.stem}_backup_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{new_path.suffix}")
                            shutil.copy2(new_path, backup_path)
                            print(f"Backed up existing file to: {backup_path}")
                            self.logger.info(f"Backed up existing file: {new_path} -> {backup_path}")
                        else:
                            print(f"Skipping {file_path} - destination already exists: {new_path}")
                            self.logger.warning(f"Skipping rename - destination exists: {new_path}")
                            skipped_count += 1
                            continue
                    
                    # Perform rename or simulate it
                    if dry_run:
                        print(f"Would rename: {file_path.name} -> {new_name}")
                        self.logger.info(f"Dry run: would rename {file_path} -> {new_path}")
                        rename_count += 1
                    else:
                        file_path.rename(new_path)
                        print(f"Renamed: {file_path.name} -> {new_path.name}")
                        self.logger.info(f"Renamed: {file_path} -> {new_path}")
                        rename_count += 1
                    
                except Exception as e:
                    error_msg = f"Error processing {file_path}: {str(e)}"
                    print(error_msg)
                    self.logger.error(error_msg)
                    errors_count += 1
        
        dry_run_prefix = "Dry run - " if dry_run else ""
        summary = (f"{dry_run_prefix}Summary: {rename_count} files {'would be ' if dry_run else ''}renamed, "
                  f"{skipped_count} skipped (destinations exist), {errors_count} errors")
        print(summary)
        self.logger.info(summary)
        
        return rename_count


def main():
    # Set up error handler for uncaught exceptions
    def show_error(exc_type, exc_value, exc_traceback):
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(error_msg)  # Print to console/terminal
        
        # Try to show error dialog if QApplication is still working
        try:
            QMessageBox.critical(None, 'Unhandled Exception', 
                               f"An error occurred: {str(exc_value)}\n\nSee log for details.")
        except:
            pass  # If messagebox fails, at least we printed to console
    
    # Set the exception hook
    sys.excepthook = show_error
    
    # Create and run the application
    app = QApplication(sys.argv)
    window = FileRenamerApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()