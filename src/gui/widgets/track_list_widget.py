"""
Track List Widget for mangpx.

Displays a list of all loaded GPX tracks with key information (name, distance,
point count, segment count). Allows track selection and provides context menu
for track operations.

Classes:
    - TrackListWidget: Main track list display widget
    - TrackListModel: Data model for track list
    - TrackListItem: Individual track item representation

Example:
    >>> from PyQt5.QtWidgets import QApplication
    >>> from src.gui.widgets.track_list_widget import TrackListWidget
    >>> from src.core.track_manager import TrackManager
    >>> 
    >>> app = QApplication([])
    >>> manager = TrackManager()
    >>> widget = TrackListWidget(manager)
    >>> widget.show()
"""

import logging
from typing import Optional, List

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QHeaderView, QAbstractItemView, QMenu
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, pyqtSignal, QSize

from src.core.track_manager import TrackManager, TrackData


# ============================================================================
# Logging
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# Track List Widget
# ============================================================================

class TrackListWidget(QWidget):
    """
    Widget displaying a list of all loaded GPX tracks.
    
    Features:
    - Display track name, distance, point count, segment count
    - Select/deselect tracks
    - Context menu for track operations
    - Real-time update when tracks change
    - Visual feedback for selected track
    
    Signals:
        track_selected: Emitted when user selects a track
        track_double_clicked: Emitted when user double-clicks a track
        track_right_clicked: Emitted when user right-clicks a track
    
    Example:
        >>> manager = TrackManager()
        >>> widget = TrackListWidget(manager)
        >>> widget.track_selected.connect(on_track_selected)
        >>> widget.refresh_tracks()
        >>> widget.show()
    """
    
    # Signals
    track_selected = pyqtSignal(int)  # Emitted with track index
    track_double_clicked = pyqtSignal(int)  # Emitted with track index
    track_right_clicked = pyqtSignal(int, QMenu)  # Emitted with track index and menu
    
    def __init__(self, track_manager: TrackManager):
        """
        Initialize Track List Widget.
        
        Args:
            track_manager (TrackManager): Reference to track manager
        
        Example:
            >>> manager = TrackManager()
            >>> widget = TrackListWidget(manager)
        """
        
        super().__init__()
        
        self.track_manager = track_manager
        self.current_selection = -1
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
        
        logger.info("TrackListWidget initialized")
    
    # ========================================================================
    # UI Setup
    # ========================================================================
    
    def _setup_ui(self):
        """Setup the user interface."""
        
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Header section
        header_layout = QHBoxLayout()
        
        # Title label
        title_label = QLabel("Tracks")
        title_font = title_label.font()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # Track count label
        self.count_label = QLabel("(0 tracks)")
        header_layout.addWidget(self.count_label)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.setMinimumHeight(200)
        
        main_layout.addWidget(self.list_widget)
        
        # Button section
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setToolTip("Refresh track list")
        button_layout.addWidget(self.refresh_button)
        
        self.clear_button = QPushButton("Clear Selection")
        self.clear_button.setToolTip("Clear current selection")
        button_layout.addWidget(self.clear_button)
        
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect internal signals."""
        
        # List widget signals
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        
        # Button signals
        self.refresh_button.clicked.connect(self.refresh_tracks)
        self.clear_button.clicked.connect(self.clear_selection)
    
    # ========================================================================
    # Track Display
    # ========================================================================
    
    def refresh_tracks(self):
        """
        Refresh the track list from track manager.
        
        Clears current list and populates with all tracks from manager.
        Preserves selection if the same track is still available.
        """
        
        # Store current selection
        old_index = self.current_selection
        
        # Clear list
        self.list_widget.clear()
        
        # Get all tracks from manager
        tracks = self.track_manager.get_all_tracks()
        
        # Populate list
        for i, track in enumerate(tracks):
            item_text = self._format_track_item(track)
            item = QListWidgetItem(item_text)
            
            # Store track index as data
            item.setData(Qt.UserRole, i)
            
            # Set selection mode
            if i == old_index:
                item.setSelected(True)
            
            self.list_widget.addItem(item)
        
        # Update count label
        count = len(tracks)
        self.count_label.setText(f"({count} track{'s' if count != 1 else ''})")
        
        logger.debug(f"Refreshed track list: {count} tracks")
    
    def _format_track_item(self, track: TrackData) -> str:
        """
        Format track information for display.
        
        Args:
            track (TrackData): Track to format
        
        Returns:
            str: Formatted track string
        
        Example:
            >>> track = TrackData(name="Test", distance_km=10.5, trackpoints=[...])
            >>> text = widget._format_track_item(track)
            >>> print(text)
            "Test - 10.50 km (5 points)"
        """
        
        name = track.name
        distance = track.distance_km
        points = track.get_point_count()
        
        return f"{name} - {distance:.2f} km ({points} points)"
    
    # ========================================================================
    # Selection Management
    # ========================================================================
    
    def select_track(self, track_index: int) -> bool:
        """
        Select a track by index.
        
        Args:
            track_index (int): Index of track to select (0-based)
        
        Returns:
            bool: True if selected successfully, False otherwise
        
        Example:
            >>> widget.select_track(2)
            True
        """
        
        if not 0 <= track_index < self.list_widget.count():
            logger.warning(f"Invalid track index: {track_index}")
            return False
        
        item = self.list_widget.item(track_index)
        if item:
            self.list_widget.setCurrentItem(item)
            self.current_selection = track_index
            return True
        
        return False
    
    def get_selected_track_index(self) -> int:
        """
        Get currently selected track index.
        
        Returns:
            int: Track index, or -1 if none selected
        """
        
        return self.current_selection
    
    def is_track_selected(self) -> bool:
        """Check if a track is currently selected."""
        
        return self.current_selection >= 0
    
    def clear_selection(self):
        """Clear current track selection."""
        
        self.list_widget.clearSelection()
        self.current_selection = -1
        
        logger.debug("Track selection cleared")
    
    # ========================================================================
    # Signal Handlers
    # ========================================================================
    
    def _on_selection_changed(self):
        """Handle selection change in list widget."""
        
        current_item = self.list_widget.currentItem()
        
        if current_item:
            # Clear background color of all items first
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item:
                    item.setBackground(QColor())  # Reset to default (white/transparent)
            
            # Get track index from item data
            track_index = current_item.data(Qt.UserRole)
            self.current_selection = track_index
            
            # Highlight selected item with blue background
            current_item.setBackground(QColor(200, 220, 255))
            
            # Emit signal
            self.track_selected.emit(track_index)
            
            logger.debug(f"Track selected: index={track_index}")
        else:
            self.current_selection = -1
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on track item."""
        
        track_index = item.data(Qt.UserRole)
        self.track_double_clicked.emit(track_index)
        
        logger.debug(f"Track double-clicked: index={track_index}")
    
    def _on_context_menu(self, position):
        """Handle right-click context menu."""
        
        item = self.list_widget.itemAt(position)
        
        if item:
            track_index = item.data(Qt.UserRole)
            
            # Create context menu
            menu = QMenu()
            menu.addAction("Rename", lambda: self._action_rename_track(track_index))
            menu.addAction("Delete", lambda: self._action_delete_track(track_index))
            menu.addSeparator()
            menu.addAction("Recalculate Distance", lambda: self._action_recalculate_distance(track_index))
            
            # Emit signal with menu
            self.track_right_clicked.emit(track_index, menu)
            
            # Show menu
            menu.exec_(self.list_widget.mapToGlobal(position))
    
    # ========================================================================
    # Context Menu Actions
    # ========================================================================
    
    def _action_rename_track(self, track_index: int):
        """Action: Rename track."""
        logger.debug(f"Rename track action: index={track_index}")
        # Will be implemented in future steps with edit dialogs
    
    def _action_delete_track(self, track_index: int):
        """Action: Delete track."""
        logger.debug(f"Delete track action: index={track_index}")
        # Will be implemented in future steps with confirmation dialogs
    
    def _action_recalculate_distance(self, track_index: int):
        """Action: Recalculate track distance."""
        logger.debug(f"Recalculate distance action: index={track_index}")
        # Will be implemented in future steps
    
    # ========================================================================
    # Updates
    # ========================================================================
    
    def update_track_info(self, track_index: int):
        """
        Update display for a specific track.
        
        Args:
            track_index (int): Index of track to update
        """
        
        track = self.track_manager.get_track_by_index(track_index)
        
        if track and 0 <= track_index < self.list_widget.count():
            item = self.list_widget.item(track_index)
            item_text = self._format_track_item(track)
            item.setText(item_text)
            
            logger.debug(f"Updated track info: index={track_index}")
    
    def highlight_track(self, track_index: int):
        """
        Highlight a track without changing selection.
        
        Args:
            track_index (int): Index of track to highlight
        """
        
        if 0 <= track_index < self.list_widget.count():
            item = self.list_widget.item(track_index)
            item.setBackground(QColor(255, 255, 200))  # Light yellow
    
    def remove_highlight(self, track_index: int):
        """
        Remove highlight from a track.
        
        Args:
            track_index (int): Index of track to unhighlight
        """
        
        if 0 <= track_index < self.list_widget.count():
            item = self.list_widget.item(track_index)
            item.setBackground(QColor())  # Default background


# ============================================================================
# Track List Model (for potential future use with MVC pattern)
# ============================================================================

class TrackListModel:
    """
    Data model for track list (prepared for future MVC implementation).
    
    Provides a structured interface to track data that could be used
    with Qt's MVC classes in the future.
    """
    
    def __init__(self, track_manager: TrackManager):
        """
        Initialize track list model.
        
        Args:
            track_manager (TrackManager): Reference to track manager
        """
        
        self.track_manager = track_manager
    
    def get_track_count(self) -> int:
        """Get total number of tracks."""
        return self.track_manager.get_track_count()
    
    def get_track_display_name(self, index: int) -> str:
        """
        Get formatted display name for track.
        
        Args:
            index (int): Track index
        
        Returns:
            str: Formatted track name with info
        """
        
        track = self.track_manager.get_track_by_index(index)
        if track:
            return f"{track.name} - {track.distance_km:.2f} km ({track.get_point_count()} points)"
        return ""
    
    def get_track_data(self, index: int) -> Optional[TrackData]:
        """
        Get track data object.
        
        Args:
            index (int): Track index
        
        Returns:
            Optional[TrackData]: Track object or None
        """
        
        return self.track_manager.get_track_by_index(index)
