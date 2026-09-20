"""
Trackpoint List Widget for mangpx.

Displays all trackpoints (individual waypoints) from a selected track with
coordinates in DMS or Decimal format. Allows point selection, highlighting,
and coordinate format toggling.

Classes:
    - TrackpointListWidget: Main trackpoint list display widget
    - TrackpointListModel: Data model for trackpoint list

Example:
    >>> from PyQt5.QtWidgets import QApplication
    >>> from src.gui.widgets.trackpoint_list_widget import TrackpointListWidget
    >>> from src.core.track_manager import TrackManager
    >>> 
    >>> app = QApplication([])
    >>> manager = TrackManager()
    >>> widget = TrackpointListWidget(manager)
    >>> widget.set_track(0)
    >>> widget.show()
"""

import logging
from typing import Optional, List

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QComboBox, QHeaderView, QAbstractItemView
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, pyqtSignal, QSize

from src.core.track_manager import TrackManager, Trackpoint
from src.utils import coordinate_formatter


# ============================================================================
# Logging
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# Trackpoint List Widget
# ============================================================================

class TrackpointListWidget(QWidget):
    """
    Widget displaying all trackpoints from a selected track.
    
    Features:
    - Display trackpoints in a table format
    - Show coordinates in DMS or Decimal format
    - Optional elevation and timestamp columns
    - Single or multiple selection
    - Point highlighting
    - Coordinate format toggle
    - Real-time update when track changes
    
    Signals:
        point_selected: Emitted when user selects a point
        point_double_clicked: Emitted when user double-clicks a point
        coordinate_format_changed: Emitted when format changes
    
    Example:
        >>> manager = TrackManager()
        >>> widget = TrackpointListWidget(manager)
        >>> widget.point_selected.connect(on_point_selected)
        >>> widget.set_track(0)
        >>> widget.show()
    """
    
    # Signals
    point_selected = pyqtSignal(int)  # Emitted with point index
    point_double_clicked = pyqtSignal(int)  # Emitted with point index
    coordinate_format_changed = pyqtSignal(str)  # Emitted with new format
    
    # Column indices
    COL_INDEX = 0
    COL_LATITUDE = 1
    COL_LONGITUDE = 2
    COL_ELEVATION = 3
    COL_TIMESTAMP = 4
    
    def __init__(self, track_manager: TrackManager, map_widget=None):
        """
        Initialize Trackpoint List Widget.
        
        Args:
            track_manager (TrackManager): Reference to track manager
            map_widget (MapWidget): Reference to map widget (optional)
        
        Example:
            >>> manager = TrackManager()
            >>> widget = TrackpointListWidget(manager)
        """
        
        super().__init__()
        
        self.track_manager = track_manager
        self.map_widget = map_widget
        self.current_track_index = -1
        self.current_selection = -1
        
        # Load saved settings or use defaults
        from config.app_config_yaml import AppConfig
        config = AppConfig()
        self.coordinate_format = config.get_str('Coordinates.last_state.format', 'dms')
        self.show_points = config.get_bool('Map.last_state.show_turning_points', True)
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
        
        logger.info("TrackpointListWidget initialized")
    
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
        title_label = QLabel("Trackpoints")
        title_font = title_label.font()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # Point count label
        self.count_label = QLabel("(0 points)")
        header_layout.addWidget(self.count_label)
        
        # Coordinate format selector
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("DMS", "dms")
        self.format_combo.addItem("Decimal", "decimal")
        # Set to saved format
        if self.coordinate_format == "decimal":
            self.format_combo.setCurrentIndex(1)
        else:
            self.format_combo.setCurrentIndex(0)
        self.format_combo.setMaximumWidth(120)
        header_layout.addWidget(self.format_combo)
        
        # Show points selector
        header_layout.addWidget(QLabel("Show points:"))
        self.show_points_combo = QComboBox()
        self.show_points_combo.addItem("Yes", True)
        self.show_points_combo.addItem("No", False)
        # Set to saved show points setting
        if self.show_points:
            self.show_points_combo.setCurrentIndex(0)  # Yes
        else:
            self.show_points_combo.setCurrentIndex(1)  # No
        self.show_points_combo.setMaximumWidth(80)
        header_layout.addWidget(self.show_points_combo)
        
        main_layout.addLayout(header_layout)
        
        # Table widget
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(5)
        self.table_widget.setHorizontalHeaderLabels([
            "#", "Latitude", "Longitude", "Elevation (m)", "Timestamp"
        ])
        self.table_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setMinimumHeight(300)
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # Set column widths
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        main_layout.addWidget(self.table_widget)
        
        # Button section
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setToolTip("Refresh trackpoint list")
        button_layout.addWidget(self.refresh_button)
        
        self.clear_button = QPushButton("Clear Selection")
        self.clear_button.setToolTip("Clear current selection")
        button_layout.addWidget(self.clear_button)
        
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect internal signals."""
        
        # Table widget signals
        self.table_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.table_widget.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table_widget.customContextMenuRequested.connect(self._on_context_menu)
        
        # Format combo signal
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        
        # Show points combo signal
        self.show_points_combo.currentIndexChanged.connect(self._on_show_points_changed)
        
        # Button signals
        self.refresh_button.clicked.connect(self.refresh_trackpoints)
        self.clear_button.clicked.connect(self.clear_selection)
    
    # ========================================================================
    # Track Management
    # ========================================================================
    
    def set_track(self, track_index: int) -> bool:
        """
        Set the track to display trackpoints for.
        
        Args:
            track_index (int): Index of track (0-based)
        
        Returns:
            bool: True if track set successfully, False otherwise
        
        Example:
            >>> widget.set_track(0)
            True
            >>> widget.refresh_trackpoints()
        """
        
        track = self.track_manager.get_track_by_index(track_index)
        if not track:
            logger.warning(f"Invalid track index: {track_index}")
            return False
        
        self.current_track_index = track_index
        logger.debug(f"Track set: index={track_index}, name={track.name}")
        
        # CRITICAL FIX: Automatically refresh trackpoints when track is set
        # This was missing before, causing trackpoints to only appear after manual refresh
        self.refresh_trackpoints()
        
        return True
    
    def get_current_track_index(self) -> int:
        """Get currently displayed track index."""
        return self.current_track_index
    
    # ========================================================================
    # Trackpoint Display
    # ========================================================================
    
    def refresh_trackpoints(self):
        """
        Refresh the trackpoint list from the current track.
        
        Clears current list and populates with all points from selected track.
        """
        
        if self.current_track_index < 0:
            self.table_widget.setRowCount(0)
            self.count_label.setText("(0 points)")
            logger.debug("No track selected, clearing table")
            return
        
        track = self.track_manager.get_track_by_index(self.current_track_index)
        if not track:
            self.table_widget.setRowCount(0)
            self.count_label.setText("(0 points)")
            return
        
        # Get trackpoints
        trackpoints = track.trackpoints
        
        # Set table row count
        self.table_widget.setRowCount(len(trackpoints))
        
        # Populate table
        for row, point in enumerate(trackpoints):
            self._populate_row(row, point)
        
        # Update count label
        count = len(trackpoints)
        self.count_label.setText(f"({count} point{'s' if count != 1 else ''})")
        
        logger.debug(f"Refreshed trackpoint list: {count} points")
    
    def _populate_row(self, row: int, point: Trackpoint):
        """
        Populate a table row with trackpoint data.
        
        Args:
            row (int): Row index
            point (Trackpoint): Trackpoint data
        """
        
        # Index column
        index_item = QTableWidgetItem(str(point.index + 1))
        index_item.setFlags(index_item.flags() & ~Qt.ItemIsEditable)
        self.table_widget.setItem(row, self.COL_INDEX, index_item)
        
        # Latitude column
        lat_text = self._format_coordinate(point.latitude, is_latitude=True)
        lat_item = QTableWidgetItem(lat_text)
        lat_item.setFlags(lat_item.flags() & ~Qt.ItemIsEditable)
        self.table_widget.setItem(row, self.COL_LATITUDE, lat_item)
        
        # Longitude column
        lon_text = self._format_coordinate(point.longitude, is_latitude=False)
        lon_item = QTableWidgetItem(lon_text)
        lon_item.setFlags(lon_item.flags() & ~Qt.ItemIsEditable)
        self.table_widget.setItem(row, self.COL_LONGITUDE, lon_item)
        
        # Elevation column
        elev_text = f"{point.elevation:.1f}" if point.elevation is not None else "-"
        elev_item = QTableWidgetItem(elev_text)
        elev_item.setFlags(elev_item.flags() & ~Qt.ItemIsEditable)
        self.table_widget.setItem(row, self.COL_ELEVATION, elev_item)
        
        # Timestamp column
        timestamp_text = point.timestamp if point.timestamp else "-"
        time_item = QTableWidgetItem(timestamp_text)
        time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
        self.table_widget.setItem(row, self.COL_TIMESTAMP, time_item)
        
        # Store row index as data (this is the trackpoint index in the current track)
        # We store the row index, not point.index, because point.index is from the original
        # trackpoint data which doesn't change after deletion
        for col in range(5):
            self.table_widget.item(row, col).setData(Qt.UserRole, row)
    
    def _format_coordinate(self, value: float, is_latitude: bool) -> str:
        """
        Format coordinate value based on current format setting.
        
        Args:
            value (float): Coordinate value in decimal degrees
            is_latitude (bool): True if latitude, False if longitude
        
        Returns:
            str: Formatted coordinate string
        """
        
        try:
            if self.coordinate_format == 'dms':
                # Convert to DMS and format
                degrees, minutes, seconds, direction = coordinate_formatter.decimal_to_dms(
                    abs(value), is_longitude=not is_latitude
                )
                # Set correct direction
                if is_latitude:
                    direction = 'N' if value >= 0 else 'S'
                else:
                    direction = 'E' if value >= 0 else 'W'
                return coordinate_formatter.format_dms(degrees, minutes, seconds, direction)
            else:
                # Format as decimal
                direction = 'N' if (is_latitude and value >= 0) or (not is_latitude and value >= 0) else ('S' if is_latitude else 'W')
                return coordinate_formatter.format_decimal(abs(value), include_direction=True)
        except Exception as e:
            logger.warning(f"Error formatting coordinate: {e}")
            return str(value)
    
    # ========================================================================
    # Selection Management
    # ========================================================================
    
    def select_point(self, point_index: int) -> bool:
        """
        Select a trackpoint by index.
        
        Args:
            point_index (int): Index of point to select (0-based)
        
        Returns:
            bool: True if selected successfully, False otherwise
        """
        
        if not 0 <= point_index < self.table_widget.rowCount():
            logger.warning(f"Invalid point index: {point_index}")
            return False
        
        self.table_widget.selectRow(point_index)
        self.current_selection = point_index
        return True
    
    def get_selected_point_index(self) -> int:
        """Get currently selected point index."""
        return self.current_selection
    
    def is_point_selected(self) -> bool:
        """Check if a point is currently selected."""
        return self.current_selection >= 0
    
    def clear_selection(self):
        """Clear current point selection."""
        self.table_widget.clearSelection()
        self.current_selection = -1
        logger.debug("Point selection cleared")
    
    # ========================================================================
    # Signal Handlers
    # ========================================================================
    
    def _on_selection_changed(self):
        """Handle selection change in table widget."""
        
        selected_items = self.table_widget.selectedItems()
        
        if selected_items:
            # Get first item in selection
            item = selected_items[0]
            row = item.row()
            point_index = item.data(Qt.UserRole)
            
            self.current_selection = row
            
            # Emit signal
            self.point_selected.emit(point_index)
            
            logger.debug(f"Point selected: index={point_index}, row={row}")
        else:
            self.current_selection = -1
    
    def _on_cell_double_clicked(self, row: int, column: int):
        """Handle double-click on table cell."""
        
        item = self.table_widget.item(row, column)
        if item:
            point_index = item.data(Qt.UserRole)
            self.point_double_clicked.emit(point_index)
            
            logger.debug(f"Point double-clicked: index={point_index}")
    
    def _on_format_changed(self, index: int):
        """Handle coordinate format change."""
        
        self.coordinate_format = self.format_combo.currentData()
        
        # Save to config file
        from config.app_config_yaml import AppConfig
        config = AppConfig()
        config.set('Coordinates.last_state.format', self.coordinate_format)
        config.save_to_file()
        
        # Refresh display
        self.refresh_trackpoints()
        
        # Emit signal
        self.coordinate_format_changed.emit(self.coordinate_format)
        
        logger.debug(f"Coordinate format changed: {self.coordinate_format}")
    
    def _on_show_points_changed(self, index: int):
        """Handle show points toggle."""
        
        show_points = self.show_points_combo.currentData()
        self.show_points = show_points
        
        # Save to config file
        from config.app_config_yaml import AppConfig
        config = AppConfig()
        config.set('Map.last_state.show_turning_points', show_points)
        config.save_to_file()
        
        # Update map widget if available
        if self.map_widget:
            self.map_widget.set_show_turning_points(show_points)
        
        logger.debug(f"Show points changed: {show_points}")
    
    # ========================================================================
    # Updates
    # ========================================================================
    
    def highlight_point(self, point_index: int):
        """
        Highlight a point without changing selection.
        
        Args:
            point_index (int): Index of point to highlight
        """
        
        if 0 <= point_index < self.table_widget.rowCount():
            for col in range(5):
                item = self.table_widget.item(point_index, col)
                if item:
                    item.setBackground(QColor(255, 255, 200))  # Light yellow
    
    def remove_highlight(self, point_index: int):
        """
        Remove highlight from a point.
        
        Args:
            point_index (int): Index of point to unhighlight
        """
        
        if 0 <= point_index < self.table_widget.rowCount():
            for col in range(5):
                item = self.table_widget.item(point_index, col)
                if item:
                    item.setBackground(QColor())  # Default background
    
    # ========================================================================
    # Context Menu & Deletion
    # ========================================================================
    
    def _on_context_menu(self, position):
        """Handle context menu on trackpoint table."""
        
        selected_row = self.table_widget.rowAt(position.y())
        if selected_row < 0:
            return
        
        # Create context menu
        from PyQt5.QtWidgets import QMenu
        menu = QMenu()
        
        delete_action = menu.addAction("Delete Trackpoint")
        delete_from_start_action = menu.addAction("Delete from Start to Here")
        delete_from_end_action = menu.addAction("Delete from Here to End")
        
        # Execute menu
        action = menu.exec_(self.table_widget.mapToGlobal(position))
        
        # Handle actions
        if action == delete_action:
            self._delete_trackpoint(selected_row)
        elif action == delete_from_start_action:
            self._delete_from_start(selected_row)
        elif action == delete_from_end_action:
            self._delete_from_end(selected_row)
    
    def keyPressEvent(self, event):
        """Handle keyboard events (Delete key for removing trackpoints)."""
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import QMessageBox
        
        # Delete key to remove trackpoint
        if event.key() == Qt.Key_Delete:
            if self.table_widget.hasFocus():
                selected_row = self.table_widget.currentRow()
                if selected_row >= 0:
                    self._delete_trackpoint(selected_row)
                return
        
        super().keyPressEvent(event)
    
    def _delete_trackpoint(self, row_index: int):
        """Delete a single trackpoint with confirmation."""
        from PyQt5.QtWidgets import QMessageBox
        
        if self.current_track_index < 0 or row_index < 0:
            return
        
        track = self.track_manager.get_track_by_index(self.current_track_index)
        if not track or row_index >= len(track.trackpoints):
            return
        
        # Get trackpoint info
        point = track.trackpoints[row_index]
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Delete Trackpoint",
            f"Delete trackpoint {row_index + 1}?\n\n({point.latitude:.4f}°, {point.longitude:.4f}°)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Remove trackpoint
            removed = self.track_manager.remove_trackpoint(self.current_track_index, row_index)
            if removed:
                logger.info(f"Deleted trackpoint {row_index} from track '{track.name}'")
                # Refresh display
                self.refresh_trackpoints()
                # Update map - re-select the current track to force redraw
                if self.map_widget:
                    self.map_widget.on_track_list_selection_changed(self.current_track_index)
                # Emit signal
                self.point_selected.emit(-1)
            else:
                QMessageBox.warning(self, "Error", "Could not delete trackpoint")
    
    def _delete_from_start(self, to_row_index: int):
        """Delete trackpoints from start to specified row (inclusive)."""
        from PyQt5.QtWidgets import QMessageBox
        
        if self.current_track_index < 0 or to_row_index < 0:
            return
        
        track = self.track_manager.get_track_by_index(self.current_track_index)
        if not track:
            return
        
        # Calculate how many will be deleted
        count_to_delete = to_row_index + 1
        count_remaining = len(track.trackpoints) - count_to_delete
        
        if count_remaining <= 0:
            QMessageBox.warning(
                self,
                "Cannot Delete",
                "This would delete all trackpoints. Track must have at least one point."
            )
            return
        
        # Show confirmation
        reply = QMessageBox.question(
            self,
            "Delete from Start",
            f"Delete {count_to_delete} trackpoint(s) from start to row {to_row_index + 1}?\n\n"
            f"{count_remaining} point(s) will remain.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            removed = self.track_manager.remove_trackpoints_from_start(self.current_track_index, to_row_index)
            if removed:
                logger.info(f"Deleted {len(removed)} trackpoints from start of track '{track.name}'")
                self.refresh_trackpoints()
                if self.map_widget:
                    self.map_widget.on_track_list_selection_changed(self.current_track_index)
                self.point_selected.emit(-1)
            else:
                QMessageBox.warning(self, "Error", "Could not delete trackpoints")
    
    def _delete_from_end(self, from_row_index: int):
        """Delete trackpoints from specified row to end."""
        from PyQt5.QtWidgets import QMessageBox
        
        if self.current_track_index < 0 or from_row_index < 0:
            return
        
        track = self.track_manager.get_track_by_index(self.current_track_index)
        if not track:
            return
        
        # Calculate how many will be deleted
        count_to_delete = len(track.trackpoints) - from_row_index
        count_remaining = from_row_index
        
        if count_remaining <= 0:
            QMessageBox.warning(
                self,
                "Cannot Delete",
                "This would delete all trackpoints. Track must have at least one point."
            )
            return
        
        # Show confirmation
        reply = QMessageBox.question(
            self,
            "Delete from End",
            f"Delete {count_to_delete} trackpoint(s) from row {from_row_index + 1} to end?\n\n"
            f"{count_remaining} point(s) will remain.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            removed = self.track_manager.remove_trackpoints_from_end(self.current_track_index, from_row_index)
            if removed:
                logger.info(f"Deleted {len(removed)} trackpoints from end of track '{track.name}'")
                self.refresh_trackpoints()
                if self.map_widget:
                    self.map_widget.on_track_list_selection_changed(self.current_track_index)
                self.point_selected.emit(-1)
            else:
                QMessageBox.warning(self, "Error", "Could not delete trackpoints")


# ============================================================================
# Trackpoint List Model (for potential future use with MVC pattern)
# ============================================================================

class TrackpointListModel:
    """
    Data model for trackpoint list (prepared for future MVC implementation).
    
    Provides a structured interface to trackpoint data that could be used
    with Qt's MVC classes in the future.
    """
    
    def __init__(self, track_manager: TrackManager):
        """
        Initialize trackpoint list model.
        
        Args:
            track_manager (TrackManager): Reference to track manager
        """
        
        self.track_manager = track_manager
    
    def get_track_point_count(self, track_index: int) -> int:
        """
        Get point count for a track.
        
        Args:
            track_index (int): Track index
        
        Returns:
            int: Number of points in track
        """
        
        track = self.track_manager.get_track_by_index(track_index)
        if track:
            return track.get_point_count()
        return 0
    
    def get_trackpoint(self, track_index: int, point_index: int) -> Optional[Trackpoint]:
        """
        Get trackpoint data.
        
        Args:
            track_index (int): Track index
            point_index (int): Point index within track
        
        Returns:
            Optional[Trackpoint]: Trackpoint data or None
        """
        
        track = self.track_manager.get_track_by_index(track_index)
        if track:
            return track.get_point(point_index)
        return None
    
    def get_trackpoint_display(self, track_index: int, point_index: int, 
                              coord_format: str = 'dms') -> dict:
        """
        Get formatted display data for trackpoint.
        
        Args:
            track_index (int): Track index
            point_index (int): Point index
            coord_format (str): 'dms' or 'decimal'
        
        Returns:
            dict: Display data with formatted values
        """
        
        point = self.get_trackpoint(track_index, point_index)
        if not point:
            return {}
        
        return {
            'index': point.index + 1,
            'latitude': point.latitude,
            'longitude': point.longitude,
            'elevation': point.elevation,
            'timestamp': point.timestamp
        }
