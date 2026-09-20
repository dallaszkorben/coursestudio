"""
Map renderer for displaying MBTiles with proper coordinate transformations.

Based on openseemap's proven working implementation.
Handles tile loading, coordinate conversion, and overlay rendering.
"""

import math
from PIL import Image

from src.map.mbtiles_provider import MBTilesProvider


class MapRenderer:
    """
    Renders map tiles and overlays to a display surface.
    
    Manages the transformation between world coordinates (tiles, GPS)
    and screen coordinates (pixels on the display).
    """
    
    TILE_SIZE = 256  # Standard tile size in pixels
    
    def __init__(self, width: int, height: int, mbtiles_provider: MBTilesProvider,
                 center_lat: float, center_lon: float, zoom_level: int = 13):
        """
        Initialize the map renderer.
        
        Args:
            width (int): Display width in pixels
            height (int): Display height in pixels
            mbtiles_provider (MBTilesProvider): The tile provider
            center_lat (float): Center latitude
            center_lon (float): Center longitude
            zoom_level (int): Initial zoom level
        """
        self.width = width
        self.height = height
        self.mbtiles_provider = mbtiles_provider
        self.zoom_level = zoom_level
        
        # Store GPS center for zoom adjustments
        self.center_lat = center_lat
        self.center_lon = center_lon
        
        # Current view center in tile coordinates
        self.center_tile_x, self.center_tile_y = self._latlon_to_tile(center_lat, center_lon, zoom_level)
    
    def _latlon_to_tile(self, latitude: float, longitude: float, zoom: int) -> tuple:
        """
        Convert latitude/longitude to tile coordinates.
        
        Args:
            latitude (float): Latitude in decimal degrees
            longitude (float): Longitude in decimal degrees
            zoom (int): Zoom level
            
        Returns:
            tuple: (tile_x, tile_y) as floats
        """
        # Web Mercator projection
        n = 2.0 ** zoom
        
        # Longitude to tile
        tile_x = (longitude + 180.0) / 360.0 * n
        
        # Latitude to tile
        lat_rad = math.radians(latitude)
        tile_y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
        
        return tile_x, tile_y
    
    def _tile_to_latlon(self, tile_x: float, tile_y: float, zoom: int) -> tuple:
        """
        Convert tile coordinates to latitude/longitude.
        
        Args:
            tile_x (float): Tile X coordinate
            tile_y (float): Tile Y coordinate
            zoom (int): Zoom level
            
        Returns:
            tuple: (latitude, longitude)
        """
        n = 2.0 ** zoom
        
        # Tile to longitude
        longitude = tile_x / n * 360.0 - 180.0
        
        # Tile to latitude
        lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * tile_y / n)))
        latitude = math.degrees(lat_rad)
        
        return latitude, longitude
    
    def render(self) -> Image.Image:
        """
        Render the current map view to a PIL Image.
        
        Returns:
            PIL.Image: The rendered map image (RGB)
        """
        # Create a blank image for the render
        render_image = Image.new('RGB', (self.width, self.height), color=(200, 200, 200))
        
        # Calculate which tiles we need to display
        # We need to show tiles that intersect with the viewport
        
        # Calculate the top-left tile coordinate of the viewport
        viewport_half_width = self.width / 2 / self.TILE_SIZE
        viewport_half_height = self.height / 2 / self.TILE_SIZE
        
        min_tile_x = int(self.center_tile_x - viewport_half_width - 1)
        max_tile_x = int(self.center_tile_x + viewport_half_width + 1)
        min_tile_y = int(self.center_tile_y - viewport_half_height - 1)
        max_tile_y = int(self.center_tile_y + viewport_half_height + 1)
        
        # Wrap tile coordinates for the current zoom level
        max_tile_coord = 2 ** self.zoom_level
        
        # Draw tiles
        for tile_y in range(min_tile_y, max_tile_y + 1):
            for tile_x in range(min_tile_x, max_tile_x + 1):
                # Wrap X coordinate (longitude wraps around)
                wrapped_tile_x = tile_x % max_tile_coord
                
                # Clamp Y coordinate (latitude doesn't wrap)
                if tile_y < 0 or tile_y >= max_tile_coord:
                    continue
                
                # Get the tile image
                tile_image = self.mbtiles_provider.get_tile_image(self.zoom_level, wrapped_tile_x, tile_y)
                
                if tile_image is not None:
                    # Calculate screen position for this tile
                    screen_x = int((tile_x - self.center_tile_x) * self.TILE_SIZE + self.width / 2)
                    screen_y = int((tile_y - self.center_tile_y) * self.TILE_SIZE + self.height / 2)
                    
                    # Paste the tile onto the render image
                    render_image.paste(tile_image, (screen_x, screen_y))
        
        return render_image
    
    def gps_to_screen(self, latitude: float, longitude: float) -> tuple:
        """
        Convert GPS coordinates to screen coordinates.
        
        Args:
            latitude (float): Latitude in decimal degrees
            longitude (float): Longitude in decimal degrees
        
        Returns:
            tuple: (screen_x, screen_y) or None if off-screen
        """
        # Convert GPS to tile coordinates
        tile_x, tile_y = self._latlon_to_tile(latitude, longitude, self.zoom_level)
        
        # Convert tile coordinates to screen coordinates
        screen_x = int((tile_x - self.center_tile_x) * self.TILE_SIZE + self.width / 2)
        screen_y = int((tile_y - self.center_tile_y) * self.TILE_SIZE + self.height / 2)
        
        # Check if point is on screen
        if -self.TILE_SIZE <= screen_x <= self.width + self.TILE_SIZE and \
           -self.TILE_SIZE <= screen_y <= self.height + self.TILE_SIZE:
            return (screen_x, screen_y)
        
        return None
    
    def screen_to_gps(self, screen_x: int, screen_y: int) -> tuple:
        """
        Convert screen coordinates to GPS coordinates.
        
        Args:
            screen_x (int): Screen X coordinate
            screen_y (int): Screen Y coordinate
        
        Returns:
            tuple: (latitude, longitude)
        """
        # Convert screen coordinates to tile coordinates
        tile_x = (screen_x - self.width / 2) / self.TILE_SIZE + self.center_tile_x
        tile_y = (screen_y - self.height / 2) / self.TILE_SIZE + self.center_tile_y
        
        # Convert tile coordinates to GPS
        latitude, longitude = self._tile_to_latlon(tile_x, tile_y, self.zoom_level)
        return (latitude, longitude)
    
    def set_center_gps(self, latitude: float, longitude: float):
        """
        Set the map center from GPS coordinates.
        
        Args:
            latitude (float): Latitude in decimal degrees
            longitude (float): Longitude in decimal degrees
        """
        self.center_lat = latitude
        self.center_lon = longitude
        self.center_tile_x, self.center_tile_y = self._latlon_to_tile(latitude, longitude, self.zoom_level)
    
    def set_zoom_level(self, zoom_level: int):
        """
        Change the zoom level.
        
        When zooming, maintain the current map center position.
        
        Args:
            zoom_level (int): New zoom level
        """
        old_zoom = self.zoom_level
        self.zoom_level = zoom_level
        
        # Recalculate tile coordinates for the new zoom level
        # The relationship between zoom levels is: tile_coord *= (2 ^ delta_zoom)
        zoom_factor = 2 ** (zoom_level - old_zoom)
        self.center_tile_x *= zoom_factor
        self.center_tile_y *= zoom_factor
    
    def pan_by_gps_delta(self, delta_lat: float, delta_lon: float):
        """
        Pan the map by GPS coordinate delta.
        
        Args:
            delta_lat (float): Latitude delta in degrees
            delta_lon (float): Longitude delta in degrees
        """
        self.center_lat += delta_lat
        self.center_lon += delta_lon
        self.center_tile_x, self.center_tile_y = self._latlon_to_tile(self.center_lat, self.center_lon, self.zoom_level)
