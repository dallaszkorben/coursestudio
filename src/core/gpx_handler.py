"""
GPX file handling for CourseStudio.

Provides GPX file loading, parsing, validation, and saving with Garmin compatibility.

Key Features:
- Load GPX files using gpxpy library
- Extract tracks, routes, and waypoints
- Validate Garmin compatibility
- Calculate track statistics (distance, point count)
- Save modified GPX files with proper formatting
- Handle errors gracefully with user-friendly messages

Author: Development Team
Date: 2026-09-20
"""

import os
import gpxpy
import gpxpy.gpx
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

from src.core.calculator import calculate_track_distance, validate_coordinate


class GPXHandler:
    """
    Handles all GPX file operations for CourseStudio.
    
    Provides methods for loading, parsing, validating, and saving GPX files
    with support for Garmin device compatibility.
    
    Attributes:
        gpx_data (gpxpy.gpx.GPX): Loaded GPX data
        file_path (str): Path to loaded GPX file
        is_valid (bool): Whether loaded GPX is valid
    
    Example:
        >>> handler = GPXHandler()
        >>> gpx = handler.load_gpx('track.gpx')
        >>> tracks = handler.get_tracks(gpx)
        >>> for track in tracks:
        ...     info = handler.get_track_info(track)
        ...     print(f"{info['name']}: {info['distance']:.2f} km")
    """
    
    def __init__(self):
        """Initialize GPXHandler."""
        self.gpx_data = None
        self.file_path = None
        self.is_valid = False
    
    # ========================================================================
    # File Loading & Parsing
    # ========================================================================
    
    def load_gpx(self, file_path: str) -> Optional[gpxpy.gpx.GPX]:
        """
        Load and parse a GPX file.
        
        Args:
            file_path (str): Path to GPX file
        
        Returns:
            Optional[gpxpy.gpx.GPX]: Parsed GPX object, or None if error
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not valid GPX
        
        Example:
            >>> handler = GPXHandler()
            >>> gpx = handler.load_gpx('track.gpx')
            >>> if gpx:
            ...     print(f"Loaded GPX file with {len(gpx.tracks)} tracks")
        """
        
        # Verify file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"GPX file not found: {file_path}")
        
        # Verify file is readable
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"Cannot read GPX file (permission denied): {file_path}")
        
        # Parse GPX file
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as gpx_file:
                self.gpx_data = gpxpy.parse(gpx_file)
        except gpxpy.gpx.GPXException as e:
            raise ValueError(f"Invalid GPX file format: {str(e)}")
        except UnicodeDecodeError as e:
            raise ValueError(f"GPX file encoding error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing GPX file: {str(e)}")
        
        # Store file path and mark as valid
        self.file_path = file_path
        self.is_valid = True
        
        print(f"✅ Loaded GPX file: {file_path}")
        print(f"   Tracks: {len(self.gpx_data.tracks)}")
        print(f"   Routes: {len(self.gpx_data.routes)}")
        print(f"   Waypoints: {len(self.gpx_data.waypoints)}")
        
        return self.gpx_data
    
    # ========================================================================
    # Track Information Extraction
    # ========================================================================
    
    def get_tracks(self, gpx_data: gpxpy.gpx.GPX) -> List[gpxpy.gpx.GPXTrack]:
        """
        Extract all tracks from GPX data.
        
        Args:
            gpx_data (gpxpy.gpx.GPX): Loaded GPX object
        
        Returns:
            List[gpxpy.gpx.GPXTrack]: List of all tracks in GPX file
        
        Example:
            >>> gpx = handler.load_gpx('track.gpx')
            >>> tracks = handler.get_tracks(gpx)
            >>> print(f"Found {len(tracks)} tracks")
        """
        return gpx_data.tracks if gpx_data else []
    
    def get_track_info(self, track: gpxpy.gpx.GPXTrack) -> Dict[str, Any]:
        """
        Extract information from a single track.
        
        Calculates distance, point count, and other metadata.
        
        Args:
            track (gpxpy.gpx.GPXTrack): GPX track object
        
        Returns:
            Dict[str, Any]: Track information dictionary with keys:
                - name: Track name (str)
                - distance: Total distance in km (float)
                - point_count: Number of trackpoints (int)
                - segment_count: Number of segments (int)
                - has_elevation: Whether track has elevation data (bool)
                - has_time: Whether track has timestamps (bool)
                - bounds: (min_lat, max_lat, min_lon, max_lon) tuple
        
        Example:
            >>> info = handler.get_track_info(track)
            >>> print(f"{info['name']}: {info['distance']:.2f} km ({info['point_count']} points)")
        """
        
        # Extract basic info
        name = track.name if track.name else "Unnamed Track"
        distance = self.calculate_distance(track)
        
        # Count points across all segments
        point_count = 0
        has_elevation = False
        has_time = False
        
        for segment in track.segments:
            point_count += len(segment.points)
            
            # Check for elevation and time data
            for point in segment.points:
                if point.elevation is not None:
                    has_elevation = True
                if point.time is not None:
                    has_time = True
        
        # Get bounds
        bounds = track.get_bounds()
        bounds_tuple = (bounds.min_latitude, bounds.max_latitude, 
                       bounds.min_longitude, bounds.max_longitude) if bounds else None
        
        return {
            'name': name,
            'distance': distance,
            'point_count': point_count,
            'segment_count': len(track.segments),
            'has_elevation': has_elevation,
            'has_time': has_time,
            'bounds': bounds_tuple
        }
    
    def get_trackpoints(self, track: gpxpy.gpx.GPXTrack) -> List[Tuple[float, float, Optional[float], Optional[str]]]:
        """
        Extract all trackpoints from a track.
        
        Returns trackpoints as (latitude, longitude, elevation, timestamp) tuples.
        
        Args:
            track (gpxpy.gpx.GPXTrack): GPX track object
        
        Returns:
            List of (lat, lon, elevation, timestamp) tuples
        
        Example:
            >>> points = handler.get_trackpoints(track)
            >>> for lat, lon, elev, time in points:
            ...     print(f"Point at {lat}, {lon}")
        """
        
        trackpoints = []
        
        for segment in track.segments:
            for point in segment.points:
                trackpoints.append((
                    point.latitude,
                    point.longitude,
                    point.elevation,
                    point.time.isoformat() if point.time else None
                ))
        
        return trackpoints
    
    def calculate_distance(self, track: gpxpy.gpx.GPXTrack) -> float:
        """
        Calculate total distance of a track.
        
        Uses Haversine formula to sum great-circle distances between points.
        
        Args:
            track (gpxpy.gpx.GPXTrack): GPX track object
        
        Returns:
            float: Total distance in kilometers
        
        Example:
            >>> distance = handler.calculate_distance(track)
            >>> print(f"Track distance: {distance:.2f} km")
        """
        
        # Extract all trackpoints from all segments as (lat, lon) tuples
        points = []
        for segment in track.segments:
            for pt in segment.points:
                points.append((pt.latitude, pt.longitude))
        
        # Use calculator to compute distance
        return calculate_track_distance(points)
    
    # ========================================================================
    # Validation
    # ========================================================================
    
    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate that a file is a valid GPX file.
        
        Does not load the file, just checks format.
        
        Args:
            file_path (str): Path to file to validate
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
                - is_valid: True if valid GPX, False otherwise
                - error_message: Empty string if valid, error description if invalid
        
        Example:
            >>> valid, msg = handler.validate_file('track.gpx')
            >>> if valid:
            ...     print("File is valid GPX")
            ... else:
            ...     print(f"Error: {msg}")
        """
        
        # Check file exists
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        
        # Check file is readable
        if not os.access(file_path, os.R_OK):
            return False, f"Cannot read file (permission denied)"
        
        # Try to parse
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                gpxpy.parse(f)
            return True, ""
        except Exception as e:
            return False, f"Invalid GPX: {str(e)}"
    
    def validate_garmin_compatibility(self, gpx_data: gpxpy.gpx.GPX) -> Tuple[bool, List[str]]:
        """
        Validate that GPX data can be imported into Garmin devices.
        
        Checks for common issues that prevent Garmin import:
        - Null bytes in names
        - Invalid coordinates
        - Malformed structure
        
        Args:
            gpx_data (gpxpy.gpx.GPX): GPX object to validate
        
        Returns:
            Tuple[bool, List[str]]: (is_compatible, list_of_errors)
                - is_compatible: True if compatible with Garmin
                - list_of_errors: Empty list if valid, list of error messages if invalid
        
        Example:
            >>> gpx = handler.load_gpx('track.gpx')
            >>> compatible, errors = handler.validate_garmin_compatibility(gpx)
            >>> if not compatible:
            ...     for error in errors:
            ...         print(f"Issue: {error}")
        """
        
        errors = []
        
        # Check tracks
        for track_idx, track in enumerate(gpx_data.tracks):
            # Check track name
            if track.name:
                # Check for null bytes
                if '\x00' in track.name:
                    errors.append(f"Track {track_idx}: Name contains null bytes")
                
                # Check length
                if len(track.name) > 255:
                    errors.append(f"Track {track_idx}: Name too long (>255 chars)")
            
            # Check trackpoints
            for seg_idx, segment in enumerate(track.segments):
                for pt_idx, point in enumerate(segment.points):
                    # Validate coordinates
                    valid, msg = validate_coordinate(point.latitude, point.longitude)
                    if not valid:
                        errors.append(f"Track {track_idx}, Segment {seg_idx}, Point {pt_idx}: {msg}")
        
        is_compatible = len(errors) == 0
        return is_compatible, errors
    
    # ========================================================================
    # File Saving
    # ========================================================================
    
    def save_gpx(self, file_path: str, gpx_data: gpxpy.gpx.GPX, 
                 create_backup: bool = True) -> Tuple[bool, str]:
        """
        Save modified GPX data to file with Garmin compatibility.
        
        Validates Garmin compatibility before saving and creates backup.
        
        Args:
            file_path (str): Path where to save GPX file
            gpx_data (gpxpy.gpx.GPX): GPX object to save
            create_backup (bool): Whether to create backup (.bak) file
        
        Returns:
            Tuple[bool, str]: (success, message)
                - success: True if saved, False if error
                - message: Success message or error description
        
        Example:
            >>> gpx = handler.load_gpx('track.gpx')
            >>> # Modify tracks...
            >>> success, msg = handler.save_gpx('track_modified.gpx', gpx)
            >>> if success:
            ...     print(f"✅ {msg}")
            ... else:
            ...     print(f"❌ {msg}")
        """
        
        # Validate Garmin compatibility
        compatible, errors = self.validate_garmin_compatibility(gpx_data)
        
        if not compatible:
            error_msg = "; ".join(errors)
            return False, f"GPX not Garmin compatible: {error_msg}"
        
        # Create backup if file exists and backup requested
        if os.path.exists(file_path) and create_backup:
            backup_path = file_path + ".bak"
            try:
                import shutil
                shutil.copy2(file_path, backup_path)
                print(f"✅ Created backup: {backup_path}")
            except Exception as e:
                print(f"⚠️  Could not create backup: {e}")
        
        # Write GPX file
        try:
            with open(file_path, 'w', encoding='utf-8') as gpx_file:
                gpx_file.write(gpx_data.to_xml())
            
            return True, f"✅ File saved: {file_path}"
        
        except Exception as e:
            return False, f"Error saving file: {str(e)}"


if __name__ == "__main__":
    # Simple test
    print("\n" + "="*70)
    print("Testing GPXHandler Module")
    print("="*70 + "\n")
    
    handler = GPXHandler()
    
    # Test validation
    print("Testing file validation:")
    valid, msg = handler.validate_file("config/settings.ini")
    print(f"  settings.ini is valid GPX: {valid} ({msg if msg else 'invalid format'})")
    
    print("\n" + "="*70 + "\n")
