"""
Zoom Generation Worker Thread - Run generation in background.

Allows the UI to stay responsive while generating tiles.
Reports progress via signals.

Usage:
    >>> worker = ZoomGenerationWorker(processor, plan, target_zoom)
    >>> worker.progress.connect(on_progress)
    >>> worker.finished.connect(on_finished)
    >>> worker.error.connect(on_error)
    >>> thread = QThread()
    >>> worker.moveToThread(thread)
    >>> thread.started.connect(worker.run)
    >>> thread.start()
"""

from PyQt5.QtCore import QObject, QThread, pyqtSignal
import logging

logger = logging.getLogger(__name__)


class ZoomGenerationWorker(QObject):
    """Worker for tile generation in background thread."""
    
    # Signals
    progress = pyqtSignal(int, int)  # (completed, total)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    cancelled = pyqtSignal()
    
    def __init__(self, processor, plan, target_zoom):
        """
        Initialize worker.
        
        Args:
            processor: TileProcessor instance
            plan: GenerationPlan from ZoomGenerator
            target_zoom: Target zoom level to generate
        """
        super().__init__()
        
        self.processor = processor
        self.plan = plan
        self.target_zoom = target_zoom
        self.should_cancel = False
    
    def run(self):
        """Run tile generation (called in background thread)."""
        try:
            logger.info(f"Starting generation of Z{self.target_zoom}")
            
            # Create temporary database for safe generation
            try:
                self.processor.create_temp_database(self.target_zoom)
            except Exception as e:
                logger.error(f"Failed to create temporary database: {e}")
                self.error.emit(f"Failed to create temporary database: {e}")
                return
            
            tiles_generated = 0
            total_tiles = self.plan.tile_count
            
            # ✅ FIX: Use tile bounds from the plan, not 2^zoom range
            # This ensures we only generate tiles in the actual coverage area
            min_col = self.plan.min_col
            max_col = self.plan.max_col
            min_row = self.plan.min_row
            max_row = self.plan.max_row
            
            logger.debug(f"Generating tiles in bounds: cols {min_col}-{max_col}, rows {min_row}-{max_row}")
            
            # Generate all tiles for this zoom within the coverage bounds
            for tile_x in range(min_col, max_col + 1):
                for tile_y in range(min_row, max_row + 1):
                    # Check if cancellation requested
                    if self.should_cancel:
                        logger.info("Generation cancelled by user")
                        self.processor.cleanup_temp_database()
                        self.cancelled.emit()
                        return
                    
                    try:
                        # Generate tile
                        tile_data = self.processor.generate_tile(
                            self.plan.source_zoom,
                            self.target_zoom,
                            tile_x,
                            tile_y
                        )
                        
                        # Write to temporary database (safe location)
                        self.processor.write_tile_to_temp(
                            self.target_zoom,
                            tile_x,
                            tile_y,
                            tile_data
                        )
                        
                        tiles_generated += 1
                        
                        # Report progress every 100 tiles
                        if tiles_generated % 100 == 0:
                            self.progress.emit(tiles_generated, total_tiles)
                            logger.debug(f"Generated {tiles_generated}/{total_tiles} tiles")
                    
                    except Exception as e:
                        logger.warning(f"Failed to generate tile Z{self.target_zoom}/{tile_x}/{tile_y}: {e}")
                        continue
            
            # Atomically commit all tiles to real database
            # Pass the expected tile count from the plan for verification
            try:
                self.processor.commit_generated_tiles(self.target_zoom, total_tiles)
            except Exception as e:
                logger.error(f"Failed to commit generated tiles: {e}")
                self.processor.cleanup_temp_database()
                self.error.emit(f"Failed to commit tiles: {e}")
                return
            
            # Final progress update
            self.progress.emit(tiles_generated, total_tiles)
            
            logger.info(f"Successfully generated Z{self.target_zoom} ({tiles_generated} tiles)")
            self.finished.emit()
        
        except Exception as e:
            logger.error(f"Error during generation: {e}", exc_info=True)
            self.processor.cleanup_temp_database()
            self.error.emit(str(e))
    
    def cancel(self):
        """Request cancellation."""
        logger.info("Cancellation requested")
        self.should_cancel = True
