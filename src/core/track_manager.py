"""
Track Manager Module for mangpx.

Manages in-memory track data structures, track selection, and operations.
Provides the data model for all track manipulation features in the application.

This module acts as the bridge between GPX file data (from GPXHandler) and
the UI layers. It maintains track state, supports undo/redo preparation,
and ensures data integrity during track operations.

Key Classes:
    - Trackpoint: Single point in a track
    - TrackData: In-memory representation of a GPX track
    - TrackManager: Central manager for all tracks and operations

Example:
    >>> from src.core.track_manager import TrackManager
    >>> from src.core.gpx_handler import GPXHandler
    >>> 
    >>> manager = TrackManager()
    >>> handler = GPXHandler()
    >>> gpx = handler.load_gpx('track.gpx')
    >>> manager.load_from_gpx(gpx)
    >>> 
    >>> # Get all tracks
    >>> tracks = manager.get_all_tracks()
    >>> 
    >>> # Select and work with a track
    >>> manager.select_track(0)
    >>> info = manager.get_selected_track_info()
    >>> print(f"Track: {info['name']} ({info['point_count']} points)")
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging

import gpxpy.gpx


# ============================================================================
# Logging Configuration
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Trackpoint:
    """
    Represents a single trackpoint (waypoint) in a track.
    
    A trackpoint is a single location with coordinates, optional elevation,
    and optional timestamp data.
    
    Attributes:
        latitude (float): Latitude in decimal degrees (-90 to 90)
        longitude (float): Longitude in decimal degrees (-180 to 180)
        elevation (Optional[float]): Elevation in meters (None if not available)
        timestamp (Optional[str]): ISO format timestamp (None if not available)
        index (int): Position in track (0-based)
    
    Example:
        >>> point = Trackpoint(57.5126, 17.2456, 25.0, "2023-06-15T10:30:00Z", 0)
        >>> print(f"Point at {point.latitude}, {point.longitude}")
    """
    
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    timestamp: Optional[str] = None
    index: int = 0
    
    def __post_init__(self):
        """Validate trackpoint data after initialization."""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Invalid longitude: {self.longitude}")


@dataclass
class TrackData:
    """
    In-memory representation of a single GPX track.
    
    Stores track metadata and all trackpoints. Tracks the dirty state
    to support undo/redo and save detection.
    
    Attributes:
        name (str): Track name
        original_name (str): Original name (for undo support)
        trackpoints (List[Trackpoint]): All trackpoints in order
        segment_count (int): Number of segments in original track
        has_elevation (bool): Whether track has elevation data
        has_time (bool): Whether track has timestamp data
        bounds (Optional[Tuple]): (min_lat, max_lat, min_lon, max_lon)
        distance_km (float): Total track distance in kilometers
        is_dirty (bool): Whether track has unsaved changes
        original_track (Optional[gpxpy.gpx.GPXTrack]): Original GPX track object
    
    Example:
        >>> points = [
        ...     Trackpoint(57.5126, 17.2456, 25.0, None, 0),
        ...     Trackpoint(57.5200, 17.2500, 26.0, None, 1),
        ... ]
        >>> track = TrackData(
        ...     name="My Track",
        ...     trackpoints=points,
        ...     distance_km=10.5
        ... )
        >>> print(f"{track.name}: {len(track.trackpoints)} points")
    """
    
    name: str
    trackpoints: List[Trackpoint] = field(default_factory=list)
    original_name: str = ""
    segment_count: int = 1
    has_elevation: bool = False
    has_time: bool = False
    bounds: Optional[Tuple[float, float, float, float]] = None
    distance_km: float = 0.0
    is_dirty: bool = False
    original_track: Optional[gpxpy.gpx.GPXTrack] = None
    
    def __post_init__(self):
        """Initialize derived values after creation."""
        if not self.original_name:
            self.original_name = self.name
    
    def get_point_count(self) -> int:
        """Get total number of trackpoints."""
        return len(self.trackpoints)
    
    def get_point(self, index: int) -> Optional[Trackpoint]:
        """Get trackpoint by index."""
        if 0 <= index < len(self.trackpoints):
            return self.trackpoints[index]
        return None
    
    def mark_dirty(self):
        """Mark track as having unsaved changes."""
        self.is_dirty = True
        logger.debug(f"Track '{self.name}' marked as dirty")


# ============================================================================
# Track Manager Class
# ============================================================================

class TrackManager:
    """
    Central manager for all tracks and track operations.
    
    Manages in-memory track data, track selection, and provides operations
    for track manipulation. Acts as the data model for the application.
    
    Attributes:
        tracks (List[TrackData]): All loaded tracks
        selected_track_index (int): Currently selected track index (-1 = none)
        gpx_file_path (Optional[str]): Path to loaded GPX file
        is_dirty (bool): Whether any track has unsaved changes
    
    Key Responsibilities:
        - Load tracks from GPX data
        - Maintain track state (selection, data)
        - Provide track information queries
        - Support track operations (rename, recalculate distance)
        - Track dirty state for save detection
    
    Example:
        >>> manager = TrackManager()
        >>> 
        >>> # Load from GPX
        >>> from src.core.gpx_handler import GPXHandler
        >>> handler = GPXHandler()
        >>> gpx = handler.load_gpx('track.gpx')
        >>> manager.load_from_gpx(gpx)
        >>> 
        >>> # Get track list
        >>> for i, track in enumerate(manager.get_all_tracks()):
        ...     print(f"{i}: {track.name} ({track.get_point_count()} points)")
        >>> 
        >>> # Select and work with a track
        >>> manager.select_track(0)
        >>> info = manager.get_selected_track_info()
        >>> print(info['name'], info['distance_km'])
        >>> 
        >>> # Rename track
        >>> manager.rename_selected_track("New Name")
        >>> print(manager.get_selected_track().name)  # "New Name"
    """
    
    def __init__(self, use_history: bool = False):
        """
        Initialize TrackManager with empty state.
        
        Args:
            use_history: If True, enable undo/redo command history
        """
        self.tracks: List[TrackData] = []
        self.selected_track_index: int = -1
        self.gpx_file_path: Optional[str] = None
        self.use_history = use_history
        
        # Optional command history for undo/redo
        if use_history:
            from src.core.command_history import CommandHistory
            self.history: Optional['CommandHistory'] = CommandHistory()
        else:
            self.history = None
        
        logger.debug(f"TrackManager initialized (history={'enabled' if use_history else 'disabled'})")
    
    # ========================================================================
    # Loading & Initialization
    # ========================================================================
    
    def load_from_gpx(self, gpx_data: gpxpy.gpx.GPX, 
                     gpx_file_path: Optional[str] = None) -> int:
        """
        Load tracks from GPX data.
        
        Converts all tracks in a GPX object into TrackData objects.
        Automatically selects the first track after loading.
        
        Args:
            gpx_data (gpxpy.gpx.GPX): Loaded GPX object from GPXHandler
            gpx_file_path (Optional[str]): Path to the GPX file (for reference)
        
        Returns:
            int: Number of tracks loaded
        
        Raises:
            ValueError: If gpx_data is None or invalid
        
        Example:
            >>> manager = TrackManager()
            >>> handler = GPXHandler()
            >>> gpx = handler.load_gpx('track.gpx')
            >>> num_tracks = manager.load_from_gpx(gpx, 'track.gpx')
            >>> print(f"Loaded {num_tracks} tracks")
        """
        
        if not gpx_data:
            raise ValueError("GPX data is None or invalid")
        
        # Import calculator for distance calculation
        from src.core.calculator import calculate_track_distance, validate_coordinate
        
        # Reset state
        self.tracks.clear()
        self.selected_track_index = -1
        self.gpx_file_path = gpx_file_path
        
        # Load each track
        for track in gpx_data.tracks:
            try:
                # Extract trackpoints
                trackpoints: List[Trackpoint] = []
                distance_tuples: List[Tuple[float, float]] = []
                has_elevation = False
                has_time = False
                
                for segment in track.segments:
                    for point_idx, point in enumerate(segment.points):
                        # Validate coordinates
                        try:
                            validate_coordinate(point.latitude, point.longitude)
                        except ValueError as e:
                            logger.warning(f"Skipping invalid trackpoint: {e}")
                            continue
                        
                        # Check for elevation and time
                        if point.elevation is not None:
                            has_elevation = True
                        if point.time is not None:
                            has_time = True
                        
                        # Create trackpoint
                        trackpoint = Trackpoint(
                            latitude=float(point.latitude),
                            longitude=float(point.longitude),
                            elevation=float(point.elevation) if point.elevation else None,
                            timestamp=point.time.isoformat() if point.time else None,
                            index=len(trackpoints)
                        )
                        trackpoints.append(trackpoint)
                        # Also track for distance calculation (calculator expects tuples)
                        distance_tuples.append((float(point.latitude), float(point.longitude)))
                
                if not trackpoints:
                    logger.warning(f"Track '{track.name}' has no valid trackpoints, skipping")
                    continue
                
                # Calculate distance using tuples (calculator API)
                distance_km = calculate_track_distance(distance_tuples)
                
                # Get bounds
                bounds = track.get_bounds()
                bounds_tuple = (bounds.min_latitude, bounds.max_latitude,
                              bounds.min_longitude, bounds.max_longitude) if bounds else None
                
                # Create TrackData
                track_data = TrackData(
                    name=track.name if track.name else "Unnamed Track",
                    original_name=track.name if track.name else "Unnamed Track",
                    trackpoints=trackpoints,
                    segment_count=len(track.segments),
                    has_elevation=has_elevation,
                    has_time=has_time,
                    bounds=bounds_tuple,
                    distance_km=distance_km,
                    is_dirty=False,
                    original_track=track
                )
                
                self.tracks.append(track_data)
                logger.info(f"Loaded track '{track_data.name}': "
                          f"{track_data.get_point_count()} points, "
                          f"{track_data.distance_km:.2f} km")
            
            except Exception as e:
                logger.error(f"Error loading track: {e}")
                continue
        
        # Auto-select first track if any loaded
        if self.tracks:
            self.selected_track_index = 0
            logger.info(f"Selected track 0: '{self.tracks[0].name}'")
        
        logger.info(f"Loaded {len(self.tracks)} tracks from GPX")
        return len(self.tracks)
    
    def clear(self):
        """Clear all tracks and reset state."""
        self.tracks.clear()
        self.selected_track_index = -1
        self.gpx_file_path = None
        logger.debug("TrackManager cleared")
    
    # ========================================================================
    # Track Selection
    # ========================================================================
    
    def select_track(self, track_index: int) -> bool:
        """
        Select a track by index.
        
        Args:
            track_index (int): Index of track to select (0-based)
        
        Returns:
            bool: True if track selected successfully, False if invalid index
        
        Example:
            >>> manager.select_track(1)
            True
            >>> print(manager.get_selected_track().name)
        """
        
        if not 0 <= track_index < len(self.tracks):
            logger.warning(f"Invalid track index: {track_index}")
            return False
        
        self.selected_track_index = track_index
        logger.debug(f"Selected track {track_index}: '{self.tracks[track_index].name}'")
        return True
    
    def get_selected_track_index(self) -> int:
        """Get currently selected track index (-1 if none selected)."""
        return self.selected_track_index
    
    def is_track_selected(self) -> bool:
        """Check if a track is currently selected."""
        return 0 <= self.selected_track_index < len(self.tracks)
    
    def get_selected_track(self) -> Optional[TrackData]:
        """
        Get the currently selected TrackData object.
        
        Returns:
            Optional[TrackData]: Selected track, or None if not selected
        
        Example:
            >>> track = manager.get_selected_track()
            >>> if track:
            ...     print(track.name)
        """
        
        if 0 <= self.selected_track_index < len(self.tracks):
            return self.tracks[self.selected_track_index]
        return None
    
    # ========================================================================
    # Track Information Queries
    # ========================================================================
    
    def get_all_tracks(self) -> List[TrackData]:
        """
        Get all loaded tracks.
        
        Returns:
            List[TrackData]: All tracks (empty list if none loaded)
        """
        return self.tracks.copy()
    
    def get_track_count(self) -> int:
        """Get total number of loaded tracks."""
        return len(self.tracks)
    
    def get_track_by_index(self, track_index: int) -> Optional[TrackData]:
        """
        Get a track by index.
        
        Args:
            track_index (int): Track index (0-based)
        
        Returns:
            Optional[TrackData]: Track if found, None otherwise
        """
        if 0 <= track_index < len(self.tracks):
            return self.tracks[track_index]
        return None
    
    def get_selected_track_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently selected track.
        
        Returns:
            Optional[Dict]: Dictionary with track info, or None if no track selected
        
        Info keys:
            - name: Track name (str)
            - point_count: Number of trackpoints (int)
            - distance_km: Distance in kilometers (float)
            - segment_count: Number of segments (int)
            - has_elevation: Has elevation data (bool)
            - has_time: Has timestamp data (bool)
            - bounds: (min_lat, max_lat, min_lon, max_lon) tuple
            - is_dirty: Has unsaved changes (bool)
        
        Example:
            >>> info = manager.get_selected_track_info()
            >>> if info:
            ...     print(f"{info['name']}: {info['distance_km']:.2f} km")
        """
        
        track = self.get_selected_track()
        if not track:
            return None
        
        return {
            'name': track.name,
            'point_count': track.get_point_count(),
            'distance_km': track.distance_km,
            'segment_count': track.segment_count,
            'has_elevation': track.has_elevation,
            'has_time': track.has_time,
            'bounds': track.bounds,
            'is_dirty': track.is_dirty
        }
    
    def get_track_info(self, track_index: int) -> Optional[Dict[str, Any]]:
        """
        Get information about a track by index.
        
        Args:
            track_index (int): Track index (0-based)
        
        Returns:
            Optional[Dict]: Track info dictionary (see get_selected_track_info)
        """
        
        track = self.get_track_by_index(track_index)
        if not track:
            return None
        
        return {
            'name': track.name,
            'point_count': track.get_point_count(),
            'distance_km': track.distance_km,
            'segment_count': track.segment_count,
            'has_elevation': track.has_elevation,
            'has_time': track.has_time,
            'bounds': track.bounds,
            'is_dirty': track.is_dirty
        }
    
    # ========================================================================
    # Track Operations
    # ========================================================================
    
    def rename_track(self, track_index: int, new_name: str) -> bool:
        """
        Rename a track by index.
        
        Args:
            track_index (int): Track index (0-based)
            new_name (str): New name for the track
        
        Returns:
            bool: True if renamed successfully, False if invalid index
        
        Example:
            >>> manager.rename_track(0, "My New Track Name")
            True
        """
        
        track = self.get_track_by_index(track_index)
        if not track:
            logger.warning(f"Cannot rename: invalid track index {track_index}")
            return False
        
        old_name = track.name
        track.name = new_name
        track.mark_dirty()
        
        logger.info(f"Renamed track: '{old_name}' → '{new_name}'")
        return True
    
    def rename_track_with_history(self, track_index: int, new_name: str) -> bool:
        """
        Rename a track using command history (undoable).
        
        Args:
            track_index (int): Track index (0-based)
            new_name (str): New name for the track
        
        Returns:
            bool: True if renamed successfully, False if invalid index or history disabled
        
        Example:
            >>> manager = TrackManager(use_history=True)
            >>> manager.rename_track_with_history(0, "New Name")
            True
            >>> manager.history.undo()  # Undo the rename
        """
        
        if not self.history:
            logger.warning("Command history not enabled")
            return False
        
        track = self.get_track_by_index(track_index)
        if not track:
            logger.warning(f"Cannot rename: invalid track index {track_index}")
            return False
        
        from src.core.command_history import RenameTrackCommand
        
        old_name = track.name
        cmd = RenameTrackCommand(self, track_index, old_name, new_name)
        
        return self.history.execute(cmd)
    
    def rename_selected_track(self, new_name: str) -> bool:
        """
        Rename the currently selected track.
        
        Args:
            new_name (str): New name for the track
        
        Returns:
            bool: True if renamed successfully, False if no track selected
        
        Example:
            >>> manager.select_track(0)
            >>> manager.rename_selected_track("Updated Track")
            True
        """
        
        if not self.is_track_selected():
            logger.warning("Cannot rename: no track selected")
            return False
        
        return self.rename_track(self.selected_track_index, new_name)
    
    def recalculate_distance(self, track_index: int) -> Optional[float]:
        """
        Recalculate distance for a track (e.g., after point modifications).
        
        Args:
            track_index (int): Track index (0-based)
        
        Returns:
            Optional[float]: New distance in km, or None if invalid index
        
        Example:
            >>> distance = manager.recalculate_distance(0)
            >>> print(f"New distance: {distance:.2f} km")
        """
        
        from src.core.calculator import calculate_track_distance
        
        track = self.get_track_by_index(track_index)
        if not track:
            logger.warning(f"Cannot recalculate: invalid track index {track_index}")
            return None
        
        # Convert trackpoints to tuples for calculator
        distance_tuples = [(tp.latitude, tp.longitude) for tp in track.trackpoints]
        
        old_distance = track.distance_km
        track.distance_km = calculate_track_distance(distance_tuples)
        track.mark_dirty()
        
        logger.info(f"Recalculated distance for '{track.name}': "
                  f"{old_distance:.2f} km → {track.distance_km:.2f} km")
        
        return track.distance_km
    
    def recalculate_selected_distance(self) -> Optional[float]:
        """
        Recalculate distance for the currently selected track.
        
        Returns:
            Optional[float]: New distance in km, or None if no track selected
        """
        
        if not self.is_track_selected():
            logger.warning("Cannot recalculate: no track selected")
            return None
        
        return self.recalculate_distance(self.selected_track_index)
    
    # ========================================================================
    # Trackpoint Access
    # ========================================================================
    
    def get_trackpoints(self, track_index: int) -> Optional[List[Trackpoint]]:
        """
        Get all trackpoints for a track.
        
        Args:
            track_index (int): Track index (0-based)
        
        Returns:
            Optional[List[Trackpoint]]: List of trackpoints, or None if invalid index
        """
        
        track = self.get_track_by_index(track_index)
        if not track:
            return None
        
        return track.trackpoints.copy()
    
    def get_selected_trackpoints(self) -> Optional[List[Trackpoint]]:
        """
        Get all trackpoints for the currently selected track.
        
        Returns:
            Optional[List[Trackpoint]]: Trackpoints, or None if no track selected
        """
        
        track = self.get_selected_track()
        if not track:
            return None
        
        return track.trackpoints.copy()
    
    def get_trackpoint(self, track_index: int, point_index: int) -> Optional[Trackpoint]:
        """
        Get a single trackpoint by track and point indices.
        
        Args:
            track_index (int): Track index (0-based)
            point_index (int): Point index within track (0-based)
        
        Returns:
            Optional[Trackpoint]: Trackpoint if found, None otherwise
        """
        
        track = self.get_track_by_index(track_index)
        if not track:
            return None
        
        return track.get_point(point_index)
    
    # ========================================================================
    # Dirty State Management
    # ========================================================================
    
    def is_any_track_dirty(self) -> bool:
        """Check if any track has unsaved changes."""
        return any(track.is_dirty for track in self.tracks)
    
    def is_track_dirty(self, track_index: int) -> bool:
        """
        Check if a specific track has unsaved changes.
        
        Args:
            track_index (int): Track index (0-based)
        
        Returns:
            bool: True if track is dirty, False otherwise
        """
        
        track = self.get_track_by_index(track_index)
        if not track:
            return False
        
        return track.is_dirty
    
    def is_selected_track_dirty(self) -> bool:
        """Check if the selected track has unsaved changes."""
        
        track = self.get_selected_track()
        if not track:
            return False
        
        return track.is_dirty
    
    def mark_clean(self, track_index: int) -> bool:
        """
        Mark a track as saved (not dirty).
        
        Args:
            track_index (int): Track index (0-based)
        
        Returns:
            bool: True if marked clean, False if invalid index
        """
        
        track = self.get_track_by_index(track_index)
        if not track:
            return False
        
        track.is_dirty = False
        logger.debug(f"Track '{track.name}' marked as clean")
        return True
    
    def mark_clean_all(self):
        """Mark all tracks as saved (not dirty)."""
        for track in self.tracks:
            track.is_dirty = False
        logger.debug("All tracks marked as clean")
    
    # ========================================================================
    # Trackpoint Operations
    # ========================================================================
    
    def remove_trackpoint(self, track_index: int, point_index: int) -> Optional[Trackpoint]:
        """
        Remove a single trackpoint from a track.
        
        Removes the trackpoint at the specified index, recalculates track
        distance, and marks track as dirty for saving.
        
        Args:
            track_index (int): Index of track to modify
            point_index (int): Index of trackpoint to remove (0-based)
        
        Returns:
            Optional[Trackpoint]: Removed trackpoint if successful, None otherwise
        
        Raises:
            ValueError: If indices are invalid or out of range
        
        Example:
            >>> manager = TrackManager()
            >>> # ... load tracks ...
            >>> manager.select_track(0)
            >>> removed = manager.remove_trackpoint(0, 5)
            >>> if removed:
            ...     print(f"Removed point at ({removed.latitude}, {removed.longitude})")
            >>> else:
            ...     print("Failed to remove trackpoint")
        """
        
        # Validate track index
        if not isinstance(track_index, int) or track_index < 0 or track_index >= len(self.tracks):
            logger.error(f"Invalid track index: {track_index}")
            return None
        
        track = self.tracks[track_index]
        
        # Validate point index
        if not isinstance(point_index, int) or point_index < 0 or point_index >= len(track.trackpoints):
            logger.error(f"Invalid trackpoint index {point_index} for track with {len(track.trackpoints)} points")
            return None
        
        # Cannot remove if only one point left
        if len(track.trackpoints) <= 1:
            logger.warning(f"Cannot remove trackpoint: Track '{track.name}' would be empty")
            return None
        
        # Remove the trackpoint
        removed_point = track.trackpoints.pop(point_index)
        logger.info(f"Removed trackpoint {point_index} from track '{track.name}' at ({removed_point.latitude:.4f}, {removed_point.longitude:.4f})")
        
        # Recalculate distance
        self.recalculate_distance(track_index)
        
        # Mark as dirty
        track.is_dirty = True
        
        return removed_point
    
    def remove_trackpoint_selected(self, point_index: int) -> Optional[Trackpoint]:
        """
        Remove trackpoint from currently selected track.
        
        Args:
            point_index (int): Index of trackpoint to remove
        
        Returns:
            Optional[Trackpoint]: Removed trackpoint if successful, None otherwise
        
        Example:
            >>> manager = TrackManager()
            >>> manager.select_track(0)
            >>> removed = manager.remove_trackpoint_selected(5)
        """
        if self.selected_track_index < 0:
            logger.warning("No track selected")
            return None
        
        return self.remove_trackpoint(self.selected_track_index, point_index)
    
    def remove_trackpoints_from_start(self, track_index: int, to_index: int) -> Optional[List[Trackpoint]]:
        """
        Remove trackpoints from start up to (and including) the specified index.
        
        Deletes points [0, 1, ..., to_index], keeping points after to_index.
        
        Args:
            track_index (int): Index of track to modify
            to_index (int): Index up to which to remove (inclusive)
        
        Returns:
            Optional[List[Trackpoint]]: Removed trackpoints if successful, None otherwise
        
        Example:
            >>> manager = TrackManager()
            >>> manager.select_track(0)
            >>> removed = manager.remove_trackpoints_from_start(0, 10)
            >>> print(f"Removed {len(removed)} points from start")
        """
        
        # Validate track index
        if not isinstance(track_index, int) or track_index < 0 or track_index >= len(self.tracks):
            logger.error(f"Invalid track index: {track_index}")
            return None
        
        track = self.tracks[track_index]
        
        # Validate to_index
        if not isinstance(to_index, int) or to_index < 0 or to_index >= len(track.trackpoints):
            logger.error(f"Invalid to_index: {to_index}")
            return None
        
        # Need at least one point left
        remaining = len(track.trackpoints) - (to_index + 1)
        if remaining <= 0:
            logger.warning(f"Cannot remove: Track would be empty (to_index={to_index}, total={len(track.trackpoints)})")
            return None
        
        # Remove from start to to_index
        removed_points = track.trackpoints[:to_index + 1]
        track.trackpoints = track.trackpoints[to_index + 1:]
        
        logger.info(f"Removed {len(removed_points)} trackpoints from start of track '{track.name}'")
        
        # Recalculate distance
        self.recalculate_distance(track_index)
        
        # Mark as dirty
        track.is_dirty = True
        
        return removed_points
    
    def remove_trackpoints_from_end(self, track_index: int, from_index: int) -> Optional[List[Trackpoint]]:
        """
        Remove trackpoints from the specified index to the end of track.
        
        Keeps points [0, 1, ..., from_index-1], deletes points [from_index, ...].
        
        Args:
            track_index (int): Index of track to modify
            from_index (int): Index from which to start removing
        
        Returns:
            Optional[List[Trackpoint]]: Removed trackpoints if successful, None otherwise
        
        Example:
            >>> manager = TrackManager()
            >>> manager.select_track(0)
            >>> removed = manager.remove_trackpoints_from_end(0, 500)
            >>> print(f"Removed {len(removed)} points from end")
        """
        
        # Validate track index
        if not isinstance(track_index, int) or track_index < 0 or track_index >= len(self.tracks):
            logger.error(f"Invalid track index: {track_index}")
            return None
        
        track = self.tracks[track_index]
        
        # Validate from_index
        if not isinstance(from_index, int) or from_index < 0 or from_index >= len(track.trackpoints):
            logger.error(f"Invalid from_index: {from_index}")
            return None
        
        # Need at least one point left
        if from_index <= 0:
            logger.warning(f"Cannot remove: Track would be empty (from_index={from_index})")
            return None
        
        # Remove from from_index to end
        removed_points = track.trackpoints[from_index:]
        track.trackpoints = track.trackpoints[:from_index]
        
        logger.info(f"Removed {len(removed_points)} trackpoints from end of track '{track.name}'")
        
        # Recalculate distance
        self.recalculate_distance(track_index)
        
        # Mark as dirty
        track.is_dirty = True
        
        return removed_points

    def add_trackpoint(self, track_index: int, latitude: float, longitude: float,
                       altitude: Optional[float] = None, position: Optional[int] = None) -> bool:
        """
        Add a new trackpoint to the track.
        
        Args:
            track_index (int): Index of track to modify
            latitude (float): Latitude in decimal degrees (-90 to 90)
            longitude (float): Longitude in decimal degrees (-180 to 180)
            altitude (Optional[float]): Elevation in meters
            position (Optional[int]): Index where to insert. If None, appends at end.
        
        Returns:
            bool: True if successful, False otherwise
        
        Example:
            >>> manager = TrackManager()
            >>> manager.select_track(0)
            >>> success = manager.add_trackpoint(0, 57.5126, 12.2584, altitude=42.5)
            >>> print(f"Added: {success}")
        """
        
        # Validate track index
        if not isinstance(track_index, int) or track_index < 0 or track_index >= len(self.tracks):
            logger.error(f"Invalid track index: {track_index}")
            return False
        
        track = self.tracks[track_index]
        
        # Validate coordinates
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            logger.error(f"Coordinates must be numeric: lat={latitude}, lon={longitude}")
            return False
        
        if not (-90.0 <= latitude <= 90.0):
            logger.error(f"Latitude out of range: {latitude}")
            return False
        
        if not (-180.0 <= longitude <= 180.0):
            logger.error(f"Longitude out of range: {longitude}")
            return False
        
        # Validate altitude if provided
        if altitude is not None and not isinstance(altitude, (int, float)):
            logger.error(f"Altitude must be numeric: {altitude}")
            return False
        
        # Validate position if provided
        if position is not None:
            if not isinstance(position, int) or position < 0 or position > len(track.trackpoints):
                logger.error(f"Invalid position: {position} (track has {len(track.trackpoints)} points)")
                return False
        
        # Create new trackpoint with next index
        next_index = len(track.trackpoints)
        new_point = Trackpoint(
            latitude=latitude,
            longitude=longitude,
            elevation=altitude,
            timestamp=None,
            index=next_index
        )
        
        # Insert at position or append
        if position is None:
            track.trackpoints.append(new_point)
            logger.info(f"Added trackpoint to end of track '{track.name}' (lat={latitude}, lon={longitude})")
        else:
            track.trackpoints.insert(position, new_point)
            # Update indices for all points from insertion point onwards
            for i in range(position, len(track.trackpoints)):
                track.trackpoints[i].index = i
            logger.info(f"Inserted trackpoint at position {position} in track '{track.name}' (lat={latitude}, lon={longitude})")
        
        # Recalculate distance
        self.recalculate_distance(track_index)
        
        # Mark as dirty
        track.is_dirty = True
        
        return True

    def add_trackpoint_selected(self, latitude: float, longitude: float,
                                altitude: Optional[float] = None, position: Optional[int] = None) -> bool:
        """
        Add a trackpoint to the currently selected track.
        
        Args:
            latitude (float): Latitude in decimal degrees
            longitude (float): Longitude in decimal degrees
            altitude (Optional[float]): Elevation in meters
            position (Optional[int]): Index where to insert. If None, appends at end.
        
        Returns:
            bool: True if successful, False otherwise
        """
        
        if self.selected_track_index < 0:
            logger.error("No track selected")
            return False
        
        return self.add_trackpoint(self.selected_track_index, latitude, longitude, altitude, position)

    def add_trackpoint_with_history(self, track_index: int, latitude: float, longitude: float,
                                    altitude: Optional[float] = None, position: Optional[int] = None) -> bool:
        """
        Add a trackpoint using command history (undoable).
        
        Args:
            track_index (int): Index of track
            latitude (float): Latitude in decimal degrees
            longitude (float): Longitude in decimal degrees
            altitude (Optional[float]): Elevation in meters
            position (Optional[int]): Index where to insert. If None, appends at end.
        
        Returns:
            bool: True if successful, False if history not enabled
        """
        
        if not self.history:
            logger.warning("Command history not enabled")
            return False
        
        from src.core.command_history import AddTrackpointCommand
        
        cmd = AddTrackpointCommand(self, track_index, latitude, longitude, altitude, position)
        return self.history.execute(cmd)

    def add_trackpoint_selected_with_history(self, latitude: float, longitude: float,
                                            altitude: Optional[float] = None, position: Optional[int] = None) -> bool:
        """
        Add a trackpoint to selected track using command history (undoable).
        
        Args:
            latitude (float): Latitude in decimal degrees
            longitude (float): Longitude in decimal degrees
            altitude (Optional[float]): Elevation in meters
            position (Optional[int]): Index where to insert. If None, appends at end.
        
        Returns:
            bool: True if successful, False if no track selected or history disabled
        """
        
        if self.selected_track_index < 0:
            logger.error("No track selected")
            return False
        
        return self.add_trackpoint_with_history(self.selected_track_index, latitude, longitude, altitude, position)

    def remove_trackpoint_with_history(self, track_index: int, point_index: int) -> bool:
        """
        Remove a trackpoint using command history (undoable).
        
        Args:
            track_index (int): Index of track
            point_index (int): Index of trackpoint to remove
        
        Returns:
            bool: True if successful, False if history not enabled
        """
        
        if not self.history:
            logger.warning("Command history not enabled")
            return False
        
        from src.core.command_history import RemoveTrackpointCommand
        
        cmd = RemoveTrackpointCommand(self, track_index, point_index)
        return self.history.execute(cmd)

    def remove_trackpoint_selected_with_history(self, point_index: int) -> bool:
        """
        Remove a trackpoint from selected track using command history (undoable).
        
        Args:
            point_index (int): Index of trackpoint to remove
        
        Returns:
            bool: True if successful, False if no track selected or history disabled
        """
        
        if self.selected_track_index < 0:
            logger.error("No track selected")
            return False
        
        return self.remove_trackpoint_with_history(self.selected_track_index, point_index)

    def remove_trackpoints_range_with_history(self, track_index: int, 
                                              start_index: int, end_index: int) -> bool:
        """
        Remove a range of trackpoints using command history (undoable).
        
        Args:
            track_index (int): Index of track
            start_index (int): First index to remove (inclusive)
            end_index (int): Last index to remove (inclusive)
        
        Returns:
            bool: True if successful, False if history not enabled
        """
        
        if not self.history:
            logger.warning("Command history not enabled")
            return False
        
        from src.core.command_history import RemoveTrackpointRangeCommand
        
        cmd = RemoveTrackpointRangeCommand(self, track_index, start_index, end_index)
        return self.history.execute(cmd)

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self.history is not None and self.history.can_undo()

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self.history is not None and self.history.can_redo()

    def undo(self) -> bool:
        """Undo the last command."""
        if self.history is None:
            logger.warning("Command history not enabled")
            return False
        
        return self.history.undo()

    def redo(self) -> bool:
        """Redo the last undone command."""
        if self.history is None:
            logger.warning("Command history not enabled")
            return False
        
        return self.history.redo()

    def get_undo_description(self) -> str:
        """Get description of next undo operation."""
        if self.history is None:
            return "Undo"
        return self.history.get_undo_description()

    def get_redo_description(self) -> str:
        """Get description of next redo operation."""
        if self.history is None:
            return "Redo"
        return self.history.get_redo_description()

    def clear_history(self):
        """Clear undo/redo history."""
        if self.history is not None:
            self.history.clear()


# ============================================================================
# Module-Level Utilities
# ============================================================================

def create_trackpoint_from_gpx_point(gpx_point: gpxpy.gpx.GPXTrackPoint, 
                                    index: int) -> Trackpoint:
    """
    Create a Trackpoint from a gpxpy track point.
    
    Args:
        gpx_point (gpxpy.gpx.GPXTrackPoint): GPX track point
        index (int): Position in track
    
    Returns:
        Trackpoint: Converted trackpoint object
    
    Raises:
        ValueError: If coordinates are invalid
    """
    
    from src.core.calculator import validate_coordinate
    
    validate_coordinate(gpx_point.latitude, gpx_point.longitude)
    
    return Trackpoint(
        latitude=float(gpx_point.latitude),
        longitude=float(gpx_point.longitude),
        elevation=float(gpx_point.elevation) if gpx_point.elevation else None,
        timestamp=gpx_point.time.isoformat() if gpx_point.time else None,
        index=index
    )
