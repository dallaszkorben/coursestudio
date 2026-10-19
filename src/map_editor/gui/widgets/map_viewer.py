"""
Interactive map viewer widget using MBTiles with pan/zoom controls.

Based on CourseStudio's proven working MapWidget implementation.
Uses real QPushButton widgets for controls, proper Web Mercator tile coordinates.
"""

import tempfile
import os
import logging
import math
import io
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PIL import Image, ImageDraw

from src.shared.map.map_renderer import MapRenderer
from src.shared.map.mbtiles_provider import MBTilesProvider
from src.shared.map.crosshair_drawer import draw_crosshair
from src.map.map_buttons import MapButtonManager, MapButtonConfig

logger = logging.getLogger(__name__)


class MapViewer(QWidget):
    """
    Interactive map viewer for MBTiles files.
    
    Features:
    - Pan by dragging mouse
    - Zoom with +/- buttons or mouse wheel
    - Recenter button to return to map center
    - Proper Web Mercator tile coordinate system
    
    Uses shared MapButtonManager for consistent button appearance across map widgets.
    """
    
    TILE_SIZE = 256
    
    def __init__(self, parent=None, config=None):
        """
        Initialize the map viewer.
        
        Args:
            parent: Parent widget
            config: AppConfig instance for state persistence (optional)
        """
        super().__init__(parent)
        
        # Configuration for state persistence
        self.config = config
        
        # Crosshair settings (read from config)
        if config:
            self.show_crosshair = config.get_bool('appearance.map_display.Crosshair.show', True)
            crosshair_color_str = config.get_str('appearance.map_display.Crosshair.body.color', 'FF0000')
            crosshair_outline_str = config.get_str('appearance.map_display.Crosshair.outline.color', 'FFFFFF')
            self.crosshair_color = self._hex_to_rgb(crosshair_color_str)
            self.crosshair_outline_color = self._hex_to_rgb(crosshair_outline_str)
            self.crosshair_outline_width = config.get_int('appearance.map_display.Crosshair.outline.width', 1)
            self.crosshair_size = config.get_int('appearance.map_display.Crosshair.size', 20)
        else:
            self.show_crosshair = True
            self.crosshair_color = (255, 0, 0)  # Red
            self.crosshair_outline_color = (255, 255, 255)  # White
            self.crosshair_outline_width = 1
            self.crosshair_size = 20
        
        # Button state tracking
        self.hovered_button = None  # Which button is currently hovered
        self.pressed_button = None  # Which button is currently being pressed
        
        # Map state
        self.mbtiles_provider = None
        self.mbtiles_reader = None  # ✅ NEW: Direct reader for accurate zoom queries
        self.center_lat = 0
        self.center_lon = 0
        self.zoom_level = 10
        self.min_zoom = 1
        self.max_zoom = 20
        
        # Store mbtiles center/zoom (loaded when mbtiles_provider is set)
        self.mbtiles_center_lon = None
        self.mbtiles_center_lat = None
        self.mbtiles_zoom = None
        
        # ✅ DO NOT load from config here!
        # The initialization will happen in set_mbtiles_provider() with proper priority:
        # 1. Primary: mbtiles_center/zoom from file
        # 2. Fallback 1: recent_center/zoom from settings
        # 3. Fallback 2: default_center/zoom from settings
        # This matches MapWidget initialization exactly.
        
        # Stored center from metadata (for recenter button)
        self.metadata_center_lon = 0
        self.metadata_center_lat = 0
        self.metadata_center_zoom = 10
        # Pan state (for mouse dragging)
        self.pan_start_x = None
        self.pan_start_y = None
        
        # Create map display label (shows pixmap)
        self.map_label = QLabel()
        self.map_label.setStyleSheet("background-color: #c0c0c0;")
        self.map_label.setScaledContents(True)
        
        # ✅ Allow map to shrink and expand - match CourseStudio
        from PyQt5.QtWidgets import QSizePolicy
        self.map_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.map_label.setMinimumSize(1, 1)  # Allow to shrink to 1x1 pixel if needed
        
        # Create button manager for shared button handling
        self.button_manager = MapButtonManager()
        
        # Create button callbacks
        callbacks = {
            'zoom_in': self.zoom_in,
            'zoom_out': self.zoom_out,
            'mark_center': self.mark_center,
            'recenter': self.recenter
        }
        
        # Create all buttons (data objects, not widgets)
        self.button_manager.create_all_buttons(self, callbacks)
        
        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.map_label)
        self.setLayout(layout)
        
        # Mouse tracking for pan and button hover detection
        self.setMouseTracking(True)
        self.map_label.setMouseTracking(True)  # ✅ CRITICAL: Also track on map_label!
        
        # ✅ NEW: Connect to config signals for live map synchronization
        if self.config:
            self.config.map_position_changed.connect(self._on_map_position_changed_external)
        
        logger.info("MapViewer initialized")
    
    def set_mbtiles_reader(self, reader):
        """
        Set the mbtiles reader for accurate zoom queries.
        
        This is used to get actual available zooms from the database,
        not the cached metadata range from the provider.
        
        Args:
            reader: MBTilesReader instance
        """
        self.mbtiles_reader = reader
        self._update_zoom_bounds_from_provider()
    
    def _update_zoom_bounds_from_provider(self):
        """Update min/max zoom based on actual available zooms."""
        # Prefer using the reader for accurate zoom list (queries database directly)
        if self.mbtiles_reader:
            available_zooms = self.mbtiles_reader.get_available_zooms()
            if available_zooms:
                self.min_zoom = min(available_zooms)
                self.max_zoom = max(available_zooms)
                logger.debug(f"Updated zoom bounds from reader: {self.min_zoom}-{self.max_zoom}")
                return
        
        # Fallback to provider if reader not available
        if not self.mbtiles_provider:
            return
        
        available_zooms = self.mbtiles_provider.get_available_zooms()
        if available_zooms:
            self.min_zoom = min(available_zooms)
            self.max_zoom = max(available_zooms)
            logger.debug(f"Updated zoom bounds from provider: {self.min_zoom}-{self.max_zoom}")
    
    def _clamp_zoom_to_valid_range(self):
        """Clamp current zoom_level to valid range for provider."""
        if self.zoom_level < self.min_zoom:
            logger.warning(f"Zoom level {self.zoom_level} too low, clamping to {self.min_zoom}")
            self.zoom_level = self.min_zoom
        elif self.zoom_level > self.max_zoom:
            logger.warning(f"Zoom level {self.zoom_level} too high, clamping to {self.max_zoom}")
            self.zoom_level = self.max_zoom
    
    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """
        Convert hex color to RGB tuple.
        
        Args:
            hex_color: Color in hex format (e.g., 'FF0000' for red)
        
        Returns:
            Tuple of (R, G, B) values 0-255
        """
        hex_color = hex_color.lstrip('#')
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except (ValueError, IndexError):
            return (255, 0, 0)  # Default to red if parsing fails
    
    def set_mbtiles_provider(self, mbtiles_provider: MBTilesProvider):
        """
        Set the MBTiles provider (called by tab handler on initialization).
        
        Implements specification Section 13.2(a) initialization sequence:
        1. Primary: Load mbtiles_center/zoom from file metadata
        2. Fallback 1: Load recent_center/zoom from config (user's last position)
        3. Fallback 2: Load default_center/zoom from config (user's "home")
        4. Fallback 3: Use hardcoded defaults
        
        This matches MapWidget initialization exactly.
        """
        self.mbtiles_provider = mbtiles_provider
        
        # Load mbtiles center and zoom from metadata
        try:
            lon, lat, zoom = mbtiles_provider.get_mbtiles_center_with_fallback()
            self.mbtiles_center_lon = lon
            self.mbtiles_center_lat = lat
            self.mbtiles_zoom = zoom
            logger.info(f"Loaded mbtiles_center from provider: ({lon}, {lat}, Z{zoom})")
        except Exception as e:
            logger.warning(f"Could not load mbtiles center: {e}")
            self.mbtiles_center_lon = None
            self.mbtiles_center_lat = None
            self.mbtiles_zoom = None
        
        # PRIMARY: Use mbtiles center/zoom if available
        if self.mbtiles_center_lon is not None and self.mbtiles_center_lat is not None:
            self.center_lon = self.mbtiles_center_lon
            self.center_lat = self.mbtiles_center_lat
            if self.mbtiles_zoom is not None:
                self.zoom_level = self.mbtiles_zoom
            logger.info(f"Using PRIMARY (mbtiles): ({self.center_lat:.4f}, {self.center_lon:.4f}), Z{self.zoom_level}")
        else:
            # FALLBACK 1: Use recent_center/zoom (user's last viewed position)
            recent_center_lat = self.config.get_float('appearance.tiles.recent_center.lat', None)
            recent_center_lon = self.config.get_float('appearance.tiles.recent_center.lon', None)
            recent_zoom = self.config.get_int('appearance.tiles.recent_zoom', None)
            
            if recent_center_lat is not None and recent_center_lon is not None:
                self.center_lat = recent_center_lat
                self.center_lon = recent_center_lon
                if recent_zoom is not None:
                    self.zoom_level = recent_zoom
                logger.info(f"Using FALLBACK 1 (recent): ({self.center_lat:.4f}, {self.center_lon:.4f}), Z{self.zoom_level}")
            else:
                # FALLBACK 2: Use default_center/zoom (user's saved "home")
                self.center_lat = self.config.get_float('appearance.tiles.default_center.lat', 56.168)
                self.center_lon = self.config.get_float('appearance.tiles.default_center.lon', 15.586)
                default_zoom = self.config.get_int('appearance.tiles.default_zoom', None)
                if default_zoom is not None:
                    self.zoom_level = default_zoom
                else:
                    self.zoom_level = 10  # FALLBACK 3: hardcoded default
                logger.info(f"Using FALLBACK 2 (default): ({self.center_lat:.4f}, {self.center_lon:.4f}), Z{self.zoom_level}")
        
        # ✅ Initialize default_center from mbtiles (user can recenter to this)
        # Only set if mbtiles has a center (don't overwrite user's previously saved default)
        if self.mbtiles_center_lon is not None and self.mbtiles_center_lat is not None:
            self.config.set('appearance.tiles.default_center.lat', self.mbtiles_center_lat)
            self.config.set('appearance.tiles.default_center.lon', self.mbtiles_center_lon)
            if self.mbtiles_zoom is not None:
                self.config.set('appearance.tiles.default_zoom', self.mbtiles_zoom)
            logger.info(f"Initialized default_center from mbtiles for Recenter button")
        
        # Update zoom bounds and clamp current zoom to valid range
        self._update_zoom_bounds_from_provider()
        self._clamp_zoom_to_valid_range()
        logger.debug("MBTilesProvider set in MapViewer")
    
    def load_mbtiles(self, mbtiles_provider: MBTilesProvider):
        """
        Load an MBTiles file via provider.
        
        ⚠️ CRITICAL: This method should NOT override center/zoom!
        
        The center/zoom was already initialized correctly in set_mbtiles_provider()
        with the proper fallback hierarchy. This method should ONLY:
        1. Update zoom bounds from available tiles
        2. Clamp current zoom to valid range
        3. Render the map
        
        Calling this after set_mbtiles_provider() would override the correct
        initialization with potentially wrong values (like old recent_center).
        """
        try:
            self.mbtiles_provider = mbtiles_provider
            
            # Get map metadata
            metadata = mbtiles_provider.get_metadata()
            if metadata is None:
                logger.error("No metadata available from mbtiles_provider")
                return
            
            # ONLY update zoom bounds, don't override center/zoom
            available_zooms = mbtiles_provider.get_available_zooms()
            if available_zooms:
                self.min_zoom = min(available_zooms)
                self.max_zoom = max(available_zooms)
                logger.info(f"Updated zoom bounds: Z{self.min_zoom}-Z{self.max_zoom}")
            else:
                self.min_zoom = 1
                self.max_zoom = 20
            
            # Clamp current zoom to valid range
            if self.zoom_level < self.min_zoom:
                self.zoom_level = self.min_zoom
                logger.info(f"Clamped zoom to min: Z{self.zoom_level}")
            elif self.zoom_level > self.max_zoom:
                self.zoom_level = self.max_zoom
                logger.info(f"Clamped zoom to max: Z{self.zoom_level}")
            
            # Store metadata center for Recenter button reference
            if metadata.center:
                self.metadata_center_lon = metadata.center[0]
                self.metadata_center_lat = metadata.center[1]
                self.metadata_center_zoom = metadata.center[2]
                logger.debug(f"Stored metadata center: ({self.metadata_center_lat:.4f}, {self.metadata_center_lon:.4f}), Z{self.metadata_center_zoom}")
            elif metadata.bounds:
                west, south, east, north = metadata.bounds
                self.metadata_center_lon = (west + east) / 2
                self.metadata_center_lat = (south + north) / 2
                self.metadata_center_zoom = self.zoom_level
                logger.debug(f"Stored metadata center from bounds: ({self.metadata_center_lat:.4f}, {self.metadata_center_lon:.4f}), Z{self.metadata_center_zoom}")
            
            logger.info(f"Loaded MBTiles: Z{self.min_zoom}-Z{self.max_zoom}, Current position: ({self.center_lat:.4f}, {self.center_lon:.4f}), Z{self.zoom_level}")
            
            # Render map
            self.render_map()
        
        except Exception as e:
            logger.error(f"Error loading MBTiles: {e}")
    
    def zoom_in(self):
        """Increase zoom level."""
        if self.zoom_level < self.max_zoom:
            self.zoom_level += 1
            logger.debug(f"Zoomed in to Z{self.zoom_level}")
            self._save_position_to_config()
            self.render_map()
    
    def zoom_out(self):
        """Decrease zoom level."""
        if self.zoom_level > self.min_zoom:
            self.zoom_level -= 1
            logger.debug(f"Zoomed out to Z{self.zoom_level}")
            self._save_position_to_config()
            self.render_map()
    
    def _save_position_to_config(self) -> None:
        """
        Save current map position to config.
        
        Stores center coordinates and zoom level so they can be restored
        in the Track Editor and other Map Editor instances.
        
        Uses set_silent() to avoid feedback loop from emitting signals 3 times,
        then emits once after all values are set.
        """
        if self.config:
            # ✅ NEW: Use set_silent to avoid feedback loop
            self.config.set_silent('appearance.tiles.recent_zoom', self.zoom_level)
            self.config.set_silent('appearance.tiles.recent_center.lat', self.center_lat)
            self.config.set_silent('appearance.tiles.recent_center.lon', self.center_lon)
            
            # ✅ NEW: Emit signal ONCE after all values are set
            self.config.emit_map_position_changed()
            
            # ✅ CRITICAL: Save to file (this was missing!)
            self.config.save_to_file()
            
            logger.debug(f"Saved position to config: Z{self.zoom_level} at ({self.center_lat:.4f}, {self.center_lon:.4f})")
    
    def _on_map_position_changed_external(self, lat, lon, zoom):
        """
        Handler for map_position_changed signal from config.
        
        Called when another tab (Track Editor) changes the map position/zoom.
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
        self.render_map()
    
    def mark_center(self):
        """
        Mark current map center and zoom as the default.
        
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
            
            # Step 2: Update settings.yaml with new default center/zoom
            self.config.set('appearance.tiles.default_zoom', self.zoom_level)
            self.config.set('appearance.tiles.default_center.lat', self.center_lat)
            self.config.set('appearance.tiles.default_center.lon', self.center_lon)
            self.config.save_to_file()
            logger.info(f"✅ mark_center: Marked as default center: Z{self.zoom_level}, ({self.center_lat:.4f}, {self.center_lon:.4f})")
            
        except Exception as e:
            logger.error(f"❌ mark_center: Error marking center: {e}", exc_info=True)
    
    def recenter(self):
        """
        Recenter map to the marked default position and zoom.
        
        If user has clicked "Mark Center" button, navigate to that location.
        If not set, do nothing (user hasn't marked a default yet).
        
        Implementation matches MapWidget.recenter_on_default() exactly.
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
        self._save_position_to_config()
        
        logger.info(f"Recentered to marked default: Z{self.zoom_level}, ({self.center_lat:.4f}, {self.center_lon:.4f})")
        self.render_map()
    
    def set_center(self, lon: float, lat: float):
        """
        Set map center to specific coordinates.
        
        Args:
            lon: Longitude
            lat: Latitude
        """
        self.center_lon = lon
        self.center_lat = lat
        logger.debug(f"Set center to ({lon:.4f}, {lat:.4f})")
        self.render_map()
    
    def mousePressEvent(self, event):
        """Handle mouse press - check for button clicks first, then start pan."""
        if event.button() == Qt.LeftButton:
            x, y = event.x(), event.y()
            
            # Check if clicking on any button
            cfg = MapButtonConfig
            button_y = cfg.PADDING_TOP
            
            for button_name in self.button_manager.BUTTON_ORDER:
                if (cfg.PADDING_LEFT <= x <= cfg.PADDING_LEFT + cfg.BUTTON_SIZE and
                    button_y <= y <= button_y + cfg.BUTTON_SIZE):
                    # Clicked on a button
                    self.pressed_button = button_name
                    self.render_map()
                    
                    if button_name == 'zoom_in':
                        self.zoom_in()
                    elif button_name == 'zoom_out':
                        self.zoom_out()
                    elif button_name == 'mark_center':
                        self.mark_center()
                    elif button_name == 'recenter':
                        self.recenter()
                    return
                
                button_y += cfg.BUTTON_SIZE + cfg.BUTTON_SPACING
            
            # Not on a button - start pan
            self.pan_start_x = x
            self.pan_start_y = y
    
    def mouseMoveEvent(self, event):
        """Handle mouse move - pan map and detect button hovers."""
        x, y = event.x(), event.y()
        
        # Check for button hover
        cfg = MapButtonConfig
        button_y = cfg.PADDING_TOP
        old_hovered = self.hovered_button
        self.hovered_button = None
        
        for button_name in self.button_manager.BUTTON_ORDER:
            if (cfg.PADDING_LEFT <= x <= cfg.PADDING_LEFT + cfg.BUTTON_SIZE and
                button_y <= y <= button_y + cfg.BUTTON_SIZE):
                if button_name != 'zoom_level_label':
                    self.hovered_button = button_name
                break
            button_y += cfg.BUTTON_SIZE + cfg.BUTTON_SPACING
        
        # Re-render only if hover state changed
        if old_hovered != self.hovered_button:
            self.render_map()
        
        # Handle panning
        if self.pan_start_x is not None and self.pan_start_y is not None:
            if self.mbtiles_provider is None:
                return
            
            # Calculate pixel delta
            delta_x = self.pan_start_x - event.x()
            delta_y = self.pan_start_y - event.y()
            
            # Convert pixel delta to tile coordinates using Web Mercator
            # Key insight: Work in tile coordinates (linear), not degrees (non-linear in Web Mercator)
            
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
            
            # Get current position in tile coordinates
            tile_x, tile_y = latlon_to_tile(self.center_lat, self.center_lon, self.zoom_level)
            
            # Calculate tile delta from pixel delta
            tile_delta_x = delta_x / self.TILE_SIZE
            tile_delta_y = delta_y / self.TILE_SIZE
            
            # Update tile position
            new_tile_x = tile_x + tile_delta_x
            new_tile_y = tile_y + tile_delta_y
            
            # Convert back to lat/lon
            self.center_lat, self.center_lon = tile_to_latlon(new_tile_x, new_tile_y, self.zoom_level)
            
            # Render and update pan start
            self.render_map()
            self.pan_start_x = event.x()
            self.pan_start_y = event.y()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release - end pan and clear pressed state."""
        if event.button() == Qt.LeftButton:
            # Clear pressed state
            if self.pressed_button is not None:
                self.pressed_button = None
                self.render_map()
            
            if self.pan_start_x is not None:
                self._save_position_to_config()
            self.pan_start_x = None
            self.pan_start_y = None
    
    def wheelEvent(self, event):
        """Handle mouse wheel - zoom at cursor position."""
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
        cursor_tile_x = (cursor_x - self.width() / 2) / self.TILE_SIZE + tile_x
        cursor_tile_y = (cursor_y - self.height() / 2) / self.TILE_SIZE + tile_y
        cursor_lat, cursor_lon = tile_to_latlon(cursor_tile_x, cursor_tile_y, self.zoom_level)
        
        # Zoom in or out
        old_zoom = self.zoom_level
        if event.angleDelta().y() > 0:
            if self.zoom_level < self.max_zoom:
                self.zoom_level += 1
        else:
            if self.zoom_level > self.min_zoom:
                self.zoom_level -= 1
        
        # If zoom changed, recalculate center to keep cursor at same GPS location
        if self.zoom_level != old_zoom:
            new_tile_x, new_tile_y = latlon_to_tile(cursor_lat, cursor_lon, self.zoom_level)
            # Calculate the new center to keep cursor at same screen position
            self.center_tile_x = new_tile_x - (cursor_x - self.width() / 2) / self.TILE_SIZE
            self.center_tile_y = new_tile_y - (cursor_y - self.height() / 2) / self.TILE_SIZE
            self.center_lat, self.center_lon = tile_to_latlon(self.center_tile_x, self.center_tile_y, self.zoom_level)
            
            logger.debug(f"Zoomed to Z{self.zoom_level} at cursor position")
            
            # ✅ CRITICAL FIX: Save new position to config after zoom
            self._save_position_to_config()
            
            self.render_map()
    
    def resizeEvent(self, event):
        """Handle window resize - re-render map with new dimensions."""
        super().resizeEvent(event)
        self.render_map()
    
    def render_map(self):
        """Render the map to display."""
        if not self.mbtiles_provider or self.width() < 10 or self.height() < 10:
            return
        
        try:
            # Create renderer
            renderer = MapRenderer(
                self.width(),
                self.height(),
                self.mbtiles_provider,
                self.center_lat,
                self.center_lon,
                self.zoom_level
            )
            
            # Render tiles (returns RGBA)
            pil_image = renderer.render()
            
            # Draw crosshair at center (shared function - same as MapWidget)
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
            
            # Draw UI controls on the image
            pil_image = self._draw_ui_controls(pil_image)
            
            # Convert to RGB for QPixmap
            pil_image = pil_image.convert('RGB')
            
            # Save to temp file and display
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
        
        # Always reposition buttons on top
        self.button_manager.position_all_buttons()
    
    def _draw_ui_controls(self, pil_image):
        """Draw button visuals on the PIL image using button manager."""
        # Ensure image is RGBA
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        
        overlay = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Button manager draws all buttons with state
        self.button_manager.draw_all_buttons(draw, zoom_level=self.zoom_level, 
                                             hovered_button=self.hovered_button,
                                             pressed_button=self.pressed_button)
        
        # Composite overlay
        result = Image.alpha_composite(pil_image, overlay)
        return result
