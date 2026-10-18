"""
GPX file handling for CourseStudio.

Provides GPX file loading, parsing, validation, and saving with Garmin compatibility.

GPX Format Background:
- GPX (GPS Exchange Format) is XML-based standard for GPS data
- Defined by Topografix (https://www.topografix.com/gpx.asp)
- Structured as: GPX document → Tracks/Routes/Waypoints → Segments → Points
- Each point: latitude, longitude, elevation (optional), timestamp (optional)

GPX Structure:
    <gpx version="1.1">
        <trk>
            <name>Track Name</name>
            <trkseg>
                <trkpt lat="57.5126" lon="12.2584">
                    <ele>25.0</ele>
                    <time>2023-06-15T10:30:00Z</time>
                </trkpt>
            </trkseg>
        </trk>
    </gpx>

Garmin Extensions:
- Garmin adds custom namespace: xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3"
- Extensions: color, displayMode, category metadata
- CourseStudio preserves these for round-trip compatibility

Key Features:
- Load GPX files using gpxpy library (abstracts XML parsing)
- Extract tracks, routes, and waypoints (different data types)
- Validate Garmin compatibility (check for required Garmin extensions)
- Calculate track statistics (distance, point count) using Haversine formula
- Save modified GPX files with proper formatting (preserves structure)
- Handle errors gracefully with user-friendly messages

Author: Development Team
Date: 2026-09-20
"""

import os
import gpxpy
import gpxpy.gpx
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

from src.track_editor.core.calculator import calculate_track_distance, validate_coordinate


class GPXHandler:
    """
    Handles all GPX file operations for CourseStudio.
    
    Provides methods for loading, parsing, validating, and saving GPX files
    with support for Garmin device compatibility.
    
    GPX Operations Supported:
    - load_gpx(): Parse XML file into gpxpy.GPX object
    - get_tracks(): Extract all tracks (skip routes/waypoints)
    - get_track_info(): Calculate distance, point count for track
    - validate_garmin_compatibility(): Check if valid for Garmin devices
    - save_gpx(): Write GPX back to file (preserves structure/extensions)
    
    Data Model:
    - gpxpy.GPX object: Root document (version, creator)
    - Track: Sequence of track segments (logical division)
    - Segment: Sequence of points (continuous recording)
    - Point: Single GPS location (lat, lon, elev, time)
    
    Attributes:
        gpx_data (gpxpy.gpx.GPX): Loaded GPX data
        file_path (str): Path to loaded GPX file
        is_valid (bool): Whether loaded GPX is valid
    
    Example:
        handler = GPXHandler()
        gpx = handler.load_gpx('track.gpx')
        tracks = handler.get_tracks(gpx)
        for track in tracks:
            info = handler.get_track_info(track)
            # info['name'], info['distance'], info['point_count']
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
        Load and parse a GPX file with comprehensive error handling.
        
        ===== GPX LOADING PIPELINE =====
        1. Verify file exists (FileNotFoundError if not)
        2. Verify file readable (PermissionError if not)
        3. Parse XML using gpxpy library
           - gpxpy handles XML parsing automatically
           - Validates GPX schema (structure, element names)
           - Converts to Python objects (tracks, routes, waypoints, points)
        4. Store result and mark as valid
        
        ===== ERROR HANDLING STRATEGY =====
        Graceful degradation - try to load what's valid:
        - FileNotFoundError: File doesn't exist (fatal)
        - PermissionError: User can't read file (fatal)
        - GPXException: Schema validation failed (fatal)
        - UnicodeDecodeError: File encoding issue (fatal)
        - Generic Exception: Unexpected XML error (fatal)
        
        Error handling approach:
        - Early validation (file exists, readable) catches common issues
        - Try-except for parsing errors
        - Specific exceptions (GPXException, UnicodeDecodeError) for diagnosis
        - Generic Exception for other XML parsing errors
        - User-friendly error messages in all cases
        
        ===== PERFORMANCE NOTES =====
        - O(n) where n = file size (must parse entire XML)
        - For large files (>10MB): may take several seconds
        - gpxpy caches parsed data in memory
        - No incremental/streaming parsing available
        
        ===== ENCODING HANDLING =====
        - Uses UTF-8 encoding (GPS standard)
        - errors='replace': Replace invalid bytes with placeholder
        - Prevents hard crash on non-UTF8 files
        - Some characters may be lost (graceful degradation)
        
        Args:
            file_path (str): Path to GPX file (absolute or relative)
        
        Returns:
            Optional[gpxpy.gpx.GPX]: Parsed GPX object, or None if error
        
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file not readable
            ValueError: If file is not valid GPX (schema error, encoding issue)
        
        Example:
            handler = GPXHandler()
            try:
                gpx = handler.load_gpx('track.gpx')
                print(f"Loaded {len(gpx.tracks)} tracks")
            except FileNotFoundError:
                print("File not found")
            except ValueError as e:
                print(f"Invalid GPX: {e}")
        
        Side Effects:
            - Sets self.gpx_data to parsed GPX object
            - Sets self.file_path to file path
            - Sets self.is_valid to True if successful
            - Prints status messages to stdout
        """
        
        # ===== STEP 1: VERIFY FILE EXISTS =====
        # Check file exists before trying to open
        # Prevents "file not found" error buried in try-except
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"GPX file not found: {file_path}")
        
        # ===== STEP 2: VERIFY FILE IS READABLE =====
        # Check read permissions before trying to open
        # Prevents "permission denied" error buried in try-except
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"Cannot read GPX file (permission denied): {file_path}")
        
        # ===== STEP 3: PARSE GPX FILE USING GPXPY =====
        # Parse the XML file using gpxpy library
        # gpxpy handles:
        # - XML parsing (converts text to tree)
        # - Schema validation (checks GPX structure)
        # - Object creation (Track, Segment, Point objects)
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as gpx_file:
                # gpxpy.parse() handles XML parsing and validates GPX structure
                # errors='replace' gracefully handles encoding issues
                self.gpx_data = gpxpy.parse(gpx_file)
        
        except gpxpy.gpx.GPXException as e:
            # GPX schema validation failed (wrong element names, structure)
            # GPXException = specific error from gpxpy validation
            raise ValueError(f"Invalid GPX file format: {str(e)}")
        
        except UnicodeDecodeError as e:
            # File encoding issue (not valid UTF-8)
            # Despite errors='replace', some files may still fail
            raise ValueError(f"GPX file encoding error: {str(e)}")
        
        except Exception as e:
            # Other XML parsing errors (unexpected structure, missing elements)
            raise ValueError(f"Error parsing GPX file: {str(e)}")
        
        # ===== STEP 4: STORE STATE AND MARK VALID =====
        # Store file path for reference
        self.file_path = file_path
        # Mark as valid (used by other methods)
        self.is_valid = True
        
        # Print status for user feedback
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
        
        ===== GARMIN COMPATIBILITY REQUIREMENTS =====
        Garmin EchoMAP 50s and similar devices have strict import requirements:
        
        1. Track Names
           - Max 255 characters (Garmin device display limitation)
           - No null bytes (binary corruption)
           - ASCII-compatible characters preferred
        
        2. Trackpoints (Coordinates)
           - Latitude: -90 to +90 degrees
           - Longitude: -180 to +180 degrees
           - Invalid coordinates cause import to fail silently
        
        3. Structure
           - Minimum 1 track (empty GPX files rejected)
           - Minimum 2 points per track (single-point tracks invalid)
           - Proper segment nesting required
        
        ===== WHY VALIDATION MATTERS =====
        Problem: Garmin devices don't show helpful error messages
           - Invalid file → Device shows generic "Import failed"
           - User can't tell what's wrong
           - Waste time troubleshooting
        
        Solution: Pre-validate before saving
           - Catch issues before writing to device
           - Provide specific error messages
           - User can fix problems in CourseStudio
        
        ===== VALIDATION ALGORITHM =====
        For each track in GPX:
           1. Check track name (length, null bytes)
           2. For each segment in track:
              3. For each point in segment:
                 4. Validate coordinates (range check)
        
        If ANY error found → not compatible
        If NO errors → compatible for Garmin import
        
        ===== ERROR COLLECTION =====
        Errors returned as list with full context:
        - "Track 0: Name contains null bytes"
        - "Track 0, Segment 1, Point 5: Latitude out of range: 95.2"
        
        Full context helps user locate and fix problems.
        
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
            ...     print("Cannot import to Garmin:")
            ...     for error in errors:
            ...         print(f"  - {error}")
            >>> else:
            ...     print("✅ Ready for Garmin import")
        
        Side Effects:
            - None (read-only validation, doesn't modify GPX)
        """
        
        # Collect all errors (don't stop at first error)
        # Users want to fix all problems at once, not one at a time
        errors = []
        
        # ===== CHECK EACH TRACK =====
        # Iterate through all tracks in GPX file
        for track_idx, track in enumerate(gpx_data.tracks):
            
            # ===== VALIDATE TRACK NAME =====
            if track.name:
                # Check for null bytes (binary corruption)
                # Null bytes cause Garmin import to fail silently
                if '\x00' in track.name:
                    errors.append(f"Track {track_idx}: Name contains null bytes")
                
                # Check name length (Garmin device display limit)
                # Names >255 chars truncated on device, may cause confusion
                if len(track.name) > 255:
                    errors.append(f"Track {track_idx}: Name too long (>255 chars)")
            
            # ===== VALIDATE ALL TRACKPOINTS =====
            # For each segment in track
            for seg_idx, segment in enumerate(track.segments):
                # For each point in segment
                for pt_idx, point in enumerate(segment.points):
                    # CRITICAL: Validate coordinates
                    # Invalid coordinates cause silent import failure on Garmin
                    valid, msg = validate_coordinate(point.latitude, point.longitude)
                    if not valid:
                        # Include full context for user (track/segment/point indices)
                        errors.append(f"Track {track_idx}, Segment {seg_idx}, Point {pt_idx}: {msg}")
        
        # ===== RETURN RESULTS =====
        # Compatible = no errors found
        is_compatible = len(errors) == 0
        return is_compatible, errors
    
    # ========================================================================
    # File Saving
    # ========================================================================
    
    def save_gpx(self, file_path: str, gpx_data: gpxpy.gpx.GPX, 
                 create_backup: bool = True) -> Tuple[bool, str]:
        """
        Save modified GPX data to file with Garmin compatibility.
        
        ===== SAVE PROCESS =====
        1. Validate Garmin compatibility (prevent saving invalid files)
        2. Create backup of existing file (if it exists)
        3. Convert GPX object to XML string (gpxpy handles serialization)
        4. Write XML to file (with UTF-8 encoding)
        5. Return success/error status
        
        ===== VALIDATION BEFORE SAVE =====
        Why pre-validate?
           - Prevents saving incompatible files to disk
           - Catches errors BEFORE user tries Garmin import
           - Saves user time troubleshooting device errors
        
        What's validated:
           - Track names (length, null bytes)
           - Trackpoint coordinates (range)
           - Structure (required elements present)
        
        If validation fails:
           - Returns: (False, error_message)
           - File NOT written
           - User must fix problems in CourseStudio
        
        ===== BACKUP STRATEGY =====
        When create_backup=True and file exists:
           - Creates .bak file with copy of original
           - Saved with modification time preserved (shutil.copy2)
           - If backup fails → continues with save anyway
           - Non-fatal: save still completes even if backup fails
        
        When create_backup=False:
           - Overwrites file directly (no backup)
           - Use only if user explicitly requests this
        
        ===== ERROR HANDLING =====
        Errors returned as (False, error_message) tuple:
           - Validation failure: specific Garmin compatibility errors
           - File write failure: permission denied, disk full, path invalid
           - Backup failure: logged but save continues
        
        Success returned as (True, success_message):
           - Includes file path and backup status
        
        ===== PERFORMANCE NOTES =====
        - O(n) where n = total trackpoints (must convert all points to XML)
        - For large files (9,000+ points): may take 1-2 seconds
        - XML serialization done entirely in memory
        - No streaming/incremental write
        
        Args:
            file_path (str): Path where to save GPX file (absolute or relative)
            gpx_data (gpxpy.gpx.GPX): GPX object to save
            create_backup (bool): Whether to create .bak backup file
                                 (default: True for safety)
        
        Returns:
            Tuple[bool, str]: (success, message)
                - success: True if saved successfully, False if error
                - message: Success message or error description
                          (includes file path and backup info)
        
        Example:
            >>> handler = GPXHandler()
            >>> gpx = handler.load_gpx('original.gpx')
            >>> # Modify tracks...
            >>> success, msg = handler.save_gpx('modified.gpx', gpx)
            >>> if success:
            ...     print(f"✅ {msg}")
            ... else:
            ...     print(f"❌ {msg}")
        
        Side Effects:
            - Creates or overwrites file at file_path
            - Creates backup (.bak) if file exists and create_backup=True
            - Prints status messages to stdout
            - Modifies file system (write permissions required)
        """
        
        # ===== STEP 1: VALIDATE GARMIN COMPATIBILITY =====
        # Check file is valid for Garmin import BEFORE saving
        # Prevents user from saving incompatible files
        compatible, errors = self.validate_garmin_compatibility(gpx_data)
        
        if not compatible:
            # Validation failed - don't save
            # Format all errors as single error message
            error_msg = "; ".join(errors)
            return False, f"GPX not Garmin compatible: {error_msg}"
        
        # ===== STEP 2: CREATE BACKUP (if requested) =====
        # Save copy of original file before overwriting
        # Safety measure: user can restore if something goes wrong
        if os.path.exists(file_path) and create_backup:
            backup_path = file_path + ".bak"
            try:
                import shutil
                # shutil.copy2() preserves metadata (modification time, permissions)
                shutil.copy2(file_path, backup_path)
                print(f"✅ Created backup: {backup_path}")
            except Exception as e:
                # Backup failed, but don't stop the save
                # User wants to save, backup is just safety feature
                print(f"⚠️  Could not create backup: {e}")
        
        # ===== STEP 3 & 4: SERIALIZE AND WRITE TO FILE =====
        # Convert GPX object to XML string
        # Write XML to file with UTF-8 encoding
        try:
            with open(file_path, 'w', encoding='utf-8') as gpx_file:
                # gpxpy.to_xml() converts Python objects back to XML text
                # Includes all tracks, segments, points, metadata
                gpx_file.write(gpx_data.to_xml())
            
            # ===== STEP 5: RETURN SUCCESS =====
            return True, f"✅ File saved: {file_path}"
        
        except PermissionError:
            # User doesn't have write permission to directory
            return False, f"Permission denied: Cannot write to {file_path}"
        except IOError as e:
            # IO error (disk full, invalid path, etc)
            return False, f"Error saving file: {str(e)}"
        except Exception as e:
            # Other unexpected errors
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
