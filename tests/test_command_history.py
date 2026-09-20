"""Unit tests for Command Pattern & History Stack."""

import pytest
from src.core.command_history import (
    CommandHistory, RenameTrackCommand, AddTrackpointCommand,
    RemoveTrackpointCommand, RemoveTrackpointRangeCommand
)
from src.core.track_manager import TrackManager
from src.core.gpx_handler import GPXHandler


class TestCommandHistory:
    """Test command history functionality."""
    
    @pytest.fixture
    def manager_with_history(self):
        """Create TrackManager with CommandHistory."""
        
        handler = GPXHandler()
        gpx = handler.load_gpx('tests/gpx/Karlskrona-Hallarum.gpx')
        
        manager = TrackManager()
        manager.load_from_gpx(gpx)
        manager.select_track(0)
        
        history = CommandHistory()
        
        return manager, history
    
    def test_execute_command(self, manager_with_history):
        """Test executing a command."""
        
        manager, history = manager_with_history
        
        cmd = RenameTrackCommand(manager, 0, "Old", "New")
        success = history.execute(cmd)
        
        assert success is True
        assert manager.get_track_by_index(0).name == "New"
        assert history.can_undo() is True
        assert history.can_redo() is False
    
    def test_undo_command(self, manager_with_history):
        """Test undoing a command."""
        
        manager, history = manager_with_history
        original_name = manager.get_track_by_index(0).name
        
        # Execute rename
        cmd = RenameTrackCommand(manager, 0, original_name, "New Name")
        history.execute(cmd)
        
        assert manager.get_track_by_index(0).name == "New Name"
        
        # Undo
        success = history.undo()
        
        assert success is True
        assert manager.get_track_by_index(0).name == original_name
        assert history.can_undo() is False
        assert history.can_redo() is True
    
    def test_redo_command(self, manager_with_history):
        """Test redoing a command."""
        
        manager, history = manager_with_history
        original_name = manager.get_track_by_index(0).name
        
        # Execute, undo, then redo
        cmd = RenameTrackCommand(manager, 0, original_name, "New Name")
        history.execute(cmd)
        history.undo()
        
        success = history.redo()
        
        assert success is True
        assert manager.get_track_by_index(0).name == "New Name"
        assert history.can_undo() is True
        assert history.can_redo() is False
    
    def test_redo_stack_cleared_on_new_command(self, manager_with_history):
        """Test that redo stack is cleared when new command executed."""
        
        manager, history = manager_with_history
        original_name = manager.get_track_by_index(0).name
        
        # Execute, undo
        cmd1 = RenameTrackCommand(manager, 0, original_name, "Name1")
        history.execute(cmd1)
        history.undo()
        
        assert history.can_redo() is True
        
        # Execute new command
        cmd2 = RenameTrackCommand(manager, 0, original_name, "Name2")
        history.execute(cmd2)
        
        # Redo stack should be cleared
        assert history.can_redo() is False
    
    def test_multiple_undo_redo(self, manager_with_history):
        """Test multiple undo/redo sequence."""
        
        manager, history = manager_with_history
        original_name = manager.get_track_by_index(0).name
        
        # Execute 3 commands
        cmd1 = RenameTrackCommand(manager, 0, original_name, "Name1")
        cmd2 = RenameTrackCommand(manager, 0, "Name1", "Name2")
        cmd3 = RenameTrackCommand(manager, 0, "Name2", "Name3")
        
        history.execute(cmd1)
        history.execute(cmd2)
        history.execute(cmd3)
        
        assert manager.get_track_by_index(0).name == "Name3"
        assert history.get_undo_stack_size() == 3
        
        # Undo 3 times
        history.undo()
        assert manager.get_track_by_index(0).name == "Name2"
        
        history.undo()
        assert manager.get_track_by_index(0).name == "Name1"
        
        history.undo()
        assert manager.get_track_by_index(0).name == original_name
        
        assert history.can_undo() is False
        assert history.get_redo_stack_size() == 3
        
        # Redo 2 times
        history.redo()
        assert manager.get_track_by_index(0).name == "Name1"
        
        history.redo()
        assert manager.get_track_by_index(0).name == "Name2"
        
        assert history.get_undo_stack_size() == 2
        assert history.get_redo_stack_size() == 1
    
    def test_can_undo_and_can_redo(self, manager_with_history):
        """Test can_undo() and can_redo() methods."""
        
        manager, history = manager_with_history
        
        assert history.can_undo() is False
        assert history.can_redo() is False
        
        cmd = RenameTrackCommand(manager, 0, "Old", "New")
        history.execute(cmd)
        
        assert history.can_undo() is True
        assert history.can_redo() is False
        
        history.undo()
        
        assert history.can_undo() is False
        assert history.can_redo() is True
    
    def test_get_descriptions(self, manager_with_history):
        """Test getting undo/redo descriptions."""
        
        manager, history = manager_with_history
        
        assert "Undo" in history.get_undo_description()
        assert "Redo" in history.get_redo_description()
        
        cmd = RenameTrackCommand(manager, 0, "Old", "New Name")
        history.execute(cmd)
        
        undo_desc = history.get_undo_description()
        assert "New Name" in undo_desc
        assert "Undo:" in undo_desc
    
    def test_clear_history(self, manager_with_history):
        """Test clearing history."""
        
        manager, history = manager_with_history
        
        cmd = RenameTrackCommand(manager, 0, "Old", "New")
        history.execute(cmd)
        history.undo()
        
        assert history.can_undo() is False
        assert history.can_redo() is True
        
        history.clear()
        
        assert history.can_undo() is False
        assert history.can_redo() is False


class TestRenameTrackCommand:
    """Test RenameTrackCommand."""
    
    @pytest.fixture
    def manager(self):
        """Create TrackManager with track."""
        
        handler = GPXHandler()
        gpx = handler.load_gpx('tests/gpx/Karlskrona-Hallarum.gpx')
        
        manager = TrackManager()
        manager.load_from_gpx(gpx)
        
        return manager
    
    def test_rename_track_execute(self, manager):
        """Test renaming a track."""
        
        original_name = manager.get_track_by_index(0).name
        cmd = RenameTrackCommand(manager, 0, original_name, "New Name")
        
        success = cmd.execute()
        
        assert success is True
        assert manager.get_track_by_index(0).name == "New Name"
        assert manager.get_track_by_index(0).is_dirty is True
    
    def test_rename_track_undo(self, manager):
        """Test undoing track rename."""
        
        original_name = manager.get_track_by_index(0).name
        cmd = RenameTrackCommand(manager, 0, original_name, "New Name")
        
        cmd.execute()
        success = cmd.undo()
        
        assert success is True
        assert manager.get_track_by_index(0).name == original_name
    
    def test_rename_invalid_track(self, manager):
        """Test renaming non-existent track."""
        
        cmd = RenameTrackCommand(manager, 999, "Old", "New")
        success = cmd.execute()
        
        assert success is False


class TestAddTrackpointCommand:
    """Test AddTrackpointCommand."""
    
    @pytest.fixture
    def manager(self):
        """Create TrackManager with track."""
        
        handler = GPXHandler()
        gpx = handler.load_gpx('tests/gpx/Karlskrona-Hallarum.gpx')
        
        manager = TrackManager()
        manager.load_from_gpx(gpx)
        manager.select_track(0)
        
        return manager
    
    def test_add_trackpoint_at_end(self, manager):
        """Test adding trackpoint at end."""
        
        initial_count = manager.get_selected_track().get_point_count()
        
        cmd = AddTrackpointCommand(manager, 0, 57.5, 12.5)
        success = cmd.execute()
        
        assert success is True
        assert manager.get_selected_track().get_point_count() == initial_count + 1
    
    def test_add_trackpoint_at_position(self, manager):
        """Test adding trackpoint at specific position."""
        
        cmd = AddTrackpointCommand(manager, 0, 57.5, 12.5, position=5)
        success = cmd.execute()
        
        assert success is True
        
        point = manager.get_selected_track().trackpoints[5]
        assert abs(point.latitude - 57.5) < 0.0001
        assert abs(point.longitude - 12.5) < 0.0001
    
    def test_add_trackpoint_undo(self, manager):
        """Test undoing trackpoint addition."""
        
        initial_count = manager.get_selected_track().get_point_count()
        
        cmd = AddTrackpointCommand(manager, 0, 57.5, 12.5)
        cmd.execute()
        
        assert manager.get_selected_track().get_point_count() == initial_count + 1
        
        success = cmd.undo()
        
        assert success is True
        assert manager.get_selected_track().get_point_count() == initial_count
    
    def test_add_trackpoint_with_elevation(self, manager):
        """Test adding trackpoint with elevation."""
        
        cmd = AddTrackpointCommand(manager, 0, 57.5, 12.5, altitude=42.5)
        success = cmd.execute()
        
        assert success is True
        
        last_point = manager.get_selected_track().trackpoints[-1]
        assert last_point.elevation == 42.5


class TestRemoveTrackpointCommand:
    """Test RemoveTrackpointCommand."""
    
    @pytest.fixture
    def manager(self):
        """Create TrackManager with track."""
        
        handler = GPXHandler()
        gpx = handler.load_gpx('tests/gpx/Karlskrona-Hallarum.gpx')
        
        manager = TrackManager()
        manager.load_from_gpx(gpx)
        manager.select_track(0)
        
        return manager
    
    def test_remove_trackpoint_execute(self, manager):
        """Test removing a trackpoint."""
        
        initial_count = manager.get_selected_track().get_point_count()
        
        cmd = RemoveTrackpointCommand(manager, 0, 5)
        success = cmd.execute()
        
        assert success is True
        assert manager.get_selected_track().get_point_count() == initial_count - 1
    
    def test_remove_trackpoint_undo(self, manager):
        """Test undoing trackpoint removal."""
        
        initial_count = manager.get_selected_track().get_point_count()
        original_point = manager.get_selected_track().trackpoints[5]
        
        cmd = RemoveTrackpointCommand(manager, 0, 5)
        cmd.execute()
        
        assert manager.get_selected_track().get_point_count() == initial_count - 1
        
        success = cmd.undo()
        
        assert success is True
        assert manager.get_selected_track().get_point_count() == initial_count
        
        # Verify the point was restored correctly
        restored_point = manager.get_selected_track().trackpoints[5]
        assert abs(restored_point.latitude - original_point.latitude) < 0.0001
        assert abs(restored_point.longitude - original_point.longitude) < 0.0001
    
    def test_remove_invalid_trackpoint(self, manager):
        """Test removing non-existent trackpoint."""
        
        cmd = RemoveTrackpointCommand(manager, 0, 999)
        success = cmd.execute()
        
        assert success is False


class TestRemoveTrackpointRangeCommand:
    """Test RemoveTrackpointRangeCommand."""
    
    @pytest.fixture
    def manager(self):
        """Create TrackManager with track."""
        
        handler = GPXHandler()
        gpx = handler.load_gpx('tests/gpx/Karlskrona-Hallarum.gpx')
        
        manager = TrackManager()
        manager.load_from_gpx(gpx)
        manager.select_track(0)
        
        return manager
    
    def test_remove_range_execute(self, manager):
        """Test removing a range of trackpoints."""
        
        initial_count = manager.get_selected_track().get_point_count()
        
        cmd = RemoveTrackpointRangeCommand(manager, 0, 2, 5)
        success = cmd.execute()
        
        assert success is True
        # Removed 4 points (2, 3, 4, 5)
        assert manager.get_selected_track().get_point_count() == initial_count - 4
    
    def test_remove_range_undo(self, manager):
        """Test undoing range removal."""
        
        initial_count = manager.get_selected_track().get_point_count()
        
        cmd = RemoveTrackpointRangeCommand(manager, 0, 2, 5)
        cmd.execute()
        
        assert manager.get_selected_track().get_point_count() == initial_count - 4
        
        success = cmd.undo()
        
        assert success is True
        assert manager.get_selected_track().get_point_count() == initial_count
    
    def test_remove_range_description(self, manager):
        """Test range command description."""
        
        cmd = RemoveTrackpointRangeCommand(manager, 0, 2, 5)
        
        description = cmd.description
        assert "Delete" in description
        assert "2" in description or "4" in description  # Should mention count or range
