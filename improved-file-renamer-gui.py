import os
import sys
import re
import logging
import pandas as pd
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import traceback
import subprocess
import datetime


class RedirectText:
    """Class to redirect stdout to a tkinter Text widget."""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""

    def write(self, string):
        self.buffer += string
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass


class FileRenamerApp:
    """GUI application for renaming files based on Excel data."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("File Renamer Tool")
        self.root.geometry("800x1200")
        self.root.minsize(800, 1000)
        
        # Column names in Excel
        self.master_name_col = tk.StringVar(value="Master Original Name")
        self.proxy_name_col = tk.StringVar(value="Avid Proxy Name")
        self.master_suffix = tk.StringVar(value="_M")
        
        # File and directory paths
        self.excel_path = tk.StringVar()
        self.target_dirs = []
        
        # Setup logger
        self.logger = self.setup_logger()
        
        # Create UI components
        self.create_widgets()
        
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
    
    def create_widgets(self):
        """Create all UI components."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Brief explanation at the top
        explanation_frame = ttk.Frame(main_frame)
        explanation_frame.pack(fill=tk.X, padx=5, pady=5)
        explanation_text = "This tool renames files based on an Excel spreadsheet. It looks for files with names matching the 'Master Original Name' column\nand renames them to the corresponding name in the 'Avid Proxy Name' column, adding the suffix at the end."
        ttk.Label(explanation_frame, text=explanation_text, justify=tk.LEFT).pack(anchor=tk.W)
        
        # Excel file selection section
        excel_frame = ttk.LabelFrame(main_frame, text="Excel File Selection", padding="5")
        excel_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(excel_frame, text="Excel File:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(excel_frame, textvariable=self.excel_path, width=50).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Replace "Open Explorer" with "Browse..." button that uses our new function
        ttk.Button(excel_frame, text="Browse...", command=self.browse_excel_file).grid(row=0, column=2, padx=5, pady=5)
        
        # Directory selection section
        dir_frame = ttk.LabelFrame(main_frame, text="Target Directories", padding="5")
        dir_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        dir_button_frame = ttk.Frame(dir_frame)
        dir_button_frame.pack(fill=tk.X)
        
        # Text entry for new directory
        ttk.Label(dir_button_frame, text="Directory:").pack(side=tk.LEFT, padx=5, pady=5)
        self.dir_entry = ttk.Entry(dir_button_frame, width=40)
        self.dir_entry.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        ttk.Button(dir_button_frame, text="Browse...", command=self.browse_directory).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(dir_button_frame, text="Add Directory", command=self.add_directory).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(dir_button_frame, text="Remove Selected", command=self.remove_directory).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Directory listbox with scrollbar
        self.dir_listbox_frame = ttk.Frame(dir_frame)
        self.dir_listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(self.dir_listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.dir_listbox = tk.Listbox(self.dir_listbox_frame)
        self.dir_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.dir_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.dir_listbox.yview)
        
        # Excel column configuration section
        config_frame = ttk.LabelFrame(main_frame, text="Excel Configuration", padding="5")
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(config_frame, text="Master Original Name Column:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.master_name_col).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Label(config_frame, text="(Column containing original filenames to search for)").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(config_frame, text="Avid Proxy Name Column:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.proxy_name_col).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Label(config_frame, text="(Column containing new filenames to rename to)").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(config_frame, text="Master File Suffix:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.master_suffix).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Label(config_frame, text="(Added to the end of each renamed file)").grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Define a style for the rename button to make it prominent
        style = ttk.Style()
        style.configure("Rename.TButton", font=("Helvetica", 12, "bold"))
        
        # Log button
        log_button = ttk.Button(button_frame, text="View Log File", command=self.open_log_file)
        log_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Rename button - make it very prominent
        rename_button = ttk.Button(button_frame, text="RENAME FILES", command=self.start_renaming, style="Rename.TButton")
        rename_button.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Output console
        console_frame = ttk.LabelFrame(main_frame, text="Console Output", padding="5")
        console_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.console = scrolledtext.ScrolledText(console_frame, state="disabled", wrap=tk.WORD)
        self.console.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Configure grid weights
        config_frame.columnconfigure(1, weight=1)
    
    def browse_excel_file(self):
        """Browse for Excel file and return the path to the text field."""
        try:
            # Instead of using tkinter's filedialog directly, use subprocess to call system commands
            # This approach is more reliable on various platforms
            
            # Create a temporary file to store the selected path
            temp_file = "selected_path.tmp"
            
            if sys.platform == "win32":
                # Windows PowerShell approach
                ps_script = (
                    "$f = New-Object System.Windows.Forms.OpenFileDialog; "
                    "$f.Filter = 'Excel Files (*.xlsx;*.xls)|*.xlsx;*.xls'; "  # Removed 'All Files' option
                    "$f.ShowDialog(); "
                    "if ($f.FileName) { $f.FileName | Out-File -FilePath '" + temp_file + "' }"
                )
                subprocess.run(["powershell", "-Command", ps_script], shell=True)
            
            elif sys.platform == "darwin":
                # macOS approach using osascript (AppleScript)
                script = (
                    'tell application "System Events"\n'
                    '   activate\n'
                    '   set fileTypes to {"xlsx", "xls"}\n'
                    '   set filePath to choose file with prompt "Select Excel File" of type fileTypes\n'
                    '   set filePath to POSIX path of filePath\n'
                    'end tell\n'
                    f'do shell script "echo " & quoted form of filePath & " > {temp_file}"'
                )
                subprocess.run(["osascript", "-e", script])
            
            else:
                # Linux approach using zenity or similar
                try:
                    result = subprocess.run(
                        ["zenity", "--file-selection", "--title=Select Excel File", "--file-filter=Excel files | *.xlsx *.xls"],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0 and result.stdout:
                        with open(temp_file, "w") as f:
                            f.write(result.stdout.strip())
                except FileNotFoundError:
                    # If zenity is not available
                    messagebox.showinfo("Not Available", 
                                       "File browser not available. Please enter the path manually.")
                    return
            
            # Read the selected path from the temporary file
            if os.path.exists(temp_file):
                with open(temp_file, "r") as f:
                    file_path = f.read().strip()
                
                # Remove the temporary file
                try:
                    os.remove(temp_file)
                except:
                    pass
                
                # Update the text field if a path was selected
                if file_path:
                    # Verify the file has an Excel extension
                    if file_path.lower().endswith(('.xlsx', '.xls')):
                        self.excel_path.set(file_path)
                        self.status_var.set(f"Excel file selected: {os.path.basename(file_path)}")
                    else:
                        messagebox.showerror("Invalid File Type", 
                                            "Please select an Excel file (.xlsx or .xls)")
        
        except Exception as e:
            error_msg = f"Error browsing for file: {str(e)}"
            self.logger.error(error_msg)
            messagebox.showerror("Error", f"Could not browse for file: {str(e)}\n\nPlease enter the path manually.")
    
    def browse_directory(self):
        """Browse for directory and return the path to the text field."""
        try:
            # Create a temporary file to store the selected path
            temp_file = "selected_dir.tmp"
            
            if sys.platform == "win32":
                # Windows PowerShell approach
                ps_script = (
                    "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                    "$f.ShowDialog(); "
                    "if ($f.SelectedPath) { $f.SelectedPath | Out-File -FilePath '" + temp_file + "' }"
                )
                subprocess.run(["powershell", "-Command", ps_script], shell=True)
            
            elif sys.platform == "darwin":
                # macOS approach using osascript (AppleScript)
                script = (
                    'tell application "System Events"\n'
                    '   activate\n'
                    '   set folderPath to choose folder with prompt "Select Target Directory"\n'
                    '   set folderPath to POSIX path of folderPath\n'
                    'end tell\n'
                    f'do shell script "echo " & quoted form of folderPath & " > {temp_file}"'
                )
                subprocess.run(["osascript", "-e", script])
            
            else:
                # Linux approach using zenity or similar
                try:
                    result = subprocess.run(
                        ["zenity", "--file-selection", "--directory", "--title=Select Target Directory"],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0 and result.stdout:
                        with open(temp_file, "w") as f:
                            f.write(result.stdout.strip())
                except FileNotFoundError:
                    # If zenity is not available
                    messagebox.showinfo("Not Available", 
                                       "Directory browser not available. Please enter the path manually.")
                    return
            
            # Read the selected path from the temporary file
            if os.path.exists(temp_file):
                with open(temp_file, "r") as f:
                    dir_path = f.read().strip()
                
                # Remove the temporary file
                try:
                    os.remove(temp_file)
                except:
                    pass
                
                # Update the text field if a path was selected
                if dir_path:
                    self.dir_entry.delete(0, tk.END)
                    self.dir_entry.insert(0, dir_path)
                    self.status_var.set(f"Directory selected: {dir_path}")
        
        except Exception as e:
            error_msg = f"Error browsing for directory: {str(e)}"
            self.logger.error(error_msg)
            messagebox.showerror("Error", f"Could not browse for directory: {str(e)}\n\nPlease enter the path manually.")
    
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
                
            self.status_var.set(f"Opened log file: {self.log_file_path}")
        except Exception as e:
            error_msg = f"Error opening log file: {str(e)}"
            self.logger.error(error_msg)
            messagebox.showerror("Error", error_msg)
            
            # Fallback: Show the log file path so the user can find it manually
            messagebox.showinfo("Log File Location", 
                               f"The log file is located at:\n{self.log_file_path}\n\n"
                               f"Please open it manually with a text editor.")
    
    def add_directory(self):
        """Add a directory to the list."""
        dir_path = self.dir_entry.get().strip()
        if not dir_path:
            messagebox.showinfo("Input Required", "Please enter a directory path.")
            return
            
        if dir_path not in self.target_dirs:
            self.target_dirs.append(dir_path)
            self.dir_listbox.insert(tk.END, dir_path)
            self.dir_entry.delete(0, tk.END)  # Clear the entry
            self.status_var.set(f"Added directory: {dir_path}")
        else:
            messagebox.showwarning("Duplicate Directory", "This directory is already in the list.")
    
    def remove_directory(self):
        """Remove selected directory from the list."""
        selected_indices = self.dir_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Selection Required", "Please select a directory to remove.")
            return
            
        for index in reversed(selected_indices):
            self.target_dirs.pop(index)
            self.dir_listbox.delete(index)
            
        self.status_var.set("Directory removed")
    
    def validate_inputs(self):
        """Validate all user inputs before running the renaming process."""
        if not self.excel_path.get():
            messagebox.showerror("Input Error", "Please enter an Excel file path.")
            return False
            
        # Verify the Excel file has the correct extension
        excel_path = self.excel_path.get()
        if not excel_path.lower().endswith(('.xlsx', '.xls')):
            messagebox.showerror("Input Error", "The specified file is not an Excel file (.xlsx or .xls).")
            return False
            
        if not os.path.exists(excel_path):
            messagebox.showerror("Input Error", "The specified Excel file does not exist.")
            return False
            
        if not self.target_dirs:
            messagebox.showerror("Input Error", "Please add at least one target directory.")
            return False
            
        for dir_path in self.target_dirs:
            if not os.path.exists(dir_path):
                messagebox.showerror("Input Error", f"Directory does not exist: {dir_path}")
                return False
                
        if not self.master_name_col.get() or not self.proxy_name_col.get():
            messagebox.showerror("Input Error", "Please provide column names for Master and Proxy names.")
            return False
            
        return True
    
    def start_renaming(self):
        """Start the file renaming process in a separate thread."""
        if not self.validate_inputs():
            return
            
        # Disable UI during processing
        self.disable_ui()
        
        # Redirect stdout to console
        sys.stdout = RedirectText(self.console)
        
        # Start processing in a separate thread
        thread = threading.Thread(target=self.rename_files_process)
        thread.daemon = True
        thread.start()
    
    def disable_ui(self):
        """Disable UI controls during processing."""
        for child in self.root.winfo_children():
            for widget in child.winfo_children():
                if isinstance(widget, (ttk.Button, ttk.Entry)):
                    widget.configure(state="disabled")
                if isinstance(widget, tk.Listbox):
                    widget.configure(state="disabled")
        self.status_var.set("Processing... Please wait.")
    
    def enable_ui(self):
        """Re-enable UI controls after processing."""
        for child in self.root.winfo_children():
            for widget in child.winfo_children():
                if isinstance(widget, (ttk.Button, ttk.Entry)):
                    widget.configure(state="normal")
                if isinstance(widget, tk.Listbox):
                    widget.configure(state="normal")
        self.status_var.set("Ready")
    
    def rename_files_process(self):
        """Main file renaming process."""
        try:
            # Get configuration values
            excel_file = Path(self.excel_path.get())
            target_dirs = [Path(dir_path) for dir_path in self.target_dirs]
            master_col = self.master_name_col.get()
            proxy_col = self.proxy_name_col.get()
            suffix = self.master_suffix.get()
            
            # Clear console
            self.console.configure(state="normal")
            self.console.delete(1.0, tk.END)
            self.console.configure(state="disabled")
            
            print(f"Starting file renaming process:")
            print(f"Excel file: {excel_file}")
            print(f"Target directories: {', '.join(str(d) for d in target_dirs)}")
            print(f"Master column: {master_col}")
            print(f"Proxy column: {proxy_col}")
            print(f"Suffix: {suffix}")
            print("-" * 50)
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file)
                print(f"Successfully read Excel file with {len(df)} rows")
            except Exception as e:
                print(f"Error reading Excel file: {str(e)}")
                self.logger.error(f"Error reading Excel file: {str(e)}")
                messagebox.showerror("Excel Error", f"Error reading Excel file: {str(e)}")
                self.root.after(0, self.enable_ui)
                return
                
            # Verify required columns exist
            if master_col not in df.columns or proxy_col not in df.columns:
                error_msg = f"Required columns not found. Need '{master_col}' and '{proxy_col}'"
                print(error_msg)
                self.logger.error(error_msg)
                messagebox.showerror("Column Error", error_msg)
                self.root.after(0, self.enable_ui)
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
                messagebox.showerror("Validation Error", error_msg)
                self.root.after(0, self.enable_ui)
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
                messagebox.showerror("Duplicate Error", error_msg)
                self.root.after(0, self.enable_ui)
                return
            
            # Collect files to process from all target directories
            files_to_rename = []
            for target_dir in target_dirs:
                print(f"Collecting files from: {target_dir}")
                dir_files = self.collect_files_recursively(target_dir)
                files_to_rename.extend(dir_files)
                print(f"Found {len(dir_files)} files in {target_dir}")
            
            print(f"Total files collected from all directories: {len(files_to_rename)}")
            
            # Perform renaming
            renamed = self.rename_files_efficiently(
                files_to_rename, 
                master_file_names, 
                proxy_names, 
                suffix
            )
            
            # Show completion message
            completion_msg = f"Successfully renamed {renamed} files out of {len(files_to_rename)} files processed."
            print(completion_msg)
            print("See 'renames.log' for complete details.")
            self.logger.info(completion_msg)
            messagebox.showinfo("Process Complete", completion_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.logger.exception(error_msg)
            messagebox.showerror("Error", error_msg)
            
        finally:
            # Restore stdout
            sys.stdout = self.stdout_backup
            
            # Re-enable UI on the main thread
            self.root.after(0, self.enable_ui)
    
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
    
    def collect_files_recursively(self, directory):
        """Recursively collect all non-hidden files from directory and subdirectories."""
        files_list = []
        
        if not directory.is_dir():
            error_msg = f"Target is not a directory: {directory}"
            print(error_msg)
            self.logger.error(error_msg)
            return files_list
            
        print(f"Target is directory: {directory}. Collecting files...")
        
        try:
            for path in directory.rglob('*'):
                if path.is_file() and not path.name.startswith('.'):
                    files_list.append(path)
        except Exception as e:
            error_msg = f"Error collecting files from {directory}: {str(e)}"
            print(error_msg)
            self.logger.error(error_msg)
        
        return files_list
    
    def rename_files_efficiently(self, target_files, master_names, proxy_names, suffix):
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
                        print(f"Skipping {file_path} - destination already exists: {new_path}")
                        self.logger.warning(f"Skipping rename - destination exists: {new_path}")
                        skipped_count += 1
                        continue
                        
                    # Perform rename
                    file_path.rename(new_path)
                    print(f"Renamed: {file_path.name} -> {new_path.name}")
                    self.logger.info(f"Renamed: {file_path} -> {new_path}")
                    rename_count += 1
                    
                except Exception as e:
                    error_msg = f"Error renaming {file_path}: {str(e)}"
                    print(error_msg)
                    self.logger.error(error_msg)
                    errors_count += 1
        
        summary = (f"Summary: {rename_count} files renamed, {skipped_count} skipped "
                  f"(destinations exist), {errors_count} errors")
        print(summary)
        self.logger.info(summary)
        
        return rename_count


def main():
    # Set up error handler for uncaught exceptions
    def show_error(exc_type, exc_value, exc_traceback):
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(error_msg)  # Print to console/terminal
        
        # Try to show error dialog if tkinter is still working
        try:
            messagebox.showerror('Unhandled Exception', 
                                 f"An error occurred: {str(exc_value)}\n\nSee log for details.")
        except:
            pass  # If messagebox fails, at least we printed to console
    
    # Set the exception hook
    sys.excepthook = show_error
    
    # Create and run the application
    root = tk.Tk()
    app = FileRenamerApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
