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
        self.center_lat = 0
        self.center_lon = 0
        self.zoom_level = 10
        self.min_zoom = 1
        self.max_zoom = 20
        
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
        """Set the MBTiles provider (called by main window)."""
        self.mbtiles_provider = mbtiles_provider
        logger.debug("MBTilesProvider set in MapViewer")
    
    def load_mbtiles(self, mbtiles_provider: MBTilesProvider):
        """Load an MBTiles file via provider."""
        try:
            self.mbtiles_provider = mbtiles_provider
            
            # Get map metadata
            metadata = mbtiles_provider.get_metadata()
            if metadata is None:
                logger.error("No metadata available from mbtiles_provider")
                return
            
            # Get actual zoom levels available
            available_zooms = mbtiles_provider.get_available_zooms()
            if available_zooms:
                self.min_zoom = min(available_zooms)
                self.max_zoom = max(available_zooms)
            else:
                self.min_zoom = 1
                self.max_zoom = 20
            
            # Set initial zoom level
            self.zoom_level = (self.min_zoom + self.max_zoom) // 2
            
            # Set center from metadata or bounds
            if metadata.center:
                # ✅ Use metadata center and zoom
                self.center_lon = metadata.center[0]
                self.center_lat = metadata.center[1]
                self.zoom_level = metadata.center[2]
                self.metadata_center_lon = metadata.center[0]
                self.metadata_center_lat = metadata.center[1]
                self.metadata_center_zoom = metadata.center[2]
            elif metadata.bounds:
                # Fallback to bounds center
                west, south, east, north = metadata.bounds
                self.center_lon = (west + east) / 2
                self.center_lat = (south + north) / 2
                self.metadata_center_lon = self.center_lon
                self.metadata_center_lat = self.center_lat
                self.metadata_center_zoom = self.zoom_level
            else:
                # Default to 0, 0
                self.center_lat = 0
                self.center_lon = 0
            
            # ✅ NEW: Load recent position from config if available
            if self.config:
                recent_center_lat = self.config.get_float('appearance.tiles.recent_center.lat', None)
                recent_center_lon = self.config.get_float('appearance.tiles.recent_center.lon', None)
                recent_zoom = self.config.get_int('appearance.tiles.recent_zoom', None)
                
                # Check if recent values are within valid bounds
                if (recent_center_lat is not None and recent_center_lon is not None and 
                    recent_zoom is not None):
                    if self.min_zoom <= recent_zoom <= self.max_zoom:
                        self.center_lat = recent_center_lat
                        self.center_lon = recent_center_lon
                        self.zoom_level = recent_zoom
                        logger.info(f"Loaded recent position from config: Z{self.zoom_level} at ({self.center_lat:.4f}, {self.center_lon:.4f})")
            
            zoom_range = f"Z{self.min_zoom}-Z{self.max_zoom}"
            logger.info(f"Loaded MBTiles via provider")
            logger.info(f"Available zoom: {zoom_range}, Current: Z{self.zoom_level}")
            logger.info(f"Center: {self.center_lat:.4f}, {self.center_lon:.4f}")
            
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
        logger.debug(f"Updated map from external signal: Z{self.zoom_level} at ({self.center_lat:.4f}, {self.center_lon:.4f})")
    
    def mark_center(self):
        """
        Mark current map center and zoom as the default.
        
        Saves current center_lat, center_lon, and zoom_level to config as defaults.
        This allows the user to have a "home" position they can jump back to with the Recenter button.
        """
        self.config.set('appearance.tiles.default_zoom', self.zoom_level)
        self.config.set('appearance.tiles.default_center.lat', self.center_lat)
        self.config.set('appearance.tiles.default_center.lon', self.center_lon)
        self.config.save_to_file()
        logger.info(f"Marked center: Z{self.zoom_level}, ({self.center_lat:.4f}, {self.center_lon:.4f})")
    
    def recenter(self):
        """
        Recenter map to the metadata center point.
        
        Moves to center coordinates and zoom level stored in metadata.
        """
        self.center_lon = self.metadata_center_lon
        self.center_lat = self.metadata_center_lat
        self.zoom_level = self.metadata_center_zoom
        logger.debug(f"Recentered to metadata center ({self.center_lon:.4f}, {self.center_lat:.4f}) at Z{self.zoom_level}")
        self._save_position_to_config()
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
