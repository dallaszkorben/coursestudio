"""
Zoom Generation Progress Dialog - User feedback during generation.

Shows:
- Tile-count based progress (e.g., "1,245 / 5,000 tiles")
- Current zoom level being generated
- Estimated time remaining
- Cancel button for interruption
- Status messages

Usage:
    >>> dialog = ZoomGenerationProgressDialog(parent)
    >>> dialog.set_total_tiles(262144)
    >>> for completed, total in generator.generate_with_progress():
    ...     dialog.update_progress(completed, total)
    ...     if dialog.is_cancelled():
    ...         break
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont
import logging
import time

logger = logging.getLogger(__name__)


class ZoomGenerationProgressDialog(QDialog):
    """
    Modal dialog showing zoom level generation progress.
    
    Features:
    - Tile-count based progress display
    - Estimated time remaining
    - Cancel button with user confirmation
    - Status message area
    - Real-time updates
    """
    
    def __init__(self, parent=None, target_zoom=None, total_tiles=None):
        """
        Initialize progress dialog.
        
        Args:
            parent: Parent widget
            target_zoom: The zoom level being generated (e.g., 13)
            total_tiles: Total tiles to generate (e.g., 262144)
        """
        super().__init__(parent)
        
        self.target_zoom = target_zoom
        self.total_tiles = total_tiles or 0
        self.completed_tiles = 0
        self.cancelled = False
        self.start_time = None  # Unix timestamp
        
        self._setup_ui()
        self._setup_timer()
    
    def _setup_ui(self):
        """Create and layout UI components."""
        self.setWindowTitle(f"Generating Zoom Level {self.target_zoom}")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout()
        
        # Title
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title = QLabel(f"Generating Zoom Level {self.target_zoom}")
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel(f"Total tiles: {self.total_tiles:,}")
        layout.addWidget(subtitle)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(self.total_tiles if self.total_tiles > 0 else 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Progress info (tiles count)
        self.progress_label = QLabel("0 / 0 tiles")
        layout.addWidget(self.progress_label)
        
        # Time info
        time_layout = QHBoxLayout()
        self.elapsed_label = QLabel("Elapsed: 0s")
        self.time_remaining_label = QLabel("Remaining: --")
        self.speed_label = QLabel("Speed: 0 tiles/s")
        time_layout.addWidget(self.elapsed_label)
        time_layout.addWidget(self.time_remaining_label)
        time_layout.addWidget(self.speed_label)
        layout.addLayout(time_layout)
        
        # Status messages
        status_label = QLabel("Status Messages:")
        layout.addWidget(status_label)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
        layout.addWidget(self.status_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _setup_timer(self):
        """Setup timer for updating elapsed time."""
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_time_display)
        self.timer.start(500)  # Update every 500ms
    
    def _update_time_display(self):
        """Update elapsed time and estimate remaining."""
        if self.start_time is None or self.completed_tiles == 0:
            return
        
        # Calculate elapsed time using Unix timestamps
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        # Update elapsed
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        self.elapsed_label.setText(f"Elapsed: {mins}m {secs}s")
        
        # Calculate speed and estimate remaining
        if elapsed > 0:
            speed = self.completed_tiles / elapsed
            self.speed_label.setText(f"Speed: {speed:.0f} tiles/s")
            
            if speed > 0:
                remaining_tiles = self.total_tiles - self.completed_tiles
                remaining_secs = remaining_tiles / speed
                
                if remaining_secs < 60:
                    self.time_remaining_label.setText(
                        f"Remaining: {int(remaining_secs)}s"
                    )
                else:
                    remaining_mins = int(remaining_secs // 60)
                    remaining_secs = int(remaining_secs % 60)
                    self.time_remaining_label.setText(
                        f"Remaining: {remaining_mins}m {remaining_secs}s"
                    )
        
        # Update UI
        self.update()
    
    def start_generation(self, target_zoom, total_tiles):
        """
        Start tracking generation progress.
        
        Args:
            target_zoom: Zoom level being generated
            total_tiles: Total tiles to generate
        """
        self.target_zoom = target_zoom
        self.total_tiles = total_tiles
        self.completed_tiles = 0
        self.cancelled = False
        self.start_time = time.time()  # Use Unix timestamp
        
        self.setWindowTitle(f"Generating Zoom Level {target_zoom}")
        self.progress_bar.setMaximum(total_tiles)
        self.progress_bar.setValue(0)
        self.status_text.clear()
        
        self._add_status(f"Starting generation of Z{target_zoom}")
        self._add_status(f"Total tiles: {total_tiles:,}")
    
    def update_progress(self, completed, total):
        """
        Update progress display.
        
        Args:
            completed: Tiles completed so far
            total: Total tiles to generate
        """
        self.completed_tiles = completed
        self.total_tiles = total
        
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(completed)
        
        percentage = (completed / total * 100) if total > 0 else 0
        self.progress_label.setText(
            f"{completed:,} / {total:,} tiles ({percentage:.1f}%)"
        )
    
    def add_status_message(self, message):
        """
        Add status message to display.
        
        Args:
            message: Message to display
        """
        self._add_status(message)
    
    def _add_status(self, message):
        """
        Internal method to add status message.
        
        Args:
            message: Message text
        """
        self.status_text.append(message)
        # Auto-scroll to bottom
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )
    
    def is_cancelled(self):
        """
        Check if user clicked Cancel.
        
        Returns:
            True if cancelled, False otherwise
        """
        return self.cancelled
    
    def _on_cancel(self):
        """Handle Cancel button click."""
        self.cancelled = True
        self.cancel_button.setEnabled(False)
        self._add_status("Cancelling... please wait")
    
    def finish_success(self):
        """Mark generation as successfully completed."""
        self.timer.stop()
        self._add_status(f"✅ Successfully generated Z{self.target_zoom}!")
        self._add_status(f"Generated {self.completed_tiles:,} tiles")
        self.cancel_button.setText("Close")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.accept)
        self.cancel_button.setEnabled(True)
    
    def finish_error(self, error_message):
        """
        Mark generation as failed.
        
        Args:
            error_message: Error description
        """
        self.timer.stop()
        self._add_status(f"❌ Error: {error_message}")
        self.cancel_button.setText("Close")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setEnabled(True)
    
    def finish_cancelled(self):
        """Mark generation as cancelled by user."""
        self.timer.stop()
        self._add_status(f"⏹ Cancelled. Generated {self.completed_tiles:,} tiles.")
        self.cancel_button.setText("Close")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setEnabled(True)
