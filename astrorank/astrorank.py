"""
astrorank - Image Ranking GUI Application
"""

import sys
import signal
import argparse
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QTextEdit, QInputDialog
)
from PyQt5.QtGui import QPixmap, QColor, QFont, QIcon
from PyQt5.QtCore import Qt, QSize, QTimer

from astrorank.utils import (
    get_jpg_files, load_rankings, save_rankings,
    find_next_unranked, find_first_unranked, is_valid_rank
)
from astrorank.ui_utils import get_astrorank_icon


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
    def __init__(self, image_dir, output_file="rankings.txt"):
        super().__init__()
        
        self.image_dir = Path(image_dir)
        self.output_file = Path(output_file)
        self.previous_index = -1  # Track previous index for efficient updates
        self.save_counter = 0  # Batch saves every N rankings
        self.table_initialized = False  # Track if table has been populated
        self.list_visible = True  # Track list visibility state
        self.zoom_level = 1.0  # Track zoom level for images
        self.helper_visible = False  # Track helper window visibility
        self.helper_window = None  # Reference to helper dialog
        self.skip_scroll = False  # Skip scroll-to-center on click navigation
        self.dark_mode = False  # Track dark mode state
        
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
        
        # Image container - wraps filename label and image together
        image_container = QWidget()
        image_container_layout = QVBoxLayout()
        image_container_layout.setContentsMargins(0, 0, 0, 0)
        image_container_layout.setSpacing(0)
        
        # Image filename and ranking info
        self.image_info_label = QLabel()
        info_font = QFont()
        info_font.setPointSize(int(info_font.pointSize() * 1.5))
        self.image_info_label.setFont(info_font)
        self.image_info_label.setAlignment(Qt.AlignLeft)
        self.image_info_label.setTextFormat(Qt.RichText)
        self.image_info_label.setMaximumHeight(30)
        image_container_layout.addWidget(self.image_info_label)
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setStyleSheet("border: 1px solid black;")
        self.image_label.setAlignment(Qt.AlignCenter)
        image_container_layout.addWidget(self.image_label)
        
        image_container.setLayout(image_container_layout)
        image_container.setMaximumHeight(680)
        image_container.setMaximumWidth(680)
        
        # Wrapper for image container with zoom buttons
        image_wrapper = QHBoxLayout()
        image_wrapper.setContentsMargins(0, 0, 0, 0)
        image_wrapper.setSpacing(5)
        image_wrapper.addWidget(image_container, 0)
        
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
        
        zoom_layout.addStretch()
        image_wrapper.addLayout(zoom_layout)
        
        left_layout.addLayout(image_wrapper, 0)
        
        # Ranking input and buttons
        control_layout = QHBoxLayout()
        control_layout.setSpacing(3)
        
        # Create larger font (1.5x default)
        large_font = QFont()
        large_font.setPointSize(int(large_font.pointSize() * 1.5))
        
        rank_label = QLabel("Rank (0-3):")
        rank_label.setFont(large_font)
        control_layout.addWidget(rank_label)
        
        self.rank_input = QLineEdit()
        self.rank_input.setMaximumWidth(120)
        self.rank_input.setMinimumHeight(40)
        self.rank_input.setFont(large_font)
        self.rank_input.setAlignment(Qt.AlignCenter)
        self.rank_input.returnPressed.connect(self.submit_rank)
        control_layout.addWidget(self.rank_input)
        
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
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Filename", "Rank", "Ranked?", "Comments"])
        # Set all columns resizable independently
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)  # Filename resizable
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)  # Rank resizable
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)  # Ranked? resizable
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)  # Comments resizable
        # Set default column widths
        self.table.setColumnWidth(0, 200)  # Filename column
        self.table.setColumnWidth(1, 45)   # Rank column
        self.table.setColumnWidth(2, 65)   # Ranked? column
        self.table.setColumnWidth(3, 110)  # Comments column
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
        
        # Add layouts to main layout
        self.main_layout.addLayout(left_layout, 2)
        self.main_layout.addWidget(table_container, 1)
        
        main_container.addLayout(self.main_layout)
        main_widget.setLayout(main_container)
        
        # Set focus to main window so arrow keys work for navigation
        self.setFocus()
    
    def display_image(self):
        """Display the current image"""
        current_file = self.jpg_files[self.current_index]
        image_path = self.image_dir / current_file
        
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.image_label.setText("Failed to load image")
        else:
            # Scale to fit, maintaining aspect ratio, with zoom applied
            base_width = int(600 * self.zoom_level)
            scaled_pixmap = pixmap.scaledToWidth(base_width, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        
        # Update image info label with filename and previous ranking
        current_index_display = self.current_index + 1
        total_images = len(self.jpg_files)
        
        if current_file in self.rankings:
            rank = self.rankings[current_file]
            self.image_info_label.setText(f"<table width='100%'><tr><td>{current_file}</td><td align='right'>(Rank: {rank}) [{current_index_display}/{total_images}]</td></tr></table>")
        else:
            self.image_info_label.setText(f"<table width='100%'><tr><td>{current_file}</td><td align='right'>[{current_index_display}/{total_images}]</td></tr></table>")
        
        # Update window title
        self.setWindowTitle(f"imrank - {current_file}")
        
        # Clear rank input (but don't focus it - keep focus on main window for arrow keys)
        self.rank_input.clear()
        
        # Set focus to main window so arrow keys work for navigation
        self.setFocus()
        
        # Highlight current row in table
        self.update_table()
    
    def update_table(self):
        """Update the rankings table - only update changed rows for speed"""
        # On first call, initialize all rows
        if not self.table_initialized:
            rows_to_update = set(range(len(self.jpg_files)))
            self.table_initialized = True
            # Initialize all row backgrounds on first call
            default_bg = QColor(30, 30, 30) if self.dark_mode else QColor(255, 255, 255)
            for i in range(len(self.jpg_files)):
                for j in range(4):
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
            
            # Highlight current row, unhighlight previous
            if i == self.current_index:
                highlight_color = QColor(70, 120, 180) if self.dark_mode else QColor(173, 216, 230)
                for j in range(4):
                    self.table.item(i, j).setBackground(highlight_color)
            else:
                bg_color = QColor(30, 30, 30) if self.dark_mode else QColor(255, 255, 255)
                for j in range(4):
                    self.table.item(i, j).setBackground(bg_color)
        
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
        """Submit a rank for the current image"""
        rank_str = self.rank_input.text().strip()
        is_valid, rank = is_valid_rank(rank_str)
        
        if not is_valid:
            QMessageBox.warning(self, "Invalid Input", "Please enter a number between 0 and 3")
            return
        
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
    
    def go_previous(self):
        """Go to previous image"""
        if self.current_index > 0:
            self.current_index -= 1
            self.display_image()
    
    def go_to_first(self):
        """Go to the first image in the list"""
        self.current_index = 0
        self.display_image()
    
    def go_next(self):
        """Go to next image"""
        if self.current_index < len(self.jpg_files) - 1:
            self.current_index += 1
            self.display_image()
    
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
        else:
            # Hide the list and adjust layout to use full width for image viewer
            self.table_container.setVisible(False)
            self.toggle_list_button.setText("Show List")
            # Give all space to left layout
            self.main_layout.setStretch(0, 1)
            self.main_layout.setStretch(1, 0)
    
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
        
        for i in range(len(self.jpg_files)):
            if i == self.current_index:
                bg_color = highlight_color
            else:
                bg_color = default_bg
            
            for j in range(4):
                if self.table.item(i, j) is not None:
                    self.table.item(i, j).setBackground(bg_color)
    
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
        self.zoom_level *= 1.1
        self.display_image()
    
    def zoom_out(self):
        """Decrease image zoom by 10%"""
        self.zoom_level /= 1.1
        self.display_image()
    
    def fit_image(self):
        """Fit the image to the image container"""
        self.zoom_level = 1.0
        self.display_image()
    
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
        row = item.row()
        self.current_index = row
        self.skip_scroll = True  # Don't scroll to center on click navigation
        self.display_image()
    
    def keyPressEvent(self, event):
        """Handle keyboard events"""
        key = event.key()
        
        # Clear input on Delete or Backspace
        if key == Qt.Key_Delete or key == Qt.Key_Backspace:
            self.rank_input.clear()
        
        # Quit on Q or q
        elif key == Qt.Key_Q:
            self.close()
        
        # Clear rank on C or c
        elif key == Qt.Key_C:
            self.clear_rank()
        
        # Fit image on F or f
        elif key == Qt.Key_F:
            self.fit_image()
        
        # Toggle helper on ? (Shift+/)
        elif key == Qt.Key_Question:
            self.toggle_helper()
        
        # Toggle list visibility on L or l
        elif key == Qt.Key_L:
            self.toggle_list_visibility()
        
        # Toggle dark mode on D or d
        elif key == Qt.Key_D:
            self.toggle_dark_mode()
        
        # Comment on K or k
        elif key == Qt.Key_K:
            self.open_comment_dialog()
        
        # Zoom on + and -
        elif key == Qt.Key_Plus or key == Qt.Key_Equal:  # Equal is unshifted +
            self.zoom_in()
        
        elif key == Qt.Key_Minus:
            self.zoom_out()
        
        # Number keys (0-3) - just fill the input field
        # Backtick (`) also works as 0 for ergonomic reasons
        elif Qt.Key_0 <= key <= Qt.Key_3:
            digit = chr(key)
            self.rank_input.setText(digit)
        elif key == Qt.Key_QuoteLeft:  # Backtick key (`)
            self.rank_input.setText("0")
        
        # Enter key - submit rank and move to next
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            self.submit_rank()
            self.go_next()
        
        # Arrow keys - submit if rank entered, then navigate
        elif key == Qt.Key_Left or key == Qt.Key_Up:
            # Shift+Left goes to first image
            if event.modifiers() & Qt.ShiftModifier:
                if self.rank_input.text().strip():
                    self.submit_rank()
                else:
                    self.go_to_first()
            else:
                if self.rank_input.text().strip():
                    self.submit_rank()
                self.go_previous()
        elif key == Qt.Key_Right or key == Qt.Key_Down:
            # Check for Shift modifier for skip behavior
            if event.modifiers() & Qt.ShiftModifier:
                if self.rank_input.text().strip():
                    self.submit_rank()
                else:
                    self.skip_to_next_unranked()
            else:
                if self.rank_input.text().strip():
                    self.submit_rank()
                self.go_next()
        else:
            super().keyPressEvent(event)
    
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
<h2>Astrorank Keyboard Shortcuts</h2>

<b>Image Navigation:</b><br>
• <b>← / ↑</b> - Go to previous image<br>
• <b>→ / ↓</b> - Go to next image<br>
• <b>Shift+←</b> - Jump to first image<br>
• <b>Shift+→</b> - Skip to next unranked image<br>
<br>

<b>Ranking:</b><br>
• <b>0-3</b> - Enter rank (0=worst, 3=best)<br>
• <b>` (backtick)</b> - Also works for rank 0 (easier key access)<br>
• <b>Enter/Return</b> - Submit rank and move to next image<br>
• <b>Delete/Backspace</b> - Clear input field<br>
• <b>C</b> - Clear rank for current image<br>
<br>

<b>Comments:</b><br>
• <b>K</b> - Open comment dialog for current image<br>
• Double-click a comment in the list to edit it<br>
<br>

<b>Display:</b><br>
• <b>L</b> - Toggle image list panel visibility<br>
• <b>D</b> - Toggle dark mode<br>
• <b>+</b> / <b>−</b> - Zoom image in/out (incremental)<br>
• <b>F</b> - Fit image to container (reset zoom)<br>
• <b>?</b> - Show/hide this helper window<br>
<br>

<b>Application:</b><br>
• <b>Q</b> - Quit astrorank<br>
<br>

<p><i>Tip: Press a number key (or backtick for 0) to fill the rank field, then use arrow keys to navigate—the rank will be submitted automatically.</i></p>
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
    
    args = parser.parse_args()
    
    # Validate image directory
    image_dir = Path(args.image_directory)
    if not image_dir.exists():
        print(f"Error: Directory not found: {args.image_directory}")
        sys.exit(1)
    
    try:
        app = QApplication(sys.argv)
        
        # Handle Ctrl+C gracefully
        def signal_handler(sig, frame):
            app.quit()
        
        signal.signal(signal.SIGINT, signal_handler)
        
        gui = AstrorankGUI(
            image_dir=str(image_dir),
            output_file=args.output
        )
        gui.show()
        sys.exit(app.exec_())
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
