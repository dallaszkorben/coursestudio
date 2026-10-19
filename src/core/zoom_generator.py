"""
Zoom Level Generation - Intelligent zoom level creation algorithm.

This module handles the analysis and generation of missing zoom levels in MBTiles files.
It supports both downsampling (from higher zoom levels) and interpolation (from lower zoom levels).

Key Concepts:
    - Downsampling: Combine 4 tiles at zoom Z+1 into 1 tile at zoom Z
    - Upsampling: Extract regions from tiles at zoom Z-1 to create tiles at zoom Z
    - Quality Warnings: Alert user when generating beyond max zoom (quality degrades)

Usage:
    >>> from src.map_editor.core.mbtiles_reader import MBTilesReader
    >>> reader = MBTilesReader('map.mbtiles')
    >>> generator = ZoomGenerator(reader)
    >>> gaps = generator.analyze_gaps()  # Detect missing zoom levels
    >>> source_z = generator.calculate_source_zoom(target_z=13)  # Find best source
    >>> if generator.should_warn_user(source_z, 13):
    ...     print("Quality will degrade")
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class GenerationPlan:
    """Plan for generating a specific zoom level."""
    target_zoom: int
    source_zoom: int
    source_type: str  # 'downsampling' or 'upsampling'
    tile_count: int
    quality_warning: bool
    quality_reason: str
    # Tile bounds for the target zoom level
    min_col: int = 0
    max_col: int = 0
    min_row: int = 0
    max_row: int = 0


class ZoomGeneratorError(Exception):
    """Base exception for zoom generation errors."""
    pass


class ZoomGenerator:
    """
    Intelligent zoom level generation for MBTiles files.
    
    Analyzes available zoom levels and determines the best strategy for generating
    missing levels using either downsampling or upsampling.
    
    Attributes:
        reader: MBTilesReader instance for database access
        min_zoom: Minimum possible zoom (usually 0)
        max_zoom: Maximum possible zoom (usually 20+)
    """
    
    def __init__(self, reader):
        """
        Initialize ZoomGenerator.
        
        Args:
            reader: MBTilesReader instance
        """
        self.reader = reader
        self.min_zoom = 0
        self.max_zoom = 28  # Web Mercator standard maximum
        
    def analyze_gaps(self) -> List[int]:
        """
        Analyze MBTiles file and detect missing zoom levels.
        
        Returns:
            List of missing zoom levels in the available range.
            
        Example:
            If file has zooms [8, 10, 12, 14, 16], returns [9, 11, 13, 15]
        """
        try:
            available_zooms = set(self.reader.get_available_zooms())
            
            if not available_zooms:
                return []
            
            min_z = min(available_zooms)
            max_z = max(available_zooms)
            
            # Find all missing zooms in range
            complete_range = set(range(min_z, max_z + 1))
            missing = sorted(list(complete_range - available_zooms))
            
            logger.debug(f"Analyzed gaps: available={sorted(available_zooms)}, "
                        f"missing={missing}")
            
            return missing
            
        except Exception as e:
            raise ZoomGeneratorError(f"Failed to analyze gaps: {e}")
    
    def calculate_source_zoom(self, target_zoom: int) -> Optional[int]:
        """
        Determine the best source zoom level for generating target zoom.
        
        Strategy:
            1. If target_zoom + 1 exists (higher), use downsampling (best quality)
            2. If target_zoom - 1 exists (lower), use upsampling
            3. If neither adjacent exists, find nearest zoom
            4. If no zooms exist at all, return None
        
        Args:
            target_zoom: The zoom level to generate
            
        Returns:
            Source zoom level, or None if no suitable source exists
        """
        try:
            available_zooms = set(self.reader.get_available_zooms())
            
            if not available_zooms:
                raise ZoomGeneratorError(
                    "No zoom levels available to use as source"
                )
            
            # Strategy 1: Use zoom Z+1 (downsampling - best quality)
            if target_zoom + 1 in available_zooms:
                logger.debug(f"Source for Z{target_zoom}: Z{target_zoom+1} (downsampling)")
                return target_zoom + 1
            
            # Strategy 2: Use zoom Z-1 (upsampling)
            if target_zoom - 1 in available_zooms:
                logger.debug(f"Source for Z{target_zoom}: Z{target_zoom-1} (upsampling)")
                return target_zoom - 1
            
            # Strategy 3: Find nearest zoom (could be multiple steps away)
            nearest = min(available_zooms, 
                         key=lambda z: abs(z - target_zoom))
            
            logger.debug(f"Source for Z{target_zoom}: Z{nearest} (fallback, "
                        f"distance={abs(nearest - target_zoom)})")
            
            return nearest
            
        except Exception as e:
            raise ZoomGeneratorError(f"Failed to calculate source zoom: {e}")
    
    def should_warn_user(self, source_zoom: int, target_zoom: int) -> Tuple[bool, str]:
        """
        Determine if user should be warned about quality issues.
        
        Quality warnings occur when:
        1. Generating beyond maximum available zoom (downsampling doesn't apply)
        2. Upsampling more than 2 levels (pixelation becomes visible)
        
        Args:
            source_zoom: Source zoom level
            target_zoom: Target zoom level to generate
            
        Returns:
            Tuple of (should_warn: bool, reason: str)
        """
        if source_zoom is None:
            return True, "No source zoom levels available"
        
        # Case 1: Upsampling (source < target)
        if source_zoom < target_zoom:
            upsample_distance = target_zoom - source_zoom
            
            if upsample_distance > 2:
                return True, (
                    f"Upsampling from Z{source_zoom} to Z{target_zoom} "
                    f"({upsample_distance} levels) - quality will degrade significantly"
                )
            
            if upsample_distance == 2:
                return True, (
                    f"Upsampling from Z{source_zoom} to Z{target_zoom} "
                    f"(2 levels) - moderate quality loss expected"
                )
            
            # 1 level upsampling is generally acceptable
            return False, ""
        
        # Case 2: Downsampling (source > target) - generally safe
        if source_zoom > target_zoom:
            return False, ""
        
        # Case 3: Same zoom (shouldn't happen)
        return False, ""
    
    def validate_generation(self, target_zoom: int) -> Tuple[bool, str]:
        """
        Validate that generation is possible for this zoom level.
        
        Checks:
        1. Zoom is within supported range (0-28)
        2. A suitable source zoom exists
        
        Note: Allows regenerating existing zoom levels and generating outside min/max range
        
        Args:
            target_zoom: The zoom level to validate
            
        Returns:
            Tuple of (is_valid: bool, reason: str)
        """
        # Range check
        if target_zoom < 0 or target_zoom > self.max_zoom:
            return False, (
                f"Zoom level {target_zoom} out of range "
                f"(must be 0-{self.max_zoom})"
            )
        
        # Check if source exists
        try:
            source_zoom = self.calculate_source_zoom(target_zoom)
            if source_zoom is None:
                return False, (
                    "No suitable source zoom levels exist to generate from"
                )
        except ZoomGeneratorError as e:
            return False, str(e)
        
        return True, ""
    
    def create_generation_plan(self, target_zoom: int) -> GenerationPlan:
        """
        Create a detailed plan for generating a zoom level.
        
        Combines all analysis into a single actionable plan with:
        - Source zoom and strategy (downsampling/upsampling)
        - Tile count to generate
        - Quality warnings and reasoning
        
        Args:
            target_zoom: The zoom level to generate
            
        Returns:
            GenerationPlan with all necessary information
            
        Raises:
            ZoomGeneratorError: If generation is not possible
        """
        # Validate
        is_valid, reason = self.validate_generation(target_zoom)
        if not is_valid:
            raise ZoomGeneratorError(reason)
        
        # Calculate source
        source_zoom = self.calculate_source_zoom(target_zoom)
        
        # Determine strategy
        if source_zoom > target_zoom:
            source_type = 'downsampling'
        else:
            source_type = 'upsampling'
        
        # ✅ FIX: Calculate tile count based on bounding box, not simple division
        # For sparse/regional MBTiles files, we need to consider the actual geographic
        # coverage (bounding box) of tiles, not just divide the tile count.
        
        source_min_col, source_max_col, source_min_row, source_max_row = \
            self.reader.get_tile_bounds(source_zoom)
        
        if source_min_col == 0 and source_max_col == 0:
            # No tiles in source zoom, shouldn't happen but handle gracefully
            tile_count = 4 ** target_zoom
        elif source_zoom > target_zoom:
            # Downsampling: convert source bounds to target bounds
            # Each coordinate gets divided by 2^(source_zoom - target_zoom)
            zoom_diff = source_zoom - target_zoom
            divisor = 2 ** zoom_diff
            
            target_min_col = source_min_col // divisor
            target_max_col = source_max_col // divisor
            target_min_row = source_min_row // divisor
            target_max_row = source_max_row // divisor
            
            # Calculate bounding box size
            width = target_max_col - target_min_col + 1
            height = target_max_row - target_min_row + 1
            tile_count = width * height
        else:
            # Upsampling: convert source bounds to target bounds
            # Each coordinate gets multiplied by 2^(target_zoom - source_zoom)
            zoom_diff = target_zoom - source_zoom
            multiplier = 2 ** zoom_diff
            
            target_min_col = source_min_col * multiplier
            target_max_col = (source_max_col + 1) * multiplier - 1
            target_min_row = source_min_row * multiplier
            target_max_row = (source_max_row + 1) * multiplier - 1
            
            # Calculate bounding box size
            width = target_max_col - target_min_col + 1
            height = target_max_row - target_min_row + 1
            tile_count = width * height
        
        logger.debug(f"Calculated tile count for Z{target_zoom}: {tile_count} tiles")
        
        # Check for warnings
        should_warn, warning_reason = self.should_warn_user(source_zoom, target_zoom)
        
        # Store the target bounds for the worker thread to use
        if source_min_col == 0 and source_max_col == 0:
            # No tiles - shouldn't happen but fallback
            bounds_min_col, bounds_max_col = 0, 0
            bounds_min_row, bounds_max_row = 0, 0
        elif source_zoom > target_zoom:
            bounds_min_col = target_min_col
            bounds_max_col = target_max_col
            bounds_min_row = target_min_row
            bounds_max_row = target_max_row
        else:
            bounds_min_col = target_min_col
            bounds_max_col = target_max_col
            bounds_min_row = target_min_row
            bounds_max_row = target_max_row
        
        plan = GenerationPlan(
            target_zoom=target_zoom,
            source_zoom=source_zoom,
            source_type=source_type,
            tile_count=tile_count,
            quality_warning=should_warn,
            quality_reason=warning_reason,
            min_col=bounds_min_col,
            max_col=bounds_max_col,
            min_row=bounds_min_row,
            max_row=bounds_max_row
        )
        
        logger.info(
            f"Generation plan: Z{target_zoom} from Z{source_zoom} "
            f"({source_type}, {tile_count} tiles)"
        )
        
        if should_warn:
            logger.warning(f"Quality warning: {warning_reason}")
        
        return plan
    
    def estimate_generation_time(self, target_zoom: int, 
                                 ms_per_tile: float = 0.05) -> float:
        """
        Estimate time to generate a zoom level.
        
        Estimation based on:
        - Tile count at zoom level
        - Assumed time per tile (typically 0.05-0.1ms)
        
        Args:
            target_zoom: The zoom level to estimate
            ms_per_tile: Estimated milliseconds per tile (default 0.05ms = 50µs)
            
        Returns:
            Estimated time in seconds
        """
        try:
            plan = self.create_generation_plan(target_zoom)
            tile_count = plan.tile_count
        except ZoomGeneratorError:
            # Fallback if plan creation fails
            tile_count = 4 ** target_zoom
        
        total_ms = tile_count * ms_per_tile
        total_seconds = total_ms / 1000
        return total_seconds
    
    def estimate_generation_size(self, target_zoom: int, 
                                 bytes_per_tile: int = 50000) -> int:
        """
        Estimate disk space required to generate a zoom level.
        
        Estimation based on:
        - Tile count at zoom level
        - Average tile size (typically 30KB-100KB depending on content)
        
        Args:
            target_zoom: The zoom level to estimate
            bytes_per_tile: Average bytes per tile (default 50KB)
            
        Returns:
            Estimated bytes needed
        """
        try:
            plan = self.create_generation_plan(target_zoom)
            tile_count = plan.tile_count
        except ZoomGeneratorError:
            # Fallback if plan creation fails
            tile_count = 4 ** target_zoom
        
        return tile_count * bytes_per_tile
    
    def get_summary(self) -> str:
        """
        Get a human-readable summary of current file state.
        
        Returns:
            Summary string with zoom levels and gaps
        """
        try:
            available = sorted(self.reader.get_available_zooms())
            missing = self.analyze_gaps()
            
            if not available:
                return "No zoom levels available"
            
            summary = f"Available: {available}\n"
            if missing:
                summary += f"Missing:   {missing}\n"
            else:
                summary += "No gaps detected\n"
            
            return summary
            
        except Exception as e:
            return f"Error getting summary: {e}"
