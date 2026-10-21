"""
Prune Points Progress Dialog - User feedback during trackpoint pruning.

Shows:
- Progress bar indicating points processed
- Current point being checked
- Count of removed/kept points
- Cancel button to stop pruning
- Status messages

Usage:
    >>> dialog = PruneProgressDialog(parent)
    >>> dialog.start_pruning(total_points)
    >>> for i in range(total_points):
    ...     if dialog.is_cancelled():
    ...         break
    ...     dialog.update_progress(i, removed_count, kept_count)
    >>> dialog.finish_success(removed_count)
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class PruneProgressDialog(QDialog):
    """
    Modal dialog showing trackpoint pruning progress.
    
    Features:
    - Progress bar showing points processed
    - Point count statistics (total, removed, kept)
    - Cancel button to stop pruning
    - Status message area
    - Real-time updates
    """
    
    def __init__(self, parent=None, total_points=None):
        """
        Initialize prune progress dialog.
        
        Args:
            parent: Parent widget
            total_points: Total trackpoints to process (e.g., 1000)
        """
        super().__init__(parent)
        
        self.total_points = total_points or 0
        self.processed_points = 0
        self.removed_count = 0
        self.kept_count = 0
        self.cancelled = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create and layout UI components."""
        self.setWindowTitle("Pruning Trackpoints")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(250)
        
        layout = QVBoxLayout()
        
        # Title
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title = QLabel("Pruning Trackpoints")
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Info line
        self.info_label = QLabel(f"Total points: {self.total_points}")
        layout.addWidget(self.info_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(self.total_points if self.total_points > 0 else 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Stats line
        self.stats_label = QLabel("Processed: 0 points | Removed: 0 | Kept: 0")
        layout.addWidget(self.stats_label)
        
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
    
    def start_pruning(self, total_points):
        """
        Start tracking pruning progress.
        
        Args:
            total_points: Total trackpoints to process
        """
        self.total_points = total_points
        self.processed_points = 0
        self.removed_count = 0
        self.kept_count = 0
        self.cancelled = False
        
        self.setWindowTitle("Pruning Trackpoints")
        self.progress_bar.setMaximum(total_points)
        self.progress_bar.setValue(0)
        self.info_label.setText(f"Total points: {total_points}")
        self.stats_label.setText("Processed: 0 points | Removed: 0 | Kept: 0")
        self.status_text.clear()
        
        self._add_status(f"Starting pruning process...")
        self._add_status(f"Processing {total_points} trackpoints...")
    
    def update_progress(self, processed, removed, kept):
        """
        Update progress display.
        
        Args:
            processed: Number of points processed so far
            removed: Number of points removed
            kept: Number of points kept
        """
        self.processed_points = processed
        self.removed_count = removed
        self.kept_count = kept
        
        self.progress_bar.setValue(processed)
        self.stats_label.setText(
            f"Processed: {processed} points | Removed: {removed} | Kept: {kept}"
        )
        
        # Update UI to show progress
        self.update()
    
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
        self._add_status("Stopping... please wait")
    
    def finish_success(self, removed_count):
        """Mark pruning as successfully completed."""
        self.progress_bar.setValue(self.total_points)  # Show 100%
        self._add_status(f"✅ Successfully pruned {removed_count} point(s)!")
        self.cancel_button.setText("Close")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.accept)
        self.cancel_button.setEnabled(True)
    
    def finish_error(self, error_message):
        """
        Mark pruning as failed.
        
        Args:
            error_message: Error description
        """
        self._add_status(f"❌ Error: {error_message}")
        self.cancel_button.setText("Close")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setEnabled(True)
    
    def finish_cancelled(self):
        """Mark pruning as cancelled by user."""
        self._add_status(f"⏹ Cancelled. Processed {self.processed_points} points, removed {self.removed_count}.")
        self.cancel_button.setText("Close")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setEnabled(True)
