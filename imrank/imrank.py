"""
imrank - Image Ranking GUI Application
"""

import sys
import argparse
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PyQt5.QtGui import QPixmap, QColor, QFont, QIcon
from PyQt5.QtCore import Qt, QSize, QTimer

from imrank.utils import (
    get_jpg_files, load_rankings, save_rankings,
    find_next_unranked, find_first_unranked, is_valid_rank
)


class ImrankGUI(QMainWindow):
    def __init__(self, image_dir, output_file="rankings.txt", resume=False):
        super().__init__()
        
        self.image_dir = Path(image_dir)
        self.output_file = Path(output_file)
        
        # Load image files and rankings
        self.jpg_files = get_jpg_files(str(self.image_dir))
        if not self.jpg_files:
            raise ValueError(f"No .jpg files found in {self.image_dir}")
        
        self.rankings = load_rankings(str(self.output_file))
        
        # Determine starting image
        if resume:
            self.current_index = find_first_unranked(self.jpg_files, self.rankings)
        else:
            self.current_index = 0
        
        self.init_ui()
        self.display_image()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("imrank - Image Ranking Tool")
        self.setGeometry(100, 100, 1400, 800)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout()
        
        # Left side: Image viewer and controls
        left_layout = QVBoxLayout()
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setMinimumSize(600, 600)
        self.image_label.setStyleSheet("border: 1px solid black;")
        self.image_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.image_label)
        
        # Ranking input and buttons
        control_layout = QHBoxLayout()
        
        rank_label = QLabel("Rank (0-3):")
        control_layout.addWidget(rank_label)
        
        self.rank_input = QLineEdit()
        self.rank_input.setMaximumWidth(60)
        self.rank_input.setAlignment(Qt.AlignCenter)
        self.rank_input.returnPressed.connect(self.submit_rank)
        control_layout.addWidget(self.rank_input)
        
        # Navigation buttons
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.clicked.connect(self.go_previous)
        control_layout.addWidget(self.prev_button)
        
        self.next_button = QPushButton("Next ▶")
        self.next_button.clicked.connect(self.go_next)
        control_layout.addWidget(self.next_button)
        
        self.skip_button = QPushButton("Skip to Next Unranked ⏭")
        self.skip_button.clicked.connect(self.skip_to_next_unranked)
        control_layout.addWidget(self.skip_button)
        
        control_layout.addStretch()
        left_layout.addLayout(control_layout)
        
        # Right side: Image list table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Filename", "Rank", "Ranked?"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setRowCount(len(self.jpg_files))
        self.table.itemClicked.connect(self.on_table_click)
        
        # Populate table
        self.update_table()
        
        # Add layouts to main layout
        main_layout.addLayout(left_layout, 2)
        main_layout.addWidget(self.table, 1)
        
        main_widget.setLayout(main_layout)
        
        # Connect keyboard events
        self.rank_input.setFocus()
    
    def display_image(self):
        """Display the current image"""
        current_file = self.jpg_files[self.current_index]
        image_path = self.image_dir / current_file
        
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.image_label.setText("Failed to load image")
        else:
            # Scale to fit, maintaining aspect ratio
            scaled_pixmap = pixmap.scaledToWidth(600, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        
        # Update window title
        self.setWindowTitle(f"imrank - {current_file}")
        
        # Clear rank input
        self.rank_input.clear()
        self.rank_input.setFocus()
        
        # Highlight current row in table
        self.update_table()
    
    def update_table(self):
        """Update the rankings table"""
        for i, filename in enumerate(self.jpg_files):
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
            
            # Highlight current row
            if i == self.current_index:
                for j in range(3):
                    self.table.item(i, j).setBackground(QColor(173, 216, 230))  # Light blue
            else:
                for j in range(3):
                    self.table.item(i, j).setBackground(QColor(255, 255, 255))  # White
    
    def submit_rank(self):
        """Submit a rank for the current image"""
        rank_str = self.rank_input.text().strip()
        is_valid, rank = is_valid_rank(rank_str)
        
        if not is_valid:
            QMessageBox.warning(self, "Invalid Input", "Please enter a number between 0 and 3")
            return
        
        current_file = self.jpg_files[self.current_index]
        self.rankings[current_file] = rank
        
        # Save rankings
        save_rankings(str(self.output_file), self.rankings, self.jpg_files)
        
        # Update table
        self.update_table()
        
        # Move to next image
        self.go_next()
    
    def go_previous(self):
        """Go to previous image"""
        if self.current_index > 0:
            self.current_index -= 1
            self.display_image()
    
    def go_next(self):
        """Go to next image"""
        if self.current_index < len(self.jpg_files) - 1:
            self.current_index += 1
            self.display_image()
    
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
    
    def on_table_click(self, item):
        """Handle clicks on the table"""
        row = item.row()
        self.current_index = row
        self.display_image()
    
    def keyPressEvent(self, event):
        """Handle keyboard events"""
        key = event.key()
        
        # Number keys (0-3)
        if Qt.Key_0 <= key <= Qt.Key_3:
            digit = chr(key)
            self.rank_input.setText(digit)
            self.submit_rank()
        
        # Arrow keys
        elif key == Qt.Key_Left or key == Qt.Key_Up:
            self.go_previous()
        elif key == Qt.Key_Right or key == Qt.Key_Down:
            # Check for Shift modifier
            if event.modifiers() & Qt.ShiftModifier:
                self.skip_to_next_unranked()
            else:
                self.go_next()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """Handle window close"""
        save_rankings(str(self.output_file), self.rankings, self.jpg_files)
        event.accept()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="imrank - Image Ranking GUI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  imrank /path/to/images
  imrank /path/to/images -o my_rankings.txt
  imrank /path/to/images -o my_rankings.txt -c
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
        "-c", "--continue",
        action="store_true",
        dest="resume",
        help="Resume from the first unranked image"
    )
    
    args = parser.parse_args()
    
    # Validate image directory
    image_dir = Path(args.image_directory)
    if not image_dir.exists():
        print(f"Error: Directory not found: {args.image_directory}")
        sys.exit(1)
    
    try:
        app = QApplication(sys.argv)
        gui = ImrankGUI(
            image_dir=str(image_dir),
            output_file=args.output,
            resume=args.resume
        )
        gui.show()
        sys.exit(app.exec_())
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
