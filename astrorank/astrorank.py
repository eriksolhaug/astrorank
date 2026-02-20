"""
astrorank - Image Ranking GUI Application
"""

import sys
import signal
import argparse
import webbrowser
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QTextEdit, QInputDialog, QProgressBar, QSlider,
    QSplitter, QPlainTextEdit
)
from PyQt5.QtGui import QPixmap, QColor, QFont, QIcon, QTransform, QImage
from PyQt5.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal, QBuffer

from astrorank.utils import (
    get_jpg_files, load_rankings, save_rankings,
    find_next_unranked, find_first_unranked, is_valid_rank,
    parse_radec_from_filename, load_config, download_secondary_image,
    parse_key_string, string_to_qt_key, parse_rank_config, get_rank_range
)
from astrorank.ui_utils import get_astrorank_icon


class DownloadWorker(QThread):
    """Worker thread for downloading secondary images without blocking UI"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)  # Emits path to downloaded image or empty string on failure
    error = pyqtSignal(str)  # Emits error message
    
    def __init__(self, ra, dec, output_dir, config, filename=None):
        super().__init__()
        self.ra = ra
        self.dec = dec
        self.output_dir = output_dir
        self.config = config
        self.filename = filename
    
    def run(self):
        """Run the download in a separate thread"""
        try:
            result = download_secondary_image(self.ra, self.dec, self.output_dir, self.config, self.filename, self.progress.emit)
            if result:
                self.finished.emit(result)
            else:
                self.error.emit("Failed to download secondary image")
        except Exception as e:
            self.error.emit(f"Download error: {str(e)}")


class NavigationAwareLineEdit(QLineEdit):
    """QLineEdit that forwards arrow keys and other navigation keys to parent window"""
    
    def keyPressEvent(self, event):
        """Override keyPressEvent to forward navigation keys to parent"""
        key = event.key()
        # Forward navigation keys to parent window
        if key in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down, Qt.Key_Return, Qt.Key_Enter]:
            # Find the main window (AstrorankGUI)
            window = self.window()
            if window and hasattr(window, 'keyPressEvent'):
                window.keyPressEvent(event)
                return
        # Handle other keys normally in the text edit
        super().keyPressEvent(event)


class CommentDialog(QDialog):
    """Dialog for adding/editing image comments"""
    def __init__(self, parent=None, initial_text=""):
        super().__init__(parent)
        self.setWindowTitle("Edit Comment")
        self.setGeometry(100, 100, 500, 200)
        
        layout = QVBoxLayout()
        
        # Comment text input
        self.text_edit = QLineEdit()
        self.text_edit.setText(initial_text)
        self.text_edit.setPlaceholderText("Enter comment...")
        layout.addWidget(QLabel("Comment:"))
        layout.addWidget(self.text_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Focus on text edit for convenience
        self.text_edit.setFocus()
        self.text_edit.selectAll()
    
    def get_comment(self):
        """Get the comment text from the dialog"""
        return self.text_edit.text().strip()


class AstrorankGUI(QMainWindow):
    def __init__(self, image_dir, output_file="rankings.txt", config_file="config.json"):
        super().__init__()
        
        self.image_dir = Path(image_dir)
        self.output_file = Path(output_file)
        self.previous_index = -1  # Track previous index for efficient updates
        self.save_counter = 0  # Batch saves every N rankings
        self.table_initialized = False  # Track if table has been populated
        self.list_visible = True  # Track list visibility state
        self.zoom_level = 1.0  # Track zoom level for single image view
        self.dual_view_zoom = 1.0  # Track zoom level for dual-view images
        self.helper_visible = False  # Track helper window visibility
        self.helper_window = None  # Reference to helper dialog
        self.skip_scroll = False  # Skip scroll-to-center on click navigation
        self.dark_mode = False  # Track dark mode state
        self.original_container_width = 680  # Original container width for reset
        self.original_container_height = 680  # Original container height for reset
        
        # Brightness and contrast adjustment tracking
        self.brightness_multiplier = 1.0  # 1.0 = normal, > 1.0 = brighter, < 1.0 = darker
        self.contrast_multiplier = 1.0    # 1.0 = normal, > 1.0 = more contrast, < 1.0 = less contrast
        
        # Secondary image download functionality (configurable survey)
        self.config = load_config(config_file)
        secondary_config = self.config.get("secondary_download", {})
        self.secondary_enabled = secondary_config.get("enabled", True)
        
        # Browser functionality (configurable)
        browser_config = self.config.get("browser", {})
        self.browser_enabled = browser_config.get("enabled", True)

        # NED search functionality (configurable)
        ned_search_config = self.config.get("ned_search", {})
        self.ned_search_enabled = ned_search_config.get("enabled", True)
        
        # Secondary directory functionality (configurable)
        secondary_dir_config = self.config.get("secondary_dir", {})
        self.secondary_dir_enabled = secondary_dir_config.get("enabled", False)
        self.secondary_dir_path = Path(secondary_dir_config.get("path", "")) if secondary_dir_config.get("path") else None
        self.use_secondary_dir = False  # Toggle state for which directory to display
        
        self.secondary_name = secondary_config.get("name", "Secondary")
        self.secondary_output_dir = Path(image_dir) / self.secondary_name.lower()
        self.secondary_images = {}  # Maps filename to path of downloaded secondary image
        self.dual_view_active = False  # Track if we're showing original + secondary image side-by-side
        self.download_worker = None  # Reference to download thread
        self.downloading = False  # Flag to disable navigation during download
        
        # Load configurable keyboard shortcuts
        self.key_config = self.config.get("keys", {})
        self._initialize_key_bindings()
        
        # Load configurable ranks
        rank_config = self.config.get("ranks", {"0": 0, "1": 1, "2": 2, "3": 3, "backtick": 0})
        self.rank_config = rank_config  # Store original config for error messages
        self.rank_map = parse_rank_config(rank_config)  # Maps Qt key enums to rank values
        self.min_rank, self.max_rank = get_rank_range(rank_config)  # Get valid range
        
        # Load image files and rankings
        self.jpg_files = get_jpg_files(str(self.image_dir))
        if not self.jpg_files:
            raise ValueError(f"No .jpg files found in {self.image_dir}")
        
        self.rankings = load_rankings(str(self.output_file))
        self.comments = {}  # Store comments for images
        self._load_comments()  # Load comments from file
        
        # Start at first image
        self.current_index = 0
        
        self.init_ui()
        self.apply_light_stylesheet()  # Apply light mode by default on startup
        self.display_image()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("astrorank - Image Ranking Tool")
        
        # Set application icon
        icon = get_astrorank_icon()
        self.setWindowIcon(icon)
        
        self.setGeometry(100, 100, 1400, 760)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_container = QVBoxLayout()
        
        # Top bar with toggle list button
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        
        large_font = QFont()
        large_font.setPointSize(int(large_font.pointSize() * 1.5))
        
        self.save_button = QPushButton("Save")
        self.save_button.setFont(large_font)
        self.save_button.setMaximumWidth(100)
        self.save_button.clicked.connect(self.save_rankings_now)
        top_bar.addWidget(self.save_button)
        
        self.view_rankings_button = QPushButton("View Rankings File")
        self.view_rankings_button.setFont(large_font)
        self.view_rankings_button.setMaximumWidth(180)
        self.view_rankings_button.clicked.connect(self.view_rankings)
        top_bar.addWidget(self.view_rankings_button)
        
        self.save_quit_button = QPushButton("Save and Quit")
        self.save_quit_button.setFont(large_font)
        self.save_quit_button.setMaximumWidth(150)
        self.save_quit_button.clicked.connect(self.close)
        top_bar.addWidget(self.save_quit_button)

        top_bar.addSpacing(30)

        self.toggle_list_button = QPushButton("Hide List")
        self.toggle_list_button.setFont(large_font)
        self.toggle_list_button.setMaximumWidth(120)
        self.toggle_list_button.clicked.connect(self.toggle_list_visibility)
        top_bar.addWidget(self.toggle_list_button)
        
        self.dark_mode_button = QPushButton("Dark")
        self.dark_mode_button.setFont(large_font)
        self.dark_mode_button.setMaximumWidth(100)
        self.dark_mode_button.clicked.connect(self.toggle_dark_mode)
        top_bar.addWidget(self.dark_mode_button)
        
        top_bar.addStretch()
        
        main_container.addLayout(top_bar)
        
        # Main content layout
        self.main_layout = QHBoxLayout()  # Store as instance variable for toggling
        
        # Left side: Image viewer and controls
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        
        # Image filename and ranking info (shown above both single and dual views)
        self.image_info_label = QLabel()
        info_font = QFont()
        info_font.setPointSize(int(info_font.pointSize() * 1.5))
        self.image_info_label.setFont(info_font)
        self.image_info_label.setAlignment(Qt.AlignLeft)
        self.image_info_label.setTextFormat(Qt.RichText)
        self.image_info_label.setMaximumHeight(30)
        
        # Secondary download progress bar and message (shown below both single and dual views)
        self.download_progress_bar = QProgressBar()
        self.download_progress_bar.setVisible(False)
        self.download_progress_bar.setMaximumHeight(20)
        
        self.download_message_label = QLabel()
        self.download_message_label.setVisible(False)
        self.download_message_label.setAlignment(Qt.AlignCenter)
        self.download_message_label.setMaximumHeight(25)
        
        # Image container - wraps image display (without info label or progress bar)
        image_container = QWidget()
        image_container_layout = QVBoxLayout()
        image_container_layout.setContentsMargins(0, 0, 0, 0)
        image_container_layout.setSpacing(0)
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setStyleSheet("border: 1px solid black;")
        self.image_label.setAlignment(Qt.AlignCenter)
        image_container_layout.addWidget(self.image_label)
        
        image_container.setLayout(image_container_layout)
        image_container.setMinimumHeight(400)
        image_container.setMinimumWidth(400)
        image_container.setMaximumHeight(680)
        image_container.setMaximumWidth(680)
        # Store reference for resizing
        self.image_container = image_container
        
        # Create dual-view container (side-by-side images for secondary comparison)
        dual_view_container = QWidget()
        dual_view_layout = QHBoxLayout()
        dual_view_layout.setContentsMargins(0, 0, 0, 0)
        dual_view_layout.setSpacing(10)
        
        # Left image in dual view
        self.dual_image_label_1 = QLabel()
        self.dual_image_label_1.setStyleSheet("border: 1px solid black;")
        self.dual_image_label_1.setAlignment(Qt.AlignCenter)
        dual_view_layout.addWidget(self.dual_image_label_1)
        
        # Right image in dual view
        self.dual_image_label_2 = QLabel()
        self.dual_image_label_2.setStyleSheet("border: 1px solid black;")
        self.dual_image_label_2.setAlignment(Qt.AlignCenter)
        dual_view_layout.addWidget(self.dual_image_label_2)
        
        dual_view_container.setLayout(dual_view_layout)
        dual_view_container.setMinimumHeight(400)
        dual_view_container.setMinimumWidth(400)
        dual_view_container.setMaximumHeight(680)
        dual_view_container.setMaximumWidth(680)
        dual_view_container.setVisible(False)  # Hidden by default
        self.dual_view_container = dual_view_container
        
        # Wrapper for image container with zoom buttons
        image_wrapper = QHBoxLayout()
        image_wrapper.setContentsMargins(0, 0, 0, 0)
        image_wrapper.setSpacing(5)
        image_wrapper.addWidget(image_container, 0)
        image_wrapper.addWidget(dual_view_container, 0)  # Add dual view container to wrapper
        
        # Zoom button layout
        zoom_layout = QVBoxLayout()
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(2)
        
        small_font = QFont()
        small_font.setPointSize(int(small_font.pointSize() * 1.2))
        
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setFont(small_font)
        self.zoom_in_button.setMaximumWidth(40)
        self.zoom_in_button.setMaximumHeight(40)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        zoom_layout.addWidget(self.zoom_in_button)
        
        self.zoom_out_button = QPushButton("−")
        self.zoom_out_button.setFont(small_font)
        self.zoom_out_button.setMaximumWidth(40)
        self.zoom_out_button.setMaximumHeight(40)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        zoom_layout.addWidget(self.zoom_out_button)
        
        self.fit_button = QPushButton("Fit")
        self.fit_button.setFont(small_font)
        self.fit_button.setMaximumWidth(40)
        self.fit_button.clicked.connect(self.fit_image)
        zoom_layout.addWidget(self.fit_button)
        
        self.reset_button = QPushButton("Resize")
        self.reset_button.setFont(small_font)
        self.reset_button.setMaximumWidth(55)
        self.reset_button.clicked.connect(self.reset_image_container)
        zoom_layout.addWidget(self.reset_button)
        
        zoom_layout.addStretch()
        
        # Brightness and Contrast control panel (below zoom buttons)
        brightness_contrast_layout = QVBoxLayout()
        brightness_contrast_layout.setContentsMargins(5, 5, 0, 0)
        brightness_contrast_layout.setSpacing(8)
        self.brightness_contrast_layout = brightness_contrast_layout  # Store reference for later
        
        # Brightness controls
        brightness_slider_layout = QVBoxLayout()
        brightness_slider_layout.setContentsMargins(0, 0, 0, 0)
        brightness_slider_layout.setSpacing(3)
        
        self.brightness_slider = QSlider(Qt.Vertical)
        self.brightness_slider.setMinimum(50)    # 0.5x brightness
        self.brightness_slider.setMaximum(200)   # 2.0x brightness
        self.brightness_slider.setValue(100)     # 1.0x = normal
        self.brightness_slider.setMaximumHeight(100)
        self.brightness_slider.setMaximumWidth(30)
        self.brightness_slider.sliderMoved.connect(self.on_brightness_changed)
        brightness_slider_layout.addWidget(self.brightness_slider)
        
        # Brightness label
        self.brightness_label = QLabel("Brightness: 1.0")
        brightness_label_font = QFont()
        brightness_label_font.setPointSize(7)
        self.brightness_label.setFont(brightness_label_font)
        self.brightness_label.setAlignment(Qt.AlignCenter)
        brightness_slider_layout.addWidget(self.brightness_label)
        
        brightness_contrast_layout.addLayout(brightness_slider_layout)
        
        # Contrast controls
        contrast_slider_layout = QVBoxLayout()
        contrast_slider_layout.setContentsMargins(0, 0, 0, 0)
        contrast_slider_layout.setSpacing(3)
        
        self.contrast_slider = QSlider(Qt.Vertical)
        self.contrast_slider.setMinimum(50)      # 0.5x contrast
        self.contrast_slider.setMaximum(200)     # 2.0x contrast
        self.contrast_slider.setValue(100)       # 1.0x = normal
        self.contrast_slider.setMaximumHeight(100)
        self.contrast_slider.setMaximumWidth(30)
        self.contrast_slider.sliderMoved.connect(self.on_contrast_changed)
        contrast_slider_layout.addWidget(self.contrast_slider)
        
        # Contrast label
        self.contrast_label = QLabel("Contrast: 1.0")
        contrast_label_font = QFont()
        contrast_label_font.setPointSize(7)
        self.contrast_label.setFont(contrast_label_font)
        self.contrast_label.setAlignment(Qt.AlignCenter)
        contrast_slider_layout.addWidget(self.contrast_label)
        
        brightness_contrast_layout.addLayout(contrast_slider_layout)
        
        # Reset Scale button
        self.reset_scale_button = QPushButton("Default")
        self.reset_scale_button.setFont(small_font)
        self.reset_scale_button.setMaximumWidth(58)
        self.reset_scale_button.clicked.connect(self.reset_brightness_contrast)
        brightness_contrast_layout.addWidget(self.reset_scale_button)
        
        brightness_contrast_layout.addStretch()
        
        # Right panel: zoom and brightness/contrast controls (stacked vertically)
        right_panel_layout = QVBoxLayout()
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        right_panel_layout.setSpacing(5)
        right_panel_layout.addLayout(zoom_layout)
        right_panel_layout.addLayout(brightness_contrast_layout)
        
        # Wrapper for image container with controls
        image_wrapper = QHBoxLayout()
        image_wrapper.setContentsMargins(0, 0, 0, 0)
        image_wrapper.setSpacing(5)
        image_wrapper.addWidget(image_container, 0)
        image_wrapper.addWidget(dual_view_container, 0)  # Add dual view container to wrapper
        image_wrapper.addLayout(right_panel_layout)
        
        # Create a container layout that includes the info label, image containers, and progress bar
        # This ensures the info label and progress bar stay visible when switching between single and dual view
        images_layout = QVBoxLayout()
        images_layout.setContentsMargins(0, 0, 0, 0)
        images_layout.setSpacing(0)
        images_layout.addWidget(self.image_info_label)
        images_layout.addLayout(image_wrapper)
        images_layout.addWidget(self.download_progress_bar)
        images_layout.addWidget(self.download_message_label)
        
        left_layout.addLayout(images_layout, 0)
        
        # Ranking input and buttons
        control_layout = QHBoxLayout()
        control_layout.setSpacing(3)
        
        # Create larger font (1.5x default)
        large_font = QFont()
        large_font.setPointSize(int(large_font.pointSize() * 1.5))
        
        # Create rank label with dynamic range
        rank_label = QLabel(f"Rank ({self.min_rank}-{self.max_rank}):")
        rank_label.setFont(large_font)
        control_layout.addWidget(rank_label)
        
        self.rank_input = NavigationAwareLineEdit()
        self.rank_input.setMaximumWidth(120)
        self.rank_input.setMinimumHeight(40)
        self.rank_input.setFont(large_font)
        self.rank_input.setAlignment(Qt.AlignCenter)
        self.rank_input.returnPressed.connect(self.submit_rank)
        control_layout.addWidget(self.rank_input)
        
        # Auto-submit checkbox
        from PyQt5.QtWidgets import QCheckBox
        self.auto_submit_checkbox = QCheckBox("Auto-Submit and Next ")
        self.auto_submit_checkbox.setChecked(True)
        self.auto_submit_checkbox.setFont(large_font)
        self.auto_submit_checkbox.setMaximumWidth(280)
        control_layout.addWidget(self.auto_submit_checkbox)
        
        # Navigation buttons
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.setFont(large_font)
        self.prev_button.clicked.connect(self.go_previous)
        control_layout.addWidget(self.prev_button)
        
        self.next_button = QPushButton("Next ▶")
        self.next_button.setFont(large_font)
        self.next_button.clicked.connect(self.go_next)
        control_layout.addWidget(self.next_button)
        
        self.skip_button = QPushButton("Skip to Next Unranked ⏭")
        self.skip_button.setFont(large_font)
        self.skip_button.clicked.connect(self.skip_to_next_unranked)
        control_layout.addWidget(self.skip_button)
        
        control_layout.addStretch()
        left_layout.addLayout(control_layout)
        
        # Right side: Image list table wrapped in container for proper scroll bar handling
        table_container = QWidget()
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        table_layout.setSpacing(0)  # No spacing
        
        self.table = QTableWidget()
        # Set column count based on whether secondary download is enabled
        num_columns = 5 if self.secondary_enabled else 4
        self.table.setColumnCount(num_columns)
        
        # Build header labels conditionally
        headers = ["Filename", "Rank", "Ranked?", "Comments"]
        if self.secondary_enabled:
            secondary_header = f"{self.secondary_name}?"
            headers.append(secondary_header)
        self.table.setHorizontalHeaderLabels(headers)
        
        # Set all columns resizable independently
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)  # Filename resizable
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)  # Rank resizable
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)  # Ranked? resizable
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)  # Comments resizable
        if self.secondary_enabled:
            self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)  # Secondary image status resizable
        
        # Set default column widths
        self.table.setColumnWidth(0, 200)  # Filename column
        self.table.setColumnWidth(1, 45)   # Rank column
        self.table.setColumnWidth(2, 65)   # Ranked? column
        self.table.setColumnWidth(3, 110)  # Comments column
        if self.secondary_enabled:
            self.table.setColumnWidth(4, 60)   # Secondary? column
        self.table.setRowCount(len(self.jpg_files))
        self.table.itemClicked.connect(self.on_table_click)
        self.table.setHorizontalScrollMode(1)  # ScrollPerPixel
        self.table.setSelectionMode(QTableWidget.NoSelection)  # Disable default selection
        self.table.itemDoubleClicked.connect(self.on_table_double_click)
        
        table_layout.addWidget(self.table)
        table_container.setLayout(table_layout)
        
        # Populate table
        self.update_table()
        
        # Store references to layouts and widgets for toggling
        self.left_layout = left_layout
        self.list_widget = self.table
        self.table_container = table_container  # Store container for toggling visibility
        
        # Create splitter for draggable resize between left panel and table
        splitter = QSplitter(Qt.Horizontal)
        
        # Create left panel widget
        left_panel = QWidget()
        left_panel.setLayout(left_layout)
        
        # Add both panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(table_container)
        
        # Set initial sizes (2:1 ratio, can be dragged to change)
        splitter.setSizes([self.width() * 2 // 3, self.width() // 3])
        splitter.setCollapsible(0, False)  # Don't allow left panel to collapse
        splitter.setCollapsible(1, False)  # Don't allow table to collapse
        
        # Add splitter to main layout
        self.main_layout.addWidget(splitter)
        
        main_container.addLayout(self.main_layout)
        main_widget.setLayout(main_container)
        
        # Set focus to main window so arrow keys work for navigation
        self.setFocus()
    
    def display_image(self):
        """Display the current image"""
        current_file = self.jpg_files[self.current_index]
        image_path = self.image_dir / current_file
        
        # Reset brightness and contrast to original values when changing images
        self.brightness_multiplier = 1.0
        self.contrast_multiplier = 1.0
        self.brightness_slider.blockSignals(True)
        self.contrast_slider.blockSignals(True)
        self.brightness_slider.setValue(100)
        self.contrast_slider.setValue(100)
        self.brightness_label.setText("Brightness: 1.0")
        self.contrast_label.setText("Contrast: 1.0")
        self.brightness_slider.blockSignals(False)
        self.contrast_slider.blockSignals(False)
        
        # Use the new display method that handles both single and dual view
        self.display_secondary_view()
        
        # Update image info label with filename and previous ranking
        current_index_display = self.current_index + 1
        total_images = len(self.jpg_files)
        
        if current_file in self.rankings:
            rank = self.rankings[current_file]
            self.image_info_label.setText(f"<table style='width: 100%;'><tr><td style='padding-right: 10px;'>{current_file}</td><td style='width: 100%;'></td><td align='right'>(Rank: {rank}) [{current_index_display}/{total_images}]</td></tr></table>")
        else:
            self.image_info_label.setText(f"<table style='width: 100%;'><tr><td style='padding-right: 10px;'>{current_file}</td><td style='width: 100%;'></td><td align='right'>[{current_index_display}/{total_images}]</td></tr></table>")
        
        # Update window title
        self.setWindowTitle("🔭 AstroRank (v1.3)")
        
        # Clear rank input (but don't focus it - keep focus on main window for arrow keys)
        self.rank_input.clear()
        
        # Set focus to main window so arrow keys work for navigation
        self.setFocus()
        
        # Highlight current row in table
        self.update_table()
    
    def _initialize_key_bindings(self):
        """Initialize key binding data for use in keyPressEvent and helper display"""
        # Parse all key bindings from config for both input and display
        self.keys = {}
        
        for action, key_str in self.key_config.items():
            key_list = parse_key_string(key_str)
            self.keys[action] = key_list
    
    def _key_matches(self, event_key, action_name, allow_shift=False):
        """Check if a keyboard event matches a configured action key"""
        key_strings = self.keys.get(action_name, [])
        # Call event.modifiers() safely in case it's not available (e.g. on some platforms or for certain events)
        event = event if hasattr(event, 'modifiers') else None
        has_shift = event.modifiers() & Qt.ShiftModifier if hasattr(event, 'modifiers') else False
        
        for key_str in key_strings:
            qt_keys = string_to_qt_key(key_str)
            for qt_key, needs_shift in qt_keys:
                if event_key == qt_key:
                    # If key requires shift and we're not allowing shift in this context, skip
                    if needs_shift and not allow_shift:
                        continue
                    # If key requires shift, check we have it
                    if needs_shift and not has_shift:
                        continue
                    # If key doesn't require shift but we have one, and this is not shift+right/left combo
                    if not needs_shift and has_shift and "+" not in key_str:
                        continue
                    return True
        return False
    
    def open_legacy_survey_viewer(self):
        """Open Legacy Survey viewer for current image's RA/Dec"""
        if not self.browser_enabled:
            self.show_secondary_error("Browser functionality is disabled in config")
            return
        
        current_file = self.jpg_files[self.current_index]
        radec = parse_radec_from_filename(current_file)
        
        if radec is None:
            self.show_wise_error("Could not parse RA/Dec from filename")
            return
        
        ra, dec = radec
        # Using the url_template from the config to allow for customization
        viewer_url_template = self.config.get("browser", {}).get("url_template", "https://www.legacysurvey.org/viewer/?ra={ra}&dec={dec}&layer=ls-dr10&zoom=16")
        viewer_url = viewer_url_template.format(ra=ra, dec=dec)
        webbrowser.open(viewer_url)

    def open_ned_search(self):
        """Open NED search for current image's RA/Dec"""
        if not self.ned_search_enabled:
            self.show_secondary_error("NED search functionality is disabled in config")
            return
        current_file = self.jpg_files[self.current_index]
        radec = parse_radec_from_filename(current_file)
        if radec is None:
            self.show_secondary_error("Could not parse RA/Dec from filename")
            return
        ra, dec = radec
        # NED expects RA in sexagesimal format, so convert it
        ra_str = f"{int(ra // 15)}h{int((ra % 15) * 4)}m{((ra % 15) * 4 - int((ra % 15) * 4)) * 60:.2f}s"
        dec_str = f"{'+' if dec >= 0 else '-'}{int(abs(dec))}d{int((abs(dec) % 1) * 60)}m{((abs(dec) % 1) * 60 - int((abs(dec) % 1) * 60)) * 60:.2f}s"
        # Using the url_template from the config to allow for customization
        ned_url_template = self.config.get("ned_search", {}).get("url_template", "https://ned.ipac.caltech.edu/conesearch?search_type=Near%20Position%20Search&in_csys=Equatorial&in_equinox=J2000&ra={ra}&dec={dec}&radius=1&Z_CONSTRAINT=Unconstrained")
        ned_url = ned_url_template.format(ra=ra_str, dec=dec_str)
        webbrowser.open(ned_url)     
        return
    
    def on_brightness_changed(self):
        """Handle brightness slider changes"""
        self.brightness_multiplier = self.brightness_slider.value() / 100.0
        self.brightness_label.setText(f"Brightness: {self.brightness_multiplier:.1f}")
        # Update image without triggering layout changes
        self._update_displayed_image()
    
    def on_contrast_changed(self):
        """Handle contrast slider changes"""
        self.contrast_multiplier = self.contrast_slider.value() / 100.0
        self.contrast_label.setText(f"Contrast: {self.contrast_multiplier:.1f}")
        # Update image without triggering layout changes
        self._update_displayed_image()
    
    def _update_displayed_image(self):
        """Update the currently displayed image with brightness/contrast applied"""
        current_file = self.jpg_files[self.current_index]
        
        # Determine which directory to use
        if self.secondary_dir_enabled and self.use_secondary_dir and self.secondary_dir_path:
            image_path = self.secondary_dir_path / current_file
        else:
            image_path = self.image_dir / current_file
        
        if self.dual_view_active and current_file in self.secondary_images:
            # Update dual view
            pixmap1 = QPixmap(str(image_path))
            pixmap2 = QPixmap(self.secondary_images[current_file])
            pixmap1 = self.apply_brightness_contrast(pixmap1)
            pixmap2 = self.apply_brightness_contrast(pixmap2)
            
            if not pixmap1.isNull() and not pixmap2.isNull():
                container_width = self.dual_view_container.width()
                width_per_image = int((container_width - 30) / 2)
                scaled_width = int(width_per_image * self.dual_view_zoom)
                scaled1 = pixmap1.scaledToWidth(scaled_width, Qt.SmoothTransformation)
                scaled2 = pixmap2.scaledToWidth(scaled_width, Qt.SmoothTransformation)
                self.dual_image_label_1.setPixmap(scaled1)
                self.dual_image_label_2.setPixmap(scaled2)
        else:
            # Update single view
            pixmap = QPixmap(str(image_path))
            pixmap = self.apply_brightness_contrast(pixmap)
            if not pixmap.isNull():
                base_width = int(600 * self.zoom_level)
                scaled_pixmap = pixmap.scaledToWidth(base_width, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
    
    def reset_brightness_contrast(self):
        """Reset brightness and contrast to original values"""
        self.brightness_multiplier = 1.0
        self.contrast_multiplier = 1.0
        self.brightness_slider.blockSignals(True)
        self.contrast_slider.blockSignals(True)
        self.brightness_slider.setValue(100)
        self.contrast_slider.setValue(100)
        self.brightness_label.setText("Brightness: 1.0")
        self.contrast_label.setText("Contrast: 1.0")
        self.brightness_slider.blockSignals(False)
        self.contrast_slider.blockSignals(False)
        self.display_secondary_view()
    
    def brightness_increase(self):
        """Increase brightness by 10%"""
        new_value = min(self.brightness_slider.value() + 10, 200)
        self.brightness_slider.blockSignals(True)
        self.brightness_slider.setValue(new_value)
        self.brightness_slider.blockSignals(False)
        self.brightness_multiplier = new_value / 100.0
        self.brightness_label.setText(f"Brightness: {self.brightness_multiplier:.1f}")
        self._update_displayed_image()
    
    def brightness_decrease(self):
        """Decrease brightness by 10%"""
        new_value = max(self.brightness_slider.value() - 10, 50)
        self.brightness_slider.blockSignals(True)
        self.brightness_slider.setValue(new_value)
        self.brightness_slider.blockSignals(False)
        self.brightness_multiplier = new_value / 100.0
        self.brightness_label.setText(f"Brightness: {self.brightness_multiplier:.1f}")
        self._update_displayed_image()
    
    def contrast_increase(self):
        """Increase contrast by 10%"""
        new_value = min(self.contrast_slider.value() + 10, 200)
        self.contrast_slider.blockSignals(True)
        self.contrast_slider.setValue(new_value)
        self.contrast_slider.blockSignals(False)
        self.contrast_multiplier = new_value / 100.0
        self.contrast_label.setText(f"Contrast: {self.contrast_multiplier:.1f}")
        self._update_displayed_image()
    
    def contrast_decrease(self):
        """Decrease contrast by 10%"""
        new_value = max(self.contrast_slider.value() - 10, 50)
        self.contrast_slider.blockSignals(True)
        self.contrast_slider.setValue(new_value)
        self.contrast_slider.blockSignals(False)
        self.contrast_multiplier = new_value / 100.0
        self.contrast_label.setText(f"Contrast: {self.contrast_multiplier:.1f}")
        self._update_displayed_image()
    
    def apply_brightness_contrast(self, pixmap):
        """Apply brightness and contrast adjustments to a pixmap"""
        if self.brightness_multiplier == 1.0 and self.contrast_multiplier == 1.0:
            return pixmap
        
        from PIL import Image, ImageEnhance
        
        # Convert QPixmap to QImage and ensure standard RGB format
        qimage = pixmap.toImage()
        
        # Convert to RGB888 format to ensure consistent byte order
        if qimage.format() != QImage.Format_RGB888:
            qimage = qimage.convertToFormat(QImage.Format_RGB888)
        
        width, height = qimage.width(), qimage.height()
        
        # Extract RGB data directly (3 bytes per pixel in standard RGB order)
        ptr = qimage.bits()
        ptr.setsize(qimage.byteCount())
        rgb_bytes = bytes(ptr)
        
        # Create PIL image from RGB bytes
        pil_image = Image.frombytes('RGB', (width, height), rgb_bytes)
        
        # Apply brightness
        brightness_enhancer = ImageEnhance.Brightness(pil_image)
        pil_image = brightness_enhancer.enhance(self.brightness_multiplier)
        
        # Apply contrast
        contrast_enhancer = ImageEnhance.Contrast(pil_image)
        pil_image = contrast_enhancer.enhance(self.contrast_multiplier)
        
        # Convert PIL image back to QImage
        rgb_data = pil_image.tobytes()
        qimage_new = QImage(rgb_data, width, height, 3 * width, QImage.Format_RGB888)
        return QPixmap.fromImage(qimage_new)
    
    def toggle_secondary_view(self):
        """Toggle between downloading secondary image or showing dual view"""
        current_file = self.jpg_files[self.current_index]
        
        # If we already have downloaded the secondary image, toggle visibility
        if current_file in self.secondary_images:
            self.dual_view_active = not self.dual_view_active
            # Reset dual-view zoom when toggling on
            if self.dual_view_active:
                self.dual_view_zoom = 1.0
                # Show dual-view container, hide single image container
                self.image_container.setVisible(False)
                self.dual_view_container.setVisible(True)
            else:
                # Show single image container, hide dual-view
                self.image_container.setVisible(True)
                self.dual_view_container.setVisible(False)
            self.display_secondary_view()
        else:
            # Set dual-view mode so it will display once download completes
            self.dual_view_active = True
            self.dual_view_zoom = 1.0
            self.image_container.setVisible(False)
            self.dual_view_container.setVisible(True)
            # Try to download the secondary image
            self.download_secondary_for_current()
    
    def download_secondary_for_current(self):
        """Download secondary image for current image's RA/Dec"""
        current_file = self.jpg_files[self.current_index]
        radec = parse_radec_from_filename(current_file)
        
        if radec is None:
            self.show_secondary_error("Could not parse RA/Dec from filename")
            return
        
        ra, dec = radec
        
        # Show progress bar
        self.download_progress_bar.setVisible(True)
        self.download_progress_bar.setValue(0)
        
        # Disable navigation keys and buttons during download
        self.downloading = True
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        
        # Create and start download worker thread
        self.download_worker = DownloadWorker(ra, dec, str(self.secondary_output_dir), self.config, current_file)
        self.download_worker.progress.connect(self.download_progress_bar.setValue)
        self.download_worker.finished.connect(self.on_secondary_download_success)
        self.download_worker.error.connect(self.show_secondary_error)
        self.download_worker.start()
    
    def on_secondary_download_success(self, image_path):
        """Handle successful secondary image download"""
        # Re-enable navigation
        self.downloading = False
        self.prev_button.setEnabled(True)
        self.next_button.setEnabled(True)
        
        current_file = self.jpg_files[self.current_index]
        self.secondary_images[current_file] = image_path
        
        # Hide progress bar and show success message
        self.download_progress_bar.setVisible(False)
        self.download_message_label.setVisible(True)
        self.download_message_label.setStyleSheet("color: green; font-weight: bold;")
        self.download_message_label.setText(f"✓ {self.secondary_name}")
        
        # Show dual view
        self.dual_view_active = True
        self.display_secondary_view()
        
        # Hide message after 5 seconds
        QTimer.singleShot(5000, lambda: self.download_message_label.setVisible(False))
    
    def show_secondary_error(self, error_msg):
        """Show secondary download error message"""
        # Re-enable navigation
        self.downloading = False
        self.prev_button.setEnabled(True)
        self.next_button.setEnabled(True)
        
        self.download_progress_bar.setVisible(False)
        self.download_message_label.setVisible(True)
        self.download_message_label.setStyleSheet("color: red; font-weight: bold;")
        self.download_message_label.setText(f"⚠ {error_msg}")
    
    def display_secondary_view(self):
        """Display secondary image alongside original or just original"""
        current_file = self.jpg_files[self.current_index]
        
        # Determine which directory to use for primary display
        if self.secondary_dir_enabled and self.use_secondary_dir and self.secondary_dir_path:
            primary_image_path = self.secondary_dir_path / current_file
        else:
            primary_image_path = self.image_dir / current_file
        
        if self.dual_view_active and current_file in self.secondary_images:
            # Load both images in separate containers
            pixmap1 = QPixmap(str(primary_image_path))
            pixmap2 = QPixmap(self.secondary_images[current_file])
            
            # Apply brightness and contrast
            pixmap1 = self.apply_brightness_contrast(pixmap1)
            pixmap2 = self.apply_brightness_contrast(pixmap2)
            
            if not pixmap1.isNull() and not pixmap2.isNull():
                # Calculate width for each image (equal size side-by-side)
                # Each image gets half the container width minus spacing
                container_width = self.dual_view_container.width()
                width_per_image = int((container_width - 30) / 2)  # 30px for spacing/margins
                
                # Scale both images by the same zoom level
                scaled_width = int(width_per_image * self.dual_view_zoom)
                scaled1 = pixmap1.scaledToWidth(scaled_width, Qt.SmoothTransformation)
                scaled2 = pixmap2.scaledToWidth(scaled_width, Qt.SmoothTransformation)
                
                # Display in separate labels
                self.dual_image_label_1.setPixmap(scaled1)
                self.dual_image_label_2.setPixmap(scaled2)
            else:
                self.dual_image_label_1.setText("Failed to load original")
                self.dual_image_label_2.setText(f"Failed to load {self.secondary_name}")
        else:
            # Just show original image in single container
            pixmap = QPixmap(str(primary_image_path))
            
            # Apply brightness and contrast
            pixmap = self.apply_brightness_contrast(pixmap)
            
            if pixmap.isNull():
                self.image_label.setText("Failed to load image")
            else:
                base_width = int(600 * self.zoom_level)
                scaled_pixmap = pixmap.scaledToWidth(base_width, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
    
    def update_table(self):
        """Update the rankings table - only update changed rows for speed"""
        # On first call, initialize all rows
        if not self.table_initialized:
            rows_to_update = set(range(len(self.jpg_files)))
            self.table_initialized = True
            # Initialize all row backgrounds on first call
            default_bg = QColor(30, 30, 30) if self.dark_mode else QColor(255, 255, 255)
            num_columns = 5 if self.secondary_enabled else 4
            for i in range(len(self.jpg_files)):
                for j in range(num_columns):
                    if self.table.item(i, j) is None:
                        self.table.setItem(i, j, QTableWidgetItem())
                    self.table.item(i, j).setBackground(default_bg)
        else:
            # Always update current row and previous row
            rows_to_update = set()
            rows_to_update.add(self.current_index)
            if self.previous_index >= 0 and self.previous_index != self.current_index:
                rows_to_update.add(self.previous_index)
        
        for i in rows_to_update:
            if i >= len(self.jpg_files):
                continue
                
            filename = self.jpg_files[i]
            
            # Filename
            name_item = QTableWidgetItem(filename)
            self.table.setItem(i, 0, name_item)
            
            # Rank
            rank = self.rankings.get(filename, "")
            rank_item = QTableWidgetItem(str(rank))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, rank_item)
            
            # Ranked? (checkmark)
            ranked_item = QTableWidgetItem("✓" if filename in self.rankings else "")
            ranked_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 2, ranked_item)
            
            # Comments (no truncation - columns are resizable)
            comment_text = self.comments.get(filename, "")
            comment_item = QTableWidgetItem(comment_text)
            self.table.setItem(i, 3, comment_item)
            
            # Secondary image indicator (checkmark if secondary image downloaded) - only if enabled
            if self.secondary_enabled:
                secondary_item = QTableWidgetItem("✓" if filename in self.secondary_images else "")
                secondary_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 4, secondary_item)
            
            # Highlight current row, unhighlight previous
            num_columns = 5 if self.secondary_enabled else 4
            text_color = QColor(255, 255, 255) if self.dark_mode else QColor(0, 0, 0)
            if i == self.current_index:
                highlight_color = QColor(70, 120, 180) if self.dark_mode else QColor(173, 216, 230)
                for j in range(num_columns):
                    self.table.item(i, j).setBackground(highlight_color)
                    self.table.item(i, j).setForeground(text_color)
            else:
                bg_color = QColor(30, 30, 30) if self.dark_mode else QColor(255, 255, 255)
                for j in range(num_columns):
                    self.table.item(i, j).setBackground(bg_color)
                    self.table.item(i, j).setForeground(text_color)
        
        # Force table repaint
        self.table.viewport().update()
        self.previous_index = self.current_index
        
        # Scroll to current row to keep it visible (unless navigating by click)
        if not self.skip_scroll:
            self.table.scrollToItem(self.table.item(self.current_index, 0), 
                                   self.table.PositionAtCenter)
        else:
            self.skip_scroll = False  # Reset flag for next navigation
    
    def submit_rank(self):
        """Submit a rank for the current image. Returns True if successful, False if invalid."""
        rank_str = self.rank_input.text().strip()
        is_valid, rank = is_valid_rank(rank_str, self.min_rank, self.max_rank, self.rank_config)
        
        if not is_valid:
            # Generate appropriate error message based on rank type
            if isinstance(self.min_rank, int) and isinstance(self.max_rank, int):
                error_msg = f"Please enter a number between {self.min_rank} and {self.max_rank}"
            else:
                # Use original config keys (not Qt Key objects)
                valid_keys = ", ".join(self.rank_config.keys()) if self.rank_config else "no ranks configured"
                error_msg = f"Please enter one of: {valid_keys}"
            QMessageBox.warning(self, "Invalid Input", error_msg)
            return False
        
        current_file = self.jpg_files[self.current_index]
        self.rankings[current_file] = rank
        self.rank_input.clear()
        
        # Batch saves: only save to disk every 10 ranks or on close
        self.save_counter += 1
        if self.save_counter >= 10:
            save_rankings(str(self.output_file), self.rankings, self.jpg_files, self.comments)
            self.save_counter = 0
        
        # Update table (only affected rows)
        self.update_table()
        return True
    
    def go_previous(self):
        """Go to previous image"""
        if self.current_index > 0:
            self.current_index -= 1
            self.display_image()
            # If in dual-view mode and new image doesn't have secondary image, download it
            if self.dual_view_active and self.secondary_enabled:
                self._ensure_secondary_for_current()
    
    def go_to_first(self):
        """Go to the first image in the list"""
        self.current_index = 0
        self.display_image()
        # If in dual-view mode and new image doesn't have secondary image, download it
        if self.dual_view_active and self.secondary_enabled:
            self._ensure_secondary_for_current()
    
    def go_next(self):
        """Go to next image"""
        if self.current_index < len(self.jpg_files) - 1:
            self.current_index += 1
            self.display_image()
            # If in dual-view mode and new image doesn't have secondary image, download it
            if self.dual_view_active and self.secondary_enabled:
                self._ensure_secondary_for_current()
    
    def _ensure_secondary_for_current(self):
        """Download secondary image for current image if not already present"""
        current_file = self.jpg_files[self.current_index]
        if current_file not in self.secondary_images:
            self.download_secondary_for_current()
    
    def toggle_list_visibility(self):
        """Toggle the visibility of the rankings list and reformat the window"""
        self.list_visible = not self.list_visible
        
        if self.list_visible:
            # Show the list and restore layout proportions
            self.table_container.setVisible(True)
            self.toggle_list_button.setText("Hide List")
            # Restore original proportions (2:1 ratio)
            self.main_layout.setStretch(0, 2)
            self.main_layout.setStretch(1, 1)
            # Restore original window size
            self.resize(1400, 760)
        else:
            # Hide the list and adjust layout to use full width for image viewer
            self.table_container.setVisible(False)
            self.toggle_list_button.setText("Show List")
            # Give all space to left layout
            self.main_layout.setStretch(0, 1)
            self.main_layout.setStretch(1, 0)
            # Resize window to fit just the image viewer
            self.resize(900, 760)
    
    def toggle_dark_mode(self):
        """Toggle between dark and light modes"""
        self.dark_mode = not self.dark_mode
        
        if self.dark_mode:
            self.dark_mode_button.setText("Light")
            self.apply_dark_stylesheet()
        else:
            self.dark_mode_button.setText("Dark")
            self.apply_light_stylesheet()
        
        # Update row colors for the new mode
        default_bg = QColor(30, 30, 30) if self.dark_mode else QColor(255, 255, 255)
        highlight_color = QColor(70, 120, 180) if self.dark_mode else QColor(173, 216, 230)
        text_color = QColor(255, 255, 255) if self.dark_mode else QColor(0, 0, 0)
        
        num_columns = 5 if self.secondary_enabled else 4
        for i in range(len(self.jpg_files)):
            if i == self.current_index:
                bg_color = highlight_color
            else:
                bg_color = default_bg
            
            for j in range(num_columns):
                if self.table.item(i, j) is not None:
                    self.table.item(i, j).setBackground(bg_color)
                    self.table.item(i, j).setForeground(text_color)
    
    def save_rankings_now(self):
        """Save rankings and comments to disk (without quitting)"""
        save_rankings(str(self.output_file), self.rankings, self.jpg_files, self.comments)
        self.save_counter = 0  # Reset counter
        print("Rankings file and rankings+comments file saved!")
        
        # Show success dialog for 5 seconds
        comments_file = str(self.output_file).rsplit('.', 1)[0] + '_comments.txt'
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Save Successful")
        dialog.setText(f"Successfully saved:\n\n{self.output_file}\n\n{comments_file}")
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.setDefaultButton(QMessageBox.Ok)
        
        # Auto-close after 5 seconds (5000 ms)
        timer = QTimer()
        timer.timeout.connect(dialog.close)
        timer.start(5000)
        
        dialog.exec_()
    
    def view_rankings(self):
        """Open a window to view the rankings files"""
        rankings_viewer = RankingsViewer(self, str(self.output_file), self.dark_mode)
        if self.dark_mode:
            rankings_viewer.setStyleSheet(self.styleSheet())
        rankings_viewer.exec_()
    
    def toggle_secondary_dir(self):
        """Toggle between primary and secondary directory images"""
        if not self.secondary_dir_enabled or not self.secondary_dir_path:
            self.show_secondary_error("Secondary directory is not enabled or configured in config")
            return
        
        self.use_secondary_dir = not self.use_secondary_dir
        self.display_image()
    
    def apply_dark_stylesheet(self):
        """Apply dark mode stylesheet to the application"""
        dark_stylesheet = """
            QMainWindow, QWidget, QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                padding: 2px;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                padding: 2px 4px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1d1d1d;
            }
            QTableWidget {
                background-color: #1e1e1e;
                gridline-color: #3d3d3d;
            }
            QTableWidget::item {
                color: #e0e0e0;
                padding: 2px;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #e0e0e0;
                padding: 2px 4px;
                border: 1px solid #3d3d3d;
            }
            QTextEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
            }
            QMessageBox {
                background-color: #1e1e1e;
            }
            QMessageBox QLabel {
                color: #e0e0e0;
            }
        """
        self.setStyleSheet(dark_stylesheet)
        # Also update any open dialogs
        if self.helper_window is not None:
            self.helper_window.setStyleSheet(dark_stylesheet)
    
    def apply_light_stylesheet(self):
        """Apply light mode stylesheet with rounded corners"""
        light_stylesheet = """
            QPushButton {
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                padding: 2px 4px;
                background-color: #f0f0f0;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
            QPushButton:pressed {
                background-color: #d8d8d8;
            }
            QLineEdit {
                border: 1px solid #c0c0c0;
                border-radius: 3px;
                padding: 2px;
                background-color: #ffffff;
            }
            QTextEdit {
                border: 1px solid #c0c0c0;
                border-radius: 3px;
                background-color: #ffffff;
            }
            QHeaderView::section {
                padding: 2px 4px;
                border: 1px solid #d0d0d0;
                background-color: #f0f0f0;
            }
        """
        self.setStyleSheet(light_stylesheet)
        # Also update any open dialogs
        if self.helper_window is not None:
            self.helper_window.setStyleSheet(light_stylesheet)
    
    def clear_rank(self):
        """Remove the rank for the current image"""
        current_file = self.jpg_files[self.current_index]
        if current_file in self.rankings:
            del self.rankings[current_file]
            # Save immediately
            save_rankings(str(self.output_file), self.rankings, self.jpg_files)
            # Update display
            self.display_image()
            self.update_table()
    
    def zoom_in(self):
        """Increase image zoom by 10%"""
        # If in dual-view, zoom the individual images; otherwise zoom container
        if self.dual_view_active:
            self.dual_view_zoom *= 1.1
        else:
            self.zoom_level *= 1.1
            # Allow container to expand up to 1400x1400 for zoomed views
            if self.zoom_level > 1.0:
                expanded_size = int(680 * self.zoom_level)
                expanded_size = min(expanded_size, 1400)  # Cap at 1400
                self.image_container.setMaximumHeight(expanded_size)
                self.image_container.setMaximumWidth(expanded_size)
        self._update_displayed_image()
    
    def zoom_out(self):
        """Decrease image zoom by 10%"""
        # If in dual-view, zoom the individual images; otherwise zoom container
        if self.dual_view_active:
            self.dual_view_zoom /= 1.1
        else:
            self.zoom_level /= 1.1
            # Shrink container back if zoom level allows
            if self.zoom_level <= 1.0:
                self.image_container.setMaximumHeight(self.original_container_height)
                self.image_container.setMaximumWidth(self.original_container_width)
            else:
                expanded_size = int(680 * self.zoom_level)
                expanded_size = min(expanded_size, 1400)
                self.image_container.setMaximumHeight(expanded_size)
                self.image_container.setMaximumWidth(expanded_size)
        self._update_displayed_image()
    
    def fit_image(self):
        """Fit the image to the image container"""
        if self.dual_view_active:
            self.dual_view_zoom = 1.0
        else:
            self.zoom_level = 1.0
        self._update_displayed_image()
    
    def reset_image_container(self):
        """Reset the image container to its original size"""
        self.image_container.setMaximumHeight(self.original_container_height)
        self.image_container.setMaximumWidth(self.original_container_width)
        self.zoom_level = 1.0
        self.dual_view_zoom = 1.0
        self._update_displayed_image()
    
    def toggle_helper(self):
        """Toggle the helper window"""
        self.helper_visible = not self.helper_visible
        
        if self.helper_visible:
            if self.helper_window is None:
                self.helper_window = HelperDialog(self)
                # Apply dark mode if active
                if self.dark_mode:
                    self.helper_window.setStyleSheet(self.styleSheet())
            self.helper_window.show()
        else:
            if self.helper_window is not None:
                self.helper_window.close()
    
    def skip_to_next_unranked(self):
        """Skip to next unranked image"""
        next_index = find_next_unranked(
            self.jpg_files, self.rankings, self.current_index + 1
        )
        
        if next_index == -1:
            QMessageBox.information(self, "All Ranked", "All images have been ranked!")
            return
        
        self.current_index = next_index
        self.display_image()
    
    def add_comment(self):
        """Add a comment to the current image"""
        current_file = self.jpg_files[self.current_index]
        
        # Create a simple input dialog
        text, ok = QInputDialog.getText(
            self, 
            "Add Comment", 
            f"Comment for {current_file}:",
            QLineEdit.Normal,
            self.comments.get(current_file, "")
        )
        
        if ok:
            if text:
                self.comments[current_file] = text
            elif current_file in self.comments:
                del self.comments[current_file]
            # Update the table to show the new comment
            self.update_table()
    
    def on_table_click(self, item):
        """Handle clicks on the table"""
        # Save pending rank before switching images
        if self.rank_input.text().strip():
            self.submit_rank()
        
        row = item.row()
        self.current_index = row
        self.skip_scroll = True  # Don't scroll to center on click navigation
        self.display_image()
    
    def keyPressEvent(self, event):
        """Handle keyboard events using configurable keys from config.json"""
        key = event.key()
        
        # Disable navigation keys during secondary image download
        if self.downloading and key in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down, Qt.Key_Return, Qt.Key_Enter]:
            return
        
        # Check rank keys first (from config.json "ranks" section)
        if self._check_rank_key(event):
            return  # Rank key was handled
        
        # Check each action against configured keys
        if self._key_matches_action(event, 'clear_input'):
            self.rank_input.clear()
        elif self._key_matches_action(event, 'quit'):
            self.close()
        elif self._key_matches_action(event, 'clear_rank'):
            self.clear_rank()
        elif self._key_matches_action(event, 'fit_image'):
            self.fit_image()
        elif self._key_matches_action(event, 'reset_container'):
            self.reset_image_container()
        elif self._key_matches_action(event, 'toggle_helper'):
            self.toggle_helper()
        elif self._key_matches_action(event, 'toggle_list'):
            self.toggle_list_visibility()
        elif self._key_matches_action(event, 'toggle_dark_mode'):
            self.toggle_dark_mode()
        elif self._key_matches_action(event, 'save'):
            self.save_rankings_now()
        elif self._key_matches_action(event, 'view_rankings'):
            self.view_rankings()
        elif self._key_matches_action(event, 'comment'):
            self.open_comment_dialog()
        elif self._key_matches_action(event, 'wise_toggle'):
            if self.secondary_enabled:
                self.toggle_secondary_view()
        elif self._key_matches_action(event, 'legacy_survey'):
            self.open_legacy_survey_viewer()
        elif self._key_matches_action(event, 'ned_search'):
            self.open_ned_search()
        elif self._key_matches_action(event, 'toggle_secondary_dir'):
            self.toggle_secondary_dir()
        elif self._key_matches_action(event, 'zoom_in'):
            self.zoom_in()
        elif self._key_matches_action(event, 'zoom_out'):
            self.zoom_out()
        elif self._key_matches_action(event, 'brightness_increase'):
            self.brightness_increase()
        elif self._key_matches_action(event, 'brightness_decrease'):
            self.brightness_decrease()
        elif self._key_matches_action(event, 'contrast_increase'):
            self.contrast_increase()
        elif self._key_matches_action(event, 'contrast_decrease'):
            self.contrast_decrease()
        elif self._key_matches_action(event, 'reset_brightness_contrast'):
            self.reset_brightness_contrast()
        elif self._key_matches_action(event, 'submit_and_next'):
            if self.submit_rank():  # Only navigate if rank submission was successful
                self.go_next()
        elif self._key_matches_action(event, 'first_image'):
            if self.rank_input.text().strip():
                if self.submit_rank():  # Only navigate if rank submission was successful
                    self.go_to_first()
            else:
                self.go_to_first()
        elif self._key_matches_action(event, 'skip_to_next_unranked'):
            if self.rank_input.text().strip():
                if self.submit_rank():  # Only navigate if rank submission was successful
                    self.skip_to_next_unranked()
            else:
                self.skip_to_next_unranked()
        elif self._key_matches_action(event, 'previous'):
            if self.rank_input.text().strip():
                if self.submit_rank():  # Only navigate if rank submission was successful
                    self.go_previous()
            else:
                self.go_previous()
        elif self._key_matches_action(event, 'next'):
            if self.rank_input.text().strip():
                if self.submit_rank():  # Only navigate if rank submission was successful
                    self.go_next()
            else:
                self.go_next()
        else:
            super().keyPressEvent(event)
    
    def _check_rank_key(self, event) -> bool:
        """Check if a key is mapped to a rank value and set input accordingly"""
        key = event.key()
        if key in self.rank_map:
            rank_value = self.rank_map[key]
            self.rank_input.setText(str(rank_value))
            
            # If auto-submit is enabled, submit the rank and go to next
            if self.auto_submit_checkbox.isChecked():
                self.submit_rank()
                self.go_next()
            
            return True
        return False
    
    def _key_matches_action(self, event, action_name):
        """Check if keyboard event matches a configured action"""
        key = event.key()
        has_shift = bool(event.modifiers() & Qt.ShiftModifier)  # Convert to boolean
        key_strings = self.keys.get(action_name, [])
        
        for key_str in key_strings:
            qt_keys = string_to_qt_key(key_str)
            for qt_key, needs_shift in qt_keys:
                if key == qt_key:
                    # Check shift modifier requirement
                    if needs_shift == has_shift:
                        return True
        return False
    
    def closeEvent(self, event):
        """Handle window close"""
        save_rankings(str(self.output_file), self.rankings, self.jpg_files, self.comments)
        event.accept()
    
    def _load_comments(self):
        """Load comments from the comments file (separate from rankings)"""
        self.comments = {}
        
        # Build the comments filename from the output file
        comments_file = self.output_file.parent / self.output_file.name.replace('.txt', '_comments.txt')
        
        if comments_file.exists():
            try:
                with open(comments_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line or '\t' not in line:
                            continue
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            filename = parts[0]
                            # parts[1] is the rank
                            comment = parts[2]
                            if comment:
                                self.comments[filename] = comment
            except Exception as e:
                print(f"Warning: Could not load comments: {e}")

    
    def open_comment_dialog(self):
        """Open dialog to add/edit comment for current image"""
        current_file = self.jpg_files[self.current_index]
        current_comment = self.comments.get(current_file, "")
        
        dialog = CommentDialog(self, current_comment)
        # Apply dark mode if active
        if self.dark_mode:
            dialog.setStyleSheet(self.styleSheet())
        if dialog.exec_() == QDialog.Accepted:
            new_comment = dialog.get_comment()
            if new_comment:
                self.comments[current_file] = new_comment
            elif current_file in self.comments:
                del self.comments[current_file]
            self.update_table()
    
    def on_table_double_click(self, item):
        """Handle double-click on table to edit comment"""
        column = item.column()
        row = item.row()
        
        # Only allow editing comments (column 3)
        if column == 3:
            self.current_index = row
            self.open_comment_dialog()


class RankingsViewer(QDialog):
    """Dialog to view rankings files with tabs to toggle between them"""
    
    def __init__(self, parent=None, output_file="rankings.txt", dark_mode=False):
        super().__init__(parent)
        self.output_file = output_file
        self.dark_mode = dark_mode
        self.comments_file = str(output_file).rsplit('.', 1)[0] + '_comments.txt'
        
        self.setWindowTitle("View Rankings")
        self.setGeometry(200, 200, 700, 500)
        
        layout = QVBoxLayout()
        
        # Create tab buttons
        button_layout = QHBoxLayout()
        
        self.rankings_button = QPushButton("Rankings")
        self.rankings_button.clicked.connect(self.show_rankings)
        self.rankings_button.setStyleSheet("background-color: #0078d4; color: white; padding: 5px;")
        button_layout.addWidget(self.rankings_button)
        
        self.comments_button = QPushButton("Rankings with Comments")
        self.comments_button.clicked.connect(self.show_comments)
        button_layout.addWidget(self.comments_button)
        
        layout.addLayout(button_layout)
        
        # Create text display area
        self.text_display = QPlainTextEdit()
        self.text_display.setReadOnly(True)
        font = QFont("Menlo", 10)
        self.text_display.setFont(font)
        # Set tab stop width for column alignment
        metrics = self.text_display.fontMetrics()
        tab_width = metrics.width(" " * 10)
        self.text_display.setTabStopDistance(tab_width)
        layout.addWidget(self.text_display)
        
        # Create close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
        
        # Load rankings by default
        self.show_rankings()
    
    def show_rankings(self):
        """Display rankings file"""
        try:
            with open(self.output_file, 'r') as f:
                content = f.read()
            self.text_display.setPlainText(content)
            self.rankings_button.setStyleSheet("background-color: #0078d4; color: white; padding: 5px;")
            self.comments_button.setStyleSheet("")
        except FileNotFoundError:
            self.text_display.setPlainText(f"File not found: {self.output_file}")
    
    def show_comments(self):
        """Display rankings with comments file"""
        try:
            with open(self.comments_file, 'r') as f:
                content = f.read()
            self.text_display.setPlainText(content)
            self.comments_button.setStyleSheet("background-color: #0078d4; color: white; padding: 5px;")
            self.rankings_button.setStyleSheet("")
        except FileNotFoundError:
            self.text_display.setPlainText(f"File not found: {self.comments_file}")


class HelperDialog(QDialog):
    """Helper dialog showing keyboard shortcuts and features"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Astrorank Helper")
        self.setGeometry(200, 200, 600, 500)
        
        layout = QVBoxLayout()
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setText("""
<h2>AstroRank Keyboard Shortcuts</h2><br>

<b>Image Navigation:</b><br>
• <b>← / ↑ / B</b> - Go to previous image<br>
• <b>→ / ↓</b> - Go to next image<br>
• <b>Shift+←</b> - Jump to first image<br>
• <b>Shift+→</b> - Skip to next unranked image<br>
<br>

<b>Ranking:</b><br>
• <b>0-3</b> - Enter rank (0=worst, 3=best)<br>
• <b>` (backtick)</b> or <b>Space</b> - Also works for rank 0 (easier key access)<br>
• <b>Enter/Return</b> - Submit rank and move to next image<br>
• <b>Delete/Backspace</b> - Clear input field<br>
• <b>C</b> - Clear rank for current image<br>
<br>

<b>Comments:</b><br>
• <b>K</b> - Open comment dialog for current image<br>
• Double-click a comment in the list to edit it<br>
<br>

<b>Brightness & Contrast:</b><br>
• <b>]</b> - Increase brightness<br>
• <b>[</b> - Decrease brightness<br>
• <b>'</b> - Increase contrast<br>
• <b>;</b> - Decrease contrast<br>
• <b>\</b> - Reset brightness and contrast to normal<br>
<br>

<b>Secondary Downloads:</b><br>
• <b>G</b> - Download secondary image for current coordinates (if enabled)<br>
• Press <b>G</b> again to toggle between single and dual view<br>
<br>

<b>Legacy Survey:</b><br>
• <b>W</b> - Open Legacy Survey viewer for current image coordinates<br>
<br>

<b>NED Search:</b><br>
• <b>N</b> - Open NED search for current image coordinates<br>
<br>

<b>Secondary Directory:</b><br>
• <b>E</b> - Toggle between primary and secondary directory images (if enabled)<br>
<br>

<b>Display:</b><br>
• <b>L</b> - Toggle image list panel visibility<br>
• <b>D</b> - Toggle dark mode<br>
• <b>F</b> - Fit image to container (reset zoom)<br>
• <b>R</b> - Reset image container to original size<br>
• <b>+</b> / <b>−</b> - Zoom image in/out (incremental)<br>
• <b>?</b> - Show/hide this helper window<br>
<br>

<b>Application:</b><br>
• <b>S</b> - Save<br>
• <b>V</b> - View rankings files (toggle between rankings and rankings with comments)<br>
• <b>Q</b> - Save and quit astrorank<br>
<br>

<p><i>Tip: Press a number key (or backtick/spacebar for 0) to fill the rank field, then use arrow keys to navigate—the rank will be submitted automatically.</i></p>
        """)
        
        layout.addWidget(help_text)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        
        self.setLayout(layout)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="astrorank - Image Ranking GUI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  astrorank /path/to/images
  astrorank /path/to/images -o my_rankings.txt
  astrorank /path/to/images -c /path/to/config.json
        """
    )
    
    parser.add_argument(
        "image_directory",
        help="Directory containing .jpg images to rank"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="rankings.txt",
        help="Output file for rankings (default: rankings.txt)"
    )
    
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Configuration file path (default: config.json)"
    )
    
    args = parser.parse_args()
    
    # Validate image directory
    image_dir = Path(args.image_directory)
    if not image_dir.exists():
        print(f"Error: Directory not found: {args.image_directory}")
        sys.exit(1)
    
    try:
        app = QApplication(sys.argv)
        
        # Set application name for macOS menu bar
        app.setApplicationName("AstroRank")
        app.setApplicationVersion("1.3")
        
        # Set application icon for better macOS dock/menu bar integration
        icon = get_astrorank_icon()
        app.setWindowIcon(icon)
        
        # Handle Ctrl+C gracefully
        def signal_handler(sig, frame):
            app.quit()
        
        signal.signal(signal.SIGINT, signal_handler)
        
        gui = AstrorankGUI(
            image_dir=str(image_dir),
            output_file=args.output,
            config_file=args.config
        )
        gui.show()
        sys.exit(app.exec_())
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
