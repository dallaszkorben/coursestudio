"""Unit tests for add_trackpoint functionality."""

import pytest
from src.core.track_manager import TrackManager, Trackpoint, TrackData
from src.core.gpx_handler import GPXHandler


class TestAddTrackpoint:
    """Test adding trackpoints to tracks."""
    
    @pytest.fixture
    def manager(self):
        """Create a TrackManager with sample track."""
        
        handler = GPXHandler()
        gpx = handler.load_gpx('tests/gpx/Karlskrona-Hallarum.gpx')
        
        manager = TrackManager()
        manager.load_from_gpx(gpx)
        manager.select_track(0)
        
        return manager
    
    def test_add_trackpoint_at_end(self, manager):
        """Test adding a trackpoint at the end of track."""
        
        initial_count = manager.get_selected_track().get_point_count()
        
        success = manager.add_trackpoint_selected(
            latitude=57.5126,
            longitude=12.2584
        )
        
        assert success is True
        assert manager.get_selected_track().get_point_count() == initial_count + 1
    
    def test_add_trackpoint_at_specific_position(self, manager):
        """Test adding a trackpoint at a specific index."""
        
        initial_count = manager.get_selected_track().get_point_count()
        
        # Add at position 10
        success = manager.add_trackpoint_selected(
            latitude=57.5126,
            longitude=12.2584,
            position=10
        )
        
        assert success is True
        assert manager.get_selected_track().get_point_count() == initial_count + 1
        
        # Check that point was inserted at position 10
        inserted_point = manager.get_selected_track().trackpoints[10]
        assert abs(inserted_point.latitude - 57.5126) < 0.0001
        assert abs(inserted_point.longitude - 12.2584) < 0.0001
    
    def test_add_trackpoint_with_altitude(self, manager):
        """Test adding a trackpoint with altitude."""
        
        success = manager.add_trackpoint_selected(
            latitude=57.5126,
            longitude=12.2584,
            altitude=42.5
        )
        
        assert success is True
        
        # Check altitude was stored
        last_point = manager.get_selected_track().trackpoints[-1]
        assert last_point.elevation == 42.5
    
    def test_add_trackpoint_invalid_latitude(self, manager):
        """Test that invalid latitude is rejected."""
        
        # Latitude > 90
        success = manager.add_trackpoint_selected(
            latitude=91.0,
            longitude=12.2584
        )
        
        assert success is False
        
        # Latitude < -90
        success = manager.add_trackpoint_selected(
            latitude=-91.0,
            longitude=12.2584
        )
        
        assert success is False
    
    def test_add_trackpoint_invalid_longitude(self, manager):
        """Test that invalid longitude is rejected."""
        
        # Longitude > 180
        success = manager.add_trackpoint_selected(
            latitude=57.5126,
            longitude=181.0
        )
        
        assert success is False
        
        # Longitude < -180
        success = manager.add_trackpoint_selected(
            latitude=57.5126,
            longitude=-181.0
        )
        
        assert success is False
    
    def test_add_trackpoint_invalid_position(self, manager):
        """Test that invalid position is rejected."""
        
        track_count = manager.get_selected_track().get_point_count()
        
        # Position beyond track length
        success = manager.add_trackpoint_selected(
            latitude=57.5126,
            longitude=12.2584,
            position=track_count + 10
        )
        
        assert success is False
        
        # Negative position
        success = manager.add_trackpoint_selected(
            latitude=57.5126,
            longitude=12.2584,
            position=-1
        )
        
        assert success is False
    
    def test_add_trackpoint_distance_recalculated(self, manager):
        """Test that distance is recalculated after adding."""
        
        initial_distance = manager.get_selected_track().distance_km
        
        # Add a point far from the current track
        success = manager.add_trackpoint_selected(
            latitude=60.0,  # Much further north
            longitude=12.2584
        )
        
        assert success is True
        
        # Distance should have changed (increased)
        new_distance = manager.get_selected_track().distance_km
        assert new_distance > initial_distance
    
    def test_add_trackpoint_marks_dirty(self, manager):
        """Test that adding a trackpoint marks track as dirty."""
        
        manager.mark_clean(manager.get_selected_track_index())
        assert manager.is_selected_track_dirty() is False
        
        success = manager.add_trackpoint_selected(
            latitude=57.5126,
            longitude=12.2584
        )
        
        assert success is True
        assert manager.is_selected_track_dirty() is True
    
    def test_add_trackpoint_no_track_selected(self):
        """Test that adding to no selected track fails."""
        
        manager = TrackManager()
        # Don't select a track
        
        success = manager.add_trackpoint_selected(
            latitude=57.5126,
            longitude=12.2584
        )
        
        assert success is False
    
    def test_add_trackpoint_index_update(self, manager):
        """Test that indices are updated correctly after insertion."""
        
        track = manager.get_selected_track()
        initial_count = len(track.trackpoints)
        
        # Insert at position 5
        success = manager.add_trackpoint_selected(
            latitude=57.0,
            longitude=12.0,
            position=5
        )
        
        assert success is True
        
        # Check that the inserted point has index 5
        assert track.trackpoints[5].latitude == 57.0
        assert track.trackpoints[5].longitude == 12.0
        assert track.trackpoints[5].index == 5
        
        # Check that indices from position 6 onwards were updated
        for i in range(6, len(track.trackpoints)):
            assert track.trackpoints[i].index == i
    
    def test_add_multiple_trackpoints(self, manager):
        """Test adding multiple trackpoints in sequence."""
        
        initial_count = manager.get_selected_track().get_point_count()
        
        # Add 5 trackpoints
        for i in range(5):
            lat = 57.0 + i * 0.01
            lon = 12.0 + i * 0.01
            
            success = manager.add_trackpoint_selected(
                latitude=lat,
                longitude=lon,
                altitude=100 + i * 10
            )
            
            assert success is True
        
        assert manager.get_selected_track().get_point_count() == initial_count + 5
    
    def test_add_trackpoint_coordinate_types(self, manager):
        """Test that coordinate types are validated."""
        
        # Non-numeric latitude
        success = manager.add_trackpoint(
            track_index=0,
            latitude="57.5126",  # String instead of float
            longitude=12.2584
        )
        
        assert success is False
        
        # Non-numeric longitude
        success = manager.add_trackpoint(
            track_index=0,
            latitude=57.5126,
            longitude="12.2584"  # String instead of float
        )
        
        assert success is False
    
    def test_add_trackpoint_to_specific_track(self, manager):
        """Test adding trackpoint to a specific track by index."""
        
        track = manager.get_track_by_index(0)
        initial_count = track.get_point_count()
        
        success = manager.add_trackpoint(
            track_index=0,
            latitude=57.5126,
            longitude=12.2584
        )
        
        assert success is True
        assert track.get_point_count() == initial_count + 1
    
    def test_add_trackpoint_invalid_track_index(self, manager):
        """Test adding to an invalid track index."""
        
        # Invalid track index
        success = manager.add_trackpoint(
            track_index=999,
            latitude=57.5126,
            longitude=12.2584
        )
        
        assert success is False
        
        # Negative track index
        success = manager.add_trackpoint(
            track_index=-1,
            latitude=57.5126,
            longitude=12.2584
        )
        
        assert success is False
    
    def test_add_trackpoint_zero_altitude(self, manager):
        """Test that zero altitude is treated as elevation."""
        
        success = manager.add_trackpoint_selected(
            latitude=57.5126,
            longitude=12.2584,
            altitude=0
        )
        
        assert success is True
        
        # Check last point
        last_point = manager.get_selected_track().trackpoints[-1]
        # Elevation should be 0 (stored as provided)
        assert last_point.elevation == 0
    
    def test_add_trackpoint_boundary_coordinates(self, manager):
        """Test adding trackpoints at coordinate boundaries."""
        
        # North pole
        success = manager.add_trackpoint_selected(latitude=90.0, longitude=0.0)
        assert success is True
        
        # South pole
        success = manager.add_trackpoint_selected(latitude=-90.0, longitude=0.0)
        assert success is True
        
        # Dateline
        success = manager.add_trackpoint_selected(latitude=0.0, longitude=180.0)
        assert success is True
        
        # Dateline (negative)
        success = manager.add_trackpoint_selected(latitude=0.0, longitude=-180.0)
        assert success is True
        
        # Equator, Prime meridian
        success = manager.add_trackpoint_selected(latitude=0.0, longitude=0.0)
        assert success is True
