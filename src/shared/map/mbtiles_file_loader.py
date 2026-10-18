"""
MBTiles File Loader - Intelligent state management when loading new mbtiles files.

Handles:
- Reading mbtiles metadata (center, zoom bounds)
- Resetting previous map state
- Determining optimal initial position using priority logic
- Updating settings.yaml
- Returning configuration for UI

Author: Development Team
Date: 2026-10-18
"""

import logging
import math
from typing import Dict, Tuple, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class MBTilesFileLoader:
    """
    Intelligent mbtiles file loader with state management.
    
    Responsibility: When user opens new mbtiles file, determine:
    1. What to clear from previous state
    2. What to read from new mbtiles metadata
    3. Best initial center/zoom based on availability
    4. What to write to settings.yaml
    """
    
    def __init__(self, mbtiles_reader, config):
        """
        Initialize loader.
        
        Args:
            mbtiles_reader: MBTilesReader instance for the newly loaded file
            config: AppConfig instance for accessing/updating settings.yaml
        """
        self.reader = mbtiles_reader
        self.config = config
        self.metadata = mbtiles_reader.metadata
        
        # Track which zoom levels are available
        self.available_zooms = set(zl.zoom for zl in mbtiles_reader.zoom_levels)
        self.min_zoom = min(self.available_zooms) if self.available_zooms else 0
        self.max_zoom = max(self.available_zooms) if self.available_zooms else 28
        
        logger.info(f"MBTilesFileLoader initialized")
        logger.info(f"Available zoom levels: {sorted(self.available_zooms)}")
        logger.info(f"Metadata center: {self.metadata.center}")
    
    
    def load_and_configure(self, mbtiles_file_path: str) -> Dict[str, Any]:
        """
        Load new mbtiles file and determine optimal configuration.
        
        Process:
        1. Clear previous state from settings.yaml
        2. Read metadata from new mbtiles
        3. Determine best center/zoom using priority logic
        4. Update settings.yaml with new values
        5. Return configuration for UI
        
        Args:
            mbtiles_file_path: Path to newly loaded mbtiles file
            
        Returns:
            Dict with keys:
            - recent_mbtiles: File path
            - recent_zoom: Determined zoom level
            - recent_center: Dict with lat/lon
            - default_zoom: Set to same as recent_zoom
            - default_center: Set to same as recent_center
            - available_zooms: List of available zoom levels
            - metadata: MBTilesMetadata object
        """
        logger.info(f"Loading mbtiles file: {mbtiles_file_path}")
        
        # Step 1: Clear previous state
        self._clear_previous_state()
        
        # Step 2: Determine optimal center and zoom
        center_lat, center_lon, zoom = self._determine_initial_position()
        
        logger.info(f"Determined initial position: Z{zoom} @ ({center_lat:.4f}, {center_lon:.4f})")
        
        # Step 3: Update settings.yaml
        config_update = {
            'recent_mbtiles': mbtiles_file_path,
            'recent_zoom': zoom,
            'recent_center': {
                'lat': center_lat,
                'lon': center_lon
            },
            'default_zoom': zoom,
            'default_center': {
                'lat': center_lat,
                'lon': center_lon
            }
        }
        
        self._update_settings(config_update)
        
        # Step 4: Return configuration for UI
        return {
            'recent_mbtiles': mbtiles_file_path,
            'recent_zoom': zoom,
            'recent_center': {'lat': center_lat, 'lon': center_lon},
            'default_zoom': zoom,
            'default_center': {'lat': center_lat, 'lon': center_lon},
            'available_zooms': sorted(self.available_zooms),
            'metadata': self.metadata,
            'min_zoom': self.min_zoom,
            'max_zoom': self.max_zoom
        }
    
    
    def _clear_previous_state(self) -> None:
        """
        Clear all previous map state from settings.yaml.
        
        Removes:
        - recent_mbtiles
        - recent_zoom
        - recent_center
        - default_zoom
        - default_center
        """
        logger.info("Clearing previous map state")
        
        # Set all to None/empty (will use defaults below)
        self.config.set_silent('appearance.tiles.recent_mbtiles', None)
        self.config.set_silent('appearance.tiles.recent_zoom', None)
        self.config.set_silent('appearance.tiles.recent_center.lat', None)
        self.config.set_silent('appearance.tiles.recent_center.lon', None)
        self.config.set_silent('appearance.tiles.default_zoom', None)
        self.config.set_silent('appearance.tiles.default_center.lat', None)
        self.config.set_silent('appearance.tiles.default_center.lon', None)
    
    
    def _determine_initial_position(self) -> Tuple[float, float, int]:
        """
        Determine optimal initial center and zoom using priority logic.
        
        Priority:
        1. Both center AND zoom in mbtiles metadata → use them
        2. Center exists, zoom doesn't → use center + lowest available zoom
        3. Zoom exists, center doesn't → try old center, or find any available position
        4. Neither exists → use lowest zoom + any available tile position
        
        Returns:
            Tuple of (latitude, longitude, zoom_level)
        """
        logger.info("Determining initial position using priority logic")
        
        # Extract from metadata
        mbtiles_center = self.metadata.center  # (lon, lat, zoom) or None
        mbtiles_bounds = self.metadata.bounds  # (west, south, east, north) or None
        
        # Case 1: Both center AND zoom exist in mbtiles
        if mbtiles_center and len(mbtiles_center) >= 3:
            lon, lat, zoom = mbtiles_center[0], mbtiles_center[1], mbtiles_center[2]
            
            # Verify zoom is available
            if zoom in self.available_zooms:
                logger.info(f"Case 1: Using center ({lat}, {lon}) and zoom {zoom} from mbtiles")
                return lat, lon, zoom
            else:
                logger.info(f"Case 1: Center from mbtiles, but zoom {zoom} not available")
                # Fall through to next case
        
        # Case 2: Center exists but zoom doesn't (or zoom from metadata unavailable)
        if mbtiles_center and len(mbtiles_center) >= 2:
            lon, lat = mbtiles_center[0], mbtiles_center[1]
            zoom = self.min_zoom  # Use lowest available zoom
            logger.info(f"Case 2: Using center ({lat}, {lon}) with lowest zoom {zoom}")
            return lat, lon, zoom
        
        # Case 3: Try to use bounds (which implies center)
        if mbtiles_bounds and len(mbtiles_bounds) == 4:
            west, south, east, north = mbtiles_bounds
            center_lon = (west + east) / 2
            center_lat = (south + north) / 2
            
            # Check if we have zoom from metadata
            if mbtiles_center and len(mbtiles_center) >= 3:
                zoom = mbtiles_center[2]
                if zoom in self.available_zooms:
                    logger.info(f"Case 3a: Using center from bounds ({center_lat}, {center_lon}) with zoom {zoom}")
                    return center_lat, center_lon, zoom
            
            # Otherwise use lowest zoom
            zoom = self.min_zoom
            logger.info(f"Case 3b: Using center from bounds ({center_lat}, {center_lon}) with lowest zoom {zoom}")
            return center_lat, center_lon, zoom
        
        # Case 4: Neither center nor bounds exist
        # Find any available tile at lowest zoom level
        logger.info(f"Case 4: No center/bounds in metadata, finding any tile at zoom {self.min_zoom}")
        
        tile_position = self._find_any_tile_at_zoom(self.min_zoom)
        if tile_position:
            lat, lon = tile_position
            logger.info(f"Case 4: Found tile at ({lat}, {lon}) zoom {self.min_zoom}")
            return lat, lon, self.min_zoom
        
        # Fallback: Use center of world at lowest zoom
        logger.warning("Case 4: No tiles found, using world center")
        return 0.0, 0.0, self.min_zoom
    
    
    def _find_any_tile_at_zoom(self, zoom: int) -> Optional[Tuple[float, float]]:
        """
        Find any available tile at given zoom level and return its center position.
        
        Strategy: Query database for first tile at this zoom, convert to center coordinates.
        
        Args:
            zoom: Zoom level to search
            
        Returns:
            Tuple of (latitude, longitude) or None if no tiles found
        """
        logger.debug(f"Searching for any tile at zoom {zoom}")
        
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.reader.file_path)
            cursor = conn.cursor()
            
            # Get first tile at this zoom level
            cursor.execute(
                "SELECT tile_column, tile_row FROM tiles WHERE zoom_level = ? LIMIT 1",
                (zoom,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                logger.debug(f"No tiles found at zoom {zoom}")
                return None
            
            x, y = result  # tile_column, tile_row (TMS coordinates)
            
            # Convert tile center to lat/lon
            lat, lon = self._tile_center_to_latlon(x, y, zoom)
            logger.info(f"Found tile at zoom {zoom}: x={x}, y={y} (TMS) → ({lat:.4f}, {lon:.4f})")
            return lat, lon
            
        except Exception as e:
            logger.error(f"Error finding tile at zoom {zoom}: {e}")
            return None
    
    
    def _tile_center_to_latlon(self, x: int, y: int, zoom: int) -> Tuple[float, float]:
        """
        Convert TMS tile coordinates to lat/lon of tile center.
        
        MBTiles stores tiles in TMS (Tile Map Service) coordinate system:
        - Y=0 at BOTTOM (south)
        - Y increases UPWARD (north)
        
        Args:
            x: Tile column (TMS)
            y: Tile row (TMS)
            zoom: Zoom level
            
        Returns:
            Tuple of (latitude, longitude) of tile center
        """
        # TMS y to Web Mercator y conversion
        n = 2 ** zoom
        web_merc_y = (n - 1) - y
        
        # Convert tile coordinates to lat/lon
        # Using Web Mercator projection formulas
        
        # Longitude: simple linear mapping
        lon = (x + 0.5) / n * 360.0 - 180.0
        
        # Latitude: inverse Mercator projection
        lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * (web_merc_y + 0.5) / n)))
        lat = math.degrees(lat_rad)
        
        return lat, lon
    
    
    def _update_settings(self, config_update: Dict[str, Any]) -> None:
        """
        Update settings.yaml with new mbtiles configuration.
        
        Args:
            config_update: Dict with keys:
                - recent_mbtiles
                - recent_zoom
                - recent_center (dict with lat/lon)
                - default_zoom
                - default_center (dict with lat/lon)
        """
        logger.info("Updating settings.yaml with new mbtiles configuration")
        
        # Update all values silently (no signals yet)
        if 'recent_mbtiles' in config_update:
            self.config.set_silent(
                'appearance.tiles.recent_mbtiles',
                config_update['recent_mbtiles']
            )
        
        if 'recent_zoom' in config_update:
            self.config.set_silent(
                'appearance.tiles.recent_zoom',
                config_update['recent_zoom']
            )
        
        if 'recent_center' in config_update:
            center = config_update['recent_center']
            self.config.set_silent('appearance.tiles.recent_center.lat', center['lat'])
            self.config.set_silent('appearance.tiles.recent_center.lon', center['lon'])
        
        if 'default_zoom' in config_update:
            self.config.set_silent(
                'appearance.tiles.default_zoom',
                config_update['default_zoom']
            )
        
        if 'default_center' in config_update:
            center = config_update['default_center']
            self.config.set_silent('appearance.tiles.default_center.lat', center['lat'])
            self.config.set_silent('appearance.tiles.default_center.lon', center['lon'])
        
        # Emit single signal with complete state
        self.config.emit_map_position_changed()
        
        # Save to file
        self.config.save_to_file()
        
        logger.info("Settings.yaml updated and saved")
