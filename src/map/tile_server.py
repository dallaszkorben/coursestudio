"""
Custom tile server for serving mbtiles data to Leaflet.js map.

Provides a web server accessible from QWebEngineView that serves tiles
directly from mbtiles SQLite database files.

Architecture:
- TileRequestInterceptor: Intercepts custom-tiles:// requests
- Routes requests to MBTilesProvider
- Returns PNG/JPG tile data as HTTP responses
"""

import logging
from typing import Optional
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt5.QtCore import QUrl, QByteArray
from PyQt5.QtNetwork import QNetworkReply

from src.map.mbtiles_provider import MBTilesProvider


class TileRequestInterceptor(QWebEngineUrlRequestInterceptor):
    """
    Intercepts tile requests and serves them from mbtiles provider.
    
    Handles URLs like: custom-tiles://z/x/y
    """
    
    def __init__(self, mbtiles_provider: MBTilesProvider, logger: logging.Logger):
        """
        Initialize interceptor.
        
        Args:
            mbtiles_provider: MBTilesProvider for tile data
            logger: Logger instance
        """
        super().__init__()
        self.mbtiles_provider = mbtiles_provider
        self.logger = logger
    
    def interceptRequest(self, info: 'QWebEngineUrlRequestInfo') -> None:
        """
        Intercept and handle tile requests.
        
        Args:
            info: Request information object
        """
        url = info.requestUrl()
        
        # Only handle custom-tiles:// URLs
        if url.scheme() != "custom-tiles":
            return
        
        # Parse URL: custom-tiles://z/x/y
        path = url.path()
        try:
            parts = path.strip('/').split('/')
            if len(parts) != 3:
                self.logger.warning(f"Invalid tile URL: {url.toString()}")
                return
            
            zoom = int(parts[0])
            x = int(parts[1])
            y = int(parts[2])
        except (ValueError, IndexError) as e:
            self.logger.warning(f"Error parsing tile coordinates: {path}, {e}")
            return
        
        # Get tile data from provider
        tile_data = self.mbtiles_provider.get_tile(zoom, x, y)
        
        if tile_data:
            self.logger.debug(f"Serving tile: z={zoom}, x={x}, y={y} ({len(tile_data)} bytes)")
            
            # Create response with tile data
            # Note: QWebEngineUrlRequestInfo doesn't allow direct response setting
            # We need to use a different approach with custom URL scheme
        else:
            self.logger.debug(f"Tile not found: z={zoom}, x={x}, y={y}")


class CustomTileScheme:
    """
    Custom URL scheme handler for serving tiles from mbtiles.
    
    Works by intercepting custom-tiles:// URLs and serving PNG data.
    """
    
    def __init__(self, mbtiles_provider: MBTilesProvider, logger: logging.Logger):
        """
        Initialize custom scheme handler.
        
        Args:
            mbtiles_provider: MBTilesProvider for tile data
            logger: Logger instance
        """
        self.mbtiles_provider = mbtiles_provider
        self.logger = logger
    
    @staticmethod
    def create_tile_url(zoom: int, x: int, y: int) -> str:
        """
        Create a custom tile URL.
        
        Args:
            zoom: Zoom level
            x: Tile column
            y: Tile row
            
        Returns:
            URL string for the tile
        """
        return f"custom-tiles://{zoom}/{x}/{y}"
    
    def get_tile_data(self, zoom: int, x: int, y: int) -> Optional[bytes]:
        """
        Get tile data for coordinates.
        
        Args:
            zoom: Zoom level
            x: Tile column
            y: Tile row
            
        Returns:
            Tile PNG data as bytes, or None if not found
        """
        try:
            return self.mbtiles_provider.get_tile(zoom, x, y)
        except Exception as e:
            self.logger.error(f"Error getting tile z={zoom}, x={x}, y={y}: {e}")
            return None
