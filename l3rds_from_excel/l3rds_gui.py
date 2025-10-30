#!/usr/bin/env python3
"""
Lower Thirds Generator GUI - Refactored Edition

A graphical interface for the Lower Thirds Generator script.
Now uses the refactored architecture directly instead of subprocess calls.
"""

import sys
import logging

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QSpinBox,
    QCheckBox, QComboBox, QGroupBox, QTabWidget, QMessageBox,
    QProgressBar, QFormLayout, QTextEdit, QRadioButton, QColorDialog,
)
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from PyQt5.QtGui import QColor

from l3rds.config.models import DefaultConfig, TextConfig, ShadowConfig, OutlineConfig, BarConfig, OutputConfig
from l3rds.data.loader import ExcelLoader
from l3rds.data.extractor import ExcelRowExtractor
from l3rds.rendering.generator import LowerThirdGenerator
from l3rds.io.image_saver import ImageSaver
from l3rds.io.preview import PreviewManager
from l3rds.io.template_generator import TemplateGenerator
from l3rds.utils.logger import setup_logging, get_logger
from l3rds.utils.exceptions import L3rdsException


class QTextEditLogger(logging.Handler, QObject):
    """Custom logging handler that emits log records to a Qt signal.

    This handler captures Python logging output and sends it to the GUI's
    log tab via Qt signals, enabling thread-safe logging display.
    """

    # Signal emits (message, level_name) tuples
    log_signal = pyqtSignal(str, str)

    # Color scheme for different log levels
    LEVEL_COLORS = {
        'DEBUG': '#808080',      # Gray
        'INFO': '#000000',       # Black
        'WARNING': '#FF8C00',    # Orange
        'ERROR': '#DC143C',      # Crimson
        'CRITICAL': '#8B0000',   # Dark Red
    }

    def __init__(self):
        """Initialize the handler."""
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record via Qt signal.

        Args:
            record: The log record to emit
        """
        try:
            # Format the message
            msg = self.format(record)
            # Emit signal with message and level name
            self.log_signal.emit(msg, record.levelname)
        except Exception:
            self.handleError(record)


class GeneratorWorker(QThread):
    """Worker thread for running generation without blocking UI."""

    progress = pyqtSignal(int, str)  # (increment, message)
    finished = pyqtSignal(bool, str)  # (success, message)
    error = pyqtSignal(str)  # error message

    def __init__(self, config: DefaultConfig, input_file: str, output_dir: str, test_mode: bool = False):
        super().__init__()
        self.config = config
        self.input_file = input_file
        self.output_dir = output_dir
        self.test_mode = test_mode

    def run(self):
        """Run the generation process."""
        try:
            # Set up logging with all config options
            setup_logging(
                level=self.config.log_level,
                log_file=self.config.log_file,
                console=False,
                verbose=(self.config.log_level == "DEBUG")
            )

            # Get logger for this worker
            from l3rds.utils.logger import get_logger
            logger = get_logger(__name__)

            # Log configuration being used
            logger.info("=" * 60)
            logger.info("CONFIGURATION FROM GUI:")
            logger.info("=" * 60)
            logger.info(f"Image Size: {self.config.width}x{self.config.height}")
            logger.info(f"Background Color: {self.config.bg_color}")
            logger.info(f"Default Position: {self.config.default_justification}")
            logger.info(f"Text Color: {self.config.text.text_color}")
            logger.info(f"Secondary Text Color: {self.config.text.secondary_text_color}")
            logger.info(f"Letter Spacing: {self.config.text.letter_spacing}")
            logger.info(f"Vertical Spacing: {self.config.text.vertical_spacing}")
            logger.info(f"Text Transform: {self.config.text.text_transform}")
            logger.info(f"Shadow Enabled: {self.config.text.shadow.enabled}")
            logger.info(f"Shadow Color: {self.config.text.shadow.color}")
            logger.info(f"Shadow Opacity: {self.config.text.shadow.opacity}")
            logger.info(f"Shadow Offset: ({self.config.text.shadow.offset_x}, {self.config.text.shadow.offset_y})")
            logger.info(f"Shadow Blur: {self.config.text.shadow.blur}")
            logger.info(f"Outline: {self.config.text.outline}")
            logger.info(f"Bar Color: {self.config.bar.color}")
            logger.info(f"Bar Height: {self.config.bar.height}")
            logger.info(f"Bar Opacity: {self.config.bar.opacity}")
            logger.info("=" * 60)

            # Load data
            loader = ExcelLoader()
            data = loader.load(self.input_file)

            if self.test_mode:
                # Test mode - preview first only
                extractor = ExcelRowExtractor(debug=self.config.debug, default_justification=self.config.default_justification)
                generator = LowerThirdGenerator(self.config)

                row_data = extractor.extract_row(data.iloc[0], row_index=0)
                image = generator.generate_preview(row_data)

                # Show preview (on main thread, so just signal)
                self.progress.emit(1, "Preview generated")
                PreviewManager.show(image, wait_for_user=False)
                self.finished.emit(True, "Preview complete")
                return

            # Normal mode - generate all
            extractor = ExcelRowExtractor(debug=self.config.debug, default_justification=self.config.default_justification)
            generator = LowerThirdGenerator(self.config)
            saver = ImageSaver(self.config.output)

            count_success = 0
            count_failed = 0

            for index, row in data.iterrows():
                try:
                    row_data = extractor.extract_row(row, row_index=index)
                    image = generator.generate_from_row(row_data)

                    filename = row_data.get_output_filename()
                    output_path = saver.save(image, self.output_dir, filename)

                    self.progress.emit(1, f"Generated: {output_path.name}")
                    count_success += 1

                except Exception as e:
                    self.error.emit(f"Row {index + 1}: {str(e)}")
                    count_failed += 1

            message = f"Generated {count_success} images"
            if count_failed > 0:
                message += f" ({count_failed} failed)"

            self.finished.emit(count_failed == 0, message)

        except Exception as e:
            self.error.emit(f"Critical error: {str(e)}")
            self.finished.emit(False, str(e))


class LowerThirdsGUI(QMainWindow):
    """Main GUI window for Lower Thirds Generator."""

    def __init__(self):
        super().__init__()

        # Set up GUI logging handler
        self.log_handler = QTextEditLogger()
        self.log_handler.log_signal.connect(self.append_colored_log)

        # Configure handler with a format that includes timestamp
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.log_handler.setFormatter(formatter)

        # Add handler to root logger to capture all logging output
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)

        # Set initial log level (will be updated when generation starts)
        self.log_handler.setLevel(logging.INFO)

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Lower Thirds Generator v2.0")
        self.setMinimumSize(800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create tabs
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Basic Settings Tab
        basic_tab = self._create_basic_tab()
        tabs.addTab(basic_tab, "Basic Settings")

        # Advanced Settings Tab
        advanced_tab = self._create_advanced_tab()
        tabs.addTab(advanced_tab, "Advanced Settings")

        # Logging Tab
        logging_tab = self._create_logging_tab()
        tabs.addTab(logging_tab, "Logging")

        # Log Tab
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)

        # Log display area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setAcceptRichText(True)  # Enable HTML formatting for color-coding
        log_layout.addWidget(self.log_text)

        # Button layout for Clear and Copy
        log_button_layout = QHBoxLayout()
        log_button_layout.addStretch()  # Push buttons to the right

        clear_log_button = QPushButton("Clear Log")
        clear_log_button.clicked.connect(self.log_text.clear)
        log_button_layout.addWidget(clear_log_button)

        copy_log_button = QPushButton("Copy to Clipboard")
        copy_log_button.clicked.connect(self.copy_log_to_clipboard)
        log_button_layout.addWidget(copy_log_button)

        log_layout.addLayout(log_button_layout)
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

        self.statusBar().showMessage("Ready")
        self.show()

    def _create_basic_tab(self) -> QWidget:
        """Create the basic settings tab."""
        basic_tab = QWidget()
        basic_layout = QHBoxLayout(basic_tab)

        # Left column
        left_column = QVBoxLayout()

        # File selection
        file_group = QGroupBox("File Selection")
        file_layout = QFormLayout(file_group)

        input_layout = QHBoxLayout()
        self.input_file = QLineEdit()
        input_browse = QPushButton("Browse...")
        input_browse.clicked.connect(self.browse_input)
        input_layout.addWidget(self.input_file)
        input_layout.addWidget(input_browse)
        file_layout.addRow("Input CSV/Excel:", input_layout)

        output_layout = QHBoxLayout()
        self.output_dir = QLineEdit()
        output_browse = QPushButton("Browse...")
        output_browse.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_dir)
        output_layout.addWidget(output_browse)
        file_layout.addRow("Output Directory:", output_layout)

        # Template generation button
        template_layout = QHBoxLayout()
        template_button = QPushButton("Generate Excel Template")
        template_button.setToolTip("Create a formatted Excel template with examples and instructions")
        template_button.clicked.connect(self.generate_excel_template)
        template_layout.addWidget(template_button)
        template_layout.addStretch()  # Push button to left
        file_layout.addRow("", template_layout)

        left_column.addWidget(file_group)

        # Dimensions
        dim_group = QGroupBox("Dimensions")
        dim_layout = QHBoxLayout(dim_group)

        self.width = QSpinBox()
        self.width.setRange(320, 7680)
        self.width.setValue(1920)
        dim_layout.addWidget(QLabel("Width:"))
        dim_layout.addWidget(self.width)

        self.height = QSpinBox()
        self.height.setRange(240, 4320)
        self.height.setValue(1080)
        dim_layout.addWidget(QLabel("Height:"))
        dim_layout.addWidget(self.height)

        left_column.addWidget(dim_group)

        # Font Settings
        font_group = QGroupBox("Font Settings")
        font_layout = QFormLayout(font_group)

        # Main font
        main_font_layout = QHBoxLayout()
        self.main_font = QLineEdit("Arial")
        self.main_font.setPlaceholderText("Font name or path to .ttf/.otf file")
        main_font_browse = QPushButton("Browse...")
        main_font_browse.clicked.connect(self.browse_main_font)
        main_font_layout.addWidget(self.main_font)
        main_font_layout.addWidget(main_font_browse)
        font_layout.addRow("Main Font:", main_font_layout)

        # Main font size
        main_font_size_layout = QHBoxLayout()
        self.main_font_size = QSpinBox()
        self.main_font_size.setRange(0, 500)
        self.main_font_size.setValue(0)
        self.main_font_size.setSpecialValueText("Auto")
        self.main_font_size.setSuffix(" pt")
        self.main_font_size.setToolTip("0 = Auto-calculate based on canvas height (height/18)")
        main_font_size_layout.addWidget(self.main_font_size)
        main_font_size_layout.addStretch()
        font_layout.addRow("Main Font Size:", main_font_size_layout)

        # Secondary font
        secondary_font_layout = QHBoxLayout()
        self.secondary_font = QLineEdit("")
        self.secondary_font.setPlaceholderText("Leave blank to use main font")
        secondary_font_browse = QPushButton("Browse...")
        secondary_font_browse.clicked.connect(self.browse_secondary_font)
        secondary_font_layout.addWidget(self.secondary_font)
        secondary_font_layout.addWidget(secondary_font_browse)
        font_layout.addRow("Secondary Font:", secondary_font_layout)

        # Secondary font size
        secondary_font_size_layout = QHBoxLayout()
        self.secondary_font_size = QSpinBox()
        self.secondary_font_size.setRange(0, 500)
        self.secondary_font_size.setValue(0)
        self.secondary_font_size.setSpecialValueText("Auto")
        self.secondary_font_size.setSuffix(" pt")
        self.secondary_font_size.setToolTip("0 = Auto-calculate based on canvas height (height/25)")
        secondary_font_size_layout.addWidget(self.secondary_font_size)
        secondary_font_size_layout.addStretch()
        font_layout.addRow("Secondary Font Size:", secondary_font_size_layout)

        help_label_font = QLabel("Note: Excel 'Main Font' and 'Secondary Font' columns are optional and override these settings when specified")
        help_label_font.setStyleSheet("font-size: 9pt; color: gray;")
        font_layout.addRow("", help_label_font)

        left_column.addWidget(font_group)
        left_column.addStretch()

        # Right column
        right_column = QVBoxLayout()

        # Text Position
        position_group = QGroupBox("Text Position")
        position_layout = QFormLayout(position_group)

        self.text_position = QComboBox()
        self.text_position.addItems([
            "lower left",
            "lower center",
            "lower right",
            "upper left",
            "upper center",
            "upper right",
            "center center",
        ])
        self.text_position.setCurrentText("lower left")  # Default to traditional lower third
        position_layout.addRow("Default Position:", self.text_position)

        help_label = QLabel("Note: Excel 'Justification' column overrides this setting")
        help_label.setStyleSheet("font-size: 9pt; color: gray;")
        position_layout.addRow("", help_label)

        # Position offsets
        offset_layout = QHBoxLayout()

        offset_x_label = QLabel("X Offset:")
        self.position_offset_x = QSpinBox()
        self.position_offset_x.setRange(-500, 500)
        self.position_offset_x.setValue(0)
        self.position_offset_x.setSuffix(" px")
        offset_layout.addWidget(offset_x_label)
        offset_layout.addWidget(self.position_offset_x)

        offset_y_label = QLabel("Y Offset:")
        self.position_offset_y = QSpinBox()
        self.position_offset_y.setRange(-500, 500)
        self.position_offset_y.setValue(0)
        self.position_offset_y.setSuffix(" px")
        offset_layout.addWidget(offset_y_label)
        offset_layout.addWidget(self.position_offset_y)

        offset_layout.addStretch()
        position_layout.addRow("Fine-tune Position:", offset_layout)

        help_label2 = QLabel("Positive X moves right, positive Y moves down")
        help_label2.setStyleSheet("font-size: 9pt; color: gray;")
        position_layout.addRow("", help_label2)

        right_column.addWidget(position_group)

        # Colors
        color_group = QGroupBox("Colors")
        color_layout = QFormLayout(color_group)

        # Background color
        bg_color_layout = QHBoxLayout()
        self.bg_color = QLineEdit("black")
        bg_color_btn = QPushButton("Pick Color")
        bg_color_btn.clicked.connect(lambda: self.pick_color(self.bg_color))
        bg_color_layout.addWidget(self.bg_color)
        bg_color_layout.addWidget(bg_color_btn)
        color_layout.addRow("Background:", bg_color_layout)

        # Main text color
        text_color_layout = QHBoxLayout()
        self.text_color = QLineEdit("white")
        text_color_btn = QPushButton("Pick Color")
        text_color_btn.clicked.connect(lambda: self.pick_color(self.text_color))
        text_color_layout.addWidget(self.text_color)
        text_color_layout.addWidget(text_color_btn)
        color_layout.addRow("Main Text:", text_color_layout)

        # Secondary text color
        secondary_text_color_layout = QHBoxLayout()
        self.secondary_text_color = QLineEdit("")
        secondary_text_color_btn = QPushButton("Pick Color")
        secondary_text_color_btn.clicked.connect(lambda: self.pick_color(self.secondary_text_color))
        secondary_text_color_layout.addWidget(self.secondary_text_color)
        secondary_text_color_layout.addWidget(secondary_text_color_btn)
        color_layout.addRow("Secondary Text:", secondary_text_color_layout)

        # Bar color
        bar_color_layout = QHBoxLayout()
        self.bar_color = QLineEdit("black")
        bar_color_btn = QPushButton("Pick Color")
        bar_color_btn.clicked.connect(lambda: self.pick_color(self.bar_color))
        bar_color_layout.addWidget(self.bar_color)
        bar_color_layout.addWidget(bar_color_btn)
        color_layout.addRow("Bar Color:", bar_color_layout)

        # Bar opacity
        bar_opacity_layout = QHBoxLayout()
        self.bar_opacity_basic = QSpinBox()
        self.bar_opacity_basic.setRange(0, 255)
        self.bar_opacity_basic.setValue(0)
        self.bar_opacity_basic.setToolTip("0 = fully transparent, 255 = fully opaque")
        bar_opacity_layout.addWidget(self.bar_opacity_basic)
        bar_opacity_layout.addStretch()
        color_layout.addRow("Bar Opacity:", bar_opacity_layout)

        right_column.addWidget(color_group)

        # Format
        format_group = QGroupBox("Output Format")
        format_layout = QFormLayout(format_group)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["png", "jpg", "tiff"])
        format_layout.addRow("Format:", self.format_combo)

        self.bit_depth = QComboBox()
        self.bit_depth.addItems(["8", "16"])
        self.bit_depth.setCurrentIndex(1)
        format_layout.addRow("Bit Depth:", self.bit_depth)

        self.transparent = QCheckBox("Use transparent background")
        format_layout.addRow("", self.transparent)

        # Connect format change to update available options
        self.format_combo.currentTextChanged.connect(self.on_format_changed)

        # Initialize control states based on default format
        self.on_format_changed(self.format_combo.currentText())

        right_column.addWidget(format_group)
        right_column.addStretch()

        # Add columns to main layout
        basic_layout.addLayout(left_column)
        basic_layout.addLayout(right_column)

        return basic_tab

    def _create_advanced_tab(self) -> QWidget:
        """Create the advanced settings tab."""
        advanced_tab = QWidget()
        advanced_layout = QHBoxLayout(advanced_tab)

        # Left column
        left_column = QVBoxLayout()

        # Text Settings Group
        text_group = QGroupBox("Text Settings")
        text_layout = QFormLayout(text_group)

        self.letter_spacing = QSpinBox()
        self.letter_spacing.setRange(-100, 100)
        self.letter_spacing.setValue(0)
        text_layout.addRow("Letter Spacing:", self.letter_spacing)

        self.vertical_spacing = QSpinBox()
        self.vertical_spacing.setRange(0, 500)
        self.vertical_spacing.setValue(0)
        self.vertical_spacing.setSpecialValueText("Auto")
        text_layout.addRow("Vertical Spacing:", self.vertical_spacing)

        self.text_transform = QComboBox()
        self.text_transform.addItems(["none", "upper", "lower", "title", "capitalize", "swapcase"])
        text_layout.addRow("Text Transform:", self.text_transform)

        # Text wrapping
        self.wrap_text = QCheckBox("Enable text wrapping")
        text_layout.addRow("", self.wrap_text)

        self.wrap_padding = QSpinBox()
        self.wrap_padding.setRange(1, 1000)
        self.wrap_padding.setValue(50)
        self.wrap_padding.setEnabled(False)  # Disabled until wrapping enabled
        self.wrap_padding.setToolTip("Distance from image border where text wraps (required when wrapping enabled)")
        text_layout.addRow("Wrap Padding:", self.wrap_padding)

        # Connect checkbox to enable/disable wrap_padding
        self.wrap_text.toggled.connect(self.wrap_padding.setEnabled)

        left_column.addWidget(text_group)

        # Shadow Settings Group
        shadow_group = QGroupBox("Shadow Settings")
        shadow_layout = QFormLayout(shadow_group)

        self.text_shadow = QCheckBox("Enable text shadow")
        shadow_layout.addRow("", self.text_shadow)

        self.shadow_blur = QSpinBox()
        self.shadow_blur.setRange(1, 100)
        self.shadow_blur.setValue(20)
        shadow_layout.addRow("Shadow Blur:", self.shadow_blur)

        self.shadow_color = QLineEdit("black")
        shadow_layout.addRow("Shadow Color:", self.shadow_color)

        self.shadow_opacity = QSpinBox()
        self.shadow_opacity.setRange(0, 255)
        self.shadow_opacity.setValue(128)
        shadow_layout.addRow("Shadow Opacity:", self.shadow_opacity)

        # Shadow offset as two separate fields
        offset_layout = QHBoxLayout()
        self.shadow_offset_x = QSpinBox()
        self.shadow_offset_x.setRange(-100, 100)
        self.shadow_offset_x.setValue(2)
        offset_layout.addWidget(QLabel("X:"))
        offset_layout.addWidget(self.shadow_offset_x)

        self.shadow_offset_y = QSpinBox()
        self.shadow_offset_y.setRange(-100, 100)
        self.shadow_offset_y.setValue(2)
        offset_layout.addWidget(QLabel("Y:"))
        offset_layout.addWidget(self.shadow_offset_y)
        offset_layout.addStretch()
        shadow_layout.addRow("Shadow Offset:", offset_layout)

        left_column.addWidget(shadow_group)

        # Outline Settings Group
        outline_group = QGroupBox("Outline Settings")
        outline_layout = QFormLayout(outline_group)

        self.outline_width = QSpinBox()
        self.outline_width.setRange(0, 50)
        self.outline_width.setValue(0)
        self.outline_width.setSpecialValueText("Disabled")
        outline_layout.addRow("Outline Width:", self.outline_width)

        self.outline_color = QLineEdit("black")
        outline_layout.addRow("Outline Color:", self.outline_color)

        self.outline_opacity = QSpinBox()
        self.outline_opacity.setRange(0, 255)
        self.outline_opacity.setValue(255)
        outline_layout.addRow("Outline Opacity:", self.outline_opacity)

        left_column.addWidget(outline_group)
        left_column.addStretch()

        # Right column
        right_column = QVBoxLayout()

        # Bar Settings Group
        bar_group = QGroupBox("Bar Settings")
        bar_layout = QFormLayout(bar_group)

        self.bar_height = QSpinBox()
        self.bar_height.setRange(0, 1000)
        self.bar_height.setValue(0)
        self.bar_height.setSpecialValueText("None")
        bar_layout.addRow("Bar Height:", self.bar_height)

        self.bar_opacity = QSpinBox()
        self.bar_opacity.setRange(0, 255)
        self.bar_opacity.setValue(0)
        bar_layout.addRow("Bar Opacity:", self.bar_opacity)
        right_column.addWidget(bar_group)

        # Miscellaneous Group
        misc_group = QGroupBox("Miscellaneous")
        misc_layout = QFormLayout(misc_group)

        self.skip_existing = QCheckBox("Skip existing files")
        misc_layout.addRow("", self.skip_existing)

        right_column.addWidget(misc_group)

        # Configuration File Group
        config_group = QGroupBox("Configuration File")
        config_layout = QVBoxLayout(config_group)

        config_help = QLabel("Save current settings to a JSON file, or load settings from an existing JSON configuration file.")
        config_help.setWordWrap(True)
        config_layout.addWidget(config_help)

        config_file_layout = QHBoxLayout()
        self.config_file = QLineEdit("")
        self.config_file.setPlaceholderText("Path to JSON config file")
        config_file_browse = QPushButton("Browse...")
        config_file_browse.clicked.connect(self.browse_config_file)
        config_file_layout.addWidget(self.config_file)
        config_file_layout.addWidget(config_file_browse)
        config_layout.addLayout(config_file_layout)

        # Load and Save buttons
        config_buttons_layout = QHBoxLayout()
        load_config_btn = QPushButton("Load Configuration")
        load_config_btn.clicked.connect(self.load_config_file)
        config_buttons_layout.addWidget(load_config_btn)

        save_config_btn = QPushButton("Save Configuration")
        save_config_btn.clicked.connect(self.save_config_file)
        config_buttons_layout.addWidget(save_config_btn)

        config_layout.addLayout(config_buttons_layout)

        right_column.addWidget(config_group)
        right_column.addStretch()

        # Add columns to main layout
        advanced_layout.addLayout(left_column)
        advanced_layout.addLayout(right_column)

        return advanced_tab

    def _create_logging_tab(self) -> QWidget:
        """Create the logging settings tab."""
        logging_tab = QWidget()
        logging_layout = QVBoxLayout(logging_tab)

        # Debug & Logging Group
        debug_group = QGroupBox("Debug & Logging")
        debug_layout = QFormLayout(debug_group)

        self.debug = QCheckBox("Show debug information")
        debug_layout.addRow("", self.debug)

        # Log level radio buttons
        log_level_layout = QHBoxLayout()
        self.log_level_normal = QRadioButton("Normal")
        self.log_level_verbose = QRadioButton("Verbose")
        self.log_level_quiet = QRadioButton("Quiet")
        self.log_level_normal.setChecked(True)  # Default to Normal
        log_level_layout.addWidget(self.log_level_normal)
        log_level_layout.addWidget(self.log_level_verbose)
        log_level_layout.addWidget(self.log_level_quiet)
        log_level_layout.addStretch()
        debug_layout.addRow("Log Level:", log_level_layout)

        # Log file path
        log_file_layout = QHBoxLayout()
        self.log_file = QLineEdit("")
        self.log_file.setPlaceholderText("Optional: path to save log file")
        log_file_browse = QPushButton("Browse...")
        log_file_browse.clicked.connect(self.browse_log_file)
        log_file_layout.addWidget(self.log_file)
        log_file_layout.addWidget(log_file_browse)
        debug_layout.addRow("Log File:", log_file_layout)

        logging_layout.addWidget(debug_group)

        return logging_tab

    def browse_log_file(self):
        """Browse for log file path."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Select Log File",
            "",
            "Log Files (*.log);;Text Files (*.txt);;All Files (*)",
        )
        if file_name:
            self.log_file.setText(file_name)

    def browse_config_file(self):
        """Browse for config file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Configuration File",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if file_name:
            self.config_file.setText(file_name)

    def browse_main_font(self):
        """Browse for main font file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Main Font File",
            "",
            "Font Files (*.ttf *.otf *.ttc);;All Files (*)",
        )
        if file_name:
            self.main_font.setText(file_name)

    def browse_secondary_font(self):
        """Browse for secondary font file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Secondary Font File",
            "",
            "Font Files (*.ttf *.otf *.ttc);;All Files (*)",
        )
        if file_name:
            self.secondary_font.setText(file_name)

    def load_config_file(self):
        """Load configuration from JSON file."""
        if not self.config_file.text():
            QMessageBox.warning(self, "No File", "Please select a configuration file first")
            return

        try:
            config = DefaultConfig.from_json(self.config_file.text())

            # Populate all GUI fields from loaded config
            self.width.setValue(config.width)
            self.height.setValue(config.height)
            self.bg_color.setText(config.bg_color or "black")
            self.text_position.setCurrentText(config.default_justification or "lower left")

            # Font settings
            self.main_font.setText(config.text.main_font or "Arial")
            self.secondary_font.setText(config.text.secondary_font or "")
            self.main_font_size.setValue(config.text.main_font_size or 0)
            self.secondary_font_size.setValue(config.text.secondary_font_size or 0)

            self.text_color.setText(config.text.text_color or "white")
            self.secondary_text_color.setText(config.text.secondary_text_color or "")

            # Bar color and opacity - split if comma-separated
            bar_color_str = config.bar.color or "black,0"
            if "," in bar_color_str:
                parts = bar_color_str.split(",")
                self.bar_color.setText(parts[0])
                try:
                    self.bar_opacity_basic.setValue(int(parts[1]))
                except (ValueError, IndexError):
                    self.bar_opacity_basic.setValue(0)
            else:
                self.bar_color.setText(bar_color_str)
                self.bar_opacity_basic.setValue(0)

            # Text settings
            self.letter_spacing.setValue(config.text.letter_spacing)
            self.vertical_spacing.setValue(config.text.vertical_spacing or 0)
            self.text_transform.setCurrentText(config.text.text_transform or "none")

            # Text wrapping
            self.wrap_text.setChecked(config.text.wrap_text)
            if config.text.wrap_padding:
                self.wrap_padding.setValue(config.text.wrap_padding)

            # Position offsets
            self.position_offset_x.setValue(config.text.position_offset_x)
            self.position_offset_y.setValue(config.text.position_offset_y)

            # Shadow settings
            self.text_shadow.setChecked(config.text.shadow.enabled)
            self.shadow_blur.setValue(config.text.shadow.blur)
            self.shadow_color.setText(config.text.shadow.color or "black")
            self.shadow_opacity.setValue(config.text.shadow.opacity)
            self.shadow_offset_x.setValue(config.text.shadow.offset_x)
            self.shadow_offset_y.setValue(config.text.shadow.offset_y)

            # Outline settings
            self.outline_width.setValue(config.text.outline.width)
            self.outline_color.setText(config.text.outline.color or "black")
            self.outline_opacity.setValue(config.text.outline.opacity)

            # Bar settings
            self.bar_height.setValue(config.bar.height or 0)
            self.bar_opacity.setValue(config.bar.opacity or 0)

            # Output settings
            self.format_combo.setCurrentText(config.output.format)
            self.bit_depth.setCurrentText(str(config.output.bit_depth))
            self.transparent.setChecked(config.output.transparent)
            self.skip_existing.setChecked(config.output.skip_existing)

            # Debug/logging
            self.debug.setChecked(config.debug)

            QMessageBox.information(self, "Success", "Configuration loaded successfully!")
            self.statusBar().showMessage(f"Loaded config from: {self.config_file.text()}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load configuration: {e}")

    def save_config_file(self):
        """Save current GUI settings to JSON configuration file."""
        # Get file path from user if not already specified
        file_path = self.config_file.text()

        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Configuration File",
                "",
                "JSON Files (*.json);;All Files (*)",
            )
            if not file_path:
                return  # User cancelled

            # Update the config file field
            self.config_file.setText(file_path)

        # Ensure file has .json extension
        if not file_path.endswith('.json'):
            file_path += '.json'
            self.config_file.setText(file_path)

        try:
            # Get current configuration from GUI
            config = self.get_config()

            # Save to JSON file
            config.to_json(file_path)

            QMessageBox.information(self, "Success", f"Configuration saved successfully to:\n{file_path}")
            self.statusBar().showMessage(f"Saved config to: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")

    def browse_input(self):
        """Browse for input file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input File",
            "",
            "Excel/CSV Files (*.xlsx *.xls *.csv);;All Files (*)",
        )
        if file_name:
            self.input_file.setText(file_name)

    def browse_output(self):
        """Browse for output directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_dir.setText(directory)

    def generate_excel_template(self):
        """Generate an Excel template with data, examples, and instructions sheets."""
        try:
            # Open save file dialog
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save Excel Template",
                "l3rds_template.xlsx",
                "Excel Files (*.xlsx);;All Files (*)",
            )

            if not file_name:
                # User cancelled
                return

            # Ensure .xlsx extension
            if not file_name.endswith('.xlsx'):
                file_name += '.xlsx'

            # Generate template
            TemplateGenerator.create_template(file_name)

            # Show success message
            QMessageBox.information(
                self,
                "Template Created",
                f"Excel template created successfully!\n\nLocation: {file_name}\n\n"
                f"The template includes:\n"
                f"• Data sheet - Ready for your entries\n"
                f"• Examples sheet - 5 sample rows\n"
                f"• Instructions sheet - Comprehensive guide"
            )

            # Update status bar
            self.statusBar().showMessage(f"Excel template generated: {file_name}", 5000)

        except Exception as e:
            # Show error message
            QMessageBox.critical(
                self,
                "Template Generation Failed",
                f"Failed to create Excel template:\n\n{str(e)}"
            )
            self.statusBar().showMessage(f"Template generation failed: {str(e)}", 5000)

    def on_format_changed(self, format_type: str):
        """Update available options based on selected output format.

        Args:
            format_type: Selected format ("png", "jpg", or "tiff")
        """
        if format_type == "jpg":
            # JPG: Force 8-bit, disable transparency, disable bit depth selector
            self.bit_depth.setCurrentText("8")
            self.bit_depth.setEnabled(False)
            self.transparent.setChecked(False)
            self.transparent.setEnabled(False)
        elif format_type == "png":
            # PNG: Enable transparency, disable bit depth (PNG doesn't use this selector)
            self.bit_depth.setEnabled(False)
            self.transparent.setEnabled(True)
        elif format_type == "tiff":
            # TIFF: Enable both transparency and bit depth selector
            self.bit_depth.setEnabled(True)
            self.transparent.setEnabled(True)

    def pick_color(self, target_field: QLineEdit):
        """Open color picker dialog and update field with hex color.

        Args:
            target_field: The QLineEdit field to update with the selected color
        """
        # Get current color from field if it exists and is valid
        current_color_text = target_field.text().strip()
        initial_color = QColor("white")  # Default to white

        # Try to parse current color
        if current_color_text:
            # Handle various color formats
            if current_color_text.startswith("#"):
                # Hex color
                initial_color = QColor(current_color_text)
            elif "," in current_color_text:
                # Color with alpha (e.g., "black,0" or "255,0,0,128")
                # Use just the color part, ignore alpha
                parts = current_color_text.split(",")
                if len(parts) >= 3:
                    # RGB format
                    try:
                        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                        initial_color = QColor(r, g, b)
                    except ValueError:
                        initial_color = QColor(parts[0])  # Try as named color
                else:
                    # Named color with alpha (e.g., "black,128")
                    initial_color = QColor(parts[0])
            else:
                # Named color (e.g., "white", "black", "red")
                initial_color = QColor(current_color_text)

        # If color is still not valid, use white
        if not initial_color.isValid():
            initial_color = QColor("white")

        # Open color picker dialog
        color = QColorDialog.getColor(initial_color, self, "Select Color")

        # If user selected a color (didn't cancel)
        if color.isValid():
            # Convert to hex format and update field
            hex_color = color.name()  # Returns format like "#rrggbb"
            target_field.setText(hex_color)

    def get_config(self) -> DefaultConfig:
        """Build configuration from GUI state."""
        config = DefaultConfig()

        # Basic settings
        config.width = self.width.value()
        config.height = self.height.value()
        config.bg_color = self.bg_color.text()
        config.default_justification = self.text_position.currentText()

        # Text configuration
        config.text = TextConfig()

        # Font settings
        config.text.main_font = self.main_font.text() or "Arial"
        config.text.secondary_font = self.secondary_font.text() or None
        config.text.main_font_size = self.main_font_size.value() if self.main_font_size.value() > 0 else None
        config.text.secondary_font_size = self.secondary_font_size.value() if self.secondary_font_size.value() > 0 else None

        config.text.text_color = self.text_color.text()
        config.text.secondary_text_color = self.secondary_text_color.text() or None
        config.text.letter_spacing = self.letter_spacing.value()

        # NEW: Vertical spacing (0 = auto/None)
        config.text.vertical_spacing = self.vertical_spacing.value() if self.vertical_spacing.value() > 0 else None

        # NEW: Text transform
        config.text.text_transform = self.text_transform.currentText()

        # Text wrapping
        config.text.wrap_text = self.wrap_text.isChecked()
        config.text.wrap_padding = self.wrap_padding.value() if self.wrap_text.isChecked() else None

        # Position offsets
        config.text.position_offset_x = self.position_offset_x.value()
        config.text.position_offset_y = self.position_offset_y.value()

        # Shadow configuration
        config.text.shadow = ShadowConfig()
        config.text.shadow.enabled = self.text_shadow.isChecked()
        config.text.shadow.blur = self.shadow_blur.value()

        # NEW: Shadow color, opacity, and offset
        config.text.shadow.color = self.shadow_color.text()
        config.text.shadow.opacity = self.shadow_opacity.value()
        config.text.shadow.offset_x = self.shadow_offset_x.value()
        config.text.shadow.offset_y = self.shadow_offset_y.value()

        # Outline configuration
        config.text.outline = OutlineConfig()
        config.text.outline.width = self.outline_width.value()
        config.text.outline.color = self.outline_color.text()
        config.text.outline.opacity = self.outline_opacity.value()

        # Bar configuration
        config.bar = BarConfig()

        # Combine bar color and opacity (from Basic Settings)
        bar_color = self.bar_color.text()
        bar_opacity = self.bar_opacity_basic.value()

        # Format: "color,opacity" - but only add opacity if not default (0)
        if bar_opacity > 0:
            config.bar.color = f"{bar_color},{bar_opacity}"
        else:
            config.bar.color = bar_color

        # NEW: Bar height and opacity override from Advanced Settings (0 = auto/None)
        config.bar.height = self.bar_height.value() if self.bar_height.value() > 0 else None
        # Advanced Settings bar_opacity can override Basic Settings if set
        if self.bar_opacity.value() > 0:
            config.bar.opacity = self.bar_opacity.value()

        # Output
        config.output = OutputConfig()
        config.output.format = self.format_combo.currentText()
        config.output.bit_depth = int(self.bit_depth.currentText())
        config.output.transparent = self.transparent.isChecked()
        config.output.skip_existing = self.skip_existing.isChecked()

        # Debug and logging
        config.debug = self.debug.isChecked()

        # NEW: Log level from radio buttons
        if self.log_level_verbose.isChecked():
            config.log_level = "DEBUG"
        elif self.log_level_quiet.isChecked():
            config.log_level = "WARNING"
        else:  # Normal
            config.log_level = "INFO"

        # Override with DEBUG if debug checkbox is checked
        if config.debug:
            config.log_level = "DEBUG"

        # NEW: Log file path
        config.log_file = self.log_file.text() if self.log_file.text() else None

        return config

    def run_test(self):
        """Run test preview."""
        if not self.validate_inputs():
            return

        self.statusBar().showMessage("Generating preview...")
        self.log_text.clear()
        self.disable_buttons()

        config = self.get_config()

        # Update log handler level based on config
        log_level = getattr(logging, config.log_level, logging.INFO)
        self.log_handler.setLevel(log_level)

        self.worker = GeneratorWorker(config, self.input_file.text(), self.output_dir.text(), test_mode=True)
        self.worker.progress.connect(self.on_progress)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def run_generation(self):
        """Run full generation."""
        if not self.validate_inputs():
            return

        try:
            loader = ExcelLoader()
            total_rows = loader.get_row_count(self.input_file.text())

            self.progress_bar.setMaximum(total_rows)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot read input file: {e}")
            return

        self.statusBar().showMessage("Generating lower thirds...")
        self.log_text.clear()
        self.disable_buttons()

        config = self.get_config()

        # Update log handler level based on config
        log_level = getattr(logging, config.log_level, logging.INFO)
        self.log_handler.setLevel(log_level)

        self.worker = GeneratorWorker(config, self.input_file.text(), self.output_dir.text(), test_mode=False)
        self.worker.progress.connect(self.on_progress)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def validate_inputs(self) -> bool:
        """Validate user inputs."""
        if not self.input_file.text():
            QMessageBox.warning(self, "Input Required", "Please select an input file")
            return False

        if not self.output_dir.text():
            QMessageBox.warning(self, "Input Required", "Please select an output directory")
            return False

        return True

    def disable_buttons(self):
        """Disable action buttons during generation."""
        self.test_button.setEnabled(False)
        self.generate_button.setEnabled(False)

    def enable_buttons(self):
        """Enable action buttons after generation."""
        self.test_button.setEnabled(True)
        self.generate_button.setEnabled(True)

    def on_progress(self, increment: int, message: str):
        """Handle progress update."""
        self.log_text.append(message)
        current = self.progress_bar.value()
        self.progress_bar.setValue(current + increment)

    def on_error(self, message: str):
        """Handle error message."""
        self.log_text.append(f"ERROR: {message}")

    def copy_log_to_clipboard(self):
        """Copy log contents to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_text.toPlainText())
        self.statusBar().showMessage("Log copied to clipboard", 2000)

    def append_colored_log(self, message: str, level: str):
        """Append a color-coded log message to the log tab.

        Args:
            message: The formatted log message (with timestamp and level)
            level: The log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        # Get color for this level
        color = QTextEditLogger.LEVEL_COLORS.get(level, '#000000')

        # Split message into timestamp+level and actual message
        # Format is: "YYYY-MM-DD HH:MM:SS - LEVEL - message"
        parts = message.split(' - ', 2)
        if len(parts) == 3:
            timestamp, level_name, msg_text = parts
            # Format with timestamp and level in black, message in level color
            html = f'<span style="color: black;">{timestamp} - {level_name} - </span><span style="color: {color};">{msg_text}</span>'
        else:
            # Fallback if format doesn't match expected pattern
            html = f'<span style="color: {color};">{message}</span>'

        self.log_text.append(html)

        # Auto-scroll to bottom if already at bottom
        scrollbar = self.log_text.verticalScrollBar()
        if scrollbar.value() >= scrollbar.maximum() - 10:  # Within 10 pixels of bottom
            scrollbar.setValue(scrollbar.maximum())

    def on_finished(self, success: bool, message: str):
        """Handle generation completion."""
        self.enable_buttons()
        self.progress_bar.setVisible(False)

        if success:
            self.statusBar().showMessage(message)
            QMessageBox.information(self, "Success", message)
        else:
            self.statusBar().showMessage(f"Error: {message}")
            QMessageBox.warning(self, "Error", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LowerThirdsGUI()
    sys.exit(app.exec_())
