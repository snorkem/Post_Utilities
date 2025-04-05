#!/usr/bin/env python3
"""
Lower Thirds Generator GUI
A graphical interface for the Lower Thirds Generator script.
"""

import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QLineEdit, QFileDialog, QSpinBox, 
                            QDoubleSpinBox, QCheckBox, QComboBox, QGroupBox, 
                            QTabWidget, QScrollArea, QMessageBox, QProgressBar,
                            QGridLayout, QFormLayout, QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPixmap, QFont, QPalette

class ColorButton(QPushButton):
    """A button that shows its color and opens a color dialog when clicked."""
    def __init__(self, color_str=None, parent=None):
        super().__init__(parent)
        self.setMinimumSize(24, 24)
        self.setMaximumSize(100, 24)
        self.color_str = color_str or "black"
        self.setText(self.color_str)
        self.setStyleSheet(f"background-color: {self.color_str}; color: {'white' if self.color_str.lower() in ['black', 'navy', 'darkblue', 'blue'] else 'black'};")
        
    def update_color(self, color_str):
        self.color_str = color_str
        self.setText(self.color_str)
        self.setStyleSheet(f"background-color: {self.color_str}; color: {'white' if self.color_str.lower() in ['black', 'navy', 'darkblue', 'blue'] else 'black'};")


class GeneratorThread(QThread):
    """Thread for running the generation process without freezing the UI."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    log = pyqtSignal(str)
    
    def __init__(self, command):
        super().__init__()
        self.command = command
        
    def run(self):
        try:
            self.log.emit(f"Running command: {' '.join(self.command)}")
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Process output line by line
            for line in iter(process.stdout.readline, ''):
                self.log.emit(line.strip())
                
                # Update progress if we detect generation messages
                if "Generated:" in line:
                    self.progress.emit(1)
            
            process.stdout.close()
            return_code = process.wait()
            
            if return_code == 0:
                self.finished.emit(True, "Generation completed successfully")
            else:
                self.finished.emit(False, f"Process exited with code {return_code}")
        except Exception as e:
            self.log.emit(f"Error: {str(e)}")
            self.finished.emit(False, str(e))


class LowerThirdsGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        # Main window setup
        self.setWindowTitle("Lower Thirds Generator")
        self.setMinimumSize(800, 600)
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create tabs for better organization
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # First tab: Basic Settings
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QFormLayout()
        file_group.setLayout(file_layout)
        
        # Input file selection
        input_layout = QHBoxLayout()
        self.input_file = QLineEdit()
        input_browse = QPushButton("Browse...")
        input_browse.clicked.connect(self.browse_input)
        input_layout.addWidget(self.input_file)
        input_layout.addWidget(input_browse)
        file_layout.addRow("Input CSV/Excel:", input_layout)
        
        # Output directory selection
        output_layout = QHBoxLayout()
        self.output_dir = QLineEdit()
        output_browse = QPushButton("Browse...")
        output_browse.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_dir)
        output_layout.addWidget(output_browse)
        file_layout.addRow("Output Directory:", output_layout)
        
        basic_layout.addWidget(file_group)
        
        # Dimensions group
        dim_group = QGroupBox("Dimensions")
        dim_layout = QHBoxLayout()
        dim_group.setLayout(dim_layout)
        
        width_layout = QHBoxLayout()
        self.width = QSpinBox()
        self.width.setRange(320, 7680)
        self.width.setValue(1920)
        width_layout.addWidget(QLabel("Width:"))
        width_layout.addWidget(self.width)
        
        height_layout = QHBoxLayout()
        self.height = QSpinBox()
        self.height.setRange(240, 4320)
        self.height.setValue(1080)
        height_layout.addWidget(QLabel("Height:"))
        height_layout.addWidget(self.height)
        
        dim_layout.addLayout(width_layout)
        dim_layout.addLayout(height_layout)
        
        basic_layout.addWidget(dim_group)
        
        # Color settings group
        color_group = QGroupBox("Colors")
        color_layout = QFormLayout()
        color_group.setLayout(color_layout)
        
        self.bg_color = QLineEdit("black")
        self.bg_color_button = ColorButton("black")
        self.bg_color_button.clicked.connect(lambda: self.open_color_picker(self.bg_color, self.bg_color_button))
        bg_color_layout = QHBoxLayout()
        bg_color_layout.addWidget(self.bg_color)
        bg_color_layout.addWidget(self.bg_color_button)
        color_layout.addRow("Background Color:", bg_color_layout)
        
        self.text_color = QLineEdit("white")
        self.text_color_button = ColorButton("white")
        self.text_color_button.clicked.connect(lambda: self.open_color_picker(self.text_color, self.text_color_button))
        text_color_layout = QHBoxLayout()
        text_color_layout.addWidget(self.text_color)
        text_color_layout.addWidget(self.text_color_button)
        color_layout.addRow("Main Text Color:", text_color_layout)
        
        self.secondary_text_color = QLineEdit("")
        self.secondary_text_color_button = ColorButton("white")
        self.secondary_text_color_button.clicked.connect(lambda: self.open_color_picker(self.secondary_text_color, self.secondary_text_color_button))
        secondary_color_layout = QHBoxLayout()
        secondary_color_layout.addWidget(self.secondary_text_color)
        secondary_color_layout.addWidget(self.secondary_text_color_button)
        color_layout.addRow("Secondary Text Color:", secondary_color_layout)
        
        self.bar_color = QLineEdit("black,0")
        self.bar_color_button = ColorButton("black")
        self.bar_color_button.clicked.connect(lambda: self.open_color_picker(self.bar_color, self.bar_color_button, with_alpha=True))
        bar_color_layout = QHBoxLayout()
        bar_color_layout.addWidget(self.bar_color)
        bar_color_layout.addWidget(self.bar_color_button)
        color_layout.addRow("Bar Color:", bar_color_layout)
        
        basic_layout.addWidget(color_group)
        
        # Format group
        format_group = QGroupBox("Output Format")
        format_layout = QFormLayout()
        format_group.setLayout(format_layout)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["png", "jpg", "tiff"])
        format_layout.addRow("Format:", self.format_combo)
        
        self.bit_depth = QComboBox()
        self.bit_depth.addItems(["8", "16"])
        self.bit_depth.setCurrentIndex(1)  # Default to 16-bit
        format_layout.addRow("TIFF Bit Depth:", self.bit_depth)
        
        self.transparent = QCheckBox("Use transparent background")
        format_layout.addRow("", self.transparent)
        
        basic_layout.addWidget(format_group)
        
        # Second tab: Advanced Settings
        advanced_tab = QWidget()
        
        # Make advanced tab scrollable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(advanced_tab)
        
        advanced_layout = QVBoxLayout(advanced_tab)
        
        # Text Effects group
        text_effects_group = QGroupBox("Text Effects")
        text_effects_layout = QFormLayout()
        text_effects_group.setLayout(text_effects_layout)
        
        # Text shadow
        self.text_shadow = QCheckBox("Enable text shadow")
        text_effects_layout.addRow("", self.text_shadow)
        
        self.shadow_offset = QLineEdit("2,2")
        text_effects_layout.addRow("Shadow Offset (X,Y):", self.shadow_offset)
        
        self.shadow_blur = QSpinBox()
        self.shadow_blur.setRange(1, 100)
        self.shadow_blur.setValue(20)
        text_effects_layout.addRow("Shadow Blur (1-100):", self.shadow_blur)
        
        self.shadow_color = QLineEdit("black")
        self.shadow_color_button = ColorButton("black")
        self.shadow_color_button.clicked.connect(lambda: self.open_color_picker(self.shadow_color, self.shadow_color_button))
        shadow_color_layout = QHBoxLayout()
        shadow_color_layout.addWidget(self.shadow_color)
        shadow_color_layout.addWidget(self.shadow_color_button)
        text_effects_layout.addRow("Shadow Color:", shadow_color_layout)
        
        self.shadow_opacity = QSpinBox()
        self.shadow_opacity.setRange(0, 255)
        self.shadow_opacity.setValue(128)
        text_effects_layout.addRow("Shadow Opacity (0-255):", self.shadow_opacity)
        
        # Text outline
        self.text_outline = QLineEdit("")
        text_effects_layout.addRow("Text Outline (W,Color[,A]):", self.text_outline)
        
        # Letter spacing
        self.letter_spacing = QSpinBox()
        self.letter_spacing.setRange(0, 100)
        self.letter_spacing.setValue(0)
        text_effects_layout.addRow("Letter Spacing (px):", self.letter_spacing)
        
        # Vertical spacing
        self.vertical_spacing = QSpinBox()
        self.vertical_spacing.setRange(0, 100)
        self.vertical_spacing.setValue(0)
        text_effects_layout.addRow("Vertical Spacing (px):", self.vertical_spacing)
        
        # Text transform
        self.text_transform = QComboBox()
        self.text_transform.addItems(["none", "upper", "lower", "title"])
        text_effects_layout.addRow("Text Transform:", self.text_transform)
        
        advanced_layout.addWidget(text_effects_group)
        
        # Bar settings group
        bar_group = QGroupBox("Bar Settings")
        bar_layout = QFormLayout()
        bar_group.setLayout(bar_layout)
        
        self.bar_height = QSpinBox()
        self.bar_height.setRange(0, 1080)
        self.bar_height.setValue(0)
        self.bar_height.setSpecialValueText("Auto")
        bar_layout.addRow("Bar Height (px):", self.bar_height)
        
        self.bar_opacity = QSpinBox()
        self.bar_opacity.setRange(0, 255)
        self.bar_opacity.setValue(0)
        bar_layout.addRow("Bar Opacity (0-255):", self.bar_opacity)
        
        advanced_layout.addWidget(bar_group)
        
        # Misc settings group
        misc_group = QGroupBox("Miscellaneous")
        misc_layout = QFormLayout()
        misc_group.setLayout(misc_layout)
        
        self.skip_existing = QCheckBox("Skip existing files")
        misc_layout.addRow("", self.skip_existing)
        
        self.debug = QCheckBox("Show debug information")
        misc_layout.addRow("", self.debug)
        
        advanced_layout.addWidget(misc_group)
        
        # Add tabs
        tabs.addTab(basic_tab, "Basic Settings")
        tabs.addTab(scroll, "Advanced Settings")
        
        # Third tab: Log
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        
        self.log_text = QTextEdit()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        tabs.addTab(log_tab, "Log")
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Test (Preview First)")
        self.test_button.clicked.connect(self.run_test)
        button_layout.addWidget(self.test_button)
        
        self.generate_button = QPushButton("Generate Lower Thirds")
        self.generate_button.clicked.connect(self.run_generation)
        self.generate_button.setStyleSheet("font-weight: bold;")
        button_layout.addWidget(self.generate_button)
        
        main_layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        self.show()
    
    def browse_input(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Input File", "", 
            "Excel/CSV Files (*.xlsx *.xls *.csv);;All Files (*)", 
            options=options
        )
        if file_name:
            self.input_file.setText(file_name)
    
    def browse_output(self):
        options = QFileDialog.Options()
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", "", options=options
        )
        if directory:
            self.output_dir.setText(directory)
    
    def open_color_picker(self, line_edit, color_button, with_alpha=False):
        from PyQt5.QtWidgets import QColorDialog
        
        # Parse current color
        current_color = line_edit.text().strip()
        qcolor = QColor()
        
        # Handle alpha separately if needed
        alpha = 255
        if with_alpha and "," in current_color:
            parts = current_color.split(",")
            color_part = ",".join(parts[:-1])
            try:
                alpha = int(parts[-1])
            except:
                alpha = 255
            qcolor.setNamedColor(color_part)
        else:
            qcolor.setNamedColor(current_color)
        
        qcolor.setAlpha(alpha)
        
        # Open color dialog
        color = QColorDialog.getColor(qcolor, self, "Select Color", QColorDialog.ShowAlphaChannel if with_alpha else QColorDialog.ColorDialogOptions())
        
        if color.isValid():
            # Format the color string
            if with_alpha:
                color_str = f"{color.name()},{color.alpha()}"
            else:
                color_str = color.name()
            
            line_edit.setText(color_str)
            color_button.update_color(color.name())
    
    def get_command_args(self, test_mode=False):
        """Build the command arguments from UI settings."""
        if not self.input_file.text() or not self.output_dir.text():
            return None
            
        args = ["python3", "l3rds_from_excel.py"]
        args.append(self.input_file.text())
        args.append(self.output_dir.text())
        
        # Basic settings
        args.append(f"--width={self.width.value()}")
        args.append(f"--height={self.height.value()}")
        
        if self.bg_color.text():
            args.append(f"--bg-color={self.bg_color.text()}")
            
        if self.text_color.text():
            args.append(f"--text-color={self.text_color.text()}")
            
        if self.secondary_text_color.text():
            args.append(f"--secondary-text-color={self.secondary_text_color.text()}")
            
        if self.bar_color.text():
            args.append(f"--bar-color={self.bar_color.text()}")
            
        args.append(f"--format={self.format_combo.currentText()}")
        args.append(f"--bit-depth={self.bit_depth.currentText()}")
        
        if self.transparent.isChecked():
            args.append("--transparent")
            
        # Advanced settings
        if self.text_shadow.isChecked():
            args.append("--text-shadow")
            
        if self.shadow_offset.text():
            args.append(f"--shadow-offset={self.shadow_offset.text()}")
            
        args.append(f"--shadow-blur={self.shadow_blur.value()}")
        
        if self.shadow_color.text():
            args.append(f"--shadow-color={self.shadow_color.text()}")
            
        args.append(f"--shadow-opacity={self.shadow_opacity.value()}")
        
        if self.text_outline.text():
            args.append(f"--text-outline={self.text_outline.text()}")
            
        if self.letter_spacing.value() > 0:
            args.append(f"--letter-spacing={self.letter_spacing.value()}")
            
        if self.vertical_spacing.value() > 0:
            args.append(f"--vertical-spacing={self.vertical_spacing.value()}")
            
        if self.text_transform.currentText() != "none":
            args.append(f"--text-transform={self.text_transform.currentText()}")
            
        if self.bar_height.value() > 0:
            args.append(f"--bar-height={self.bar_height.value()}")
            
        if self.bar_opacity.value() > 0:
            args.append(f"--bar-opacity={self.bar_opacity.value()}")
            
        if self.skip_existing.isChecked():
            args.append("--skip-existing")
            
        if self.debug.isChecked():
            args.append("--debug")
            
        if test_mode:
            args.append("--test")
            
        return args
    
    def run_test(self):
        """Run a test preview."""
        args = self.get_command_args(test_mode=True)
        if not args:
            QMessageBox.warning(self, "Input Error", "Please select input file and output directory")
            return
            
        self.statusBar().showMessage("Running test preview...")
        self.log_text.clear()
        
        # Create thread
        self.generator_thread = GeneratorThread(args)
        self.generator_thread.log.connect(self.append_log)
        self.generator_thread.finished.connect(self.on_generation_finished)
        
        # Disable buttons while running
        self.test_button.setEnabled(False)
        self.generate_button.setEnabled(False)
        
        # Start thread
        self.generator_thread.start()
    
    def run_generation(self):
        """Run full generation."""
        args = self.get_command_args()
        if not args:
            QMessageBox.warning(self, "Input Error", "Please select input file and output directory")
            return
            
        # Count number of rows in the file to set up progress bar
        try:
            import pandas as pd
            if self.input_file.text().endswith('.csv'):
                df = pd.read_csv(self.input_file.text())
            else:
                df = pd.read_excel(self.input_file.text())
                
            total_rows = len(df)
            self.progress_bar.setMaximum(total_rows)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
        except Exception as e:
            self.append_log(f"Error reading file for progress: {str(e)}")
            self.progress_bar.setVisible(False)
        
        self.statusBar().showMessage("Generating lower thirds...")
        self.log_text.clear()
        
        # Create thread
        self.generator_thread = GeneratorThread(args)
        self.generator_thread.log.connect(self.append_log)
        self.generator_thread.progress.connect(self.update_progress)
        self.generator_thread.finished.connect(self.on_generation_finished)
        
        # Disable buttons while running
        self.test_button.setEnabled(False)
        self.generate_button.setEnabled(False)
        
        # Start thread
        self.generator_thread.start()
    
    def append_log(self, text):
        """Add text to the log tab."""
        self.log_text.append(text)
        # Auto-scroll to the bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_progress(self, increment):
        """Update the progress bar."""
        current = self.progress_bar.value()
        self.progress_bar.setValue(current + increment)
    
    def on_generation_finished(self, success, message):
        """Handle generation completion."""
        # Re-enable buttons
        self.test_button.setEnabled(True)
        self.generate_button.setEnabled(True)
        
        if success:
            self.statusBar().showMessage(message)
            if not self.progress_bar.isHidden():
                QMessageBox.information(self, "Success", f"Successfully generated {self.progress_bar.value()} lower thirds.")
                self.progress_bar.setVisible(False)
        else:
            self.statusBar().showMessage(f"Error: {message}")
            QMessageBox.warning(self, "Error", f"Generation failed: {message}")
            self.progress_bar.setVisible(False)


from PyQt5.QtWidgets import QTextEdit  # For log display

if __name__ == "__main__":
    # Check if we have the required dependencies
    try:
        import pandas as pd
        from PIL import Image
    except ImportError as e:
        print(f"Error: Missing required dependency: {e}")
        print("Please install required packages: pip install pandas pillow")
        sys.exit(1)
        
    app = QApplication(sys.argv)
    window = LowerThirdsGUI()
    sys.exit(app.exec_())
