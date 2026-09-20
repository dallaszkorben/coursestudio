"""
MBTiles provider for loading and serving map tiles.

This module handles:
- Loading mbtiles files (SQLite-based tile database)
- Querying tile data by zoom level and tile coordinates
- Caching loaded mbtiles metadata
- Fallback mbtiles file support
- Zoom level validation and range checking

MBTiles Format:
- SQLite database containing raster or vector tiles
- Tables: metadata (key-value pairs), tiles (zoom/column/row tile data)
- Raster format: PNG/JPG image tiles (used in this application)
- Vector format: PBF vector tiles (not currently supported)

Usage:
    provider = MBTilesProvider(config, logger)
    provider.load_default_mbtiles()
    if provider.is_loaded():
        tile_data = provider.get_tile(z=13, x=1234, y=5678)
        metadata = provider.get_metadata()
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass


@dataclass
class TileMetadata:
    """
    Metadata extracted from MBTiles file.
    
    Attributes:
        name: Tileset name (e.g., "OpenMapTiles")
        version: Tileset version
        format: Tile format (e.g., "png", "jpg", "pbf")
        bounds: Geographic bounds as (west, south, east, north)
        center: Center point as (longitude, latitude, zoom)
        min_zoom: Minimum zoom level
        max_zoom: Maximum zoom level
        attribution: Data attribution string
        description: Tileset description
        tile_format: Format of tiles (png, jpg, pbf, etc.)
    """
    name: str
    version: str
    format: str
    bounds: Optional[Tuple[float, float, float, float]]
    center: Optional[Tuple[float, float, int]]
    min_zoom: int
    max_zoom: int
    attribution: str
    description: str
    tile_format: str


class MBTilesProvider:
    """
    Provider for loading and querying mbtiles tile databases.
    
    Handles SQLite-based mbtiles files containing raster or vector tiles.
    Supports fallback file selection if primary file not found.
    
    Attributes:
        config: AppConfig instance for reading configuration
        logger: Logger instance for debug/info/error messages
        _db_connection: SQLite database connection (or None if not loaded)
        _metadata: Cached metadata from mbtiles file
        _loaded_path: Path to currently loaded mbtiles file
    """
    
    def __init__(self, config: Any, logger: logging.Logger) -> None:
        """
        Initialize MBTiles provider.
        
        Args:
            config: AppConfig instance with map settings
            logger: Logger instance for logging operations
            
        Raises:
            ValueError: If config or logger is None
        """
        if config is None:
            raise ValueError("config cannot be None")
        if logger is None:
            raise ValueError("logger cannot be None")
        
        self.config = config
        self.logger = logger
        self._db_connection: Optional[sqlite3.Connection] = None
        self._metadata: Optional[TileMetadata] = None
        self._loaded_path: Optional[Path] = None
    
    def _get_mbtiles_path(self, filename: str) -> Optional[Path]:
        """
        Get full path to mbtiles file.
        
        Constructs path as: project_root/mbtiles/{filename}
        
        Args:
            filename: Name of mbtiles file (e.g., "Sweden-Raster-Z10-Z16.mbtiles")
            
        Returns:
            Path object if file exists, None otherwise
        """
        # Get project root from config
        project_root = Path(self.config.get_str("Application.project_root", "./"))
        mbtiles_path = project_root / "mbtiles" / filename
        
        if mbtiles_path.exists() and mbtiles_path.is_file():
            return mbtiles_path
        
        return None
    
    def load_default_mbtiles(self) -> bool:
        """
        Load default mbtiles file from configuration.
        
        Attempts to load the default file specified in config[Map].default_mbtiles.
        If that fails, tries fallback files from config[Map].fallback_mbtiles.
        
        Returns:
            True if a file was successfully loaded, False if all attempts failed
            
        Raises:
            sqlite3.Error: If database connection fails
        """
        # Get default filename from config
        default_file = self.config.get_str("Map.tiles.mbtiles_file", None)
        
        if not default_file:
            self.logger.error("No default_mbtiles configured in settings.ini")
            return False
        
        # Try loading default file
        if self._load_file(default_file):
            self.logger.info(f"Successfully loaded default mbtiles: {default_file}")
            return True
        
        self.logger.warning(f"Failed to load default mbtiles: {default_file}")
        
        # Try fallback files
        fallback_files = self.config.get_list("Map.tiles.fallback_files", [])
        if fallback_files:
            for fallback_file in fallback_files:
                if self._load_file(fallback_file):
                    self.logger.info(f"Successfully loaded fallback mbtiles: {fallback_file}")
                    return True
                self.logger.debug(f"Fallback mbtiles not found: {fallback_file}")
        
        self.logger.error("Could not load any mbtiles files (default or fallback)")
        return False
    
    def _load_file(self, filename: str) -> bool:
        """
        Internal method to load a specific mbtiles file.
        
        Args:
            filename: Name of mbtiles file to load
            
        Returns:
            True if file was loaded successfully, False otherwise
            
        Raises:
            sqlite3.Error: If database connection or query fails
        """
        # Close existing connection if any
        if self._db_connection:
            self._db_connection.close()
            self._db_connection = None
        
        # Get full path to file
        mbtiles_path = self._get_mbtiles_path(filename)
        if not mbtiles_path:
            self.logger.debug(f"MBTiles file not found: {filename}")
            return False
        
        try:
            # Open SQLite connection to mbtiles file
            self._db_connection = sqlite3.connect(str(mbtiles_path))
            self._db_connection.row_factory = sqlite3.Row
            
            # Verify it's a valid mbtiles file (has required tables)
            cursor = self._db_connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            
            if "metadata" not in tables or "tiles" not in tables:
                self.logger.warning(f"Invalid mbtiles file (missing tables): {mbtiles_path}")
                self._db_connection.close()
                self._db_connection = None
                return False
            
            # Load metadata
            self._metadata = self._load_metadata()
            self._loaded_path = mbtiles_path
            
            self.logger.debug(f"Loaded mbtiles file: {mbtiles_path}")
            self.logger.debug(f"Metadata: name={self._metadata.name}, "
                            f"zoom={self._metadata.min_zoom}-{self._metadata.max_zoom}")
            
            return True
        
        except sqlite3.Error as e:
            self.logger.error(f"Database error loading mbtiles file {mbtiles_path}: {e}")
            if self._db_connection:
                self._db_connection.close()
                self._db_connection = None
            return False
    
    def _load_metadata(self) -> TileMetadata:
        """
        Load metadata from mbtiles file.
        
        Extracts key-value metadata from the metadata table and constructs
        TileMetadata object with parsed values.
        
        If metadata minzoom/maxzoom don't match actual tiles, query the tiles
        table to get accurate zoom levels.
        
        Returns:
            TileMetadata object with extracted metadata
            
        Raises:
            sqlite3.Error: If database query fails
        """
        if not self._db_connection:
            raise RuntimeError("Database connection not established")
        
        cursor = self._db_connection.cursor()
        cursor.execute("SELECT name, value FROM metadata")
        
        metadata_dict = {}
        for row in cursor.fetchall():
            metadata_dict[row["name"]] = row["value"]
        
        # Parse bounds (format: "west,south,east,north")
        bounds = None
        if "bounds" in metadata_dict:
            try:
                bounds_str = metadata_dict["bounds"]
                bounds = tuple(float(x) for x in bounds_str.split(","))
                bounds = (bounds[0], bounds[1], bounds[2], bounds[3])
            except (ValueError, IndexError):
                self.logger.warning(f"Invalid bounds format: {metadata_dict.get('bounds')}")
        
        # Parse center (format: "longitude,latitude,zoom")
        center = None
        if "center" in metadata_dict:
            try:
                center_str = metadata_dict["center"]
                parts = center_str.split(",")
                center = (float(parts[0]), float(parts[1]), int(parts[2]))
            except (ValueError, IndexError):
                self.logger.warning(f"Invalid center format: {metadata_dict.get('center')}")
        
        # Parse zoom levels from metadata
        min_zoom = int(metadata_dict.get("minzoom", 0))
        max_zoom = int(metadata_dict.get("maxzoom", 14))
        
        # Verify and correct zoom levels by querying actual tiles
        # (metadata can be inaccurate)
        try:
            cursor.execute("SELECT MIN(zoom_level) as min_z, MAX(zoom_level) as max_z FROM tiles")
            result = cursor.fetchone()
            if result and result[0] is not None and result[1] is not None:
                actual_min_zoom = result[0]
                actual_max_zoom = result[1]
                
                # Use actual zoom levels if they differ from metadata
                if actual_min_zoom != min_zoom or actual_max_zoom != max_zoom:
                    self.logger.debug(
                        f"Metadata zoom ({min_zoom}-{max_zoom}) differs from actual tiles "
                        f"({actual_min_zoom}-{actual_max_zoom}). Using actual tile ranges."
                    )
                    min_zoom = actual_min_zoom
                    max_zoom = actual_max_zoom
        except Exception as e:
            self.logger.warning(f"Could not query actual zoom levels from tiles table: {e}")
        
        return TileMetadata(
            name=metadata_dict.get("name", "Unknown"),
            version=metadata_dict.get("version", "1.0"),
            format=metadata_dict.get("format", "png"),
            bounds=bounds,
            center=center,
            min_zoom=min_zoom,
            max_zoom=max_zoom,
            attribution=metadata_dict.get("attribution", ""),
            description=metadata_dict.get("description", ""),
            tile_format=metadata_dict.get("format", "png")
        )
    
    def is_loaded(self) -> bool:
        """
        Check if an mbtiles file is currently loaded.
        
        Returns:
            True if a file is loaded and connection is valid, False otherwise
        """
        return self._db_connection is not None and self._metadata is not None
    
    def get_metadata(self) -> Optional[TileMetadata]:
        """
        Get metadata from currently loaded mbtiles file.
        
        Returns:
            TileMetadata object if file is loaded, None otherwise
        """
        return self._metadata if self.is_loaded() else None
    
    def get_loaded_path(self) -> Optional[Path]:
        """
        Get path to currently loaded mbtiles file.
        
        Returns:
            Path object if file is loaded, None otherwise
        """
        return self._loaded_path if self.is_loaded() else None
    
    def validate_zoom_level(self, zoom: int) -> bool:
        """
        Validate if zoom level is supported by loaded mbtiles file.
        
        Args:
            zoom: Zoom level to validate (0-18)
            
        Returns:
            True if zoom level is within supported range, False otherwise
        """
        if not self.is_loaded() or not self._metadata:
            return False
        
        return self._metadata.min_zoom <= zoom <= self._metadata.max_zoom
    
    def get_supported_zoom_range(self) -> Optional[Tuple[int, int]]:
        """
        Get supported zoom level range from loaded mbtiles file.
        
        Returns:
            Tuple of (min_zoom, max_zoom) if file loaded, None otherwise
        """
        if not self.is_loaded() or not self._metadata:
            return None
        
        return (self._metadata.min_zoom, self._metadata.max_zoom)
    
    def get_available_zooms(self) -> List[int]:
        """
        Get list of all available zoom levels in loaded mbtiles file.
        
        Returns:
            List of available zoom levels, empty list if no file loaded
        """
        if not self.is_loaded() or not self._metadata:
            return []
        
        min_zoom = self._metadata.min_zoom
        max_zoom = self._metadata.max_zoom
        return list(range(min_zoom, max_zoom + 1))
    
    def latlon_to_tile(self, lat: float, lon: float, zoom: int) -> Tuple[int, int]:
        """
        Convert geographic coordinates to Web Mercator tile coordinates.
        
        Public wrapper for the static _lat_lon_to_tile method.
        
        Args:
            lat: Latitude (-85 to 85 degrees)
            lon: Longitude (-180 to 180 degrees)
            zoom: Zoom level (0-18)
            
        Returns:
            Tuple of (tile_x, tile_y)
        """
        return self._lat_lon_to_tile(lon, lat, zoom)
    
    def get_tile(self, zoom: int, x: int, y: int) -> Optional[bytes]:
        """
        Get tile image data for given tile coordinates.
        
        Uses Web Mercator (XYZ) tile coordinates where:
        - zoom: Zoom level (0-18)
        - x: Column index (0 to 2^zoom - 1)
        - y: Row index (0 to 2^zoom - 1)
        
        Args:
            zoom: Zoom level
            x: Tile column index
            y: Tile row index
            
        Returns:
            Tile image data (bytes) if found, None if not found or error
            
        Raises:
            ValueError: If zoom level not supported
            sqlite3.Error: If database query fails
        """
        if not self.is_loaded():
            self.logger.warning("Cannot get tile: no mbtiles file loaded")
            return None
        
        if not self.validate_zoom_level(zoom):
            raise ValueError(f"Zoom level {zoom} not supported "
                           f"(range: {self._metadata.min_zoom}-{self._metadata.max_zoom})")
        
        # Validate tile coordinates
        max_tile = 2 ** zoom
        if not (0 <= x < max_tile and 0 <= y < max_tile):
            self.logger.debug(f"Invalid tile coordinates: z={zoom}, x={x}, y={y}")
            return None
        
        try:
            cursor = self._db_connection.cursor()
            
            # MBTiles uses TMS (Tile Map Service) coordinates for Y axis
            # TMS Y is inverted compared to Web Mercator: max_y - web_mercator_y
            max_tile_y = (2 ** zoom) - 1
            tms_y = max_tile_y - y
            
            # Query tile data from database
            cursor.execute(
                "SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?",
                (zoom, x, tms_y)
            )
            
            row = cursor.fetchone()
            if row:
                return row[0]
            
            return None
        
        except sqlite3.Error as e:
            self.logger.error(f"Database error getting tile z={zoom}, x={x}, y={y}: {e}")
            return None
    
    def get_tile_image(self, zoom: int, x: int, y: int):
        """
        Get tile image as PIL Image object.
        
        Args:
            zoom: Zoom level
            x: Tile column index
            y: Tile row index
            
        Returns:
            PIL.Image if found, None if not found or error
        """
        import io
        from PIL import Image
        
        tile_data = self.get_tile(zoom, x, y)
        
        if tile_data is None:
            return None
        
        try:
            tile_image = Image.open(io.BytesIO(tile_data))
            
            # Convert palette mode to RGB if needed
            if tile_image.mode == 'P':
                tile_image = tile_image.convert('RGB')
            elif tile_image.mode == 'RGBA':
                # Create white background and composite
                background = Image.new('RGB', tile_image.size, 'white')
                background.paste(tile_image, mask=tile_image.split()[3])
                tile_image = background
            
            return tile_image
        except Exception as e:
            self.logger.error(f"Error decoding tile z={zoom}, x={x}, y={y}: {e}")
            return None
    
    def tile_exists(self, zoom: int, x: int, y: int) -> bool:
        """
        Check if a tile exists in the database.
        
        Args:
            zoom: Zoom level
            x: Tile column index
            y: Tile row index
            
        Returns:
            True if tile exists, False otherwise
        """
        try:
            return self.get_tile(zoom, x, y) is not None
        except ValueError:
            return False
    
    def get_tiles_for_bounds(self, zoom: int, west: float, south: float,
                            east: float, north: float) -> List[Tuple[int, int, bytes]]:
        """
        Get all tiles within geographic bounds at given zoom level.
        
        Converts geographic bounds to tile coordinates and retrieves all
        tiles within that range.
        
        Args:
            zoom: Zoom level
            west: Western longitude boundary
            south: Southern latitude boundary
            east: Eastern longitude boundary
            north: Northern latitude boundary
            
        Returns:
            List of tuples: (tile_x, tile_y, tile_data)
            Empty list if no tiles found or invalid bounds
        """
        if not self.is_loaded():
            return []
        
        if not self.validate_zoom_level(zoom):
            self.logger.warning(f"Zoom level {zoom} not supported")
            return []
        
        # Convert geographic bounds to tile coordinates
        tile_x_min, tile_y_max = self._lat_lon_to_tile(west, south, zoom)
        tile_x_max, tile_y_min = self._lat_lon_to_tile(east, north, zoom)
        
        # Ensure valid ranges
        tile_x_min = max(0, tile_x_min)
        tile_x_max = min(2 ** zoom - 1, tile_x_max)
        tile_y_min = max(0, tile_y_min)
        tile_y_max = min(2 ** zoom - 1, tile_y_max)
        
        tiles = []
        
        try:
            cursor = self._db_connection.cursor()
            
            # Query all tiles in range
            cursor.execute(
                """SELECT tile_column, tile_row, tile_data 
                   FROM tiles 
                   WHERE zoom_level = ? 
                   AND tile_column >= ? AND tile_column <= ? 
                   AND tile_row >= ? AND tile_row <= ?""",
                (zoom, tile_x_min, tile_x_max, tile_y_min, tile_y_max)
            )
            
            for row in cursor.fetchall():
                tiles.append((row[0], row[1], row[2]))
            
            self.logger.debug(f"Found {len(tiles)} tiles for bounds at zoom {zoom}")
            return tiles
        
        except sqlite3.Error as e:
            self.logger.error(f"Database error getting tiles for bounds: {e}")
            return []
    
    @staticmethod
    def _lat_lon_to_tile(lon: float, lat: float, zoom: int) -> Tuple[int, int]:
        """
        Convert geographic coordinates to Web Mercator tile coordinates.
        
        Args:
            lon: Longitude (-180 to 180)
            lat: Latitude (-85 to 85)
            zoom: Zoom level (0-18)
            
        Returns:
            Tuple of (tile_x, tile_y)
        """
        import math
        
        # Normalize longitude
        lon = lon % 360
        if lon > 180:
            lon -= 360
        
        # Clamp latitude to valid Mercator range
        lat = max(-85.0511287798066, min(85.0511287798066, lat))
        
        # Convert to tile coordinates
        n = 2.0 ** zoom
        x = (lon + 180.0) / 360.0 * n
        
        lat_rad = math.radians(lat)
        y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n
        
        return (int(x), int(y))
    
    def close(self) -> None:
        """
        Close the database connection and clean up resources.
        
        Safe to call even if no file is loaded.
        """
        if self._db_connection:
            try:
                self._db_connection.close()
            except sqlite3.Error as e:
                self.logger.error(f"Error closing database connection: {e}")
            finally:
                self._db_connection = None
                self._metadata = None
                self._loaded_path = None
    
    def __del__(self) -> None:
        """
        Destructor: ensure database connection is closed.
        """
        self.close()
