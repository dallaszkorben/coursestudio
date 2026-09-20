"""
PIL-based interactive map widget for displaying GPX tracks and trackpoints.

Uses direct mbtiles rendering via PIL/Pillow instead of web-based Leaflet.js.

Features:
- Map display from MBTiles files using PIL image rendering
- Mouse wheel zoom (+ to zoom in, - to zoom out)
- Mouse drag panning (left button drag to pan)
- On-screen zoom +/- buttons (top-left overlay)
- Pan/center controls
- Real-time track/point highlighting
- Signal-based communication: map_ready, track_clicked, point_clicked
"""

import logging
from typing import Optional, List
from pathlib import Path
import math

from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRect
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtGui import QPixmap, QFont

from src.map.mbtiles_provider import MBTilesProvider
from src.map.map_renderer import MapRenderer


class MapWidget(QWidget):
    """
    Interactive map display widget using PIL-based rendering.
    
    Displays GPX tracks and trackpoints on offline maps from MBTiles files.
    Supports track/point selection via signals and interactive controls.
    
    Signals:
        map_ready: Emitted when map is ready to display
        track_clicked: Emitted when user clicks on a track
        point_clicked: Emitted when user clicks on a trackpoint
    """

    # Custom signals for user interaction
    map_ready = pyqtSignal()  # Emitted when map is ready to display
    track_clicked = pyqtSignal(int)  # Emitted when user clicks on a track
    point_clicked = pyqtSignal(int, int)  # Emitted when user clicks on a point (track_idx, point_idx)

    def __init__(self, track_manager, mbtiles_provider: MBTilesProvider, logger: logging.Logger, parent=None):
        """
        Initialize map widget.
        
        Args:
            track_manager: TrackManager instance for track access
            mbtiles_provider: MBTilesProvider instance for tile access
            logger: Logger instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.track_manager = track_manager
        self.mbtiles_provider = mbtiles_provider
        self.logger = logger
        
        # Map state
        self.center_lat = 56.1612  # Karlskrona, Sweden
        self.center_lon = 15.5869
        self.zoom_level = 13
        self.tracks = None
        self.highlighted_track_index = None
        self.highlighted_point_index = None
        
        # Map renderer
        self.map_renderer = MapRenderer(self.mbtiles_provider, width=800, height=600)
        
        # Pan state
        self.pan_start_x = None
        self.pan_start_y = None
        self.is_panning = False
        
        # CRITICAL FIX: Enable mouse tracking and set focus policy
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # UI components
        self._init_ui()
        
        # Render timer (debounce rapid updates)
        self.render_timer = QTimer()
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self._do_render)
        self.render_timer.setInterval(100)  # 100ms debounce
        
        # Perform initial render
        self._schedule_render()

    def _init_ui(self) -> None:
        """Initialize user interface components."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Map display label (background for pixmap) - MUST EXPAND
        self.map_label = QLabel()
        self.map_label.setAlignment(Qt.AlignCenter)
        self.map_label.setMinimumSize(400, 300)
        self.map_label.setStyleSheet("background-color: #cccccc; border: 1px solid gray;")
        self.map_label.setMouseTracking(True)
        # CRITICAL FIX: Forward mouse events from label to widget
        # Install event filter to intercept mouse events on the label
        self.map_label.installEventFilter(self)
        main_layout.addWidget(self.map_label, 1)  # Add stretch factor to expand
        
        self.setLayout(main_layout)
        
        # Create overlay zoom buttons (these will be positioned over the map)
        self._create_zoom_buttons()
        
        # Status label at bottom
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray; font-size: 10px; padding: 5px;")
        main_layout.addWidget(self.status_label, 0)  # No stretch, fixed height
    
    def eventFilter(self, obj, event):
        """Forward mouse events from map_label to widget handlers."""
        if obj == self.map_label:
            if event.type() == event.MouseMove:
                self.mouseMoveEvent(event)
                return True
            elif event.type() == event.MouseButtonPress:
                self.mousePressEvent(event)
                return True
            elif event.type() == event.MouseButtonRelease:
                self.mouseReleaseEvent(event)
                return True
            elif event.type() == event.Wheel:
                self.wheelEvent(event)
                return True
        return super().eventFilter(obj, event)

    def _create_zoom_buttons(self) -> None:
        """Create overlay zoom buttons at top-left corner."""
        # Zoom in button (+)
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setParent(self)
        self.zoom_in_button.setFixedSize(50, 50)
        self.zoom_in_button.setFont(QFont("Arial", 20, QFont.Bold))
        self.zoom_in_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 150, 200, 220);
                color: white;
                border: 2px solid white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 170, 220, 240);
            }
            QPushButton:pressed {
                background-color: rgba(0, 120, 180, 220);
            }
        """)
        self.zoom_in_button.clicked.connect(self._on_zoom_in)
        self.zoom_in_button.move(10, 10)
        
        # Zoom out button (−)
        self.zoom_out_button = QPushButton("−")  # Unicode minus
        self.zoom_out_button.setParent(self)
        self.zoom_out_button.setFixedSize(50, 50)
        self.zoom_out_button.setFont(QFont("Arial", 24, QFont.Bold))
        self.zoom_out_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 150, 200, 220);
                color: white;
                border: 2px solid white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 170, 220, 240);
            }
            QPushButton:pressed {
                background-color: rgba(0, 120, 180, 220);
            }
        """)
        self.zoom_out_button.clicked.connect(self._on_zoom_out)
        self.zoom_out_button.move(10, 65)
        
        # Recenter button (C for Center)
        self.recenter_button = QPushButton("⊙")  # Circled dot
        self.recenter_button.setParent(self)
        self.recenter_button.setFixedSize(50, 50)
        self.recenter_button.setFont(QFont("Arial", 16, QFont.Bold))
        self.recenter_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 150, 50, 220);
                color: white;
                border: 2px solid white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(120, 170, 70, 240);
            }
            QPushButton:pressed {
                background-color: rgba(80, 120, 40, 220);
            }
        """)
        self.recenter_button.clicked.connect(self._on_reset_center)
        self.recenter_button.move(10, 120)

    def set_center(self, lat: float, lon: float) -> None:
        """Set map center and trigger re-render."""
        self.center_lat = lat
        self.center_lon = lon
        self._schedule_render()

    def set_tracks(self, tracks: List = None, highlighted_track_index: int = None,
                   highlighted_point_index: int = None) -> None:
        """
        Set tracks to display and trigger re-render.
        
        Args:
            tracks: List of Track objects to display
            highlighted_track_index: Index of track to highlight (None for no highlight)
            highlighted_point_index: Index of point to highlight in highlighted track
        """
        self.tracks = tracks
        self.highlighted_track_index = highlighted_track_index
        self.highlighted_point_index = highlighted_point_index
        self._schedule_render()

    def on_track_list_selection_changed(self, track_index: int) -> None:
        """Called when track selection changes in the track list."""
        self.highlighted_track_index = track_index
        self._schedule_render()

    def on_track_selected(self, track_index: int) -> None:
        """Called when a track is selected/double-clicked."""
        self.highlighted_track_index = track_index
        
        # Center map on first point of selected track
        if track_index < len(self.track_manager.get_all_tracks()):
            track = self.track_manager.get_all_tracks()[track_index]
            if track.trackpoints:
                first_point = track.trackpoints[0]
                self.set_center(first_point.latitude, first_point.longitude)
        else:
            self._schedule_render()

    def on_trackpoint_selected(self, track_index: int, point_index: int) -> None:
        """Called when a trackpoint is selected in the trackpoint list."""
        self.highlighted_track_index = track_index
        self.highlighted_point_index = point_index
        
        # Center map on selected point if available
        if track_index < len(self.track_manager.get_all_tracks()):
            track = self.track_manager.get_all_tracks()[track_index]
            if point_index < len(track.trackpoints):
                point = track.trackpoints[point_index]
                self.set_center(point.latitude, point.longitude)
        else:
            self._schedule_render()

    def on_point_selected(self, track_index: int, point_index: int) -> None:
        """Alias for on_trackpoint_selected (for compatibility with main_window.py)."""
        self.on_trackpoint_selected(track_index, point_index)

    def _schedule_render(self) -> None:
        """Schedule map render (debounced)."""
        self.render_timer.stop()
        self.render_timer.start()

    def _do_render(self) -> None:
        """Actually render the map."""
        try:
            if not self.mbtiles_provider.is_loaded():
                self._show_error("No mbtiles file loaded")
                return
            
            self.status_label.setText(f"Rendering at zoom {self.zoom_level}...")
            self.repaint()  # Force UI update
            
            # Get tracks from manager if not explicitly set
            tracks = self.tracks if self.tracks is not None else self.track_manager.get_all_tracks()
            
            # Render map
            pixmap = self.map_renderer.render_map(
                center_lat=self.center_lat,
                center_lon=self.center_lon,
                zoom=self.zoom_level,
                tracks=tracks,
                highlighted_track_index=self.highlighted_track_index,
                highlighted_point_index=self.highlighted_point_index,
            )
            
            if pixmap:
                self.map_label.setPixmap(pixmap)
                self.status_label.setText(
                    f"Center: ({self.center_lat:.4f}, {self.center_lon:.4f}) Z{self.zoom_level}"
                )
                # Emit map ready signal on first successful render
                if not hasattr(self, '_map_ready_emitted'):
                    self.map_ready.emit()
                    self._map_ready_emitted = True
            else:
                self._show_error("Failed to render map")
        
        except Exception as e:
            self.logger.error(f"Map render error: {e}")
            self._show_error(f"Render error: {e}")

    def _on_zoom_in(self) -> None:
        """Handle zoom in button click."""
        available_zooms = self.mbtiles_provider.get_available_zooms()
        if available_zooms:
            max_zoom = max(available_zooms)
            if self.zoom_level < max_zoom:
                self.zoom_level += 1
                self._schedule_render()

    def _on_zoom_out(self) -> None:
        """Handle zoom out button click."""
        available_zooms = self.mbtiles_provider.get_available_zooms()
        if available_zooms:
            min_zoom = min(available_zooms)
            if self.zoom_level > min_zoom:
                self.zoom_level -= 1
                self._schedule_render()

    def _on_reset_center(self) -> None:
        """Reset map center to default location."""
        self.set_center(56.1612, 15.5869)

    def wheelEvent(self, event) -> None:
        """Handle mouse wheel for zooming - forward to map label."""
        # Process wheel event
        if event.angleDelta().y() > 0:
            self._on_zoom_in()
        else:
            self._on_zoom_out()

    def mousePressEvent(self, event) -> None:
        """Handle mouse button press - forward to map label or buttons."""
        if event.button() == Qt.LeftButton:
            # Check if click is on any button (using local coordinates)
            if self._is_point_in_button(event.x(), event.y(), self.zoom_in_button.geometry()):
                self.zoom_in_button.click()
                return
            
            if self._is_point_in_button(event.x(), event.y(), self.zoom_out_button.geometry()):
                self.zoom_out_button.click()
                return
            
            if self._is_point_in_button(event.x(), event.y(), self.recenter_button.geometry()):
                self.recenter_button.click()
                return
            
            # Start panning on map area
            self.pan_start_x = event.x()
            self.pan_start_y = event.y()
            self.is_panning = True

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse movement for panning."""
        if self.is_panning and self.pan_start_x is not None and self.pan_start_y is not None:
            # Calculate pan distance in pixels
            # CRITICAL FIX: Use proper pan calculation via map_renderer
            delta_x = self.pan_start_x - event.x()
            delta_y = self.pan_start_y - event.y()
            
            # Pan the map through the map_renderer (handles coordinate conversion)
            if self.map_renderer:
                self.map_renderer.pan(delta_x, delta_y)
                self._schedule_render()
            
            # Update pan start position for next movement
            self.pan_start_x = event.x()
            self.pan_start_y = event.y()

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse button release."""
        if event.button() == Qt.LeftButton:
            self.pan_start_x = None
            self.pan_start_y = None
            self.is_panning = False

    def _is_point_in_button(self, x: int, y: int, geometry: QRect) -> bool:
        """Check if a point is within a button's geometry."""
        return (geometry.x() <= x <= geometry.x() + geometry.width() and
                geometry.y() <= y <= geometry.y() + geometry.height())

    def _show_error(self, message: str) -> None:
        """Display error message in status label."""
        self.status_label.setText(f"ERROR: {message}")
        self.status_label.setStyleSheet("color: red; font-size: 10px; padding: 5px;")
