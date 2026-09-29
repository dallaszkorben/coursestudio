"""
Map widget for displaying GPS tracks with pan and zoom controls.

Direct adaptation of openseemap's proven working MapWidget.
"""

import tempfile
import os
import logging
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QApplication
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PIL import Image, ImageDraw

from src.map.mbtiles_provider import MBTilesProvider
from src.map.map_renderer import MapRenderer

logger = logging.getLogger(__name__)


class MapWidget(QWidget):
    """
    Custom widget that displays the map.
    
    Handles map rendering and user interactions like panning and zooming.
    """
    
    # Signals
    map_ready = pyqtSignal()
    track_clicked = pyqtSignal(str)
    point_clicked = pyqtSignal(str, int)
    range_selection_changed = pyqtSignal(bool)  # Emitted when range selection changes (True = has range, False = no range)
    trackpoint_dragging = pyqtSignal(int, float, float)  # Emitted during drag: (index, latitude, longitude)
    
    # UI Constants
    ZOOM_BUTTON_SIZE = 40
    ZOOM_BUTTON_SPACING = 5
    CONTROLS_PADDING_LEFT = 10
    CONTROLS_PADDING_TOP = 10
    ZOOM_LEVEL_DEFAULT = 15  # Sweden-Raster-Z10-Z16 has min zoom 15
    
    def __init__(self, parent=None, mbtiles_provider=None):
        """
        Initialize the map widget.
        
        Args:
            parent (QWidget): Parent widget
            mbtiles_provider (MBTilesProvider): The tile provider to use
        """
        super().__init__(parent)
        
        self.mbtiles_provider = mbtiles_provider
        self.track_manager = None
        self.selected_track_id = None
        self.selected_trackpoint_index = None
        self.selected_trackpoint_range = None  # NEW: For selecting 2 neighboring points (start_idx, end_idx)
        self.show_turning_points = True  # Show/hide turning points
        
        # Load track display settings from config
        from config.app_config_yaml import AppConfig
        config = AppConfig()
        
        # Parse colors from config (hex format: RRGGBB)
        # New structure: Appearance.MapDisplay
        self.track_color = self._hex_to_rgb(config.get_str('Appearance.MapDisplay.TrackPath.color', 'FF0000'))
        self.selected_track_color = self._hex_to_rgb(config.get_str('Appearance.MapDisplay.TrackPath.color', 'FF0000'))
        self.selected_point_color = self._hex_to_rgb(config.get_str('Appearance.MapDisplay.TurningPoints.selected.color', '0000FF'))
        
        # Turning points settings
        # NOTE: Read from config to get user's preference
        self.show_turning_points = config.get_bool('Appearance.MapDisplay.TurningPoints.show', True)
        self.turning_point_color = self._hex_to_rgb(config.get_str('Appearance.MapDisplay.TurningPoints.color', 'FFFF00'))
        self.selected_turning_point_color = self._hex_to_rgb(config.get_str('Appearance.MapDisplay.TurningPoints.selected.color', '0000FF'))
        self.turning_point_size = config.get_int('Appearance.MapDisplay.TurningPoints.size', 4)
        self.selected_turning_point_size = config.get_int('Appearance.MapDisplay.TurningPoints.selected.size', 7)
        
        # Double selected (range) turning points settings
        self.double_selected_turning_point_color = self._hex_to_rgb(config.get_str('Appearance.MapDisplay.TurningPoints.doubleSelected.color', 'FFA500'))
        self.double_selected_turning_point_size = config.get_int('Appearance.MapDisplay.TurningPoints.doubleSelected.size', 8)
        
        # Track path width
        self.track_path_width = config.get_int('Appearance.MapDisplay.TrackPath.width', 3)
        
        # Map state
        self.center_lat = 56.168
        self.center_lon = 15.586
        self.zoom_level = self.ZOOM_LEVEL_DEFAULT
        
        # Drag state for moving trackpoints
        self.dragging_trackpoint = False
        self.dragged_trackpoint_index = None
        self.drag_start_x = None
        self.drag_start_y = None
        self.drag_original_lat = None
        self.drag_original_lon = None
        
        # Map display label
        self.map_label = QLabel()
        self.map_label.setStyleSheet("background-color: #c0c0c0;")
        self.map_label.setAlignment(Qt.AlignCenter)
        
        # Allow map label to shrink (important for window resizing)
        from PyQt5.QtWidgets import QSizePolicy
        self.map_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.map_label.setScaledContents(True)  # Scale pixmap to fit label size
        
        # Override minimum size to allow actual shrinking
        self.map_label.setMinimumSize(1, 1)  # Allow to shrink to 1x1 pixel if needed
        
        # Zoom controls (invisible clickable overlays - visuals drawn on map)
        self.zoom_in_button = QPushButton("+", self)
        self.zoom_in_button.setFixedSize(self.ZOOM_BUTTON_SIZE, self.ZOOM_BUTTON_SIZE)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_in_button.setStyleSheet("background-color: transparent; border: none; color: transparent;")
        self.zoom_in_button.setFocusPolicy(Qt.NoFocus)
        
        self.zoom_out_button = QPushButton("-", self)
        self.zoom_out_button.setFixedSize(self.ZOOM_BUTTON_SIZE, self.ZOOM_BUTTON_SIZE)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.zoom_out_button.setStyleSheet("background-color: transparent; border: none; color: transparent;")
        self.zoom_out_button.setFocusPolicy(Qt.NoFocus)
        
        # Zoom level display
        self.zoom_level_label = QLabel(f"Z:{self.ZOOM_LEVEL_DEFAULT}", self)
        font = QFont()
        font.setPointSize(self.ZOOM_BUTTON_SIZE // 2)
        self.zoom_level_label.setFont(font)
        self.zoom_level_label.setStyleSheet("background-color: transparent; border: none; color: transparent;")
        
        # Recenter button
        self.recenter_button = QPushButton("⊙", self)
        self.recenter_button.setFixedSize(self.ZOOM_BUTTON_SIZE, self.ZOOM_BUTTON_SIZE)
        self.recenter_button.setToolTip("Recenter on default position")
        self.recenter_button.clicked.connect(self.recenter_on_default)
        self.recenter_button.setStyleSheet("background-color: transparent; border: none; color: transparent;")
        self.recenter_button.setFocusPolicy(Qt.NoFocus)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.map_label)
        self.setLayout(main_layout)
        
        # Mouse tracking for panning
        self.pan_start_x = None
        self.pan_start_y = None
        self.setMouseTracking(True)
        
        # Render timer
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self.render_map)
        self.render_timer.start(100)  # Update every 100ms
        
        # Initial render
        self.render_map()
        self._reposition_controls()
        self.map_ready.emit()
    
    @staticmethod
    def _hex_to_rgb(hex_color):
        """Convert hex color string (RRGGBB) to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (255, 0, 0)  # Default to red if invalid
    
    def screen_to_gps(self, screen_x: int, screen_y: int):
        """
        Convert screen coordinates to GPS coordinates (inverse of rendering).
        Uses Web Mercator projection - inverse of gps_to_screen.
        
        Args:
            screen_x: X position on screen in pixels
            screen_y: Y position on screen in pixels
        
        Returns:
            Tuple of (latitude, longitude) or None if conversion fails
        """
        if not self.mbtiles_provider:
            return None
        
        try:
            import math
            
            # Do the conversion directly without creating a new MapRenderer
            # We need to calculate tile coordinates from screen position
            
            # First, calculate center tile coordinates for the current map view
            n = 2.0 ** self.zoom_level
            center_tile_x, center_tile_y = self._latlon_to_tile(self.center_lat, self.center_lon, self.zoom_level)
            
            # Convert screen position to tile offset
            # Screen center (width/2, height/2) corresponds to center_tile
            TILE_SIZE = 256
            tile_offset_x = (screen_x - self.width() / 2) / TILE_SIZE
            tile_offset_y = (screen_y - self.height() / 2) / TILE_SIZE
            
            # Calculate actual tile coordinates
            tile_x = center_tile_x + tile_offset_x
            tile_y = center_tile_y + tile_offset_y
            
            # Tile X to longitude
            longitude = (tile_x / n) * 360.0 - 180.0
            
            # Tile Y to latitude (Web Mercator inverse)
            normalized_y = tile_y / n
            sinh_arg = math.pi * (1.0 - 2.0 * normalized_y)
            sinh_arg = max(-100, min(100, sinh_arg))
            
            latitude_rad = math.atan(math.sinh(sinh_arg))
            latitude = math.degrees(latitude_rad)
            
            return (latitude, longitude)
        except Exception as e:
            logger.error(f"Error converting screen to GPS: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _latlon_to_tile(self, latitude: float, longitude: float, zoom: int) -> tuple:
        """
        Convert latitude/longitude to tile coordinates (Web Mercator).
        Same as MapRenderer._latlon_to_tile.
        """
        import math
        
        n = 2.0 ** zoom
        
        # Longitude to tile
        tile_x = (longitude + 180.0) / 360.0 * n
        
        # Latitude to tile
        lat_rad = math.radians(latitude)
        tile_y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
        
        return tile_x, tile_y
    
    def set_show_turning_points(self, show: bool):
        """Set whether to show turning points on the map."""
        self.show_turning_points = show
        self.render_map()
    
    def set_track_manager(self, track_manager):
        """Set the track manager for accessing track data."""
        self.track_manager = track_manager
        self.render_map()
    
    def on_track_list_selection_changed(self, track_id):
        """Handle track selection."""
        logger.info(f"[MAP] on_track_list_selection_changed called with track_id={track_id} (type={type(track_id).__name__})")
        self.selected_track_id = track_id
        self.selected_trackpoint_index = None
        self.selected_trackpoint_range = None  # Clear range selection when track changes
        logger.info(f"[MAP] After assignment: self.selected_track_id={self.selected_track_id}")
        self.render_map()
    
    def on_trackpoint_selected(self, track_id, trackpoint_index):
        """Handle trackpoint selection."""
        self.selected_track_id = track_id
        self.selected_trackpoint_index = trackpoint_index
        self.render_map()
    
    def on_point_selected(self, track_index, point_index):
        """Alias for on_trackpoint_selected for compatibility."""
        self.on_trackpoint_selected(track_index, point_index)
    
    def render_map(self):
        """Render the current map view."""
        if not self.mbtiles_provider:
            return
        
        try:
            # Create map renderer
            map_renderer = MapRenderer(
                self.width(),
                self.height(),
                self.mbtiles_provider,
                self.center_lat,
                self.center_lon,
                self.zoom_level
            )
            
            # Render tiles
            pil_image = map_renderer.render()
            
            # Draw tracks
            pil_image = self._draw_tracks_on_image(pil_image, map_renderer)
            
            # Draw UI controls
            pil_image = self.draw_ui_controls(pil_image)
            
            # Convert PIL to QPixmap
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                pil_image.save(tmp_path, 'PNG')
                pixmap = QPixmap(tmp_path)
                self.map_label.setPixmap(pixmap)
                self._reposition_controls()
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        
        except Exception as e:
            print(f"Error rendering map: {e}")
    
    def _draw_tracks_on_image(self, pil_image, map_renderer):
        """
        Draw tracks on the map.
        
        Logic:
        - Always draw the track path if a track is selected
        - show_turning_points controls visibility of turning points:
          - If True: Draw all turning points (yellow), selected one in blue (drawn last to appear on top)
          - If False: Draw no turning points normally
        - Exception: If show_turning_points is False BUT a trackpoint is selected,
          draw only that selected turning point in blue
        """
        if not self.track_manager:
            return pil_image
        
        # Only draw the selected track (handle both None and -1)
        logger.debug(f"[RENDER] Checking: selected_track_id={self.selected_track_id} (is None: {self.selected_track_id is None}, is < 0: {self.selected_track_id is not None and self.selected_track_id < 0})")
        if self.selected_track_id is None or (isinstance(self.selected_track_id, int) and self.selected_track_id < 0):
            logger.debug(f"[RENDER] selected_track_id is None or negative, skipping track rendering")
            return pil_image
        
        draw = ImageDraw.Draw(pil_image)
        
        tracks = self.track_manager.get_all_tracks()
        
        # Only draw the selected track
        if self.selected_track_id < len(tracks):
            track = tracks[self.selected_track_id]
            trackpoints = track.trackpoints
            
            if trackpoints:
                # ALWAYS draw the track path (regardless of show_turning_points)
                line_color = self.selected_track_color
                
                # Draw track line
                for i in range(len(trackpoints) - 1):
                    lat1 = trackpoints[i].latitude
                    lon1 = trackpoints[i].longitude
                    lat2 = trackpoints[i + 1].latitude
                    lon2 = trackpoints[i + 1].longitude
                    
                    screen1 = map_renderer.gps_to_screen(lat1, lon1)
                    screen2 = map_renderer.gps_to_screen(lat2, lon2)
                    
                    if screen1 and screen2:
                        draw.line([screen1, screen2], fill=line_color, width=self.track_path_width)
                
                # Draw turning points based on show_turning_points setting
                if self.show_turning_points:
                    # FIRST: Draw all unselected turning points (yellow)
                    for i, tp in enumerate(trackpoints):
                        # Skip selected point and range points - draw them last
                        if i == self.selected_trackpoint_index:
                            continue
                        if self.selected_trackpoint_range and (i == self.selected_trackpoint_range[0] or i == self.selected_trackpoint_range[1]):
                            continue
                        
                        screen = map_renderer.gps_to_screen(tp.latitude, tp.longitude)
                        
                        if screen:
                            x, y = screen
                            point_color = self.turning_point_color
                            r = self.turning_point_size
                            
                            # Draw circle for turning point
                            draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=point_color, outline=(255,255,255), width=1)
                    
                    # SECOND: Draw selected range points (from doubleSelected settings)
                    if self.selected_trackpoint_range is not None:
                        start_idx, end_idx = self.selected_trackpoint_range
                        for idx in [start_idx, end_idx]:
                            if idx < len(trackpoints):
                                tp = trackpoints[idx]
                                screen = map_renderer.gps_to_screen(tp.latitude, tp.longitude)
                                if screen:
                                    x, y = screen
                                    # Use doubleSelected color and size for range selection
                                    r = self.double_selected_turning_point_size
                                    draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=self.double_selected_turning_point_color, outline=(255,255,255), width=2)
                    
                    # THIRD: Draw single selected point LAST so it appears on top
                    elif self.selected_trackpoint_index is not None and self.selected_trackpoint_index < len(trackpoints):
                        tp = trackpoints[self.selected_trackpoint_index]
                        screen = map_renderer.gps_to_screen(tp.latitude, tp.longitude)
                        
                        if screen:
                            x, y = screen
                            point_color = self.selected_turning_point_color
                            r = self.selected_turning_point_size
                            
                            # Draw circle for selected turning point (on top)
                            draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=point_color, outline=(255,255,255), width=1)
                
                # NEW FEATURE: If show_turning_points is False but a trackpoint is selected,
                # show only that selected turning point in blue
                elif self.selected_trackpoint_index is not None:
                    if self.selected_trackpoint_index < len(trackpoints):
                        tp = trackpoints[self.selected_trackpoint_index]
                        screen = map_renderer.gps_to_screen(tp.latitude, tp.longitude)
                        
                        if screen:
                            x, y = screen
                            # Draw only the selected point in blue with larger radius
                            r = self.selected_turning_point_size
                            draw.ellipse([(x-r, y-r), (x+r, y+r)], 
                                       fill=self.selected_turning_point_color, 
                                       outline=(255,255,255), width=1)
        
        return pil_image
    
    def zoom_in(self):
        """Zoom in by one level."""
        if self.mbtiles_provider:
            available_zooms = self.mbtiles_provider.get_available_zooms()
            if available_zooms:
                max_zoom = max(available_zooms)
                new_zoom = min(self.zoom_level + 1, max_zoom)
                self.zoom_level = new_zoom
                self.zoom_level_label.setText(f"Z:{new_zoom}")
                self.render_map()
    
    def zoom_out(self):
        """Zoom out by one level."""
        if self.mbtiles_provider:
            available_zooms = self.mbtiles_provider.get_available_zooms()
            if available_zooms:
                min_zoom = min(available_zooms)
                new_zoom = max(self.zoom_level - 1, min_zoom)
                self.zoom_level = new_zoom
                self.zoom_level_label.setText(f"Z:{new_zoom}")
                self.render_map()
    
    def recenter_on_default(self):
        """Recenter on default position."""
        self.center_lat = 56.168
        self.center_lon = 15.586
        self.render_map()
    
    def reload_settings(self):
        """Reload turning points settings from config and re-render map."""
        from config.app_config_yaml import AppConfig
        config = AppConfig()
        
        # Reload all turning points settings
        self.show_turning_points = config.get_bool('Appearance.MapDisplay.TurningPoints.show', True)
        self.turning_point_color = self._hex_to_rgb(config.get_str('Appearance.MapDisplay.TurningPoints.color', 'FFFF00'))
        self.selected_turning_point_color = self._hex_to_rgb(config.get_str('Appearance.MapDisplay.TurningPoints.selected.color', '0000FF'))
        self.turning_point_size = config.get_int('Appearance.MapDisplay.TurningPoints.size', 4)
        self.selected_turning_point_size = config.get_int('Appearance.MapDisplay.TurningPoints.selected.size', 7)
        
        # Reload double selected (range) turning points settings
        self.double_selected_turning_point_color = self._hex_to_rgb(config.get_str('Appearance.MapDisplay.TurningPoints.doubleSelected.color', 'FFA500'))
        self.double_selected_turning_point_size = config.get_int('Appearance.MapDisplay.TurningPoints.doubleSelected.size', 8)
        
        # Re-render the map with new settings
        self.render_map()
        logger.debug("Map settings reloaded from config")
    
    def mousePressEvent(self, event):
        """Handle mouse button press."""
        if event.button() == Qt.RightButton:
            # Right-click: show context menu
            self._show_context_menu(event.pos())
            return
        
        if event.button() == Qt.LeftButton:
            x, y = event.x(), event.y()
            
            # Check if clicking on zoom_in button (top)
            button_x = self.CONTROLS_PADDING_LEFT
            button_y = self.CONTROLS_PADDING_TOP
            if (button_x <= x <= button_x + self.ZOOM_BUTTON_SIZE and
                button_y <= y <= button_y + self.ZOOM_BUTTON_SIZE):
                self.zoom_in()
                return
            
            # Check if clicking on zoom_out button (middle)
            button_y = self.CONTROLS_PADDING_TOP + self.ZOOM_BUTTON_SIZE + self.ZOOM_BUTTON_SPACING
            if (button_x <= x <= button_x + self.ZOOM_BUTTON_SIZE and
                button_y <= y <= button_y + self.ZOOM_BUTTON_SIZE):
                self.zoom_out()
                return
            
            # Check if clicking on recenter button (bottom)
            button_y = self.CONTROLS_PADDING_TOP + 2 * (self.ZOOM_BUTTON_SIZE + self.ZOOM_BUTTON_SPACING) + 30  # Approximate label height
            if (button_x <= x <= button_x + self.ZOOM_BUTTON_SIZE and
                button_y <= y <= button_y + self.ZOOM_BUTTON_SIZE):
                self.recenter_on_default()
                return
            
            # Check if clicking on a turning point (PRIORITY: check this first for Shift+click range selection)
            if self.show_turning_points or self.selected_trackpoint_index is not None or self.selected_trackpoint_range is not None:
                clicked_point_index = self._find_turning_point_at_click(x, y)
                if clicked_point_index is not None:
                    # Check if Shift is pressed (for range selection on an existing point)
                    if event.modifiers() & Qt.ShiftModifier:
                        # Shift+click on a point: try to select range
                        if self.selected_trackpoint_index is not None:
                            # We have a single point selected - try to make it a range with this point
                            min_idx = min(self.selected_trackpoint_index, clicked_point_index)
                            max_idx = max(self.selected_trackpoint_index, clicked_point_index)
                            
                            # Only allow selecting consecutive neighbors
                            if max_idx - min_idx == 1:
                                self.selected_trackpoint_range = (min_idx, max_idx)
                                self.selected_trackpoint_index = None  # Clear single selection
                                self.range_selection_changed.emit(True)  # Signal range change
                                logger.info(f"[RANGE] Selected range: ({min_idx}, {max_idx})")
                                self.render_map()
                                return
                        elif self.selected_trackpoint_range is not None:
                            # We have a range - try to extend or modify it
                            start_idx, end_idx = self.selected_trackpoint_range
                            min_idx = min(start_idx, end_idx, clicked_point_index)
                            max_idx = max(start_idx, end_idx, clicked_point_index)
                            
                            # Only allow selecting consecutive neighbors
                            if max_idx - min_idx == 1:
                                self.selected_trackpoint_range = (min_idx, max_idx)
                                self.render_map()
                        # For Shift+click on point, don't fall through
                        return
                    
                    # Normal click (no Shift): select single point
                    self.selected_trackpoint_index = clicked_point_index
                    if self.selected_trackpoint_range is not None:
                        self.range_selection_changed.emit(False)  # Signal range cleared
                    self.selected_trackpoint_range = None  # Clear range selection
                    self.point_clicked.emit(str(self.selected_track_id), clicked_point_index)
                    
                    # Start drag mode for moving the point
                    self.dragging_trackpoint = True
                    self.dragged_trackpoint_index = clicked_point_index
                    self.drag_start_x = x
                    self.drag_start_y = y
                    
                    # Store original coordinates in case we need to revert
                    if self.track_manager:
                        trackpoints = self.track_manager.get_selected_trackpoints()
                        if clicked_point_index < len(trackpoints):
                            tp = trackpoints[clicked_point_index]
                            self.drag_original_lat = tp.latitude
                            self.drag_original_lon = tp.longitude
                    
                    self.render_map()
                    return
                
                # If range selected but no point clicked, insert new point at cursor and start dragging
                if self.selected_trackpoint_range is not None:
                    start_idx, end_idx = self.selected_trackpoint_range
                    
                    # Convert click position to GPS
                    gps_coords = self.screen_to_gps(x, y)
                    if gps_coords and self.track_manager and self.selected_track_id is not None:
                        lat, lon = gps_coords
                        
                        # Ensure track is selected in track_manager
                        self.track_manager.select_track(self.selected_track_id)
                        
                        # Insert new trackpoint at position between the two selected points
                        insert_position = end_idx
                        success = self.track_manager.add_trackpoint_selected_with_history(
                            lat, lon, None, insert_position
                        )
                        
                        if success:
                            # Immediately start drag mode for the newly inserted point
                            self.dragging_trackpoint = True
                            self.dragged_trackpoint_index = insert_position
                            self.drag_start_x = x
                            self.drag_start_y = y
                            
                            # Store original coordinates (the position we just inserted)
                            trackpoints = self.track_manager.get_selected_trackpoints()
                            if insert_position < len(trackpoints):
                                tp = trackpoints[insert_position]
                                self.drag_original_lat = tp.latitude
                                self.drag_original_lon = tp.longitude
                            
                            # Clear range selection and select the new point
                            self.selected_trackpoint_range = None
                            self.selected_trackpoint_index = insert_position
                            
                            # Refresh list and render
                            main_window = QApplication.instance().activeWindow()
                            if main_window and hasattr(main_window, 'trackpoint_list_widget'):
                                main_window.trackpoint_list_widget.refresh_trackpoints()
                            
                            self.render_map()
                            logger.info(f"[INSERT+DRAG] Inserted point at {insert_position}, starting drag")
                            return
            
            # NEW: Shift+click on empty space (only if no point was found above) - insert point at end (or as first point)
            if event.modifiers() & Qt.ShiftModifier:
                logger.info(f"[DEBUG] Shift+click on empty space at ({x}, {y})")
                gps_coords = self.screen_to_gps(x, y)
                logger.info(f"[DEBUG] gps_coords={gps_coords}, track_manager={self.track_manager}, selected_track_id={self.selected_track_id}")
                if gps_coords and self.track_manager:
                    lat, lon = gps_coords
                    
                    # If no track selected, create a new one
                    if self.selected_track_id is None:
                        from src.core.track_manager import TrackData
                        new_track = TrackData(name=f"Track {len(self.track_manager.get_all_tracks()) + 1}", trackpoints=[])
                        self.track_manager.tracks.append(new_track)
                        self.selected_track_id = len(self.track_manager.get_all_tracks()) - 1
                        self.track_manager.select_track(self.selected_track_id)
                        logger.info(f"[DEBUG] Created new track: {new_track.name} at index {self.selected_track_id}")
                        
                        # Emit signal to update track list in UI
                        main_window = QApplication.instance().activeWindow()
                        if main_window and hasattr(main_window, 'track_list_widget'):
                            main_window.track_list_widget.refresh_tracks()
                            main_window.track_list_widget.select_track(self.selected_track_id)
                    
                    # Now ensure track is selected in track_manager
                    self.track_manager.select_track(self.selected_track_id)
                    
                    # Get current trackpoint count
                    trackpoints = self.track_manager.get_selected_trackpoints()
                    if trackpoints:
                        # Insert at end
                        insert_position = len(trackpoints)
                    else:
                        # Insert as first point
                        insert_position = 0
                    
                    # Insert new trackpoint
                    success = self.track_manager.add_trackpoint_selected_with_history(
                        lat, lon, None, insert_position
                    )
                    logger.info(f"[DEBUG] Insert result: success={success}")
                    
                    if success:
                        # Select the new point
                        self.selected_trackpoint_index = insert_position
                        self.selected_trackpoint_range = None
                        
                        # Refresh list and render
                        main_window = QApplication.instance().activeWindow()
                        if main_window and hasattr(main_window, 'trackpoint_list_widget'):
                            main_window.trackpoint_list_widget.refresh_trackpoints()
                        
                        self.render_map()
                        logger.info(f"[SHIFT+INSERT] Inserted point at position {insert_position}")
                        return
                return  # Don't pan if Shift+click, even if insert failed
            
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement for panning or dragging trackpoint."""
        
        # Handle trackpoint dragging
        if self.dragging_trackpoint and self.dragged_trackpoint_index is not None:
            x, y = event.x(), event.y()
            
            # Convert screen coordinates to GPS
            gps_coords = self.screen_to_gps(x, y)
            if gps_coords and self.track_manager:
                lat, lon = gps_coords
                
                # Update the trackpoint in memory (temporary, not saved yet)
                trackpoints = self.track_manager.get_selected_trackpoints()
                if self.dragged_trackpoint_index < len(trackpoints):
                    # Update in-memory temporarily for visual feedback
                    tp = trackpoints[self.dragged_trackpoint_index]
                    tp.latitude = lat
                    tp.longitude = lon
                    
                    # Emit signal to update trackpoint list in real-time
                    self.trackpoint_dragging.emit(self.dragged_trackpoint_index, lat, lon)
                    
                    # Re-render to show the point at new position
                    self.render_map()
            return
        
        # Handle map panning
        if self.pan_start_x is not None and self.pan_start_y is not None:
            delta_x = self.pan_start_x - event.x()
            delta_y = self.pan_start_y - event.y()
            
            if self.mbtiles_provider:
                # Pan using Web Mercator math
                import math
                TILE_SIZE = 256
                tiles_at_zoom = 2 ** self.zoom_level
                earth_circumference_m = 40075016.686
                
                cos_lat = math.cos(math.radians(self.center_lat))
                m_per_pixel_lon = (earth_circumference_m * cos_lat) / (TILE_SIZE * tiles_at_zoom)
                m_per_pixel_lat = earth_circumference_m / (TILE_SIZE * tiles_at_zoom)
                
                deg_per_m = 1.0 / 111320.0
                
                lon_delta = delta_x * m_per_pixel_lon * deg_per_m
                lat_delta = -delta_y * m_per_pixel_lat * deg_per_m
                
                self.center_lon += lon_delta
                self.center_lat += lat_delta
                
                self.render_map()
            
            self.pan_start_x = event.x()
            self.pan_start_y = event.y()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse button release."""
        if event.button() == Qt.LeftButton:
            # Handle end of trackpoint drag
            if self.dragging_trackpoint and self.dragged_trackpoint_index is not None:
                # Save the new position as an undoable command
                if self.track_manager:
                    trackpoints = self.track_manager.get_selected_trackpoints()
                    if self.dragged_trackpoint_index < len(trackpoints):
                        tp = trackpoints[self.dragged_trackpoint_index]
                        new_lat = tp.latitude
                        new_lon = tp.longitude
                        
                        # Create undo/redo command for moving the point
                        self.track_manager.move_trackpoint_with_history(
                            self.track_manager.get_selected_track_index(),
                            self.dragged_trackpoint_index,
                            new_lat,
                            new_lon,
                            tp.elevation
                        )
                        
                        # Emit signal to update UI
                        self.point_clicked.emit(str(self.selected_track_id), self.dragged_trackpoint_index)
                        
                        # Update ONLY the one row that changed (not the entire table!)
                        main_window = QApplication.instance().activeWindow()
                        if main_window and hasattr(main_window, 'trackpoint_list_widget'):
                            # Update just the row that was moved with new coordinates
                            main_window.trackpoint_list_widget.update_trackpoint_row(
                                self.dragged_trackpoint_index, new_lat, new_lon
                            )
                
                # Exit drag mode
                self.dragging_trackpoint = False
                self.dragged_trackpoint_index = None
                self.drag_start_x = None
                self.drag_start_y = None
                self.drag_original_lat = None
                self.drag_original_lon = None
                
                # NO render_map() here - the map already shows the point in correct position
                # from the last mouseMoveEvent during dragging
            else:
                # Normal pan end
                self.pan_start_x = None
                self.pan_start_y = None
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming centered on cursor position."""
        if not self.mbtiles_provider:
            return
        
        # Get mouse cursor position relative to map widget
        mouse_pos = event.pos()
        mouse_x = mouse_pos.x()
        mouse_y = mouse_pos.y()
        
        # Create renderer at CURRENT state to get cursor GPS location
        current_renderer = MapRenderer(
            self.width(),
            self.height(),
            self.mbtiles_provider,
            self.center_lat,
            self.center_lon,
            self.zoom_level
        )
        
        # Get what GPS point is currently under the cursor
        cursor_lat, cursor_lon = current_renderer.screen_to_gps(mouse_x, mouse_y)
        
        # Determine zoom direction and get available zooms
        zoom_in = event.angleDelta().y() > 0
        available_zooms = self.mbtiles_provider.get_available_zooms()
        
        if available_zooms:
            min_zoom = min(available_zooms)
            max_zoom = max(available_zooms)
            
            if zoom_in:
                new_zoom = min(self.zoom_level + 1, max_zoom)
            else:
                new_zoom = max(self.zoom_level - 1, min_zoom)
            
            # Only proceed if zoom actually changed
            if new_zoom != self.zoom_level:
                self.zoom_level = new_zoom
                self.zoom_level_label.setText(f"Z:{new_zoom}")
                
                # Create new renderer with NEW zoom level, but centered on the cursor's GPS location
                # This way, the GPS point that was under the cursor will stay under the cursor
                new_renderer = MapRenderer(
                    self.width(),
                    self.height(),
                    self.mbtiles_provider,
                    cursor_lat,  # Center on the GPS point under cursor
                    cursor_lon,
                    new_zoom
                )
                
                # Now find where that GPS point appears on screen in the new zoom
                # We want it to be at (mouse_x, mouse_y)
                cursor_screen_x, cursor_screen_y = new_renderer.gps_to_screen(cursor_lat, cursor_lon)
                
                # Calculate the offset (how far from center the cursor point is)
                offset_x = mouse_x - self.width() / 2
                offset_y = mouse_y - self.height() / 2
                
                # The GPS point is currently at screen center. We need to move it to mouse position.
                # Convert the screen offset to GPS offset
                screen_center_lat, screen_center_lon = new_renderer.screen_to_gps(self.width() / 2, self.height() / 2)
                mouse_pos_lat, mouse_pos_lon = new_renderer.screen_to_gps(mouse_x, mouse_y)
                
                # Adjust center so cursor point appears at mouse location
                self.center_lat = cursor_lat + (screen_center_lat - mouse_pos_lat)
                self.center_lon = cursor_lon + (screen_center_lon - mouse_pos_lon)
                
                self.render_map()
    
    def resizeEvent(self, event):
        """Handle window resize."""
        super().resizeEvent(event)
        self.render_map()
        self._reposition_controls()
    
    def _reposition_controls(self):
        """Reposition invisible button hitboxes."""
        x_pos = self.CONTROLS_PADDING_LEFT
        y_pos = self.CONTROLS_PADDING_TOP
        
        self.zoom_in_button.move(x_pos, y_pos)
        
        y_pos += self.ZOOM_BUTTON_SIZE + self.ZOOM_BUTTON_SPACING
        self.zoom_out_button.move(x_pos, y_pos)
        
        y_pos += self.ZOOM_BUTTON_SIZE + self.ZOOM_BUTTON_SPACING
        self.zoom_level_label.move(x_pos, y_pos)
        
        y_pos += self.zoom_level_label.height() + self.ZOOM_BUTTON_SPACING
        self.recenter_button.move(x_pos, y_pos)
    
    def draw_ui_controls(self, pil_image):
        """Draw UI control buttons on PIL image with transparency."""
        # Create a transparent overlay for buttons
        overlay = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Button colors with alpha channel (transparency)
        # RGBA: (R, G, B, Alpha) where 255 is opaque, 0 is fully transparent
        button_bg = (52, 144, 220, 200)  # Blue with 200/255 opacity (~78% opaque)
        button_text = (255, 255, 255, 255)  # White, fully opaque
        
        x_pos = self.CONTROLS_PADDING_LEFT
        y_pos = self.CONTROLS_PADDING_TOP
        button_size = self.ZOOM_BUTTON_SIZE
        corner_radius = 8
        
        # Draw zoom in button - simple rounded rectangle
        bbox = [x_pos, y_pos, x_pos + button_size, y_pos + button_size]
        overlay_draw.rounded_rectangle(bbox, radius=corner_radius, fill=button_bg)
        center = button_size // 2
        # Draw + icon
        overlay_draw.line([(x_pos + center - 6, y_pos + center), (x_pos + center + 6, y_pos + center)], fill=button_text, width=2)
        overlay_draw.line([(x_pos + center, y_pos + center - 6), (x_pos + center, y_pos + center + 6)], fill=button_text, width=2)
        
        # Draw zoom out button
        y_pos += button_size + self.ZOOM_BUTTON_SPACING
        bbox = [x_pos, y_pos, x_pos + button_size, y_pos + button_size]
        overlay_draw.rounded_rectangle(bbox, radius=corner_radius, fill=button_bg)
        center = button_size // 2
        # Draw - icon
        overlay_draw.line([(x_pos + center - 6, y_pos + center), (x_pos + center + 6, y_pos + center)], fill=button_text, width=2)
        
        # Draw zoom level label
        y_pos += button_size + self.ZOOM_BUTTON_SPACING
        zoom_text = f"Z:{self.zoom_level}"
        bbox = [x_pos, y_pos, x_pos + button_size, y_pos + button_size]
        overlay_draw.rounded_rectangle(bbox, radius=corner_radius, fill=button_bg)
        overlay_draw.text((x_pos + 8, y_pos + 12), zoom_text, fill=button_text)
        
        # Draw recenter button
        y_pos += button_size + self.ZOOM_BUTTON_SPACING
        bbox = [x_pos, y_pos, x_pos + button_size, y_pos + button_size]
        overlay_draw.rounded_rectangle(bbox, radius=corner_radius, fill=button_bg)
        center_x = x_pos + button_size // 2
        center_y = y_pos + button_size // 2
        # Draw circle target icon
        overlay_draw.ellipse((center_x - 12, center_y - 12, center_x + 12, center_y + 12), outline=button_text, width=2)
        overlay_draw.ellipse((center_x - 7, center_y - 7, center_x + 7, center_y + 7), outline=button_text, width=1)
        overlay_draw.ellipse((center_x - 3, center_y - 3, center_x + 3, center_y + 3), fill=button_text)
        
        # Composite the overlay onto the image
        pil_image = Image.alpha_composite(pil_image, overlay)
        return pil_image
    
    def _show_context_menu(self, pos):
        """Show context menu on right-click."""
        from PyQt5.QtWidgets import QMenu
        
        menu = QMenu()
        
        # If range is selected: show insert option
        if self.selected_trackpoint_range is not None:
            insert_action = menu.addAction("Insert Trackpoint Between Selected")
            insert_action.triggered.connect(self._on_insert_triggered)
        # If single point is selected: show delete options
        elif self.selected_trackpoint_index is not None:
            delete_action = menu.addAction("Delete Trackpoint")
            delete_from_start_action = menu.addAction("Delete from Start to Here")
            delete_from_end_action = menu.addAction("Delete from Here to End")
            
            delete_action.triggered.connect(self._on_delete_single)
            delete_from_start_action.triggered.connect(self._on_delete_from_start)
            delete_from_end_action.triggered.connect(self._on_delete_from_end)
        else:
            menu.addAction("Select a point to delete or Shift+Click two neighbors to insert").setEnabled(False)
        
        menu.exec_(self.mapToGlobal(pos))
    
    def _on_insert_triggered(self):
        """Handle insert action from context menu."""
        # Find the main window and call its insert action
        main_window = QApplication.instance().activeWindow()
        if main_window and hasattr(main_window, 'action_insert_trackpoint'):
            main_window.action_insert_trackpoint()
    
    def _on_delete_single(self):
        """Handle delete single trackpoint action."""
        main_window = QApplication.instance().activeWindow()
        if main_window and hasattr(main_window, 'trackpoint_list_widget'):
            if self.selected_trackpoint_index is not None:
                main_window.trackpoint_list_widget._delete_trackpoint(self.selected_trackpoint_index)
    
    def _on_delete_from_start(self):
        """Handle delete from start to here action."""
        main_window = QApplication.instance().activeWindow()
        if main_window and hasattr(main_window, 'trackpoint_list_widget'):
            if self.selected_trackpoint_index is not None:
                main_window.trackpoint_list_widget._delete_from_start(self.selected_trackpoint_index)
    
    def _on_delete_from_end(self):
        """Handle delete from here to end action."""
        main_window = QApplication.instance().activeWindow()
        if main_window and hasattr(main_window, 'trackpoint_list_widget'):
            if self.selected_trackpoint_index is not None:
                main_window.trackpoint_list_widget._delete_from_end(self.selected_trackpoint_index)
    
    def _find_turning_point_at_click(self, click_x, click_y):
        """
        Find the closest turning point to a click location.
        Only checks points that are on-screen for performance.
        
        Args:
            click_x (int): X coordinate of click in widget space
            click_y (int): Y coordinate of click in widget space
            
        Returns:
            int or None: Index of the closest turning point within click radius, or None if none found
        """
        if not self.track_manager or self.selected_track_id is None:
            return None
        
        tracks = self.track_manager.get_all_tracks()
        if self.selected_track_id >= len(tracks):
            return None
        
        track = tracks[self.selected_track_id]
        trackpoints = track.trackpoints
        
        if not trackpoints:
            return None
        
        # Create map renderer with current map position to convert GPS to screen coordinates
        map_renderer = MapRenderer(self.width(), self.height(), self.mbtiles_provider,
                                   self.center_lat, self.center_lon, self.zoom_level)
        
        # Click tolerance in pixels (allow clicking within this distance of a point)
        CLICK_TOLERANCE = 10
        
        closest_distance = CLICK_TOLERANCE + 1  # Start beyond tolerance
        closest_index = None
        
        # Create search area around click to limit points to check
        SEARCH_RADIUS = CLICK_TOLERANCE + 20  # Extra margin for safety
        search_left = click_x - SEARCH_RADIUS
        search_right = click_x + SEARCH_RADIUS
        search_top = click_y - SEARCH_RADIUS
        search_bottom = click_y + SEARCH_RADIUS
        
        # Find the closest turning point to the click (only check on-screen points in search area)
        for i, tp in enumerate(trackpoints):
            screen = map_renderer.gps_to_screen(tp.latitude, tp.longitude)
            
            if screen:
                screen_x, screen_y = screen
                
                # Quick bounding box check first (much faster than distance calculation)
                if not (search_left <= screen_x <= search_right and 
                        search_top <= screen_y <= search_bottom):
                    continue  # Skip points outside search area
                
                # Calculate distance from click to this point
                distance = ((click_x - screen_x) ** 2 + (click_y - screen_y) ** 2) ** 0.5
                
                # If this is the closest point so far and within tolerance
                if distance < closest_distance:
                    closest_distance = distance
                    closest_index = i
        
        return closest_index
