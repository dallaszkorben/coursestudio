"""
Map widget for displaying GPS tracks with pan and zoom controls.

Direct adaptation of openseemap's proven working MapWidget.
"""

import tempfile
import os
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PIL import ImageDraw

from src.map.mbtiles_provider import MBTilesProvider
from src.map.map_renderer import MapRenderer


class MapWidget(QWidget):
    """
    Custom widget that displays the map.
    
    Handles map rendering and user interactions like panning and zooming.
    """
    
    # Signals
    map_ready = pyqtSignal()
    track_clicked = pyqtSignal(str)
    point_clicked = pyqtSignal(str, int)
    
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
        self.show_turning_points = True  # Show/hide turning points
        
        # Load track display settings from config
        from config.app_config_yaml import AppConfig
        config = AppConfig()
        
        # Parse colors from config (hex format: RRGGBB)
        self.track_color = self._hex_to_rgb(config.get_str('Map.track.path.color', 'FF0000'))
        self.selected_track_color = self._hex_to_rgb(config.get_str('Map.track.selected.color', 'FF3232'))
        self.selected_point_color = self._hex_to_rgb(config.get_str('Map.turning_points.selected.color', 'FFFF00'))
        
        # Turning points settings
        # NOTE: Read from last_state to get user's preference, not the default
        self.show_turning_points = config.get_bool('Map.last_state.show_turning_points', True)
        self.turning_point_color = self._hex_to_rgb(config.get_str('Map.turning_points.color', 'FFFF00'))
        self.selected_turning_point_color = self._hex_to_rgb(config.get_str('Map.turning_points.selected.color', '0000FF'))
        self.turning_point_size = config.get_int('Map.turning_points.size', 4)
        self.selected_turning_point_size = config.get_int('Map.turning_points.selected.size', 5)
        
        # Track path width
        self.track_path_width = config.get_int('Map.track.path.width', 3)
        
        # Map state
        self.center_lat = 56.168
        self.center_lon = 15.586
        self.zoom_level = self.ZOOM_LEVEL_DEFAULT
        
        # Map display label
        self.map_label = QLabel()
        self.map_label.setStyleSheet("background-color: #c0c0c0;")
        self.map_label.setAlignment(Qt.AlignCenter)
        
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
        self.selected_track_id = track_id
        self.selected_trackpoint_index = None
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
          - If True: Draw all turning points (yellow), selected one in blue
          - If False: Draw no turning points normally
        - Exception: If show_turning_points is False BUT a trackpoint is selected,
          draw only that selected turning point in blue
        """
        if not self.track_manager:
            return pil_image
        
        # Only draw the selected track
        if self.selected_track_id is None:
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
                    # Draw all turning points (yellow for normal, blue for selected)
                    for i, tp in enumerate(trackpoints):
                        screen = map_renderer.gps_to_screen(tp.latitude, tp.longitude)
                        
                        if screen:
                            x, y = screen
                            
                            # Determine color and size: selected point is blue and larger, others are yellow
                            if i == self.selected_trackpoint_index:
                                point_color = self.selected_turning_point_color
                                r = self.selected_turning_point_size
                            else:
                                point_color = self.turning_point_color
                                r = self.turning_point_size
                            
                            # Draw circle for turning point
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
    
    def mousePressEvent(self, event):
        """Handle mouse button press."""
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
            
            # Otherwise, start pan
            self.pan_start_x = x
            self.pan_start_y = y
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement for panning."""
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
        """Draw UI control buttons on PIL image."""
        draw = ImageDraw.Draw(pil_image)
        
        button_bg = (52, 144, 220)
        button_border = (255, 255, 255)
        button_text = (255, 255, 255)
        border_width = 2
        corner_radius = 6
        
        x_pos = self.CONTROLS_PADDING_LEFT
        y_pos = self.CONTROLS_PADDING_TOP
        
        def draw_rounded_rect(x, y, size, fill_color, border_color, border_w):
            """Draw a rounded rectangle."""
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
        
        # Draw zoom in button
        draw_rounded_rect(x_pos, y_pos, self.ZOOM_BUTTON_SIZE, button_bg, button_border, border_width)
        center = self.ZOOM_BUTTON_SIZE // 2
        draw.line([(x_pos + center - 6, y_pos + center), (x_pos + center + 6, y_pos + center)], fill=button_text, width=2)
        draw.line([(x_pos + center, y_pos + center - 6), (x_pos + center, y_pos + center + 6)], fill=button_text, width=2)
        
        # Draw zoom out button
        y_pos += self.ZOOM_BUTTON_SIZE + self.ZOOM_BUTTON_SPACING
        draw_rounded_rect(x_pos, y_pos, self.ZOOM_BUTTON_SIZE, button_bg, button_border, border_width)
        center = self.ZOOM_BUTTON_SIZE // 2
        draw.line([(x_pos + center - 6, y_pos + center), (x_pos + center + 6, y_pos + center)], fill=button_text, width=2)
        
        # Draw zoom level label
        y_pos += self.ZOOM_BUTTON_SIZE + self.ZOOM_BUTTON_SPACING
        zoom_text = f"Z:{self.zoom_level}"
        draw_rounded_rect(x_pos, y_pos, self.ZOOM_BUTTON_SIZE, button_bg, button_border, border_width)
        draw.text((x_pos + 8, y_pos + 12), zoom_text, fill=button_text)
        
        # Draw recenter button
        y_pos += self.ZOOM_BUTTON_SIZE + self.ZOOM_BUTTON_SPACING
        draw_rounded_rect(x_pos, y_pos, self.ZOOM_BUTTON_SIZE, button_bg, button_border, border_width)
        center_x = x_pos + self.ZOOM_BUTTON_SIZE // 2
        center_y = y_pos + self.ZOOM_BUTTON_SIZE // 2
        draw.ellipse((center_x - 12, center_y - 12, center_x + 12, center_y + 12), outline=button_text, width=2)
        draw.ellipse((center_x - 7, center_y - 7, center_x + 7, center_y + 7), outline=button_text, width=1)
        draw.ellipse((center_x - 3, center_y - 3, center_x + 3, center_y + 3), fill=button_text)
        
        return pil_image
