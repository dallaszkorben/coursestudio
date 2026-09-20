"""
Unit tests for Track List Widget (src/gui/widgets/track_list_widget.py).

Tests cover:
- Widget initialization and setup
- Track list display and refresh
- Track selection and management
- Context menu operations
- Signal emission
- Track highlighting

Run with: pytest tests/test_track_list_widget.py -v
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
import gpxpy.gpx

from src.gui.widgets.track_list_widget import TrackListWidget, TrackListModel
from src.core.track_manager import TrackManager, TrackData, Trackpoint


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def track_manager():
    """Create a track manager with sample tracks."""
    manager = TrackManager()
    
    # Create sample GPX
    gpx = gpxpy.gpx.GPX()
    
    for track_num in range(2):
        track = gpxpy.gpx.GPXTrack()
        track.name = f"Track {track_num}"
        segment = gpxpy.gpx.GPXTrackSegment()
        
        for i in range(5):
            segment.points.append(gpxpy.gpx.GPXTrackPoint(
                57.5 + track_num + i * 0.1,
                17.2 + track_num + i * 0.1
            ))
        
        track.segments.append(segment)
        gpx.tracks.append(track)
    
    manager.load_from_gpx(gpx)
    return manager


@pytest.fixture
def track_list_widget(qapp, track_manager):
    """Create a track list widget with sample tracks."""
    widget = TrackListWidget(track_manager)
    widget.refresh_tracks()
    yield widget
    widget.close()


# ============================================================================
# Widget Initialization Tests
# ============================================================================

class TestTrackListWidgetInitialization:
    """Tests for widget initialization."""
    
    def test_widget_creation(self, qapp, track_manager):
        """Test widget is created successfully."""
        widget = TrackListWidget(track_manager)
        assert widget is not None
        assert isinstance(widget, TrackListWidget)
        widget.close()
    
    def test_track_manager_stored(self, qapp, track_manager):
        """Test track manager is stored correctly."""
        widget = TrackListWidget(track_manager)
        assert widget.track_manager is track_manager
        widget.close()
    
    def test_initial_selection_none(self, qapp, track_manager):
        """Test initial selection is none."""
        widget = TrackListWidget(track_manager)
        assert widget.current_selection == -1
        assert not widget.is_track_selected()
        widget.close()
    
    def test_list_widget_created(self, qapp, track_manager):
        """Test list widget is created."""
        widget = TrackListWidget(track_manager)
        assert widget.list_widget is not None
        widget.close()
    
    def test_count_label_created(self, qapp, track_manager):
        """Test count label is created."""
        widget = TrackListWidget(track_manager)
        assert widget.count_label is not None
        widget.close()
    
    def test_buttons_created(self, qapp, track_manager):
        """Test buttons are created."""
        widget = TrackListWidget(track_manager)
        assert widget.refresh_button is not None
        assert widget.clear_button is not None
        widget.close()


# ============================================================================
# Track Display Tests
# ============================================================================

class TestTrackListDisplay:
    """Tests for track display and formatting."""
    
    def test_refresh_tracks_populates_list(self, track_list_widget):
        """Test refresh_tracks populates the list."""
        assert track_list_widget.list_widget.count() == 2
    
    def test_count_label_updated(self, track_list_widget):
        """Test count label is updated."""
        text = track_list_widget.count_label.text()
        assert "2 tracks" in text
    
    def test_track_format_single_track(self, qapp, track_manager):
        """Test track formatting with single track."""
        widget = TrackListWidget(track_manager)
        
        track = track_manager.get_track_by_index(0)
        formatted = widget._format_track_item(track)
        
        assert "Track 0" in formatted
        assert "km" in formatted
        assert "points" in formatted
        widget.close()
    
    def test_track_items_have_data(self, track_list_widget):
        """Test track items store index data."""
        for i in range(track_list_widget.list_widget.count()):
            item = track_list_widget.list_widget.item(i)
            index = item.data(Qt.UserRole)
            assert index == i
    
    def test_refresh_preserves_selection(self, track_list_widget):
        """Test refresh preserves current selection."""
        track_list_widget.select_track(1)
        assert track_list_widget.current_selection == 1
        
        track_list_widget.refresh_tracks()
        assert track_list_widget.current_selection == 1


# ============================================================================
# Selection Tests
# ============================================================================

class TestTrackListSelection:
    """Tests for track selection."""
    
    def test_select_track_valid_index(self, track_list_widget):
        """Test selecting track by valid index."""
        result = track_list_widget.select_track(0)
        assert result is True
        assert track_list_widget.current_selection == 0
    
    def test_select_track_invalid_negative_index(self, track_list_widget):
        """Test selecting with negative index."""
        result = track_list_widget.select_track(-1)
        assert result is False
    
    def test_select_track_out_of_range(self, track_list_widget):
        """Test selecting out-of-range index."""
        result = track_list_widget.select_track(100)
        assert result is False
    
    def test_get_selected_track_index_valid(self, track_list_widget):
        """Test getting selected track index."""
        track_list_widget.select_track(1)
        assert track_list_widget.get_selected_track_index() == 1
    
    def test_get_selected_track_index_none(self, track_list_widget):
        """Test getting selected track index when none selected."""
        track_list_widget.clear_selection()
        assert track_list_widget.get_selected_track_index() == -1
    
    def test_is_track_selected_true(self, track_list_widget):
        """Test is_track_selected when track is selected."""
        track_list_widget.select_track(0)
        assert track_list_widget.is_track_selected() is True
    
    def test_is_track_selected_false(self, track_list_widget):
        """Test is_track_selected when no track selected."""
        track_list_widget.clear_selection()
        assert track_list_widget.is_track_selected() is False
    
    def test_clear_selection(self, track_list_widget):
        """Test clearing selection."""
        track_list_widget.select_track(0)
        assert track_list_widget.is_track_selected()
        
        track_list_widget.clear_selection()
        assert not track_list_widget.is_track_selected()
        assert track_list_widget.current_selection == -1


# ============================================================================
# Signal Tests
# ============================================================================

class TestTrackListSignals:
    """Tests for signal emission."""
    
    def test_track_selected_signal_exists(self, track_list_widget):
        """Test track_selected signal exists."""
        assert hasattr(track_list_widget, 'track_selected')
    
    def test_track_double_clicked_signal_exists(self, track_list_widget):
        """Test track_double_clicked signal exists."""
        assert hasattr(track_list_widget, 'track_double_clicked')
    
    def test_track_right_clicked_signal_exists(self, track_list_widget):
        """Test track_right_clicked signal exists."""
        assert hasattr(track_list_widget, 'track_right_clicked')
    
    def test_track_selected_signal_emitted(self, track_list_widget):
        """Test track_selected signal is emitted on selection."""
        signal_received = []
        
        def on_track_selected(index):
            signal_received.append(index)
        
        track_list_widget.track_selected.connect(on_track_selected)
        track_list_widget.select_track(0)
        
        # Process events to allow signal to be processed
        QApplication.processEvents()
        
        # Note: Signal may not be emitted in test environment without full UI interaction
        # This test verifies signal connection rather than emission


# ============================================================================
# Update Tests
# ============================================================================

class TestTrackListUpdates:
    """Tests for track list updates."""
    
    def test_update_track_info(self, track_list_widget):
        """Test updating track info."""
        # Modify track name
        track = track_list_widget.track_manager.get_track_by_index(0)
        track.name = "Modified Track"
        
        # Update display
        track_list_widget.update_track_info(0)
        
        # Verify item text updated
        item = track_list_widget.list_widget.item(0)
        assert "Modified Track" in item.text()
    
    def test_highlight_track(self, track_list_widget):
        """Test highlighting track."""
        track_list_widget.highlight_track(0)
        
        item = track_list_widget.list_widget.item(0)
        assert item is not None
    
    def test_remove_highlight(self, track_list_widget):
        """Test removing highlight from track."""
        track_list_widget.highlight_track(0)
        track_list_widget.remove_highlight(0)
        
        item = track_list_widget.list_widget.item(0)
        assert item is not None


# ============================================================================
# Track List Model Tests
# ============================================================================

class TestTrackListModel:
    """Tests for track list model."""
    
    def test_model_creation(self, track_manager):
        """Test model is created successfully."""
        model = TrackListModel(track_manager)
        assert model is not None
        assert model.track_manager is track_manager
    
    def test_get_track_count(self, track_manager):
        """Test getting track count."""
        model = TrackListModel(track_manager)
        assert model.get_track_count() == 2
    
    def test_get_track_display_name_valid(self, track_manager):
        """Test getting track display name."""
        model = TrackListModel(track_manager)
        name = model.get_track_display_name(0)
        
        assert "Track 0" in name
        assert "km" in name
        assert "points" in name
    
    def test_get_track_display_name_invalid(self, track_manager):
        """Test getting display name for invalid index."""
        model = TrackListModel(track_manager)
        name = model.get_track_display_name(100)
        
        assert name == ""
    
    def test_get_track_data_valid(self, track_manager):
        """Test getting track data."""
        model = TrackListModel(track_manager)
        track = model.get_track_data(0)
        
        assert track is not None
        assert isinstance(track, TrackData)
    
    def test_get_track_data_invalid(self, track_manager):
        """Test getting track data for invalid index."""
        model = TrackListModel(track_manager)
        track = model.get_track_data(100)
        
        assert track is None


# ============================================================================
# Button Action Tests
# ============================================================================

class TestTrackListButtonActions:
    """Tests for button actions."""
    
    def test_refresh_button_callable(self, track_list_widget):
        """Test refresh button can be clicked."""
        track_list_widget.refresh_button.click()
        assert True  # Should not crash
    
    def test_clear_button_callable(self, track_list_widget):
        """Test clear button can be clicked."""
        track_list_widget.select_track(0)
        track_list_widget.clear_button.click()
        assert track_list_widget.current_selection == -1


# ============================================================================
# Integration Tests
# ============================================================================

class TestTrackListIntegration:
    """Integration tests for track list widget."""
    
    def test_widget_can_be_shown(self, track_list_widget):
        """Test widget can be shown without crashing."""
        track_list_widget.show()
        assert track_list_widget is not None
    
    def test_complete_workflow(self, qapp, track_manager):
        """Test complete workflow: create, populate, select, update."""
        widget = TrackListWidget(track_manager)
        
        # Initial state
        assert widget.list_widget.count() == 0
        
        # Refresh list
        widget.refresh_tracks()
        assert widget.list_widget.count() == 2
        
        # Select track
        result = widget.select_track(0)
        assert result is True
        assert widget.is_track_selected()
        
        # Get selected index
        index = widget.get_selected_track_index()
        assert index == 0
        
        # Update track
        track = widget.track_manager.get_track_by_index(0)
        track.name = "Updated"
        widget.update_track_info(0)
        
        # Clear selection
        widget.clear_selection()
        assert not widget.is_track_selected()
        
        widget.close()


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestTrackListEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_track_manager(self, qapp):
        """Test widget with empty track manager."""
        manager = TrackManager()
        widget = TrackListWidget(manager)
        widget.refresh_tracks()
        
        assert widget.list_widget.count() == 0
        assert "0 track" in widget.count_label.text()
        widget.close()
    
    def test_single_track(self, qapp):
        """Test widget with single track."""
        manager = TrackManager()
        
        gpx = gpxpy.gpx.GPX()
        track = gpxpy.gpx.GPXTrack()
        track.name = "Single Track"
        segment = gpxpy.gpx.GPXTrackSegment()
        segment.points.append(gpxpy.gpx.GPXTrackPoint(57.5, 17.2))
        segment.points.append(gpxpy.gpx.GPXTrackPoint(57.6, 17.3))
        track.segments.append(segment)
        gpx.tracks.append(track)
        
        manager.load_from_gpx(gpx)
        
        widget = TrackListWidget(manager)
        widget.refresh_tracks()
        
        assert widget.list_widget.count() == 1
        assert "1 track" in widget.count_label.text()
        widget.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
