"""
WORKING PIL-based interactive map widget - modeled after proven openseemap implementation.

This is a corrected implementation that uses proper tile-based pan/zoom calculations.
Key difference from previous: Uses MapRenderer directly with tile coordinates, not lat/lon.
"""

import logging
from typing import Optional, List
import tempfile
import os

from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRect, QSize
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtGui import QPixmap, QFont

from src.map.mbtiles_provider import MBTilesProvider

logger = logging.getLogger(__name__)


class MapWidget(QWidget):
    """
    Working PIL-based interactive map widget.
    
    Handles:
    - Map rendering from MBTiles via PIL
    - Mouse panning (left-drag)
    - Mouse wheel zoom (+/-)
    - Zoom buttons
    """
    
    # Signals
    map_ready = pyqtSignal()
    track_clicked = pyqtSignal(int)  # track_index
    point_clicked = pyqtSignal(int)  # point_index
    
    def __init__(self, track_manager, mbtiles_provider: MBTilesProvider, logger_obj: logging.Logger, parent=None):
        """
        Initialize the map widget.
        
        Args:
            track_manager: TrackManager instance
            mbtiles_provider: MBTilesProvider for tile loading
            logger_obj: Logger instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.track_manager = track_manager
        self.mbtiles_provider = mbtiles_provider
        self.logger = logger_obj
        
        # Store track data for rendering
        self.tracks = None
        self.highlighted_track_index = None
        self.highlighted_point_index = None
        
        # Map center (in latitude/longitude)
        self.center_lat = 56.1612  # Karlskrona, Sweden
        self.center_lon = 15.5869
        self.zoom_level = 13
        
        # Panning state
        self.pan_start_x = None
        self.pan_start_y = None
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # UI components
        self._init_ui()
        
        # Render timer (100ms debounce)
        self.render_timer = QTimer()
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self._do_render)
        self.render_timer.setInterval(100)
        
        # Initial render
        self._schedule_render()
    
    def _init_ui(self) -> None:
        """Initialize UI components."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Map display label
        self.map_label = QLabel()
        self.map_label.setAlignment(Qt.AlignCenter)
        self.map_label.setMinimumSize(400, 300)
        self.map_label.setStyleSheet("background-color: #cccccc; border: 1px solid gray;")
        self.map_label.setMouseTracking(True)
        self.map_label.installEventFilter(self)  # Forward events
        main_layout.addWidget(self.map_label, 1)
        
        self.setLayout(main_layout)
        
        # Zoom buttons (invisible overlay with transparent background)
        self.zoom_in_button = QPushButton("+", self)
        self.zoom_in_button.setFixedSize(60, 60)
        self.zoom_in_button.clicked.connect(self._on_zoom_in)
        self.zoom_in_button.setStyleSheet("background-color: transparent; border: none; color: transparent;")
        self.zoom_in_button.setFocusPolicy(Qt.NoFocus)
        
        self.zoom_out_button = QPushButton("−", self)
        self.zoom_out_button.setFixedSize(60, 60)
        self.zoom_out_button.clicked.connect(self._on_zoom_out)
        self.zoom_out_button.setStyleSheet("background-color: transparent; border: none; color: transparent;")
        self.zoom_out_button.setFocusPolicy(Qt.NoFocus)
        
        self.recenter_button = QPushButton("⊙", self)
        self.recenter_button.setFixedSize(60, 60)
        self.recenter_button.setToolTip("Recenter on track")
        self.recenter_button.clicked.connect(self._on_reset_center)
        self.recenter_button.setStyleSheet("background-color: transparent; border: none; color: transparent;")
        self.recenter_button.setFocusPolicy(Qt.NoFocus)
        
        self.zoom_level_label = QLabel(f"Z: {self.zoom_level}", self)
        self.zoom_level_label.setStyleSheet("background-color: transparent; border: none; color: transparent;")
        
        self._reposition_controls()
    
    def _reposition_controls(self) -> None:
        """Reposition invisible button hitboxes."""
        x = 10
        y = 10
        
        self.zoom_in_button.move(x, y)
        y += 70
        self.zoom_out_button.move(x, y)
        y += 70
        self.zoom_level_label.move(x, y)
        y += 70
        self.recenter_button.move(x, y)
    
    def _on_zoom_in(self) -> None:
        """Zoom in."""
        available = self.mbtiles_provider.get_available_zooms()
        if available:
            max_z = max(available)
            if self.zoom_level < max_z:
                self.zoom_level += 1
                self._schedule_render()
    
    def _on_zoom_out(self) -> None:
        """Zoom out."""
        available = self.mbtiles_provider.get_available_zooms()
        if available:
            min_z = min(available)
            if self.zoom_level > min_z:
                self.zoom_level -= 1
                self._schedule_render()
    
    def _on_reset_center(self) -> None:
        """Reset to default center."""
        self.center_lat = 56.1612
        self.center_lon = 15.5869
        self._schedule_render()
    
    def _schedule_render(self) -> None:
        """Schedule a render (debounced)."""
        self.render_timer.stop()
        self.render_timer.start()
    
    def _do_render(self) -> None:
        """Perform map render."""
        try:
            from src.map.map_renderer import MapRenderer
            from PIL import ImageDraw, ImageFont
            import tempfile
            
            # Get tracks
            if hasattr(self.track_manager, 'get_all_tracks'):
                tracks = self.track_manager.get_all_tracks()
            else:
                tracks = None
            
            # Create renderer with correct dimensions
            renderer = MapRenderer(self.mbtiles_provider, self.width(), self.height())
            
            # Render map (returns PIL Image)
            pil_image = renderer._render_from_tiles(self.center_lat, self.center_lon, self.zoom_level)[0]
            
            if not pil_image:
                self.logger.error("Map rendering returned None")
                return
            
            # Draw tracks on the PIL image
            if tracks:
                draw = ImageDraw.Draw(pil_image)
                for track_idx, track in enumerate(tracks):
                    if track.trackpoints and len(track.trackpoints) > 1:
                        is_highlighted = track_idx == self.highlighted_track_index
                        color = (255, 0, 0) if is_highlighted else (0, 0, 255)  # Red or Blue
                        width = 2 if is_highlighted else 1
                        self._draw_track_on_image(draw, pil_image, track, color, width, renderer)
            
            # Draw UI controls directly on the PIL image
            pil_image = self._draw_ui_controls_on_image(pil_image, renderer)
            
            # Convert PIL to QPixmap and display
            self._pil_to_pixmap_and_display(pil_image)
            
            self.zoom_level_label.setText(f"Z: {self.zoom_level}")
            self.map_ready.emit()
        
        except Exception as e:
            self.logger.error(f"Map render error: {e}")
            import traceback
            traceback.print_exc()
    
    def _draw_track_on_image(self, draw, pil_image, track, color, width, renderer):
        """Draw a track on the PIL image."""
        try:
            from utils.helpers import lat_lon_to_tile_coords, tile_coords_to_pixel
            
            points = []
            for point in track.trackpoints:
                tile_x, tile_y = lat_lon_to_tile_coords(point.latitude, point.longitude, self.zoom_level)
                
                # Convert tile to screen coordinates relative to map center
                center_tile_x, center_tile_y = lat_lon_to_tile_coords(
                    self.center_lat, self.center_lon, self.zoom_level
                )
                
                screen_x = int((tile_x - center_tile_x) * 256 + self.width() / 2)
                screen_y = int((tile_y - center_tile_y) * 256 + self.height() / 2)
                
                if -256 <= screen_x <= self.width() + 256 and -256 <= screen_y <= self.height() + 256:
                    points.append((screen_x, screen_y))
            
            if len(points) > 1:
                draw.line(points, fill=color, width=width)
        
        except Exception as e:
            self.logger.debug(f"Error drawing track: {e}")
    
    def _draw_ui_controls_on_image(self, pil_image, renderer):
        """Draw UI controls directly onto the PIL image."""
        from PIL import ImageDraw
        
        draw = ImageDraw.Draw(pil_image)
        
        # Button styling
        button_bg = (52, 144, 220)
        button_border = (255, 255, 255)
        button_text = (255, 255, 255)
        border_width = 2
        corner_radius = 6
        button_size = 60
        
        x_pos = 10
        y_pos = 10
        spacing = 8
        
        def draw_rounded_rect(x, y, size, fill_color, border_color, border_w):
            """Draw a rounded rectangle button."""
            r = corner_radius
            draw.rectangle([x+r, y, x+size-r, y+size], fill=fill_color)
            draw.rectangle([x, y+r, x+size, y+size-r], fill=fill_color)
            draw.ellipse([x, y, x+2*r, y+2*r], fill=fill_color)
            draw.ellipse([x+size-2*r, y, x+size, y+2*r], fill=fill_color)
            draw.ellipse([x, y+size-2*r, x+2*r, y+size], fill=fill_color)
            draw.ellipse([x+size-2*r, y+size-2*r, x+size, y+size], fill=fill_color)
            
            if border_w > 0:
                draw.rectangle([x+r, y, x+size-r, y+border_w], fill=border_color)
                draw.rectangle([x+r, y+size-border_w, x+size-r, y+size], fill=border_color)
                draw.rectangle([x, y+r, x+border_w, y+size-r], fill=border_color)
                draw.rectangle([x+size-border_w, y+r, x+size, y+size-r], fill=border_color)
        
        # Zoom in button
        draw_rounded_rect(x_pos, y_pos, button_size, button_bg, button_border, border_width)
        center = button_size // 2
        draw.line([(x_pos + center - 6, y_pos + center), (x_pos + center + 6, y_pos + center)], 
                 fill=button_text, width=2)
        draw.line([(x_pos + center, y_pos + center - 6), (x_pos + center, y_pos + center + 6)], 
                 fill=button_text, width=2)
        
        # Zoom out button
        y_pos += button_size + spacing
        draw_rounded_rect(x_pos, y_pos, button_size, button_bg, button_border, border_width)
        center = button_size // 2
        draw.line([(x_pos + center - 6, y_pos + center), (x_pos + center + 6, y_pos + center)], 
                 fill=button_text, width=2)
        
        # Zoom level label
        y_pos += button_size + spacing
        zoom_text = f"Z:{self.zoom_level}"
        draw_rounded_rect(x_pos, y_pos, button_size, button_bg, button_border, border_width)
        draw.text((x_pos + 12, y_pos + 18), zoom_text, fill=button_text)
        
        # Recenter button
        y_pos += button_size + spacing
        draw_rounded_rect(x_pos, y_pos, button_size, button_bg, button_border, border_width)
        center_x = x_pos + button_size // 2
        center_y = y_pos + button_size // 2
        draw.ellipse((center_x - 12, center_y - 12, center_x + 12, center_y + 12), 
                    outline=button_text, width=2)
        draw.ellipse((center_x - 7, center_y - 7, center_x + 7, center_y + 7), 
                    outline=button_text, width=1)
        draw.ellipse((center_x - 3, center_y - 3, center_x + 3, center_y + 3), 
                    fill=button_text)
        
        return pil_image
    
    def _pil_to_pixmap_and_display(self, pil_image):
        """Convert PIL image to QPixmap and display."""
        import tempfile
        import os
        
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
    
    def set_tracks(self, tracks: List = None, highlighted_track_index: int = None, 
                   highlighted_point_index: int = None) -> None:
        """Set tracks to display."""
        self.tracks = tracks
        self.highlighted_track_index = highlighted_track_index
        self.highlighted_point_index = highlighted_point_index
        self._schedule_render()
    
    def on_track_list_selection_changed(self, track_index: int) -> None:
        """Handle track selection from track list."""
        self.highlighted_track_index = track_index
        self._schedule_render()
    
    def on_track_selected(self, track_index: int) -> None:
        """Alias for compatibility."""
        self.on_track_list_selection_changed(track_index)
    
    def on_trackpoint_selected(self, track_index: int, point_index: int) -> None:
        """Handle trackpoint selection."""
        self.highlighted_track_index = track_index
        self.highlighted_point_index = point_index
        self._schedule_render()
    
    def on_point_selected(self, track_index: int, point_index: int) -> None:
        """Alias for on_trackpoint_selected."""
        self.on_trackpoint_selected(track_index, point_index)
    
    def eventFilter(self, obj, event):
        """Forward mouse events from map_label."""
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
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            x, y = event.x(), event.y()
            
            # Check buttons
            if self._is_point_in_button(x, y, self.zoom_in_button.geometry()):
                self.zoom_in_button.click()
                return
            if self._is_point_in_button(x, y, self.zoom_out_button.geometry()):
                self.zoom_out_button.click()
                return
            if self._is_point_in_button(x, y, self.recenter_button.geometry()):
                self.recenter_button.click()
                return
            
            # Start panning
            self.pan_start_x = x
            self.pan_start_y = y
    
    def _is_point_in_button(self, x: int, y: int, geometry: QRect) -> bool:
        """Check if point is in button."""
        return (geometry.x() <= x <= geometry.x() + geometry.width() and
                geometry.y() <= y <= geometry.y() + geometry.height())
    
    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move for panning - use proper Web Mercator math."""
        if self.pan_start_x is not None and self.pan_start_y is not None:
            # Calculate delta pixels
            delta_x = self.pan_start_x - event.x()
            delta_y = self.pan_start_y - event.y()
            
            if delta_x != 0 or delta_y != 0:
                import math
                
                # Correct Web Mercator pan calculation
                TILE_SIZE = 256
                tiles_at_zoom = 2 ** self.zoom_level
                earth_circumference_m = 40075016.686
                
                # Meters per pixel at this zoom and latitude
                cos_lat = math.cos(math.radians(self.center_lat))
                m_per_pixel_lon = (earth_circumference_m * cos_lat) / (TILE_SIZE * tiles_at_zoom)
                m_per_pixel_lat = earth_circumference_m / (TILE_SIZE * tiles_at_zoom)
                
                # Convert to degrees
                deg_per_m = 1.0 / 111320.0
                
                lon_delta = delta_x * m_per_pixel_lon * deg_per_m
                lat_delta = -delta_y * m_per_pixel_lat * deg_per_m
                
                # Apply pan
                self.center_lon += lon_delta
                self.center_lat += lat_delta
                
                # Clamp latitude
                self.center_lat = max(-85.051129, min(85.051129, self.center_lat))
                
                # Wrap longitude
                while self.center_lon > 180:
                    self.center_lon -= 360
                while self.center_lon < -180:
                    self.center_lon += 360
                
                self._schedule_render()
            
            # Update pan start
            self.pan_start_x = event.x()
            self.pan_start_y = event.y()
    
    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self.pan_start_x = None
            self.pan_start_y = None
    
    def wheelEvent(self, event) -> None:
        """Handle mouse wheel zoom."""
        if event.angleDelta().y() > 0:
            self._on_zoom_in()
        else:
            self._on_zoom_out()
    
    def resizeEvent(self, event) -> None:
        """Handle window resize."""
        super().resizeEvent(event)
        self._reposition_controls()
        self._schedule_render()
