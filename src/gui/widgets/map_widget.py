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

from src.shared.map.mbtiles_provider import MBTilesProvider
from src.shared.map.map_renderer import MapRenderer
from src.map.map_buttons import MapButtonManager, MapButtonConfig
from src.shared.map.crosshair_drawer import draw_crosshair

logger = logging.getLogger(__name__)


class MapWidget(QWidget):
    """
    Interactive map widget for displaying GPS tracks with pan, zoom, and trackpoint editing.
    
    ARCHITECTURE OVERVIEW
    =====================
    MapWidget is the visual anchor of the application. It displays:
    1. Map tiles (MBTiles format) as background
    2. Selected track as a colored path
    3. Trackpoints (turning points) as interactive circles
    4. UI controls (zoom +/-, recenter button, zoom level display)
    5. Crosshair at center (optional)
    
    CRITICAL: THREE COORDINATE SYSTEMS
    ==================================
    Conversions between systems happen constantly. Mistakes here cause visual errors.
    
    1. GPS Coordinates (Decimal Degrees)
       - What: Latitude/Longitude as decimal numbers
       - Example: (57.5126°N, 12.2584°E)
       - Range: Lat [-90, 90], Lon [-180, 180]
       - Source: GPX files, business logic
       - Used for: Storing data, calculations
    
    2. Web Mercator (Projected)
       - What: GPS converted to screen-like coordinate system
       - Reason: Maps are flat, Earth is spherical
       - Formula: x = lon * R, y = log(tan(π/4 + lat/2)) * R (where R = radius)
       - Tiles: Organized as grid in Web Mercator space
       - Problem: Y-axis inverts at equator (confusing!)
       - Used for: Tile indexing, pan/zoom calculations
    
    3. Screen Pixels
       - What: Actual display coordinates (0,0 at top-left)
       - Range: (0, 0) to (width-1, height-1)
       - Used for: Mouse events, drawing, button hit detection
       - Problem: Must convert GPS → Screen for rendering AND Screen → GPS for click detection
    
    Conversion Chain:
    GPS (57.5126°, 12.2584°)
        ↓
    [gps_to_mercator] ← MapRenderer handles this
        ↓
    Mercator (x=1403.9km, y=7473.2km)
        ↓
    [mercator_to_screen] ← MapRenderer handles this
        ↓
    Screen (x=423px, y=187px)
    
    For click detection, reverse the chain:
    Screen (x=423px, y=187px)
        ↓
    [screen_to_mercator] ← Calculate from screen size & map bounds
        ↓
    Mercator (x=1403.9km, y=7473.2km)
        ↓
    [mercator_to_gps] ← Reverse Mercator projection
        ↓
    GPS (57.5126°, 12.2584°)
    
    RENDERING PIPELINE
    ==================
    Order matters! Render sequence determines what appears on top.
    
    Step 1: RENDER BASE TILES
            - MapRenderer.render() fetches tiles from MBTiles
            - Returns PIL Image with tile grid
            - Tiles rendered in Web Mercator space
    
    Step 2: DRAW TRACK PATH
            - For selected track only
            - Render ALL trackpoints as a line
            - Uses outline effect (thicker outline color first, then thin line on top)
            - Always rendered (regardless of show_turning_points setting)
    
    Step 3: DRAW TURNING POINTS (Trackpoints)
            - Yellow dots for unselected points
            - Blue dot for selected single point
            - Orange dots for range-selected points (2 points marked for insertion)
            - Order: Unselected first (bottom), range second, single last (top layer)
            - Why: Selected points appear on top visually
    
    Step 4: DRAW UI CONTROLS
            - Zoom +/- buttons
            - Recenter button
            - Zoom level display
            - Crosshair at center (optional)
            - Also calculates button hit areas (for click detection)
    
    Z-ORDER (Top to Bottom):
    1. UI Controls (buttons, labels)
    2. Selected trackpoint (single selection, blue)
    3. Range-selected trackpoints (orange)
    4. Unselected trackpoints (yellow)
    5. Track path (red line with outline)
    6. Map tiles (background)
    
    TRACKPOINT INTERACTION STATE MACHINE
    ====================================
    Trackpoints can be modified by dragging. State flow:
    
    State 1: IDLE (no mouse action)
             - Variables: dragging_trackpoint = False
             - User can see trackpoints, clicking prepares for drag
    
    State 2: MOUSE PRESSED (user clicked on trackpoint)
             - Event: mousePressEvent() called
             - Actions:
               a. Detect which trackpoint under cursor (hit detection with radius)
               b. If trackpoint found:
                  - Store: dragged_trackpoint_index = i
                  - Store: drag_start_x, drag_start_y (cursor position)
                  - Store: drag_original_lat, drag_original_lon (point's original position)
                  - Set: dragging_trackpoint = True
               c. If button clicked: Handle zoom/recenter/show buttons
    
    State 3: MOUSE MOVE (user dragging with button held)
             - Event: mouseMoveEvent() called while mouse button held
             - Condition: dragging_trackpoint == True
             - Actions:
               a. Calculate new cursor position
               b. Convert screen coordinates to GPS coordinates
               c. Update trackpoint position in business logic
               d. Emit signal: trackpoint_dragging(index, new_lat, new_lon)
               e. Render map (visual feedback of moving point)
             - Visual: Point follows cursor in real-time
    
    State 4: MOUSE RELEASED (user released button)
             - Event: mouseReleaseEvent() called
             - Actions:
               a. If was dragging (dragging_trackpoint == True):
                  - Create command for undo/redo
                  - Call track_manager with final coordinates
                  - Set: dragging_trackpoint = False
               b. Clean up drag state variables
             - Result: Point locked at final position, undo available
    
    Edge Cases in State Machine:
    - User presses outside any trackpoint: No drag state entered
    - User presses on button: Button action, not drag
    - User presses on trackpoint, drags outside map: Still updates while outside
    - User rapidly presses/releases: State properly resets each time
    
    HIT DETECTION (Click Detection Algorithm)
    ==========================================
    When user clicks, we need to determine:
    1. Is it a button click? (zoom +/-, recenter, etc.)
    2. Is it a trackpoint click? (for editing)
    3. Is it empty space? (for panning)
    
    Algorithm for Trackpoint Click Detection:
    
    For each trackpoint in selected track:
        1. Convert GPS (lat, lon) to screen pixels using map_renderer
        2. Calculate distance from cursor to point
        3. If distance <= click_radius (e.g., 10 pixels):
            - Point is under cursor
            - Use smallest distance if multiple points close
            - Enter drag state
    
    Why radius check? GPS points are tiny (1 pixel), hard to click. Radius makes it easy.
    
    SIGNAL EMISSIONS (Communication with MainWindow)
    ================================================
    MapWidget emits signals when important events happen:
    
    - map_ready: When map finishes initial render
    - track_clicked(track_id): When user clicks track path
    - point_clicked(track_id, point_id): When user clicks trackpoint
    - range_selection_changed(bool): When user selects/deselects 2 points (for insertion)
    - trackpoint_dragging(index, lat, lon): During drag, for real-time feedback
    
    MainWindow receives these and coordinates with other widgets.
    
    CONFIG INTEGRATION
    ==================
    MapWidget reads appearance settings from config:
    - track_color: Track path color (hex RRGGBB)
    - track_path_width: Line width in pixels
    - turning_point_color: Default trackpoint color
    - turning_point_size: Trackpoint radius
    - selected_turning_point_color: Blue color when selected
    - Coordinate limits: Default center, zoom levels
    
    Settings can be changed in real-time:
    - Apply button in Settings widget → emits signal
    - MainWindow receives → calls widget refresh methods
    - MapWidget re-renders with new colors/sizes
    
    STATE VARIABLES (Track Application State)
    ==========================================
    selected_track_id: Which track visible (-1 = none)
    selected_trackpoint_index: Single point highlighted (-1 = none)
    selected_trackpoint_range: Two points marked (tuple or None)
    show_turning_points: Display trackpoints? (True/False toggle)
    
    Dragging State:
    dragging_trackpoint: Currently dragging? (T/F)
    dragged_trackpoint_index: Which point? (index or None)
    drag_start_x, drag_start_y: Initial cursor position
    drag_original_lat, drag_original_lon: Point's original position (for visualization)
    
    PERFORMANCE CONSIDERATIONS
    ==========================
    Large tracks (1000+ points) can cause slowness:
    
    Problem Areas:
    1. Tile rendering: ~500ms for full screen
    2. Track path drawing: O(n) where n = trackpoints
    3. Trackpoint rendering: O(n)
    4. Hit detection: O(n) for each click
    
    Optimizations (not currently implemented):
    - Cache rendered tiles
    - Cull points outside screen bounds
    - Use spatial hash for hit detection
    - Batch render operations
    
    Current approach: Works fine for typical tracks (100-1000 points).
    
    Signals:
        map_ready: Emitted when map finishes rendering
        track_clicked: Emitted when track path clicked
        point_clicked: Emitted when trackpoint clicked
        range_selection_changed: Emitted when point range changes
        trackpoint_dragging: Emitted during trackpoint drag (real-time feedback)
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
    
    def __init__(self, parent=None, mbtiles_provider=None, config=None):
        """
        Initialize the map widget.
        
        Args:
            parent (QWidget): Parent widget
            mbtiles_provider (MBTilesProvider): The tile provider to use
            config (AppConfig): Application configuration (optional, loads from scratch if not provided)
        """
        super().__init__(parent)
        
        self.mbtiles_provider = mbtiles_provider
        self.track_manager = None
        self.selected_track_id = None
        self.selected_trackpoint_index = None
        self.selected_trackpoint_range = None  # NEW: For selecting 2 neighboring points (start_idx, end_idx)
        self.show_turning_points = True  # Show/hide turning points
        
        # Load track display settings from config
        if config is None:
            from config.app_config_yaml import AppConfig
            config = AppConfig()
        
        # Parse colors from config (hex format: RRGGBB)
        # TrackPath - body and outline
        self.track_color = self._hex_to_rgb(config.get_str('appearance.map_display.track_path.body.color', 'FF0000'))
        self.track_path_width = config.get_int('appearance.map_display.track_path.body.width', 3)
        self.track_path_outline_color = self._hex_to_rgb(config.get_str('appearance.map_display.track_path.outline.color', 'FFFFFF'))
        self.track_path_outline_width = config.get_int('appearance.map_display.track_path.outline.width', 1)
        
        # Trackpoints settings
        self.show_turning_points = config.get_bool('appearance.map_display.trackpoints.show', True)
        
        # General trackpoints (body and outline)
        self.turning_point_color = self._hex_to_rgb(config.get_str('appearance.map_display.trackpoints.GeneralPoints.body.color', 'FFFF00'))
        self.turning_point_size = config.get_int('appearance.map_display.trackpoints.GeneralPoints.body.size', 4)
        self.turning_point_outline_color = self._hex_to_rgb(config.get_str('appearance.map_display.trackpoints.GeneralPoints.outline.color', 'FFFFFF'))
        self.turning_point_outline_width = config.get_int('appearance.map_display.trackpoints.GeneralPoints.outline.size', 1)
        
        # Selected trackpoints (body and outline)
        self.selected_turning_point_color = self._hex_to_rgb(config.get_str('appearance.map_display.trackpoints.SelectedPoints.body.color', '0000FF'))
        self.selected_turning_point_size = config.get_int('appearance.map_display.trackpoints.SelectedPoints.body.size', 7)
        self.selected_turning_point_outline_color = self._hex_to_rgb(config.get_str('appearance.map_display.trackpoints.SelectedPoints.outline.color', 'FFFFFF'))
        self.selected_turning_point_outline_width = config.get_int('appearance.map_display.trackpoints.SelectedPoints.outline.size', 2)
        
        # Double selected trackpoints (body and outline)
        self.double_selected_turning_point_color = self._hex_to_rgb(config.get_str('appearance.map_display.trackpoints.DoubleSelectedPoints.body.color', 'FFA500'))
        self.double_selected_turning_point_size = config.get_int('appearance.map_display.trackpoints.DoubleSelectedPoints.body.size', 8)
        self.double_selected_turning_point_outline_color = self._hex_to_rgb(config.get_str('appearance.map_display.trackpoints.DoubleSelectedPoints.outline.color', 'FFFFFF'))
        self.double_selected_turning_point_outline_width = config.get_int('appearance.map_display.trackpoints.DoubleSelectedPoints.outline.size', 2)
        
        # Crosshair settings
        self.show_crosshair = config.get_bool('appearance.map_display.Crosshair.show', True)
        self.crosshair_color = self._hex_to_rgb(config.get_str('appearance.map_display.Crosshair.body.color', 'FF0000'))
        self.crosshair_outline_color = self._hex_to_rgb(config.get_str('appearance.map_display.Crosshair.outline.color', 'FFFFFF'))
        self.crosshair_outline_width = config.get_int('appearance.map_display.Crosshair.outline.width', 1)
        self.crosshair_size = config.get_int('appearance.map_display.Crosshair.size', 20)
        
        # Zoom bounds (will be set when MBTiles is loaded, default to safe values)
        self.min_zoom = 1
        self.max_zoom = 20
        
        # Map state - load from mbtiles first, then recent, then default
        # Store mbtiles_center/zoom for reference (used by Recenter button)
        self.mbtiles_center_lon = None
        self.mbtiles_center_lat = None
        self.mbtiles_zoom = None
        
        if mbtiles_provider:
            try:
                lon, lat, zoom = mbtiles_provider.get_mbtiles_center_with_fallback()
                self.mbtiles_center_lon = lon
                self.mbtiles_center_lat = lat
                self.mbtiles_zoom = zoom
                logger.info(f"Loaded mbtiles_center from provider: ({lon}, {lat}, Z{zoom})")
            except Exception as e:
                logger.warning(f"Could not load mbtiles center: {e}")
        
        # Primary: Load current center/zoom from mbtiles
        if self.mbtiles_center_lon is not None and self.mbtiles_center_lat is not None:
            self.center_lat = self.mbtiles_center_lat
            self.center_lon = self.mbtiles_center_lon
            if self.mbtiles_zoom is not None:
                self.zoom_level = self.mbtiles_zoom
        else:
            # Fallback 1: Load from recent (user's last viewed position)
            recent_center_lat = config.get_float('appearance.tiles.recent_center.lat', None)
            recent_center_lon = config.get_float('appearance.tiles.recent_center.lon', None)
            
            if recent_center_lat is not None and recent_center_lon is not None:
                self.center_lat = recent_center_lat
                self.center_lon = recent_center_lon
            else:
                # Fallback 2: Load from default (user's saved "home")
                self.center_lat = config.get_float('appearance.tiles.default_center.lat', 56.168)
                self.center_lon = config.get_float('appearance.tiles.default_center.lon', 15.586)
        
        # Load zoom level with same fallback priority
        recent_zoom = config.get_int('appearance.tiles.recent_zoom', None)
        if recent_zoom is not None and self.mbtiles_zoom is None:
            self.zoom_level = recent_zoom
        elif self.mbtiles_zoom is None:
            default_zoom = config.get_int('appearance.tiles.default_zoom', None)
            if default_zoom is not None:
                self.zoom_level = default_zoom
            else:
                self.zoom_level = self.ZOOM_LEVEL_DEFAULT
        
        # Initialize default_center/zoom from mbtiles (these are what "Recenter" button uses)
        if self.mbtiles_center_lon is not None:
            config.set('appearance.tiles.default_center.lat', self.mbtiles_center_lat)
            config.set('appearance.tiles.default_center.lon', self.mbtiles_center_lon)
        if self.mbtiles_zoom is not None:
            config.set('appearance.tiles.default_zoom', self.mbtiles_zoom)
        
        # Clamp zoom to valid range for current mbtiles provider
        self._update_zoom_bounds_from_provider()
        self._clamp_zoom_to_valid_range()
        
        self.config = config  # Store config for later use (e.g., saving center position and zoom)
        
        # ✅ NEW: Connect to config signals for live map synchronization
        if self.config:
            self.config.map_position_changed.connect(self._on_map_position_changed_external)
        
        # Drag state for moving trackpoints
        self.dragging_trackpoint = False
        self.dragged_trackpoint_index = None
        self.drag_start_x = None
        self.drag_start_y = None
        self.drag_original_lat = None
        self.drag_original_lon = None
        
        # Button hit areas (populated during render)
        self.button_rects = {}
        self.map_label = QLabel()
        self.map_label.setStyleSheet("background-color: #c0c0c0;")
        self.map_label.setAlignment(Qt.AlignCenter)
        
        # Allow map label to shrink (important for window resizing)
        from PyQt5.QtWidgets import QSizePolicy
        self.map_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.map_label.setScaledContents(True)  # Scale pixmap to fit label size
        
        # Override minimum size to allow actual shrinking
        self.map_label.setMinimumSize(1, 1)  # Allow to shrink to 1x1 pixel if needed
        
        # Zoom level display (not a button, just a label)
        self.zoom_level_label = QLabel(f"Z:{self.ZOOM_LEVEL_DEFAULT}", self)
        font = QFont()
        font.setPointSize(self.ZOOM_BUTTON_SIZE // 2)
        self.zoom_level_label.setFont(font)
        self.zoom_level_label.setStyleSheet("background-color: transparent; border: none; color: transparent;")
        
        # Button hit areas (for click detection)
        # We'll handle clicks in mousePressEvent and check which button was clicked
        self.button_rects = {
            'zoom_in': None,
            'zoom_out': None,
            'zoom_level': None,
            'mark_center': None,
            'recenter': None
        }
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.map_label)
        self.setLayout(main_layout)
        
        # Mouse tracking for panning
        self.pan_start_x = None
        self.pan_start_y = None
        self.setMouseTracking(True)
        
        # Also enable mouse tracking on the label so we can intercept events
        self.map_label.setMouseTracking(True)
        
        # Enable keyboard events (for ESC to deselect)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Install event filter on map_label to intercept mouse events
        self.map_label.installEventFilter(self)
        
        # Dirty flag to avoid unnecessary renders
        self.needs_render = True
        
        # Hover state for button effects
        self.hovered_button = None  # Which button is currently hovered
        self.pressed_button = None  # Which button is currently being pressed
        
        # Create shared button manager
        self.button_manager = MapButtonManager()
        
        # Render timer
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self._on_render_timer)
        self.render_timer.start(100)  # Check every 100ms if render needed
        
        # Mark for initial render
        self.needs_render = True
        self.map_ready.emit()
    
    def refresh_zoom_bounds(self):
        """
        Refresh zoom bounds from provider.
        
        Call this after the mbtiles provider has been updated
        (e.g., after generating new zoom levels).
        """
        self._update_zoom_bounds_from_provider()
        logger.info(f"✅ Refreshed MapWidget zoom bounds: Z{self.min_zoom}-Z{self.max_zoom}")
    
    def _update_zoom_bounds_from_provider(self):
        """Update min/max zoom based on mbtiles provider's available zooms."""
        if not self.mbtiles_provider:
            return
        
        available_zooms = self.mbtiles_provider.get_available_zooms()
        if available_zooms:
            self.min_zoom = min(available_zooms)
            self.max_zoom = max(available_zooms)
            logger.debug(f"Updated zoom bounds: {self.min_zoom}-{self.max_zoom}")
    
    def _clamp_zoom_to_valid_range(self):
        """Clamp current zoom_level to valid range for provider."""
        if self.zoom_level < self.min_zoom:
            logger.warning(f"Zoom level {self.zoom_level} too low, clamping to {self.min_zoom}")
            self.zoom_level = self.min_zoom
        elif self.zoom_level > self.max_zoom:
            logger.warning(f"Zoom level {self.zoom_level} too high, clamping to {self.max_zoom}")
            self.zoom_level = self.max_zoom
    
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
        self.needs_render = True
    
    def set_track_manager(self, track_manager):
        """Set the track manager for accessing track data."""
        self.track_manager = track_manager
        self.needs_render = True
    
    def on_track_list_selection_changed(self, track_id):
        """Handle track selection."""
        self.selected_track_id = track_id
        self.selected_trackpoint_index = None
        self.selected_trackpoint_range = None  # Clear range selection when track changes
        self.needs_render = True
    
    def on_trackpoint_selected(self, track_id, trackpoint_index):
        """Handle trackpoint selection."""
        self.selected_track_id = track_id
        self.selected_trackpoint_index = trackpoint_index
        self.needs_render = True
    
    def on_point_selected(self, track_index, point_index):
        """Alias for on_trackpoint_selected for compatibility."""
        self.on_trackpoint_selected(track_index, point_index)
    
    def eventFilter(self, obj, event):
        """
        Intercept events from child widgets (map_label).
        Forward mouse move events to our handler so we can detect button hovers.
        """
        if obj == self.map_label:
            if event.type() == 5:  # QEvent::MouseMove
                self.mouseMoveEvent(event)
                return True
        return super().eventFilter(obj, event)
    
    def _on_render_timer(self):
        """Timer callback: only render if dirty flag is set."""
        if self.needs_render:
            self.needs_render = False
            self.render_map()
    
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
            
            # Draw UI controls and calculate button hit areas
            pil_image, button_rects = self.draw_ui_controls(pil_image)
            self.button_rects = button_rects
            
            # Convert PIL to QPixmap
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                pil_image.save(tmp_path, 'PNG')
                pixmap = QPixmap(tmp_path)
                self.map_label.setPixmap(pixmap)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        
        except Exception as e:
            logger.error(f"Error rendering map: {e}")
    
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
        if self.selected_track_id is None or (isinstance(self.selected_track_id, int) and self.selected_track_id < 0):
            return pil_image
        
        draw = ImageDraw.Draw(pil_image)
        
        tracks = self.track_manager.get_all_tracks()
        
        # Only draw the selected track
        if self.selected_track_id < len(tracks):
            track = tracks[self.selected_track_id]
            trackpoints = track.trackpoints
            
            if trackpoints:
                # ALWAYS draw the track path (regardless of show_turning_points)
                line_color = self.track_color
                
                # Draw track line with outline effect
                for i in range(len(trackpoints) - 1):
                    lat1 = trackpoints[i].latitude
                    lon1 = trackpoints[i].longitude
                    lat2 = trackpoints[i + 1].latitude
                    lon2 = trackpoints[i + 1].longitude
                    
                    screen1 = map_renderer.gps_to_screen(lat1, lon1)
                    screen2 = map_renderer.gps_to_screen(lat2, lon2)
                    
                    if screen1 and screen2:
                        # Draw outline first (thicker, white)
                        outline_width = self.track_path_width + 2 * self.track_path_outline_width
                        draw.line([screen1, screen2], fill=self.track_path_outline_color, width=outline_width)
                        
                        # Draw main track path on top
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
                            
                            # Draw circle for turning point with outline
                            draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=point_color, outline=self.turning_point_outline_color, width=self.turning_point_outline_width)
                    
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
                                    draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=self.double_selected_turning_point_color, outline=self.double_selected_turning_point_outline_color, width=self.double_selected_turning_point_outline_width)
                    
                    # THIRD: Draw single selected point LAST so it appears on top
                    elif self.selected_trackpoint_index is not None and self.selected_trackpoint_index < len(trackpoints):
                        tp = trackpoints[self.selected_trackpoint_index]
                        screen = map_renderer.gps_to_screen(tp.latitude, tp.longitude)
                        
                        if screen:
                            x, y = screen
                            point_color = self.selected_turning_point_color
                            r = self.selected_turning_point_size
                            
                            # Draw circle for selected turning point (on top) with outline
                            draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=point_color, outline=self.selected_turning_point_outline_color, width=self.selected_turning_point_outline_width)
                
                # NEW FEATURE: If show_turning_points is False but a trackpoint is selected,
                # show only that selected turning point in blue
                elif self.selected_trackpoint_index is not None:
                    if self.selected_trackpoint_index < len(trackpoints):
                        tp = trackpoints[self.selected_trackpoint_index]
                        screen = map_renderer.gps_to_screen(tp.latitude, tp.longitude)
                        
                        if screen:
                            x, y = screen
                            # Draw only the selected point with outline
                            r = self.selected_turning_point_size
                            draw.ellipse([(x-r, y-r), (x+r, y+r)], 
                                       fill=self.selected_turning_point_color, 
                                       outline=self.selected_turning_point_outline_color,
                                       width=self.selected_turning_point_outline_width)
        
        return pil_image
    
    def zoom_in(self):
        """Zoom in by one level."""
        if self.mbtiles_provider:
            available_zooms = self.mbtiles_provider.get_available_zooms()
            if available_zooms:
                max_zoom = max(available_zooms)
                if self.zoom_level < max_zoom:
                    self.zoom_level += 1
                    self.zoom_level_label.setText(f"Z:{self.zoom_level}")
                    self.update_recent_state()
                    self.needs_render = True
    
    def zoom_out(self):
        """Zoom out by one level."""
        if self.mbtiles_provider:
            available_zooms = self.mbtiles_provider.get_available_zooms()
            if available_zooms:
                min_zoom = min(available_zooms)
                if self.zoom_level > min_zoom:
                    self.zoom_level -= 1
                    self.zoom_level_label.setText(f"Z:{self.zoom_level}")
                    self.update_recent_state()
                    self.needs_render = True
    
    def recenter_on_default(self):
        """
        Recenter on marked default position and zoom.
        
        If default_center and default_zoom are set (user marked them), navigate to that location.
        If not set, do nothing (user hasn't marked a default yet).
        """
        default_zoom = self.config.get_int('appearance.tiles.default_zoom', None)
        default_center_lat = self.config.get_float('appearance.tiles.default_center.lat', None)
        default_center_lon = self.config.get_float('appearance.tiles.default_center.lon', None)
        
        # Only recenter if default has been explicitly set (not None)
        if default_zoom is None or default_center_lat is None or default_center_lon is None:
            logger.info("Default center/zoom not yet marked - nothing to recenter to")
            return
        
        self.zoom_level = default_zoom
        self.center_lat = default_center_lat
        self.center_lon = default_center_lon
        
        # Also update recent center/zoom since we're navigating
        self.update_recent_state()
        
        self.needs_render = True
        logger.info(f"Recentered to marked default: Z{self.zoom_level}, ({self.center_lat}, {self.center_lon})")
    
    def on_mark_center_clicked(self):
        """
        Mark current map center and zoom as the default.
        
        Called when user clicks the "Mark Center" button.
        Saves current center_lat, center_lon, and zoom_level to config as defaults.
        """
        self.mark_center()
    
    def mark_center(self):
        """
        Save current center position and zoom level as the default.
        
        Updates both:
        1. mbtiles file metadata (mbtiles_center, mbtiles_zoom)
        2. settings.yaml (default_center, default_zoom)
        
        This allows the user to have a "home" position they can jump back to with the Recenter button.
        The mbtiles update ensures next file reload centers to this marked position.
        """
        try:
            # Step 1: Update mbtiles file metadata (if mbtiles provider available)
            if self.mbtiles_provider and hasattr(self.mbtiles_provider, 'update_mbtiles_center'):
                logger.info(f"🔵 mark_center: Updating mbtiles metadata...")
                success = self.mbtiles_provider.update_mbtiles_center(
                    self.center_lon, self.center_lat, self.zoom_level
                )
                if success:
                    logger.info(f"✅ mark_center: mbtiles metadata updated")
                else:
                    logger.warning(f"⚠️  mark_center: Failed to update mbtiles metadata")
            
            # Step 2: Save current center and zoom as default in settings.yaml
            self.config.set('appearance.tiles.default_zoom', self.zoom_level)
            self.config.set('appearance.tiles.default_center.lat', self.center_lat)
            self.config.set('appearance.tiles.default_center.lon', self.center_lon)
            self.config.save_to_file()
            
            logger.info(f"✅ mark_center: Marked as default center: Z{self.zoom_level}, ({self.center_lat:.4f}, {self.center_lon:.4f})")
            
        except Exception as e:
            logger.error(f"❌ mark_center: Error marking center: {e}", exc_info=True)
    
    def update_recent_state(self):
        """
        Update recent center and zoom in config file.
        
        Called automatically after navigation to persist map state.
        This ensures that if the app closes, the user returns to their last viewed location.
        
        Uses set_silent() to avoid feedback loop from emitting signals 3 times,
        then emits once after all values are set.
        """
        # ✅ NEW: Use set_silent to avoid feedback loop
        self.config.set_silent('appearance.tiles.recent_zoom', self.zoom_level)
        self.config.set_silent('appearance.tiles.recent_center.lat', self.center_lat)
        self.config.set_silent('appearance.tiles.recent_center.lon', self.center_lon)
        
        # ✅ NEW: Emit signal ONCE after all values are set
        self.config.emit_map_position_changed()
        
        self.config.save_to_file()
    
    def reset_to_recent_center(self):
        """Reset map to the recent center position (same as startup)."""
        recent_center_lat = self.config.get_float('appearance.tiles.recent_center.lat', None)
        recent_center_lon = self.config.get_float('appearance.tiles.recent_center.lon', None)
        
        if recent_center_lat is not None and recent_center_lon is not None:
            self.center_lat = recent_center_lat
            self.center_lon = recent_center_lon
        else:
            # Fall back to default if recent not available
            self.center_lat = self.config.get_float('appearance.tiles.default_center.lat', 56.168)
            self.center_lon = self.config.get_float('appearance.tiles.default_center.lon', 15.586)
        
        self.needs_render = True
    
    def _on_map_position_changed_external(self, lat, lon, zoom):
        """
        Handler for map_position_changed signal from config.
        
        Called when another tab (Map Editor) changes the map position/zoom.
        Updates this map to show the same view.
        
        Args:
            lat (float): New center latitude
            lon (float): New center longitude
            zoom (int): New zoom level
        """
        # Update our position
        self.center_lat = lat
        self.center_lon = lon
        
        # Update zoom if it's within valid bounds
        if self.min_zoom <= zoom <= self.max_zoom:
            self.zoom_level = zoom
        
        # Trigger re-render
        self.needs_render = True
    
    def save_center_position(self):
        """
        Save current map center to recent_center in config.
        
        DEPRECATED: Use update_recent_state() instead, which saves both center and zoom.
        Kept for backwards compatibility.
        """
        self.update_recent_state()
    
    def save_zoom_level(self):
        """
        Save current zoom level to recent_zoom in config.
        
        DEPRECATED: Use update_recent_state() instead, which saves both center and zoom.
        Kept for backwards compatibility.
        """
        self.update_recent_state()
    
    def set_zoom_with_compatibility(self, new_zoom):
        """
        Set zoom level, checking if it's available in current mbtiles.
        If not available, use the closest available zoom level.
        
        Args:
            new_zoom: Desired zoom level
        """
        if self.mbtiles_provider:
            available_zooms = self.mbtiles_provider.get_available_zooms()
            if available_zooms:
                # Check if requested zoom is available
                if new_zoom in available_zooms:
                    self.zoom_level = new_zoom
                else:
                    # Find closest available zoom
                    closest_zoom = min(available_zooms, key=lambda z: abs(z - new_zoom))
                    logger.info(f"Requested zoom {new_zoom} not available in mbtiles. "
                               f"Using closest available: {closest_zoom}")
                    self.zoom_level = closest_zoom
            else:
                # No zoom info available, just use requested
                self.zoom_level = new_zoom
        else:
            self.zoom_level = new_zoom
        
        # Save the zoom level we actually set
        self.save_zoom_level()
    
    def reload_settings(self):
        """Reload turning points settings from config and re-render map."""
        from config.app_config_yaml import AppConfig
        config = AppConfig()
        
        # Reload all turning points settings
        self.show_turning_points = config.get_bool('appearance.map_display.TurningPoints.show', True)
        self.turning_point_color = self._hex_to_rgb(config.get_str('appearance.map_display.TurningPoints.color', 'FFFF00'))
        self.selected_turning_point_color = self._hex_to_rgb(config.get_str('appearance.map_display.TurningPoints.selected.color', '0000FF'))
        self.turning_point_size = config.get_int('appearance.map_display.TurningPoints.size', 4)
        self.selected_turning_point_size = config.get_int('appearance.map_display.TurningPoints.selected.size', 7)
        
        # Reload double selected (range) turning points settings
        self.double_selected_turning_point_color = self._hex_to_rgb(config.get_str('appearance.map_display.TurningPoints.doubleSelected.color', 'FFA500'))
        self.double_selected_turning_point_size = config.get_int('appearance.map_display.TurningPoints.doubleSelected.size', 8)
        
        # Mark for re-render with new settings
        self.needs_render = True
        logger.debug("Map settings reloaded from config")
    
    def mousePressEvent(self, event):
        """
        Handle mouse button press - implements trackpoint dragging, map panning, and button interaction.
        
        State Machine (mutually exclusive behaviors):
        
        1. BUTTON CLICK: User clicks zoom/recenter buttons
           - Execute button action
        
        2. TRACKPOINT CLICK: User clicks on a trackpoint marker
           - Single click: Select point, start drag mode
           - Shift+click: Select range (2 consecutive points)
           - Insert point between selected range on Shift+click
        
        3. EMPTY SPACE CLICK: User clicks on map background
           - Normal click: Pan the map
           - Shift+click: Insert new trackpoint (create track if needed)
        
        4. RIGHT-CLICK: Show context menu
        """
        if event.button() == Qt.RightButton:
            # Right-click: show context menu
            self._show_context_menu(event.pos())
            return
        
        if event.button() == Qt.LeftButton:
            x, y = event.x(), event.y()
            
            # Check if clicking on any button (same logic as Map Editor)
            # Calculate button positions on the fly using MapButtonConfig
            cfg = MapButtonConfig
            button_y = cfg.PADDING_TOP
            
            for button_name in self.button_manager.BUTTON_ORDER:
                if (cfg.PADDING_LEFT <= x <= cfg.PADDING_LEFT + cfg.BUTTON_SIZE and
                    button_y <= y <= button_y + cfg.BUTTON_SIZE):
                    # Button clicked - execute callback
                    self.pressed_button = button_name
                    self.needs_render = True
                    
                    if button_name == 'zoom_in':
                        self.zoom_in()
                    elif button_name == 'zoom_out':
                        self.zoom_out()
                    elif button_name == 'zoom_level':
                        # Zoom level label - no action
                        pass
                    elif button_name == 'mark_center':
                        self.mark_center()
                    elif button_name == 'recenter':
                        self.recenter_on_default()
                    return
                
                button_y += cfg.BUTTON_SIZE + cfg.BUTTON_SPACING
            
            # Check if clicking on a turning point (PRIORITY: check this first for Shift+click range selection)
            # Only do this if a track is actually selected
            if self.selected_track_id is not None and (self.show_turning_points or self.selected_trackpoint_index is not None or self.selected_trackpoint_range is not None):
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
                                self.needs_render = True
                                return
                        elif self.selected_trackpoint_range is not None:
                            # We have a range - try to extend or modify it
                            start_idx, end_idx = self.selected_trackpoint_range
                            min_idx = min(start_idx, end_idx, clicked_point_index)
                            max_idx = max(start_idx, end_idx, clicked_point_index)
                            
                            # Only allow selecting consecutive neighbors
                            if max_idx - min_idx == 1:
                                self.selected_trackpoint_range = (min_idx, max_idx)
                                self.needs_render = True
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
                    
                    self.needs_render = True
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
                            
                            # Refresh list FIRST so it has the new trackpoint
                            main_window = QApplication.instance().activeWindow()
                            if main_window:
                                if hasattr(main_window, 'trackpoint_list_widget'):
                                    main_window.trackpoint_list_widget.refresh_trackpoints()
                                if hasattr(main_window, 'track_list_widget'):
                                    main_window.track_list_widget.update_track_info(self.selected_track_id)
                            
                            # NOW emit signal to sync selection with updated trackpoints list
                            self.point_clicked.emit(str(self.selected_track_id), insert_position)
                            
                            self.needs_render = True
                            return
            
            # Shift+click on empty space - insert point at end of current track (or create new track if none selected)
            # Note: When user clicks "X" to unselect a track, track_selected emits -1 (not None), so we check both
            if event.modifiers() & Qt.ShiftModifier:
                gps_coords = self.screen_to_gps(x, y)
                if gps_coords and self.track_manager:
                    lat, lon = gps_coords
                    
                    # If no track selected (selected_track_id is None or -1 from unselect), create a new one
                    if self.selected_track_id is None or self.selected_track_id == -1:
                        from src.track_editor.core.track_manager import TrackData
                        # Create new track with auto-incremented name
                        track_count = len(self.track_manager.get_all_tracks())
                        new_track = TrackData(name=f"Track {track_count + 1}", trackpoints=[])
                        self.track_manager.tracks.append(new_track)
                        self.selected_track_id = len(self.track_manager.get_all_tracks()) - 1
                        self.track_manager.select_track(self.selected_track_id)
                        
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
                    
                    if success:
                        # Select the new point
                        self.selected_trackpoint_index = insert_position
                        self.selected_trackpoint_range = None
                        
                        # Refresh list FIRST so it has the new trackpoint
                        main_window = QApplication.instance().activeWindow()
                        if main_window:
                            if hasattr(main_window, 'trackpoint_list_widget'):
                                main_window.trackpoint_list_widget.refresh_trackpoints()
                            if hasattr(main_window, 'track_list_widget'):
                                main_window.track_list_widget.update_track_info(self.selected_track_id)
                        
                        # NOW emit signal to sync selection with updated trackpoints list
                        self.point_clicked.emit(str(self.selected_track_id), insert_position)
                        
                        self.needs_render = True
                        return
                return  # Don't pan if Shift+click, even if insert failed
            
            # Otherwise, clear any selection and start pan
            # Clicking on empty space should deselect
            if self.selected_trackpoint_index is not None or self.selected_trackpoint_range is not None:
                self.selected_trackpoint_index = None
                self.selected_trackpoint_range = None
                # Emit signal to deselect in list as well
                self.point_clicked.emit(str(self.selected_track_id), -1)
                self.needs_render = True
            
            self.pan_start_x = x
            self.pan_start_y = y
    
    def _point_in_rect(self, x, y, rect):
        """Check if point (x, y) is inside rectangle (x1, y1, x2, y2)."""
        return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement for panning, dragging trackpoint, and button hover effects."""
        
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
                    self.needs_render = True
            return
        
        # Check for button hover
        x, y = event.x(), event.y()
        
        # Transform screen coordinates to map coordinates (accounting for scaling)
        # The QLabel may scale the pixmap, so we need to convert back to original map size
        label_width = self.map_label.width()
        label_height = self.map_label.height()
        
        if label_width > 0 and label_height > 0:
            # Get the actual pixmap size (original map render size)
            if self.map_label.pixmap():
                pixmap_width = self.map_label.pixmap().width()
                pixmap_height = self.map_label.pixmap().height()
                
                # Calculate scale factors
                scale_x = pixmap_width / label_width if label_width > 0 else 1
                scale_y = pixmap_height / label_height if label_height > 0 else 1
                
                # Transform mouse coordinates from label space to pixmap space
                map_x = int(x * scale_x)
                map_y = int(y * scale_y)
            else:
                map_x, map_y = x, y
        else:
            map_x, map_y = x, y
        
        old_hovered = self.hovered_button
        self.hovered_button = None
        
        # Check which button (if any) is being hovered (using map coordinates)
        # Skip hover effect for zoom_level button (it's display-only)
        for button_name, rect in self.button_rects.items():
            if button_name == 'zoom_level':
                continue  # Skip hover on zoom level display
            x1, y1, x2, y2 = rect
            if x1 <= map_x <= x2 and y1 <= map_y <= y2:
                self.hovered_button = button_name
                break
        
        # Only re-render if hover state changed
        if old_hovered != self.hovered_button:
            if self.hovered_button:
                logger.info(f"Button hovered: {self.hovered_button}")
            else:
                logger.info(f"Button unhovered")
            self.needs_render = True
        
        # Handle map panning
        if self.pan_start_x is not None and self.pan_start_y is not None:
            # Get delta in pixels (how far the cursor moved)
            delta_x = self.pan_start_x - event.x()
            delta_y = self.pan_start_y - event.y()
            
            if self.mbtiles_provider:
                import math
                
                # ===== WEB MERCATOR PANNING - CORRECTED FORMULA =====
                # 
                # The issue with the previous approach was using a linear meter-to-degree
                # conversion for latitude, which doesn't work in Web Mercator.
                #
                # Correct approach: Use Web Mercator's tile coordinate system
                # Screen pixels → Tile coords → Lat/Lon (proper inverse formula)
                #
                # Web Mercator properties:
                # - At zoom level N: 2^N tiles horizontally and vertically
                # - Each tile is 256x256 pixels
                # - Tiles are addressed as (zoom, x, y) where:
                #   * x: 0 to 2^N-1 (increases left to right)
                #   * y: 0 to 2^N-1 (increases top to bottom in tile coords)
                
                TILE_SIZE = 256
                tiles_at_zoom = 2 ** self.zoom_level
                earth_circumference_m = 40075016.686
                
                # Convert current center lat/lon to tile coordinates
                # This is the Web Mercator projection formula
                def latlon_to_tile(lat, lon, zoom):
                    """Convert lat/lon to tile coordinates (as floats, not integers)."""
                    n = 2.0 ** zoom
                    # Longitude to tile X
                    tile_x = (lon + 180.0) / 360.0 * n
                    # Latitude to tile Y (using Web Mercator formula)
                    lat_rad = math.radians(lat)
                    tile_y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n
                    return tile_x, tile_y
                
                def tile_to_latlon(tile_x, tile_y, zoom):
                    """Convert tile coordinates back to lat/lon."""
                    n = 2.0 ** zoom
                    # Tile X to longitude
                    lon = tile_x / n * 360.0 - 180.0
                    # Tile Y to latitude (using Web Mercator inverse formula)
                    lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * tile_y / n)))
                    lat = math.degrees(lat_rad)
                    return lat, lon
                
                # Get current position in tile coordinates
                tile_x, tile_y = latlon_to_tile(self.center_lat, self.center_lon, self.zoom_level)
                
                # Calculate tile delta from pixel delta
                # (pixels_per_tile = TILE_SIZE, so tile_delta = pixel_delta / TILE_SIZE)
                tile_delta_x = delta_x / TILE_SIZE
                tile_delta_y = delta_y / TILE_SIZE
                
                # Update tile position
                new_tile_x = tile_x + tile_delta_x
                new_tile_y = tile_y + tile_delta_y
                
                # Convert back to lat/lon
                self.center_lat, self.center_lon = tile_to_latlon(new_tile_x, new_tile_y, self.zoom_level)
                
                self.needs_render = True
            
            self.pan_start_x = event.x()
            self.pan_start_y = event.y()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse button release - clears pressed state and completes dragging/panning."""
        if event.button() == Qt.LeftButton:
            # Clear pressed button state
            if self.pressed_button is not None:
                self.pressed_button = None
                self.needs_render = True
                logger.info(f"Button released")
            
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
                            
                            # Update track info (distance and point count) in track list
                            # because moving a point can change the track distance
                            if hasattr(main_window, 'track_list_widget'):
                                main_window.track_list_widget.update_track_info(
                                    self.track_manager.get_selected_track_index()
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
                # Normal pan end - save the new center position
                self.pan_start_x = None
                self.pan_start_y = None
                
                # Save center position to config after panning completes
                self.save_center_position()
    
    def wheelEvent(self, event):
        """Handle mouse wheel - zoom at cursor position (exact MapLoom implementation)."""
        if not self.mbtiles_provider:
            return
        
        # Get cursor position in pixels
        cursor_x = event.x()
        cursor_y = event.y()
        
        # Convert cursor screen position to GPS coordinates
        import math
        
        def latlon_to_tile(lat, lon, zoom):
            """Convert GPS to tile coordinates."""
            n = 2.0 ** zoom
            tile_x = (lon + 180.0) / 360.0 * n
            lat_rad = math.radians(lat)
            tile_y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
            return tile_x, tile_y
        
        def tile_to_latlon(tile_x, tile_y, zoom):
            """Convert tile coordinates to GPS."""
            n = 2.0 ** zoom
            lon = tile_x / n * 360.0 - 180.0
            lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * tile_y / n)))
            lat = math.degrees(lat_rad)
            return lat, lon
        
        # Get cursor location in GPS
        tile_x, tile_y = latlon_to_tile(self.center_lat, self.center_lon, self.zoom_level)
        cursor_tile_x = (cursor_x - self.width() / 2) / 256.0 + tile_x
        cursor_tile_y = (cursor_y - self.height() / 2) / 256.0 + tile_y
        cursor_lat, cursor_lon = tile_to_latlon(cursor_tile_x, cursor_tile_y, self.zoom_level)
        
        # Zoom in or out
        old_zoom = self.zoom_level
        available_zooms = self.mbtiles_provider.get_available_zooms()
        if available_zooms:
            min_zoom = min(available_zooms)
            max_zoom = max(available_zooms)
            
            if event.angleDelta().y() > 0:
                if self.zoom_level < max_zoom:
                    self.zoom_level += 1
            else:
                if self.zoom_level > min_zoom:
                    self.zoom_level -= 1
        
        # If zoom changed, recalculate center to keep cursor at same GPS location
        if self.zoom_level != old_zoom:
            new_tile_x, new_tile_y = latlon_to_tile(cursor_lat, cursor_lon, self.zoom_level)
            # Calculate the new center to keep cursor at same screen position
            center_tile_x = new_tile_x - (cursor_x - self.width() / 2) / 256.0
            center_tile_y = new_tile_y - (cursor_y - self.height() / 2) / 256.0
            self.center_lat, self.center_lon = tile_to_latlon(center_tile_x, center_tile_y, self.zoom_level)
            
            self.zoom_level_label.setText(f"Z:{self.zoom_level}")
            self.update_recent_state()
            self.needs_render = True
    
    def keyPressEvent(self, event):
        """Handle keyboard events."""
        if event.key() == Qt.Key_Escape:
            # ESC clears selection
            if self.selected_trackpoint_index is not None or self.selected_trackpoint_range is not None:
                self.selected_trackpoint_index = None
                self.selected_trackpoint_range = None
                # Emit signal to deselect in list as well
                self.point_clicked.emit(str(self.selected_track_id), -1)
                self.needs_render = True
            return
        
        super().keyPressEvent(event)
    
    def resizeEvent(self, event):
        """Handle window resize."""
        super().resizeEvent(event)
        self.needs_render = True
    
    
    def draw_ui_controls(self, pil_image):
        """Draw UI control buttons on PIL image. Returns button hit areas."""
        # Create overlay
        overlay = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Position buttons first (so their x,y coords are set for drawing)
        cfg = MapButtonConfig
        x_pos = cfg.PADDING_LEFT
        y_pos = cfg.PADDING_TOP
        
        for button_name in self.button_manager.BUTTON_ORDER:
            button = self.button_manager.get_button(button_name)
            if button:
                button.set_position(x_pos, y_pos)
                y_pos += cfg.BUTTON_SIZE + cfg.BUTTON_SPACING
        
        # Now draw buttons with their positions set
        self.button_manager.draw_all_buttons(overlay_draw, zoom_level=self.zoom_level,
                                             hovered_button=self.hovered_button,
                                             pressed_button=self.pressed_button)
        
        # Build button rects for hit detection
        button_rects = {}
        x_pos = cfg.PADDING_LEFT
        y_pos = cfg.PADDING_TOP
        
        for button_name in self.button_manager.BUTTON_ORDER:
            # Normalize zoom_level_label to zoom_level for hover detection
            rect_name = 'zoom_level' if button_name == 'zoom_level_label' else button_name
            button_rects[rect_name] = (x_pos, y_pos, x_pos + cfg.BUTTON_SIZE, y_pos + cfg.BUTTON_SIZE)
            y_pos += cfg.BUTTON_SIZE + cfg.BUTTON_SPACING
        
        # Composite the button overlay onto the image first
        pil_image = Image.alpha_composite(pil_image, overlay)
        
        # Draw center crosshair if enabled (using shared function)
        # Note: draw_crosshair takes pil_image and returns it with crosshair drawn
        pil_image = draw_crosshair(
            pil_image,
            pil_image.width // 2,
            pil_image.height // 2,
            self.show_crosshair,
            self.crosshair_color,
            self.crosshair_outline_color,
            self.crosshair_outline_width,
            self.crosshair_size
        )
        
        return pil_image, button_rects
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
        if not tracks or self.selected_track_id < 0 or self.selected_track_id >= len(tracks):
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
