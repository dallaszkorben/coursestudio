"""
Tile Processing - Image resampling and database operations.

This module handles the actual generation of tiles through downsampling and upsampling
operations using PIL/Pillow for image processing.

Key Operations:
    - Downsampling: Combine 4 source tiles into 1 target tile
    - Upsampling: Extract quadrant from source tile and resample
    - Format Conversion: Handle PNG, JPEG, WebP tile formats
    - Database Writing: Safe, atomic tile writes with transaction support
    - Temporary Database: Safe generation without orphaned incomplete tiles

Safety Feature:
    - Tiles generated to temporary database during process
    - Only committed to real database when fully complete
    - Cancellation or crash leaves no traces in real database

Usage:
    >>> processor = TileProcessor(reader, filepath)
    >>> temp_db = processor.generate_tiles_to_temp(source_zoom, target_zoom, progress_callback)
    >>> processor.commit_generated_tiles(temp_db, target_zoom)
"""

import io
import logging
import sqlite3
import time
from pathlib import Path
from typing import List, Tuple, Callable, Optional, Generator
from dataclasses import dataclass

from PIL import Image

logger = logging.getLogger(__name__)


class TileProcessorError(Exception):
    """Base exception for tile processing errors."""
    pass


@dataclass
class TileData:
    """Represents a single tile."""
    zoom: int
    column: int
    row: int
    data: bytes
    format: str = 'png'


class TileCache:
    """Simple LRU cache for tiles during generation."""
    
    def __init__(self, max_size: int = 256):
        """
        Initialize tile cache.
        
        Args:
            max_size: Maximum number of tiles to cache in memory
        """
        self.cache = {}  # {(zoom, x, y): tile_data}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, zoom: int, column: int, row: int, 
            fetch_func: Callable) -> bytes:
        """
        Get tile from cache or fetch if missing.
        
        Args:
            zoom: Zoom level
            column: Tile column (x)
            row: Tile row (y)
            fetch_func: Function to call if tile not in cache
            
        Returns:
            Tile data (bytes)
        """
        key = (zoom, column, row)
        
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        
        self.misses += 1
        
        # Fetch from database
        tile_data = fetch_func(zoom, column, row)
        
        # Add to cache (evict oldest if full)
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.debug(f"Cache evicted: {oldest_key}")
        
        self.cache[key] = tile_data
        return tile_data
    
    def clear(self):
        """Clear all cached tiles."""
        self.cache.clear()
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'size': len(self.cache),
            'max_size': self.max_size
        }


class TileProcessor:
    """
    Tile resampling and database operations.
    
    Handles:
    - Reading tiles from MBTiles database
    - Resampling tiles using PIL/Pillow
    - Writing generated tiles to temporary database first
    - Atomically committing tiles to real database when complete
    - Format conversions (PNG, JPEG, WebP)
    
    Safety Features:
    - Tiles written to temporary database during generation
    - Real database only modified when all tiles verified
    - Cancellation leaves no traces in real database
    - App crashes can't leave orphaned incomplete zooms
    
    Attributes:
        reader: MBTilesReader instance
        filepath: Path to MBTiles file
        format: Tile format (png, jpg, webp)
        cache: Tile cache for frequently accessed tiles
        temp_dir: Directory for temporary databases
    """
    
    def __init__(self, reader, filepath: str, cache_size: int = 256, temp_dir: Optional[str] = None):
        """
        Initialize TileProcessor.
        
        Args:
            reader: MBTilesReader instance
            filepath: Path to MBTiles file
            cache_size: Tile cache size (default 256)
            temp_dir: Directory for temporary databases (default: .maploom_temp in file dir)
        """
        self.reader = reader
        self.filepath = filepath
        self.metadata = reader.get_metadata()
        self.format = self._parse_format(self.metadata.format)
        self.cache = TileCache(cache_size)
        
        # Setup temporary directory for safe generation
        if temp_dir:
            self.temp_dir = Path(temp_dir)
        else:
            self.temp_dir = Path(filepath).parent / ".maploom_temp"
        
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.temp_db_path = None
        
        logger.debug(f"TileProcessor initialized: format={self.format}, cache_size={cache_size}, temp_dir={self.temp_dir}")
    
    def _parse_format(self, format_str: str) -> str:
        """
        Parse format string to standard format name.
        
        Args:
            format_str: Format from metadata (e.g., 'png', 'jpg', 'webp')
            
        Returns:
            Normalized format name (png, jpeg, webp)
        """
        format_str = format_str.lower().strip()
        
        # Normalize common variations
        if format_str in ['jpg', 'jpeg']:
            return 'jpeg'
        elif format_str in ['webp', 'web']:
            return 'webp'
        elif format_str == 'png':
            return 'png'
        else:
            logger.warning(f"Unknown format '{format_str}', defaulting to png")
            return 'png'
    
    def _get_tile(self, zoom: int, column: int, row: int) -> Optional[bytes]:
        """
        Get tile data from database.
        
        Args:
            zoom: Zoom level
            column: Tile column (x)
            row: Tile row (y)
            
        Returns:
            Tile data (bytes) or None if not found
        """
        try:
            return self.reader.get_tile(zoom, column, row)
        except Exception as e:
            logger.debug(f"Failed to fetch tile Z{zoom}/{column}/{row}: {e}")
            return None
    
    def _create_placeholder(self) -> bytes:
        """
        Create a gray placeholder tile.
        
        Used when source tiles are missing to avoid transparency or errors.
        
        Returns:
            PNG tile data (bytes)
        """
        # Create gray tile (RGB 200, 200, 200)
        image = Image.new('RGB', (256, 256), (200, 200, 200))
        
        # Save to bytes
        output = io.BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()
    
    def _bytes_to_image(self, tile_data: bytes) -> Image.Image:
        """
        Convert tile bytes to PIL Image.
        
        Handles format conversion and corruption gracefully.
        
        Args:
            tile_data: Raw tile data (bytes)
            
        Returns:
            PIL Image in RGB mode
            
        Raises:
            TileProcessorError: If tile cannot be decoded
        """
        try:
            image = Image.open(io.BytesIO(tile_data))
            
            # Convert to RGB if needed (handles RGBA, grayscale, palette, etc.)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            return image
            
        except Exception as e:
            logger.warning(f"Failed to decode tile: {e}")
            raise TileProcessorError(f"Cannot decode tile: {e}")
    
    def _image_to_bytes(self, image: Image.Image, format_name: str) -> bytes:
        """
        Convert PIL Image to tile bytes.
        
        Args:
            image: PIL Image to save
            format_name: Format (png, jpeg, webp)
            
        Returns:
            Tile data (bytes)
        """
        output = io.BytesIO()
        
        # Format-specific options
        save_kwargs = {'format': format_name.upper()}
        
        if format_name == 'jpeg':
            save_kwargs['quality'] = 90
        
        try:
            image.save(output, **save_kwargs)
            return output.getvalue()
        except Exception as e:
            raise TileProcessorError(f"Failed to save tile as {format_name}: {e}")
    
    def downsample_tile(self, source_zoom: int, target_zoom: int,
                       target_column: int, target_row: int) -> bytes:
        """
        Downsample 4 source tiles into 1 target tile.
        
        Strategy:
            1. Fetch 4 source tiles (at source_zoom, one level higher)
            2. Create 512×512 canvas and place tiles
            3. Resample to 256×256 using LANCZOS
            4. Save as target format
        
        Args:
            source_zoom: Source zoom level (target_zoom + 1)
            target_zoom: Target zoom level
            target_column: Target tile column (x)
            target_row: Target tile row (y)
            
        Returns:
            Generated tile data (bytes)
            
        Raises:
            TileProcessorError: If resampling fails
        """
        try:
            # ✅ CRITICAL FIX: Account for TMS conversion in the viewer
            # The viewer applies TMS conversion: tms_y = (2^zoom - 1) - y
            # This means when the viewer displays a tile at position (x, y),
            # it's actually retrieving tile at database coordinates (x, inverted_y)
            #
            # When we GENERATE Z9 tiles by downsampling Z10:
            # - Z10 tiles are stored in database as (col, row) with row going 688-768
            # - The viewer will apply TMS conversion when displaying
            # - So we need to compose tiles in a way that compensates for this
            #
            # Normal downsampling would do:
            #   (col*2, row*2), (col*2+1, row*2) at TOP
            #   (col*2, row*2+1), (col*2+1, row*2+1) at BOTTOM
            #
            # But since the viewer will invert Y when displaying, we need to
            # SWAP the top and bottom quadrants to compensate:
            
            # Fetch source tiles (standard math, as stored in database)
            source_tiles_db = [
                (target_column * 2,     target_row * 2),      
                (target_column * 2 + 1, target_row * 2),      
                (target_column * 2,     target_row * 2 + 1),  
                (target_column * 2 + 1, target_row * 2 + 1)   
            ]
            
            # But position them with TOP and BOTTOM swapped to compensate for viewer's TMS conversion
            canvas_positions = [
                (0, 256),      # DB top-left → canvas BOTTOM-left (gets inverted by viewer)
                (256, 256),    # DB top-right → canvas BOTTOM-right
                (0, 0),        # DB bottom-left → canvas TOP-left
                (256, 0)       # DB bottom-right → canvas TOP-right
            ]
            
            # Create 512×512 canvas
            canvas = Image.new('RGB', (512, 512), (200, 200, 200))
            
            for i, (src_col, src_row) in enumerate(source_tiles_db):
                # Try to fetch tile from cache
                try:
                    tile_data = self.cache.get(
                        source_zoom, src_col, src_row,
                        lambda z, c, r: self.reader.get_tile(z, c, r)
                    )
                    
                    if tile_data:
                        source_image = self._bytes_to_image(tile_data)
                    else:
                        # Use placeholder if tile doesn't exist
                        source_image = Image.new('RGB', (256, 256), (200, 200, 200))
                
                except TileProcessorError:
                    # Use placeholder if tile is corrupted
                    source_image = Image.new('RGB', (256, 256), (200, 200, 200))
                
                # Paste into canvas at the SWAPPED position
                canvas.paste(source_image, canvas_positions[i])
            
            # Resample 512×512 to 256×256 using LANCZOS (best quality)
            output = canvas.resize((256, 256), Image.LANCZOS)
            
            # Save as target format
            return self._image_to_bytes(output, self.format)
            
        except Exception as e:
            raise TileProcessorError(f"Downsampling failed: {e}")
    
    def upsample_tile(self, source_zoom: int, target_zoom: int,
                     target_column: int, target_row: int) -> bytes:
        """
        Upsample single source tile into target tile.
        
        Strategy:
            1. Calculate source tile coordinate (parent)
            2. Determine which quadrant this target tile is
            3. Fetch source tile and extract quadrant
            4. Resample to 256×256
        
        Args:
            source_zoom: Source zoom level (target_zoom - 1)
            target_zoom: Target zoom level
            target_column: Target tile column (x)
            target_row: Target tile row (y)
            
        Returns:
            Generated tile data (bytes)
            
        Raises:
            TileProcessorError: If resampling fails
        """
        try:
            # Calculate source tile (parent)
            source_column = target_column // 2
            source_row = target_row // 2
            
            # Determine which quadrant this target tile occupies
            quadrant_x = target_column % 2
            quadrant_y = target_row % 2
            quadrant = (quadrant_x * 2) + quadrant_y
            
            # Quadrant positions in 256×256 tile:
            #  0 1
            #  2 3
            quadrant_positions = {
                0: (0, 0, 128, 128),      # top-left
                1: (128, 0, 256, 128),    # top-right
                2: (0, 128, 128, 256),    # bottom-left
                3: (128, 128, 256, 256)   # bottom-right
            }
            
            # Fetch source tile
            try:
                source_data = self.cache.get(
                    source_zoom, source_column, source_row,
                    lambda z, c, r: self.reader.get_tile(z, c, r)
                )
                
                if not source_data:
                    # Use placeholder if source doesn't exist
                    return self._create_placeholder()
                
                source_image = self._bytes_to_image(source_data)
                
            except TileProcessorError:
                # Use placeholder if source is corrupted
                return self._create_placeholder()
            
            # Extract quadrant from source
            x1, y1, x2, y2 = quadrant_positions[quadrant]
            quadrant_image = source_image.crop((x1, y1, x2, y2))
            
            # Resample to 256×256 using LANCZOS
            output = quadrant_image.resize((256, 256), Image.LANCZOS)
            
            # Save as target format
            return self._image_to_bytes(output, self.format)
            
        except Exception as e:
            raise TileProcessorError(f"Upsampling failed: {e}")
    
    def generate_tile(self, source_zoom: int, target_zoom: int,
                     target_column: int, target_row: int) -> bytes:
        """
        Generate a single tile using appropriate strategy.
        
        Args:
            source_zoom: Source zoom level
            target_zoom: Target zoom level
            target_column: Target tile column
            target_row: Target tile row
            
        Returns:
            Generated tile data (bytes)
        """
        if source_zoom > target_zoom:
            # Downsampling
            return self.downsample_tile(source_zoom, target_zoom,
                                       target_column, target_row)
        else:
            # Upsampling
            return self.upsample_tile(source_zoom, target_zoom,
                                     target_column, target_row)
    
    def write_tile(self, zoom: int, column: int, row: int, tile_data: bytes):
        """
        Write a single tile to the database.
        
        Args:
            zoom: Zoom level
            column: Tile column (x)
            row: Tile row (y)
            tile_data: Tile data (bytes)
            
        Raises:
            TileProcessorError: If write fails
        """
        try:
            conn = sqlite3.connect(self.filepath)
            cursor = conn.cursor()
            
            insert_sql = """
                INSERT OR IGNORE INTO tiles 
                (zoom_level, tile_column, tile_row, tile_data)
                VALUES (?, ?, ?, ?)
            """
            
            cursor.execute(insert_sql, (zoom, column, row, tile_data))
            conn.commit()
            conn.close()
            
        except sqlite3.Error as e:
            raise TileProcessorError(f"Database write failed: {e}")
    
    def write_tiles_batch(self, zoom: int, tiles: List[Tuple[int, int, bytes]],
                         batch_size: int = 100,
                         progress_callback: Optional[Callable] = None) -> Generator:
        """
        Write tiles to database in batches with progress reporting.
        
        Batching improves performance significantly compared to writing one at a time.
        
        Args:
            zoom: Zoom level for all tiles
            tiles: List of (column, row, tile_data) tuples
            batch_size: Tiles per transaction (default 100)
            progress_callback: Optional callback(completed, total) for progress reporting
            
        Yields:
            (completed, total) tuples for progress tracking
            
        Raises:
            TileProcessorError: If any write fails
        """
        try:
            conn = sqlite3.connect(self.filepath)
            cursor = conn.cursor()
            
            insert_sql = """
                INSERT OR IGNORE INTO tiles 
                (zoom_level, tile_column, tile_row, tile_data)
                VALUES (?, ?, ?, ?)
            """
            
            total_tiles = len(tiles)
            
            for i in range(0, total_tiles, batch_size):
                # Start transaction
                cursor.execute("BEGIN TRANSACTION")
                
                # Insert batch
                batch = tiles[i:i+batch_size]
                for column, row, tile_data in batch:
                    cursor.execute(insert_sql, (zoom, column, row, tile_data))
                
                # Commit transaction
                cursor.execute("COMMIT")
                
                # Report progress
                completed = min(i + batch_size, total_tiles)
                yield (completed, total_tiles)
                
                if progress_callback:
                    progress_callback(completed, total_tiles)
                
                logger.debug(f"Wrote batch: {i}-{completed}/{total_tiles}")
            
            conn.close()
            
        except sqlite3.Error as e:
            raise TileProcessorError(f"Batch write failed: {e}")
    
    def mark_zoom_generated(self, zoom: int):
        """
        Mark a zoom level as generated in metadata.
        
        This allows tracking which zooms are original vs generated.
        
        Args:
            zoom: Zoom level
        """
        try:
            conn = sqlite3.connect(self.filepath)
            cursor = conn.cursor()
            
            # Insert metadata entry
            cursor.execute(
                "INSERT OR REPLACE INTO metadata (name, value) VALUES (?, ?)",
                (f"generated_zoom_{zoom}", "true")
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Marked Z{zoom} as generated")
            
        except sqlite3.Error as e:
            logger.warning(f"Failed to mark zoom as generated: {e}")
    
    
    def create_temp_database(self, target_zoom: int) -> Path:
        """
        Create temporary database for safe tile generation.
        
        Temporary database is used during generation. Once complete and verified,
        all tiles are atomically committed to the real database.
        
        Args:
            target_zoom: The zoom level being generated
            
        Returns:
            Path to temporary database
            
        Raises:
            TileProcessorError: If database creation fails
        """
        try:
            # Create unique temp database filename
            timestamp = int(time.time() * 1000)  # Milliseconds for uniqueness
            self.temp_db_path = self.temp_dir / f"gen_z{target_zoom}_{timestamp}.db"
            
            # Create database with tiles table
            conn = sqlite3.connect(str(self.temp_db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tiles (
                    zoom_level INTEGER,
                    tile_column INTEGER,
                    tile_row INTEGER,
                    tile_data BLOB,
                    PRIMARY KEY (zoom_level, tile_column, tile_row)
                )
            """)
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Created temporary database: {self.temp_db_path}")
            return self.temp_db_path
            
        except sqlite3.Error as e:
            raise TileProcessorError(f"Failed to create temporary database: {e}")
    
    
    def write_tile_to_temp(self, zoom: int, column: int, row: int, tile_data: bytes):
        """
        Write a single tile to temporary database.
        
        Args:
            zoom: Zoom level
            column: Tile column (x)
            row: Tile row (y)
            tile_data: Tile data (bytes)
            
        Raises:
            TileProcessorError: If write fails
        """
        if not self.temp_db_path:
            raise TileProcessorError("Temporary database not initialized")
        
        try:
            conn = sqlite3.connect(str(self.temp_db_path))
            cursor = conn.cursor()
            
            insert_sql = """
                INSERT OR REPLACE INTO tiles 
                (zoom_level, tile_column, tile_row, tile_data)
                VALUES (?, ?, ?, ?)
            """
            
            cursor.execute(insert_sql, (zoom, column, row, tile_data))
            conn.commit()
            conn.close()
            
        except sqlite3.Error as e:
            raise TileProcessorError(f"Failed to write tile to temp database: {e}")
    
    
    def verify_generation_complete(self, target_zoom: int, expected_tile_count: int) -> Tuple[bool, str]:
        """
        Verify that all tiles were generated for a zoom level.
        
        Checks:
        1. Tile count matches expected (passed in, not calculated from 4^zoom)
        2. No SQL errors or corruption
        3. All tiles present
        
        Args:
            target_zoom: The zoom level to verify
            expected_tile_count: The expected number of tiles (from generation plan)
            
        Returns:
            Tuple of (is_complete: bool, reason: str)
        """
        try:
            conn = sqlite3.connect(str(self.temp_db_path))
            cursor = conn.cursor()
            
            # Get actual tile count
            result = cursor.execute(
                "SELECT COUNT(*) FROM tiles WHERE zoom_level = ?",
                (target_zoom,)
            ).fetchone()
            
            actual_tiles = result[0] if result else 0
            conn.close()
            
            if actual_tiles != expected_tile_count:
                return False, (
                    f"Tile count mismatch: {actual_tiles}/{expected_tile_count} tiles. "
                    f"Generation incomplete or corrupted."
                )
            
            logger.info(f"Verified Z{target_zoom}: {actual_tiles:,} tiles (expected {expected_tile_count:,})")
            return True, ""
            
        except Exception as e:
            return False, f"Verification failed: {e}"
    
    
    def commit_generated_tiles(self, target_zoom: int, expected_tile_count: int) -> bool:
        """
        Atomically commit all generated tiles from temp database to real database.
        
        This is the critical safety operation:
        1. All tiles verified before commit (count must match plan)
        2. Single atomic transaction to real database
        3. Either all tiles written or none (no partial states)
        4. Temp database cleaned up after successful commit
        
        Args:
            target_zoom: The zoom level being committed
            expected_tile_count: The expected number of tiles from generation plan
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            TileProcessorError: If commit fails
        """
        if not self.temp_db_path:
            raise TileProcessorError("No temporary database to commit")
        
        # Verify first (with expected tile count from plan)
        is_complete, reason = self.verify_generation_complete(target_zoom, expected_tile_count)
        if not is_complete:
            # Clean up temp database
            try:
                Path(self.temp_db_path).unlink()
            except Exception:
                pass
            raise TileProcessorError(f"Cannot commit incomplete generation: {reason}")
        
        try:
            # Open real database for atomic transaction
            conn = sqlite3.connect(self.filepath)
            cursor = conn.cursor()
            
            # Open temp database for reading
            temp_conn = sqlite3.connect(str(self.temp_db_path))
            temp_cursor = temp_conn.cursor()
            
            # Begin atomic transaction
            cursor.execute("BEGIN TRANSACTION")
            
            try:
                # Copy all tiles from temp to real database
                tiles = temp_cursor.execute(
                    "SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles "
                    "WHERE zoom_level = ?",
                    (target_zoom,)
                ).fetchall()
                
                insert_sql = """
                    INSERT OR IGNORE INTO tiles 
                    (zoom_level, tile_column, tile_row, tile_data)
                    VALUES (?, ?, ?, ?)
                """
                
                cursor.executemany(insert_sql, tiles)
                
                # Mark zoom as generated
                cursor.execute(
                    "INSERT OR REPLACE INTO metadata (name, value) VALUES (?, ?)",
                    (f"generated_zoom_{target_zoom}", "true")
                )
                
                # Commit atomic transaction
                cursor.execute("COMMIT")
                
                logger.info(f"Successfully committed Z{target_zoom}: {len(tiles):,} tiles")
                
            except Exception as e:
                # Rollback if anything fails
                cursor.execute("ROLLBACK")
                raise TileProcessorError(f"Commit transaction failed: {e}")
            
            finally:
                conn.close()
                temp_conn.close()
            
            # Clean up temp database after successful commit
            try:
                Path(self.temp_db_path).unlink()
                logger.debug(f"Cleaned up temporary database")
            except Exception as e:
                logger.warning(f"Failed to delete temporary database: {e}")
            
            self.temp_db_path = None
            return True
            
        except Exception as e:
            logger.error(f"Failed to commit generated tiles: {e}")
            raise TileProcessorError(f"Failed to commit generated tiles: {e}")
    
    
    def cleanup_temp_database(self):
        """Clean up temporary database if it exists (e.g., on cancellation)."""
        if self.temp_db_path:
            try:
                Path(self.temp_db_path).unlink()
                logger.debug(f"Cleaned up temporary database after cancellation")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary database: {e}")
            
            self.temp_db_path = None
