"""
Unit tests for Track Manager module (src/core/track_manager.py).

Tests cover:
- Trackpoint creation and validation
- TrackData initialization and operations
- TrackManager loading, selection, and state management
- Track information queries
- Track operations (rename, recalculate distance)
- Trackpoint access and dirty state management

Run with: pytest tests/test_track_manager.py -v
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
import sys
import os

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.track_manager import (
    Trackpoint, TrackData, TrackManager, create_trackpoint_from_gpx_point
)
import gpxpy.gpx


# ============================================================================
# Trackpoint Tests
# ============================================================================

class TestTrackpoint:
    """Tests for Trackpoint dataclass."""
    
    def test_trackpoint_creation_valid(self):
        """Test creating a valid trackpoint."""
        point = Trackpoint(57.5126, 17.2456, 25.0, "2023-06-15T10:30:00Z", 0)
        
        assert point.latitude == 57.5126
        assert point.longitude == 17.2456
        assert point.elevation == 25.0
        assert point.timestamp == "2023-06-15T10:30:00Z"
        assert point.index == 0
    
    def test_trackpoint_creation_minimal(self):
        """Test creating trackpoint with minimal data."""
        point = Trackpoint(0.0, 0.0)
        
        assert point.latitude == 0.0
        assert point.longitude == 0.0
        assert point.elevation is None
        assert point.timestamp is None
        assert point.index == 0
    
    def test_trackpoint_latitude_range(self):
        """Test latitude validation (-90 to 90)."""
        # Valid boundaries
        Trackpoint(-90.0, 0.0)  # Should not raise
        Trackpoint(90.0, 0.0)   # Should not raise
        
        # Invalid values
        with pytest.raises(ValueError):
            Trackpoint(-90.1, 0.0)
        with pytest.raises(ValueError):
            Trackpoint(90.1, 0.0)
    
    def test_trackpoint_longitude_range(self):
        """Test longitude validation (-180 to 180)."""
        # Valid boundaries
        Trackpoint(0.0, -180.0)  # Should not raise
        Trackpoint(0.0, 180.0)   # Should not raise
        
        # Invalid values
        with pytest.raises(ValueError):
            Trackpoint(0.0, -180.1)
        with pytest.raises(ValueError):
            Trackpoint(0.0, 180.1)
    
    def test_trackpoint_north_pole(self):
        """Test trackpoint at north pole."""
        point = Trackpoint(90.0, 0.0)
        assert point.latitude == 90.0
    
    def test_trackpoint_south_pole(self):
        """Test trackpoint at south pole."""
        point = Trackpoint(-90.0, 0.0)
        assert point.latitude == -90.0
    
    def test_trackpoint_negative_elevation(self):
        """Test trackpoint with negative elevation (below sea level)."""
        point = Trackpoint(0.0, 0.0, -100.0)
        assert point.elevation == -100.0
    
    def test_trackpoint_zero_elevation(self):
        """Test trackpoint with zero elevation."""
        point = Trackpoint(0.0, 0.0, 0.0)
        assert point.elevation == 0.0


# ============================================================================
# TrackData Tests
# ============================================================================

class TestTrackData:
    """Tests for TrackData dataclass."""
    
    def test_trackdata_creation_basic(self):
        """Test basic TrackData creation."""
        track = TrackData(name="Test Track")
        
        assert track.name == "Test Track"
        assert track.original_name == "Test Track"
        assert len(track.trackpoints) == 0
        assert track.is_dirty is False
    
    def test_trackdata_creation_with_points(self):
        """Test TrackData creation with trackpoints."""
        points = [
            Trackpoint(57.5, 17.2, 25.0, None, 0),
            Trackpoint(57.6, 17.3, 26.0, None, 1),
        ]
        
        track = TrackData(
            name="Test Track",
            trackpoints=points,
            distance_km=10.5
        )
        
        assert len(track.trackpoints) == 2
        assert track.distance_km == 10.5
    
    def test_trackdata_get_point_count(self):
        """Test getting point count."""
        points = [Trackpoint(57.5, 17.2, None, None, i) for i in range(5)]
        track = TrackData(name="Test", trackpoints=points)
        
        assert track.get_point_count() == 5
    
    def test_trackdata_get_point_valid_index(self):
        """Test getting point by valid index."""
        points = [
            Trackpoint(57.5, 17.2, None, None, 0),
            Trackpoint(57.6, 17.3, None, None, 1),
        ]
        track = TrackData(name="Test", trackpoints=points)
        
        point = track.get_point(0)
        assert point is not None
        assert point.latitude == 57.5
    
    def test_trackdata_get_point_invalid_index(self):
        """Test getting point by invalid index."""
        points = [Trackpoint(57.5, 17.2, None, None, 0)]
        track = TrackData(name="Test", trackpoints=points)
        
        assert track.get_point(5) is None
        assert track.get_point(-1) is None
    
    def test_trackdata_mark_dirty(self):
        """Test marking track as dirty."""
        track = TrackData(name="Test Track", is_dirty=False)
        
        assert track.is_dirty is False
        track.mark_dirty()
        assert track.is_dirty is True
    
    def test_trackdata_with_elevation_and_time(self):
        """Test TrackData with elevation and time data."""
        track = TrackData(
            name="Test",
            has_elevation=True,
            has_time=True
        )
        
        assert track.has_elevation is True
        assert track.has_time is True
    
    def test_trackdata_with_bounds(self):
        """Test TrackData with geographic bounds."""
        bounds = (57.5, 57.6, 17.2, 17.3)
        track = TrackData(name="Test", bounds=bounds)
        
        assert track.bounds == bounds


# ============================================================================
# TrackManager - Initialization & Loading
# ============================================================================

class TestTrackManagerInitialization:
    """Tests for TrackManager initialization and GPX loading."""
    
    def test_trackmanager_init(self):
        """Test TrackManager initialization."""
        manager = TrackManager()
        
        assert len(manager.tracks) == 0
        assert manager.selected_track_index == -1
        assert manager.gpx_file_path is None
    
    def test_load_from_gpx_invalid_data(self):
        """Test loading from invalid GPX data."""
        manager = TrackManager()
        
        with pytest.raises(ValueError):
            manager.load_from_gpx(None)
    
    def test_load_from_gpx_empty(self):
        """Test loading from GPX with no tracks."""
        manager = TrackManager()
        gpx = gpxpy.gpx.GPX()
        
        count = manager.load_from_gpx(gpx)
        
        assert count == 0
        assert len(manager.tracks) == 0
    
    def test_load_from_gpx_single_track(self):
        """Test loading a single track from GPX."""
        manager = TrackManager()
        
        # Create GPX with one track
        gpx = gpxpy.gpx.GPX()
        track = gpxpy.gpx.GPXTrack()
        track.name = "Test Track"
        segment = gpxpy.gpx.GPXTrackSegment()
        
        segment.points.append(gpxpy.gpx.GPXTrackPoint(57.5, 17.2))
        segment.points.append(gpxpy.gpx.GPXTrackPoint(57.6, 17.3))
        track.segments.append(segment)
        gpx.tracks.append(track)
        
        count = manager.load_from_gpx(gpx)
        
        assert count == 1
        assert len(manager.tracks) == 1
        assert manager.tracks[0].name == "Test Track"
        assert manager.tracks[0].get_point_count() == 2
    
    def test_load_from_gpx_multiple_tracks(self):
        """Test loading multiple tracks from GPX."""
        manager = TrackManager()
        gpx = gpxpy.gpx.GPX()
        
        for track_num in range(3):
            track = gpxpy.gpx.GPXTrack()
            track.name = f"Track {track_num}"
            segment = gpxpy.gpx.GPXTrackSegment()
            segment.points.append(gpxpy.gpx.GPXTrackPoint(57.5 + track_num, 17.2))
            segment.points.append(gpxpy.gpx.GPXTrackPoint(57.6 + track_num, 17.3))
            track.segments.append(segment)
            gpx.tracks.append(track)
        
        count = manager.load_from_gpx(gpx)
        
        assert count == 3
        assert len(manager.tracks) == 3
        assert manager.tracks[0].name == "Track 0"
        assert manager.tracks[2].name == "Track 2"
    
    def test_load_from_gpx_auto_selects_first(self):
        """Test that loading GPX auto-selects first track."""
        manager = TrackManager()
        gpx = gpxpy.gpx.GPX()
        
        track = gpxpy.gpx.GPXTrack()
        track.name = "First Track"
        segment = gpxpy.gpx.GPXTrackSegment()
        segment.points.append(gpxpy.gpx.GPXTrackPoint(57.5, 17.2))
        track.segments.append(segment)
        gpx.tracks.append(track)
        
        manager.load_from_gpx(gpx)
        
        assert manager.selected_track_index == 0
    
    def test_load_from_gpx_preserves_file_path(self):
        """Test that load_from_gpx stores the file path."""
        manager = TrackManager()
        gpx = gpxpy.gpx.GPX()
        
        track = gpxpy.gpx.GPXTrack()
        segment = gpxpy.gpx.GPXTrackSegment()
        segment.points.append(gpxpy.gpx.GPXTrackPoint(57.5, 17.2))
        track.segments.append(segment)
        gpx.tracks.append(track)
        
        manager.load_from_gpx(gpx, "/path/to/file.gpx")
        
        assert manager.gpx_file_path == "/path/to/file.gpx"
    
    def test_load_from_gpx_with_elevation_and_time(self):
        """Test loading track with elevation and time data."""
        manager = TrackManager()
        gpx = gpxpy.gpx.GPX()
        
        track = gpxpy.gpx.GPXTrack()
        track.name = "Track with Data"
        segment = gpxpy.gpx.GPXTrackSegment()
        
        point = gpxpy.gpx.GPXTrackPoint(57.5, 17.2)
        point.elevation = 25.0
        point.time = datetime(2023, 6, 15, 10, 30, 0)
        segment.points.append(point)
        
        point2 = gpxpy.gpx.GPXTrackPoint(57.6, 17.3)
        point2.elevation = 26.0
        point2.time = datetime(2023, 6, 15, 10, 31, 0)
        segment.points.append(point2)
        
        track.segments.append(segment)
        gpx.tracks.append(track)
        
        manager.load_from_gpx(gpx)
        
        track_data = manager.tracks[0]
        assert track_data.has_elevation is True
        assert track_data.has_time is True
    
    def test_clear_manager(self):
        """Test clearing manager state."""
        manager = TrackManager()
        gpx = gpxpy.gpx.GPX()
        
        track = gpxpy.gpx.GPXTrack()
        track.name = "Track"
        segment = gpxpy.gpx.GPXTrackSegment()
        segment.points.append(gpxpy.gpx.GPXTrackPoint(57.5, 17.2))
        track.segments.append(segment)
        gpx.tracks.append(track)
        
        manager.load_from_gpx(gpx, "/path/to/file.gpx")
        assert len(manager.tracks) == 1
        
        manager.clear()
        
        assert len(manager.tracks) == 0
        assert manager.selected_track_index == -1
        assert manager.gpx_file_path is None


# ============================================================================
# TrackManager - Selection
# ============================================================================

class TestTrackManagerSelection:
    """Tests for track selection functionality."""
    
    @pytest.fixture
    def manager_with_tracks(self):
        """Create manager with 3 sample tracks."""
        manager = TrackManager()
        gpx = gpxpy.gpx.GPX()
        
        for i in range(3):
            track = gpxpy.gpx.GPXTrack()
            track.name = f"Track {i}"
            segment = gpxpy.gpx.GPXTrackSegment()
            segment.points.append(gpxpy.gpx.GPXTrackPoint(57.5 + i, 17.2))
            segment.points.append(gpxpy.gpx.GPXTrackPoint(57.6 + i, 17.3))
            track.segments.append(segment)
            gpx.tracks.append(track)
        
        manager.load_from_gpx(gpx)
        return manager
    
    def test_select_track_valid(self, manager_with_tracks):
        """Test selecting a valid track."""
        manager = manager_with_tracks
        
        result = manager.select_track(1)
        
        assert result is True
        assert manager.selected_track_index == 1
    
    def test_select_track_invalid_negative(self, manager_with_tracks):
        """Test selecting with negative index."""
        manager = manager_with_tracks
        
        result = manager.select_track(-1)
        
        assert result is False
    
    def test_select_track_invalid_out_of_range(self, manager_with_tracks):
        """Test selecting index out of range."""
        manager = manager_with_tracks
        
        result = manager.select_track(10)
        
        assert result is False
    
    def test_get_selected_track_index(self, manager_with_tracks):
        """Test getting selected track index."""
        manager = manager_with_tracks
        manager.select_track(2)
        
        assert manager.get_selected_track_index() == 2
    
    def test_is_track_selected_true(self, manager_with_tracks):
        """Test is_track_selected when track is selected."""
        manager = manager_with_tracks
        manager.select_track(0)
        
        assert manager.is_track_selected() is True
    
    def test_is_track_selected_false(self, manager_with_tracks):
        """Test is_track_selected when no track selected."""
        manager = manager_with_tracks
        manager.selected_track_index = -1
        
        assert manager.is_track_selected() is False
    
    def test_get_selected_track_valid(self, manager_with_tracks):
        """Test getting selected track object."""
        manager = manager_with_tracks
        manager.select_track(1)
        
        track = manager.get_selected_track()
        
        assert track is not None
        assert track.name == "Track 1"
    
    def test_get_selected_track_none(self, manager_with_tracks):
        """Test getting selected track when none selected."""
        manager = manager_with_tracks
        manager.selected_track_index = -1
        
        track = manager.get_selected_track()
        
        assert track is None


# ============================================================================
# TrackManager - Information Queries
# ============================================================================

class TestTrackManagerQueries:
    """Tests for track information queries."""
    
    @pytest.fixture
    def manager_with_tracks(self):
        """Create manager with sample tracks."""
        manager = TrackManager()
        gpx = gpxpy.gpx.GPX()
        
        for i in range(2):
            track = gpxpy.gpx.GPXTrack()
            track.name = f"Track {i}"
            segment = gpxpy.gpx.GPXTrackSegment()
            segment.points.append(gpxpy.gpx.GPXTrackPoint(57.5 + i, 17.2))
            segment.points.append(gpxpy.gpx.GPXTrackPoint(57.6 + i, 17.3))
            track.segments.append(segment)
            gpx.tracks.append(track)
        
        manager.load_from_gpx(gpx)
        return manager
    
    def test_get_all_tracks(self, manager_with_tracks):
        """Test getting all tracks."""
        manager = manager_with_tracks
        
        tracks = manager.get_all_tracks()
        
        assert len(tracks) == 2
        assert tracks[0].name == "Track 0"
        assert tracks[1].name == "Track 1"
    
    def test_get_track_count(self, manager_with_tracks):
        """Test getting track count."""
        manager = manager_with_tracks
        
        count = manager.get_track_count()
        
        assert count == 2
    
    def test_get_track_by_index_valid(self, manager_with_tracks):
        """Test getting track by valid index."""
        manager = manager_with_tracks
        
        track = manager.get_track_by_index(0)
        
        assert track is not None
        assert track.name == "Track 0"
    
    def test_get_track_by_index_invalid(self, manager_with_tracks):
        """Test getting track by invalid index."""
        manager = manager_with_tracks
        
        track = manager.get_track_by_index(10)
        
        assert track is None
    
    def test_get_selected_track_info(self, manager_with_tracks):
        """Test getting selected track info."""
        manager = manager_with_tracks
        manager.select_track(0)
        
        info = manager.get_selected_track_info()
        
        assert info is not None
        assert info['name'] == "Track 0"
        assert info['point_count'] == 2
        assert 'distance_km' in info
        assert 'segment_count' in info
    
    def test_get_selected_track_info_none_selected(self, manager_with_tracks):
        """Test getting track info when no track selected."""
        manager = manager_with_tracks
        manager.selected_track_index = -1
        
        info = manager.get_selected_track_info()
        
        assert info is None
    
    def test_get_track_info_by_index(self, manager_with_tracks):
        """Test getting track info by index."""
        manager = manager_with_tracks
        
        info = manager.get_track_info(1)
        
        assert info is not None
        assert info['name'] == "Track 1"
        assert info['point_count'] == 2
    
    def test_get_track_info_invalid_index(self, manager_with_tracks):
        """Test getting track info with invalid index."""
        manager = manager_with_tracks
        
        info = manager.get_track_info(10)
        
        assert info is None


# ============================================================================
# TrackManager - Operations
# ============================================================================

class TestTrackManagerOperations:
    """Tests for track operations (rename, recalculate distance)."""
    
    @pytest.fixture
    def manager_with_tracks(self):
        """Create manager with sample tracks."""
        manager = TrackManager()
        gpx = gpxpy.gpx.GPX()
        
        track = gpxpy.gpx.GPXTrack()
        track.name = "Original Track"
        segment = gpxpy.gpx.GPXTrackSegment()
        segment.points.append(gpxpy.gpx.GPXTrackPoint(57.5, 17.2))
        segment.points.append(gpxpy.gpx.GPXTrackPoint(57.6, 17.3))
        track.segments.append(segment)
        gpx.tracks.append(track)
        
        manager.load_from_gpx(gpx)
        return manager
    
    def test_rename_track_valid(self, manager_with_tracks):
        """Test renaming a track by index."""
        manager = manager_with_tracks
        
        result = manager.rename_track(0, "New Track Name")
        
        assert result is True
        assert manager.tracks[0].name == "New Track Name"
        assert manager.tracks[0].is_dirty is True
    
    def test_rename_track_invalid_index(self, manager_with_tracks):
        """Test renaming with invalid index."""
        manager = manager_with_tracks
        
        result = manager.rename_track(10, "New Name")
        
        assert result is False
    
    def test_rename_selected_track_valid(self, manager_with_tracks):
        """Test renaming selected track."""
        manager = manager_with_tracks
        manager.select_track(0)
        
        result = manager.rename_selected_track("Updated Name")
        
        assert result is True
        assert manager.get_selected_track().name == "Updated Name"
    
    def test_rename_selected_track_none_selected(self, manager_with_tracks):
        """Test renaming when no track selected."""
        manager = manager_with_tracks
        manager.selected_track_index = -1
        
        result = manager.rename_selected_track("New Name")
        
        assert result is False
    
    def test_recalculate_distance(self, manager_with_tracks):
        """Test recalculating distance for a track."""
        manager = manager_with_tracks
        old_distance = manager.tracks[0].distance_km
        
        new_distance = manager.recalculate_distance(0)
        
        assert new_distance is not None
        assert isinstance(new_distance, float)
        # Distance should be recalculated
        assert manager.tracks[0].is_dirty is True
    
    def test_recalculate_distance_invalid_index(self, manager_with_tracks):
        """Test recalculating distance with invalid index."""
        manager = manager_with_tracks
        
        result = manager.recalculate_distance(10)
        
        assert result is None
    
    def test_recalculate_selected_distance(self, manager_with_tracks):
        """Test recalculating distance for selected track."""
        manager = manager_with_tracks
        manager.select_track(0)
        
        new_distance = manager.recalculate_selected_distance()
        
        assert new_distance is not None
        assert isinstance(new_distance, float)
    
    def test_recalculate_selected_distance_none_selected(self, manager_with_tracks):
        """Test recalculating distance when no track selected."""
        manager = manager_with_tracks
        manager.selected_track_index = -1
        
        result = manager.recalculate_selected_distance()
        
        assert result is None


# ============================================================================
# TrackManager - Trackpoint Access
# ============================================================================

class TestTrackManagerTrackpoints:
    """Tests for trackpoint access."""
    
    @pytest.fixture
    def manager_with_tracks(self):
        """Create manager with sample tracks."""
        manager = TrackManager()
        gpx = gpxpy.gpx.GPX()
        
        track = gpxpy.gpx.GPXTrack()
        track.name = "Test Track"
        segment = gpxpy.gpx.GPXTrackSegment()
        for i in range(5):
            segment.points.append(gpxpy.gpx.GPXTrackPoint(57.5 + i * 0.1, 17.2 + i * 0.1))
        track.segments.append(segment)
        gpx.tracks.append(track)
        
        manager.load_from_gpx(gpx)
        return manager
    
    def test_get_trackpoints_valid(self, manager_with_tracks):
        """Test getting trackpoints for valid track."""
        manager = manager_with_tracks
        
        points = manager.get_trackpoints(0)
        
        assert points is not None
        assert len(points) == 5
        assert isinstance(points[0], Trackpoint)
    
    def test_get_trackpoints_invalid_index(self, manager_with_tracks):
        """Test getting trackpoints for invalid track."""
        manager = manager_with_tracks
        
        points = manager.get_trackpoints(10)
        
        assert points is None
    
    def test_get_selected_trackpoints(self, manager_with_tracks):
        """Test getting trackpoints for selected track."""
        manager = manager_with_tracks
        manager.select_track(0)
        
        points = manager.get_selected_trackpoints()
        
        assert points is not None
        assert len(points) == 5
    
    def test_get_selected_trackpoints_none_selected(self, manager_with_tracks):
        """Test getting trackpoints when no track selected."""
        manager = manager_with_tracks
        manager.selected_track_index = -1
        
        points = manager.get_selected_trackpoints()
        
        assert points is None
    
    def test_get_trackpoint_valid(self, manager_with_tracks):
        """Test getting single trackpoint."""
        manager = manager_with_tracks
        
        point = manager.get_trackpoint(0, 2)
        
        assert point is not None
        assert isinstance(point, Trackpoint)
        assert point.index == 2
    
    def test_get_trackpoint_invalid_track_index(self, manager_with_tracks):
        """Test getting trackpoint with invalid track index."""
        manager = manager_with_tracks
        
        point = manager.get_trackpoint(10, 0)
        
        assert point is None
    
    def test_get_trackpoint_invalid_point_index(self, manager_with_tracks):
        """Test getting trackpoint with invalid point index."""
        manager = manager_with_tracks
        
        point = manager.get_trackpoint(0, 100)
        
        assert point is None


# ============================================================================
# TrackManager - Dirty State
# ============================================================================

class TestTrackManagerDirtyState:
    """Tests for dirty state management."""
    
    @pytest.fixture
    def manager_with_tracks(self):
        """Create manager with sample tracks."""
        manager = TrackManager()
        gpx = gpxpy.gpx.GPX()
        
        for i in range(2):
            track = gpxpy.gpx.GPXTrack()
            track.name = f"Track {i}"
            segment = gpxpy.gpx.GPXTrackSegment()
            segment.points.append(gpxpy.gpx.GPXTrackPoint(57.5 + i, 17.2))
            segment.points.append(gpxpy.gpx.GPXTrackPoint(57.6 + i, 17.3))
            track.segments.append(segment)
            gpx.tracks.append(track)
        
        manager.load_from_gpx(gpx)
        return manager
    
    def test_is_any_track_dirty_false(self, manager_with_tracks):
        """Test is_any_track_dirty when all clean."""
        manager = manager_with_tracks
        
        result = manager.is_any_track_dirty()
        
        assert result is False
    
    def test_is_any_track_dirty_true(self, manager_with_tracks):
        """Test is_any_track_dirty when at least one is dirty."""
        manager = manager_with_tracks
        manager.tracks[0].mark_dirty()
        
        result = manager.is_any_track_dirty()
        
        assert result is True
    
    def test_is_track_dirty_false(self, manager_with_tracks):
        """Test is_track_dirty when clean."""
        manager = manager_with_tracks
        
        result = manager.is_track_dirty(0)
        
        assert result is False
    
    def test_is_track_dirty_true(self, manager_with_tracks):
        """Test is_track_dirty when dirty."""
        manager = manager_with_tracks
        manager.tracks[0].mark_dirty()
        
        result = manager.is_track_dirty(0)
        
        assert result is True
    
    def test_is_track_dirty_invalid_index(self, manager_with_tracks):
        """Test is_track_dirty with invalid index."""
        manager = manager_with_tracks
        
        result = manager.is_track_dirty(10)
        
        assert result is False
    
    def test_is_selected_track_dirty_true(self, manager_with_tracks):
        """Test is_selected_track_dirty when selected track is dirty."""
        manager = manager_with_tracks
        manager.select_track(0)
        manager.tracks[0].mark_dirty()
        
        result = manager.is_selected_track_dirty()
        
        assert result is True
    
    def test_is_selected_track_dirty_false(self, manager_with_tracks):
        """Test is_selected_track_dirty when selected track is clean."""
        manager = manager_with_tracks
        manager.select_track(0)
        
        result = manager.is_selected_track_dirty()
        
        assert result is False
    
    def test_is_selected_track_dirty_none_selected(self, manager_with_tracks):
        """Test is_selected_track_dirty when no track selected."""
        manager = manager_with_tracks
        manager.selected_track_index = -1
        
        result = manager.is_selected_track_dirty()
        
        assert result is False
    
    def test_mark_clean(self, manager_with_tracks):
        """Test marking track as clean."""
        manager = manager_with_tracks
        manager.tracks[0].mark_dirty()
        assert manager.tracks[0].is_dirty is True
        
        result = manager.mark_clean(0)
        
        assert result is True
        assert manager.tracks[0].is_dirty is False
    
    def test_mark_clean_invalid_index(self, manager_with_tracks):
        """Test marking invalid track as clean."""
        manager = manager_with_tracks
        
        result = manager.mark_clean(10)
        
        assert result is False
    
    def test_mark_clean_all(self, manager_with_tracks):
        """Test marking all tracks as clean."""
        manager = manager_with_tracks
        manager.tracks[0].mark_dirty()
        manager.tracks[1].mark_dirty()
        
        manager.mark_clean_all()
        
        assert manager.tracks[0].is_dirty is False
        assert manager.tracks[1].is_dirty is False


# ============================================================================
# Module-Level Utilities
# ============================================================================

class TestCreateTrackpointFromGpxPoint:
    """Tests for create_trackpoint_from_gpx_point utility."""
    
    def test_create_from_gpx_point_basic(self):
        """Test creating trackpoint from GPX point."""
        gpx_point = gpxpy.gpx.GPXTrackPoint(57.5126, 17.2456)
        
        point = create_trackpoint_from_gpx_point(gpx_point, 0)
        
        assert point.latitude == 57.5126
        assert point.longitude == 17.2456
        assert point.elevation is None
        assert point.timestamp is None
    
    def test_create_from_gpx_point_with_data(self):
        """Test creating trackpoint from GPX point with elevation and time."""
        gpx_point = gpxpy.gpx.GPXTrackPoint(57.5126, 17.2456)
        gpx_point.elevation = 25.0
        gpx_point.time = datetime(2023, 6, 15, 10, 30, 0)
        
        point = create_trackpoint_from_gpx_point(gpx_point, 5)
        
        assert point.latitude == 57.5126
        assert point.longitude == 17.2456
        assert point.elevation == 25.0
        assert point.timestamp == "2023-06-15T10:30:00"
        assert point.index == 5
    
    def test_create_from_gpx_point_invalid_coordinates(self):
        """Test creating trackpoint with invalid coordinates."""
        gpx_point = gpxpy.gpx.GPXTrackPoint(91.0, 17.2456)  # Invalid latitude
        
        with pytest.raises(ValueError):
            create_trackpoint_from_gpx_point(gpx_point, 0)


# ============================================================================
# Integration Tests
# ============================================================================

class TestTrackManagerIntegration:
    """Integration tests for complete workflows."""
    
    def test_workflow_load_select_query(self):
        """Test workflow: load tracks, select one, query info."""
        manager = TrackManager()
        gpx = gpxpy.gpx.GPX()
        
        track = gpxpy.gpx.GPXTrack()
        track.name = "Integration Track"
        segment = gpxpy.gpx.GPXTrackSegment()
        segment.points.append(gpxpy.gpx.GPXTrackPoint(57.5, 17.2))
        segment.points.append(gpxpy.gpx.GPXTrackPoint(57.6, 17.3))
        track.segments.append(segment)
        gpx.tracks.append(track)
        
        # Load and verify
        count = manager.load_from_gpx(gpx)
        assert count == 1
        
        # Get info
        info = manager.get_selected_track_info()
        assert info['name'] == "Integration Track"
        assert info['point_count'] == 2
        
        # Get trackpoints
        points = manager.get_selected_trackpoints()
        assert len(points) == 2
    
    def test_workflow_load_rename_check_dirty(self):
        """Test workflow: load, rename, check dirty state."""
        manager = TrackManager()
        gpx = gpxpy.gpx.GPX()
        
        track = gpxpy.gpx.GPXTrack()
        track.name = "Original"
        segment = gpxpy.gpx.GPXTrackSegment()
        segment.points.append(gpxpy.gpx.GPXTrackPoint(57.5, 17.2))
        track.segments.append(segment)
        gpx.tracks.append(track)
        
        manager.load_from_gpx(gpx)
        
        # Initially clean
        assert manager.is_any_track_dirty() is False
        
        # Rename
        manager.rename_selected_track("Modified")
        
        # Now dirty
        assert manager.is_any_track_dirty() is True
        
        # Mark clean
        manager.mark_clean_all()
        assert manager.is_any_track_dirty() is False


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
