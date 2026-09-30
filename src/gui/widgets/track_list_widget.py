"""
Track List Widget for CourseStudio.

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
    QLabel, QPushButton, QHeaderView, QAbstractItemView, QMenu, QLineEdit
)
from PyQt5.QtGui import QFont, QIcon, QColor, QBrush
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
        
        # Inline editing state
        self.editing_track_index = -1
        self.edit_line_edit = None
        self.original_track_name = None
        
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
        
        self.add_track_button = QPushButton("+")
        self.add_track_button.setToolTip("Create new empty track")
        self.add_track_button.setMaximumWidth(40)
        button_layout.addWidget(self.add_track_button)
        
        self.delete_track_button = QPushButton("-")
        self.delete_track_button.setToolTip("Delete selected track")
        self.delete_track_button.setMaximumWidth(40)
        self.delete_track_button.setEnabled(False)  # Inactive by default
        button_layout.addWidget(self.delete_track_button)
        
        self.unselect_track_button = QPushButton("X")
        self.unselect_track_button.setToolTip("Unselect track")
        self.unselect_track_button.setMaximumWidth(40)
        self.unselect_track_button.setEnabled(False)  # Inactive by default
        button_layout.addWidget(self.unselect_track_button)
        
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect internal signals."""
        
        # List widget signals
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        
        # Button signals
        self.add_track_button.clicked.connect(self._on_add_track_clicked)
        self.delete_track_button.clicked.connect(self._on_delete_track_clicked)
        self.unselect_track_button.clicked.connect(self._on_unselect_track_clicked)
    
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
        
        # Clear both selection and current item to completely deselect
        self.list_widget.setCurrentItem(None)
        self.list_widget.clearSelection()
        self.current_selection = -1
        
        # Disable delete and unselect buttons
        self.delete_track_button.setEnabled(False)
        self.unselect_track_button.setEnabled(False)
        
        # Emit signal to notify that no track is selected
        self.track_selected.emit(-1)
        
        logger.debug("Track selection cleared")
    
    # ========================================================================
    # Signal Handlers
    # ========================================================================
    
    def _on_selection_changed(self):
        """Handle selection change in list widget."""
        
        current_item = self.list_widget.currentItem()
        
        if current_item:
            # Get track index from item data
            track_index = current_item.data(Qt.UserRole)
            self.current_selection = track_index
            
            # Enable delete and unselect buttons
            self.delete_track_button.setEnabled(True)
            self.unselect_track_button.setEnabled(True)
            
            # Emit signal
            self.track_selected.emit(track_index)
            
            logger.debug(f"Track selected: index={track_index}")
        else:
            self.current_selection = -1
            
            # Disable delete and unselect buttons
            self.delete_track_button.setEnabled(False)
            self.unselect_track_button.setEnabled(False)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on track item to enter edit mode."""
        
        track_index = item.data(Qt.UserRole)
        track = self.track_manager.get_track_by_index(track_index)
        
        if not track:
            return
        
        # Start inline editing
        self._start_inline_edit(track_index, track.name, item)
    
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
    
    def _on_add_track_clicked(self):
        """Handle '+' button click to create a new track."""
        
        # Create a new track with default name
        from src.core.track_manager import TrackData
        track_count = len(self.track_manager.get_all_tracks())
        new_track = TrackData(name=f"Track {track_count + 1}", trackpoints=[])
        
        # Add to track manager
        self.track_manager.tracks.append(new_track)
        new_track_index = len(self.track_manager.get_all_tracks()) - 1
        
        # Select the new track in the manager
        self.track_manager.select_track(new_track_index)
        
        # Refresh the list and select the new track
        self.refresh_tracks()
        self.select_track(new_track_index)
        
        logger.info(f"New track created: {new_track.name} at index {new_track_index}")
    
    def _on_delete_track_clicked(self):
        """Handle '-' button click to delete selected track."""
        
        if self.current_selection < 0:
            logger.warning("No track selected for deletion")
            return
        
        track_index = self.current_selection
        track = self.track_manager.get_track_by_index(track_index)
        
        if not track:
            logger.warning(f"Track not found: index={track_index}")
            return
        
        # Delete the track from manager
        del self.track_manager.tracks[track_index]
        
        # Deselect in manager
        self.track_manager.selected_track_index = -1
        
        # Refresh the list
        self.refresh_tracks()
        
        logger.info(f"Track deleted: {track.name} at index {track_index}")
    
    def _on_unselect_track_clicked(self):
        """Handle 'X' button click to unselect current track."""
        
        self.clear_selection()
        
        logger.info("Track unselected")
    
    # ========================================================================
    # Inline Editing
    # ========================================================================
    
    def _start_inline_edit(self, track_index: int, current_name: str, item: QListWidgetItem):
        """Start inline editing mode for a track name."""
        
        # Cancel any ongoing edit first
        if self.editing_track_index >= 0:
            self._cancel_inline_edit()
        
        # Store state
        self.editing_track_index = track_index
        self.original_track_name = current_name
        
        # Create line edit widget
        self.edit_line_edit = QLineEdit()
        self.edit_line_edit.setText(current_name)
        self.edit_line_edit.selectAll()  # Select all text so user can start typing
        
        # Connect signals for Enter, Escape, and focus loss
        self.edit_line_edit.returnPressed.connect(self._finish_inline_edit)
        self.edit_line_edit.editingFinished.connect(self._finish_inline_edit)
        
        # Set as item widget
        self.list_widget.setItemWidget(item, self.edit_line_edit)
        
        # Focus on the edit field
        self.edit_line_edit.setFocus()
        
        # Handle Escape key
        self.edit_line_edit.keyPressEvent = lambda e: self._handle_edit_key_press(e)
        
        logger.debug(f"Started inline edit for track {track_index}: '{current_name}'")
    
    def _handle_edit_key_press(self, event):
        """Handle key press events in edit mode."""
        from PyQt5.QtGui import QKeySequence
        
        if event.key() == Qt.Key_Escape:
            self._cancel_inline_edit()
        else:
            QLineEdit.keyPressEvent(self.edit_line_edit, event)
    
    def _finish_inline_edit(self):
        """Finish editing and save the new track name."""
        
        if self.editing_track_index < 0 or not self.edit_line_edit:
            return
        
        new_name = self.edit_line_edit.text().strip()
        
        # Validate: reject empty names
        if not new_name:
            logger.warning("Cannot set empty track name")
            self._cancel_inline_edit()
            return
        
        # If name hasn't changed, just cancel
        if new_name == self.original_track_name:
            self._cancel_inline_edit()
            return
        
        # Rename the track
        success = self.track_manager.rename_track(self.editing_track_index, new_name)
        
        if success:
            logger.info(f"Renamed track {self.editing_track_index} to '{new_name}'")
            # Refresh the list to show updated name
            self.update_track_info(self.editing_track_index)
        else:
            logger.warning(f"Failed to rename track {self.editing_track_index}")
        
        # Exit edit mode
        self._exit_inline_edit()
    
    def _cancel_inline_edit(self):
        """Cancel inline editing and revert to original name."""
        
        if self.editing_track_index < 0:
            return
        
        logger.debug(f"Cancelled inline edit for track {self.editing_track_index}")
        self._exit_inline_edit()
    
    def _exit_inline_edit(self):
        """Exit inline edit mode and restore normal display."""
        
        if self.editing_track_index < 0:
            return
        
        track_index = self.editing_track_index
        item = self.list_widget.item(track_index)
        
        if item:
            # Restore normal display (remove the line edit widget)
            self.list_widget.setItemWidget(item, None)
            
            # Refresh the item text to show updated content
            track = self.track_manager.get_track_by_index(track_index)
            if track:
                item_text = self._format_track_item(track)
                item.setText(item_text)
        
        # Clear edit state
        self.editing_track_index = -1
        self.edit_line_edit = None
        self.original_track_name = None
    
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
