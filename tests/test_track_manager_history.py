"""Unit tests for TrackManager with integrated CommandHistory."""

import pytest
from src.core.track_manager import TrackManager
from src.core.gpx_handler import GPXHandler


class TestTrackManagerWithHistory:
    """Test TrackManager with command history enabled."""
    
    @pytest.fixture
    def manager_with_history(self):
        """Create TrackManager with history enabled."""
        
        handler = GPXHandler()
        gpx = handler.load_gpx('tests/gpx/Karlskrona-Hallarum.gpx')
        
        manager = TrackManager(use_history=True)
        manager.load_from_gpx(gpx)
        manager.select_track(0)
        
        return manager
    
    @pytest.fixture
    def manager_without_history(self):
        """Create TrackManager with history disabled."""
        
        handler = GPXHandler()
        gpx = handler.load_gpx('tests/gpx/Karlskrona-Hallarum.gpx')
        
        manager = TrackManager(use_history=False)
        manager.load_from_gpx(gpx)
        manager.select_track(0)
        
        return manager
    
    def test_manager_initialization_with_history(self):
        """Test TrackManager initializes with history."""
        
        manager = TrackManager(use_history=True)
        
        assert manager.use_history is True
        assert manager.history is not None
        assert manager.can_undo() is False
        assert manager.can_redo() is False
    
    def test_manager_initialization_without_history(self):
        """Test TrackManager initializes without history."""
        
        manager = TrackManager(use_history=False)
        
        assert manager.use_history is False
        assert manager.history is None
    
    def test_rename_track_with_history(self, manager_with_history):
        """Test renaming track with history."""
        
        original_name = manager_with_history.get_track_by_index(0).name
        
        success = manager_with_history.rename_track_with_history(0, "New Name")
        
        assert success is True
        assert manager_with_history.get_track_by_index(0).name == "New Name"
        assert manager_with_history.can_undo() is True
    
    def test_rename_track_without_history(self, manager_without_history):
        """Test renaming with history disabled returns False."""
        
        success = manager_without_history.rename_track_with_history(0, "New Name")
        
        assert success is False
    
    def test_add_trackpoint_with_history(self, manager_with_history):
        """Test adding trackpoint with history."""
        
        initial_count = manager_with_history.get_selected_track().get_point_count()
        
        success = manager_with_history.add_trackpoint_selected_with_history(57.5, 12.5)
        
        assert success is True
        assert manager_with_history.get_selected_track().get_point_count() == initial_count + 1
        assert manager_with_history.can_undo() is True
    
    def test_remove_trackpoint_with_history(self, manager_with_history):
        """Test removing trackpoint with history."""
        
        initial_count = manager_with_history.get_selected_track().get_point_count()
        
        success = manager_with_history.remove_trackpoint_selected_with_history(5)
        
        assert success is True
        assert manager_with_history.get_selected_track().get_point_count() == initial_count - 1
        assert manager_with_history.can_undo() is True
    
    def test_undo_rename(self, manager_with_history):
        """Test undoing a rename."""
        
        original_name = manager_with_history.get_track_by_index(0).name
        
        manager_with_history.rename_track_with_history(0, "New Name")
        assert manager_with_history.get_track_by_index(0).name == "New Name"
        
        success = manager_with_history.undo()
        
        assert success is True
        assert manager_with_history.get_track_by_index(0).name == original_name
        assert manager_with_history.can_undo() is False
        assert manager_with_history.can_redo() is True
    
    def test_undo_add_trackpoint(self, manager_with_history):
        """Test undoing add trackpoint."""
        
        initial_count = manager_with_history.get_selected_track().get_point_count()
        
        manager_with_history.add_trackpoint_selected_with_history(57.5, 12.5)
        assert manager_with_history.get_selected_track().get_point_count() == initial_count + 1
        
        success = manager_with_history.undo()
        
        assert success is True
        assert manager_with_history.get_selected_track().get_point_count() == initial_count
    
    def test_undo_remove_trackpoint(self, manager_with_history):
        """Test undoing remove trackpoint."""
        
        initial_count = manager_with_history.get_selected_track().get_point_count()
        original_point = manager_with_history.get_selected_track().trackpoints[5]
        
        manager_with_history.remove_trackpoint_selected_with_history(5)
        assert manager_with_history.get_selected_track().get_point_count() == initial_count - 1
        
        success = manager_with_history.undo()
        
        assert success is True
        assert manager_with_history.get_selected_track().get_point_count() == initial_count
        
        # Verify point was restored
        restored_point = manager_with_history.get_selected_track().trackpoints[5]
        assert abs(restored_point.latitude - original_point.latitude) < 0.0001
    
    def test_redo_rename(self, manager_with_history):
        """Test redoing a rename."""
        
        manager_with_history.rename_track_with_history(0, "New Name")
        manager_with_history.undo()
        
        success = manager_with_history.redo()
        
        assert success is True
        assert manager_with_history.get_track_by_index(0).name == "New Name"
        assert manager_with_history.can_undo() is True
        assert manager_with_history.can_redo() is False
    
    def test_redo_add_trackpoint(self, manager_with_history):
        """Test redoing add trackpoint."""
        
        initial_count = manager_with_history.get_selected_track().get_point_count()
        
        manager_with_history.add_trackpoint_selected_with_history(57.5, 12.5)
        manager_with_history.undo()
        
        assert manager_with_history.get_selected_track().get_point_count() == initial_count
        
        success = manager_with_history.redo()
        
        assert success is True
        assert manager_with_history.get_selected_track().get_point_count() == initial_count + 1
    
    def test_multiple_undo_redo_sequence(self, manager_with_history):
        """Test complex undo/redo sequence."""
        
        original_name = manager_with_history.get_track_by_index(0).name
        initial_count = manager_with_history.get_selected_track().get_point_count()
        
        # Execute 3 operations
        manager_with_history.rename_track_with_history(0, "Name1")
        manager_with_history.add_trackpoint_selected_with_history(57.5, 12.5)
        manager_with_history.remove_trackpoint_selected_with_history(5)
        
        # Verify state after operations
        assert manager_with_history.get_track_by_index(0).name == "Name1"
        assert manager_with_history.get_selected_track().get_point_count() == initial_count
        
        # Undo all 3
        manager_with_history.undo()
        assert manager_with_history.get_selected_track().get_point_count() == initial_count + 1
        
        manager_with_history.undo()
        assert manager_with_history.get_selected_track().get_point_count() == initial_count
        
        manager_with_history.undo()
        assert manager_with_history.get_track_by_index(0).name == original_name
        
        # Verify all are redoable
        assert manager_with_history.can_redo() is True
        
        # Redo 2 operations
        manager_with_history.redo()
        manager_with_history.redo()
        
        assert manager_with_history.get_track_by_index(0).name == "Name1"
        assert manager_with_history.get_selected_track().get_point_count() == initial_count + 1
        assert manager_with_history.can_undo() is True
        assert manager_with_history.can_redo() is True
    
    def test_can_undo_can_redo_queries(self, manager_with_history):
        """Test can_undo() and can_redo() queries."""
        
        assert manager_with_history.can_undo() is False
        assert manager_with_history.can_redo() is False
        
        manager_with_history.rename_track_with_history(0, "New Name")
        
        assert manager_with_history.can_undo() is True
        assert manager_with_history.can_redo() is False
        
        manager_with_history.undo()
        
        assert manager_with_history.can_undo() is False
        assert manager_with_history.can_redo() is True
    
    def test_get_undo_description(self, manager_with_history):
        """Test getting undo description."""
        
        desc = manager_with_history.get_undo_description()
        assert "Undo" in desc
        
        manager_with_history.rename_track_with_history(0, "New Name")
        
        desc = manager_with_history.get_undo_description()
        assert "Undo:" in desc
        assert "New Name" in desc
    
    def test_get_redo_description(self, manager_with_history):
        """Test getting redo description."""
        
        manager_with_history.rename_track_with_history(0, "New Name")
        manager_with_history.undo()
        
        desc = manager_with_history.get_redo_description()
        assert "Redo:" in desc
        assert "New Name" in desc
    
    def test_clear_history(self, manager_with_history):
        """Test clearing history."""
        
        manager_with_history.rename_track_with_history(0, "Name1")
        manager_with_history.undo()
        
        assert manager_with_history.can_undo() is False
        assert manager_with_history.can_redo() is True
        
        manager_with_history.clear_history()
        
        assert manager_with_history.can_undo() is False
        assert manager_with_history.can_redo() is False
    
    def test_remove_range_with_history(self, manager_with_history):
        """Test removing range with history."""
        
        initial_count = manager_with_history.get_selected_track().get_point_count()
        
        success = manager_with_history.remove_trackpoints_range_with_history(0, 2, 5)
        
        assert success is True
        # Removed 4 points (2, 3, 4, 5)
        assert manager_with_history.get_selected_track().get_point_count() == initial_count - 4
        assert manager_with_history.can_undo() is True
    
    def test_undo_remove_range(self, manager_with_history):
        """Test undoing range removal."""
        
        initial_count = manager_with_history.get_selected_track().get_point_count()
        
        manager_with_history.remove_trackpoints_range_with_history(0, 2, 5)
        
        success = manager_with_history.undo()
        
        assert success is True
        assert manager_with_history.get_selected_track().get_point_count() == initial_count
    
    def test_add_trackpoint_selected_with_history_no_track(self, manager_with_history):
        """Test adding with no track selected fails."""
        
        manager_with_history.selected_track_index = -1
        
        success = manager_with_history.add_trackpoint_selected_with_history(57.5, 12.5)
        
        assert success is False
    
    def test_remove_trackpoint_selected_with_history_no_track(self, manager_with_history):
        """Test removing with no track selected fails."""
        
        manager_with_history.selected_track_index = -1
        
        success = manager_with_history.remove_trackpoint_selected_with_history(5)
        
        assert success is False
    
    def test_undo_without_history_enabled(self, manager_without_history):
        """Test undo with history disabled."""
        
        success = manager_without_history.undo()
        
        assert success is False
    
    def test_redo_without_history_enabled(self, manager_without_history):
        """Test redo with history disabled."""
        
        success = manager_without_history.redo()
        
        assert success is False
    
    def test_get_descriptions_without_history(self, manager_without_history):
        """Test getting descriptions with history disabled."""
        
        undo_desc = manager_without_history.get_undo_description()
        redo_desc = manager_without_history.get_redo_description()
        
        assert undo_desc == "Undo"
        assert redo_desc == "Redo"
