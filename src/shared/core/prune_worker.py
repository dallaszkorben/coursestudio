"""
Prune Points Worker - Background thread worker for trackpoint pruning.

Executes the pruning algorithm in a background thread to keep the UI responsive.
Similar to ZoomGenerationWorker pattern.

Usage:
    >>> worker = PruneWorker(track_manager, track_index, min_distance_m)
    >>> worker.progress.connect(on_progress)
    >>> worker.finished.connect(on_finished)
    >>> worker.error.connect(on_error)
    >>> worker.start()
"""

from PyQt5.QtCore import QThread, pyqtSignal
import logging

logger = logging.getLogger(__name__)


class PruneWorker(QThread):
    """
    Background worker thread for pruning trackpoints.
    
    Runs the prune algorithm in a separate thread so the UI stays responsive.
    Emits signals to report progress and results.
    
    Signals:
        progress: (processed, removed, kept) - Emitted after each point
        finished: (removed_count) - Emitted when pruning completes successfully
        error: (error_message) - Emitted if an error occurs
        cancelled: () - Emitted if user cancels the operation
    """
    
    # Signals
    progress = pyqtSignal(int, int, int)  # (processed, removed, kept)
    finished = pyqtSignal(int)  # (removed_count)
    error = pyqtSignal(str)  # (error_message)
    cancelled = pyqtSignal()  # User cancelled
    
    def __init__(self, track_manager, track_index: int, min_distance_m: float):
        """
        Initialize prune worker.
        
        Args:
            track_manager: TrackManager instance
            track_index: Index of track to prune
            min_distance_m: Minimum distance threshold in meters
        """
        super().__init__()
        
        self.track_manager = track_manager
        self.track_index = track_index
        self.min_distance_m = min_distance_m
        self._cancel_requested = False
    
    def run(self):
        """
        Execute pruning in background thread.
        
        This runs in a separate thread, so the main UI thread can
        process events and update the progress dialog.
        """
        try:
            logger.info(f"Prune worker: Starting pruning for track {self.track_index}")
            
            # Execute pruning with progress callback
            removed_count = self.track_manager.prune_trackpoints_by_distance(
                self.track_index,
                self.min_distance_m,
                progress_callback=self._on_progress,
                cancel_check=self._check_cancelled
            )
            
            # Check if cancelled
            if self._cancel_requested:
                logger.info("Prune worker: Cancelled by user")
                self.cancelled.emit()
                return
            
            logger.info(f"Prune worker: Finished, removed {removed_count} points")
            self.finished.emit(removed_count)
        
        except Exception as e:
            logger.error(f"Prune worker: Error during pruning: {e}", exc_info=True)
            self.error.emit(str(e))
    
    def cancel(self):
        """Request cancellation of pruning operation."""
        logger.info("Prune worker: Cancellation requested")
        self._cancel_requested = True
    
    def _check_cancelled(self):
        """Check if cancellation was requested."""
        return self._cancel_requested
    
    def _on_progress(self, processed, removed, kept):
        """
        Called by prune algorithm to report progress.
        
        Args:
            processed: Number of points processed
            removed: Number of points removed so far
            kept: Number of points kept so far
        """
        if not self._cancel_requested:
            self.progress.emit(processed, removed, kept)
