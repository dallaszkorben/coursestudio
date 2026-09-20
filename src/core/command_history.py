"""Command Pattern & History Stack for mangpx.

Implements the Command Pattern to support undo/redo functionality.
All track modifications are represented as reversible Command objects.

Classes:
    - Command: Abstract base class for all commands
    - RenameTrackCommand: Rename a track
    - AddTrackpointCommand: Add a trackpoint
    - RemoveTrackpointCommand: Remove a single trackpoint
    - RemoveTrackpointRangeCommand: Remove a range of trackpoints
    - CommandHistory: Manages undo/redo stacks

Example:
    >>> from src.core.command_history import CommandHistory, RenameTrackCommand
    >>> from src.core.track_manager import TrackManager
    >>> 
    >>> manager = TrackManager()
    >>> history = CommandHistory()
    >>> 
    >>> # Create and execute a command
    >>> cmd = RenameTrackCommand(manager, 0, "Old Name", "New Name")
    >>> history.execute(cmd)
    >>> 
    >>> # Undo the change
    >>> history.undo()
    >>> 
    >>> # Redo the change
    >>> history.redo()
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass

from src.core.track_manager import TrackManager, Trackpoint


logger = logging.getLogger(__name__)


# ============================================================================
# Abstract Command Base Class
# ============================================================================

class Command(ABC):
    """
    Abstract base class for all reversible commands.
    
    All command subclasses must implement execute() and undo() methods
    to support reversible operations.
    
    Example:
        >>> class MyCommand(Command):
        ...     def execute(self) -> bool:
        ...         # Perform operation
        ...         return True
        ...     
        ...     def undo(self) -> bool:
        ...         # Reverse operation
        ...         return True
        ...     
        ...     @property
        ...     def description(self) -> str:
        ...         return "My Operation"
    """
    
    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the command.
        
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """
        Reverse the command.
        
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Get human-readable description for undo/redo menu.
        
        Returns:
            str: Description like "Rename Track", "Delete Point"
        """
        pass


# ============================================================================
# Concrete Command Classes
# ============================================================================

class RenameTrackCommand(Command):
    """Command to rename a track."""
    
    def __init__(self, track_manager: TrackManager, track_index: int,
                 old_name: str, new_name: str):
        """
        Initialize rename command.
        
        Args:
            track_manager: TrackManager instance
            track_index: Index of track to rename
            old_name: Original track name
            new_name: New track name
        """
        self.track_manager = track_manager
        self.track_index = track_index
        self.old_name = old_name
        self.new_name = new_name
        self.executed = False
    
    def execute(self) -> bool:
        """Execute the rename command."""
        
        track = self.track_manager.get_track_by_index(self.track_index)
        if not track:
            logger.error(f"Track {self.track_index} not found")
            return False
        
        track.name = self.new_name
        track.is_dirty = True
        self.executed = True
        logger.info(f"Executed: Renamed track {self.track_index} from '{self.old_name}' to '{self.new_name}'")
        return True
    
    def undo(self) -> bool:
        """Undo the rename command."""
        
        track = self.track_manager.get_track_by_index(self.track_index)
        if not track:
            logger.error(f"Track {self.track_index} not found")
            return False
        
        track.name = self.old_name
        track.is_dirty = True
        self.executed = False
        logger.info(f"Undone: Renamed track {self.track_index} back to '{self.old_name}'")
        return True
    
    @property
    def description(self) -> str:
        """Get command description."""
        return f"Rename to '{self.new_name}'"


class AddTrackpointCommand(Command):
    """Command to add a trackpoint."""
    
    def __init__(self, track_manager: TrackManager, track_index: int,
                 latitude: float, longitude: float, altitude: Optional[float] = None,
                 position: Optional[int] = None):
        """
        Initialize add trackpoint command.
        
        Args:
            track_manager: TrackManager instance
            track_index: Index of track
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            altitude: Elevation in meters (optional)
            position: Insert position (None = append at end)
        """
        self.track_manager = track_manager
        self.track_index = track_index
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.position = position
        self.executed = False
    
    def execute(self) -> bool:
        """Execute the add trackpoint command."""
        
        success = self.track_manager.add_trackpoint(
            self.track_index, self.latitude, self.longitude,
            self.altitude, self.position
        )
        
        if success:
            self.executed = True
            logger.info(f"Executed: Added trackpoint at ({self.latitude}, {self.longitude})")
        else:
            logger.error(f"Failed to add trackpoint")
        
        return success
    
    def undo(self) -> bool:
        """Undo the add trackpoint command."""
        
        track = self.track_manager.get_track_by_index(self.track_index)
        if not track:
            logger.error(f"Track {self.track_index} not found")
            return False
        
        # Determine which point was added (it should be at the position we specified)
        if self.position is None:
            # It was added at the end
            point_index = len(track.trackpoints) - 1
        else:
            # It was added at the specified position
            point_index = self.position
        
        # Remove the point - returns the removed point if successful, None otherwise
        removed = self.track_manager.remove_trackpoint(self.track_index, point_index)
        
        if removed is not None:
            self.executed = False
            logger.info(f"Undone: Removed added trackpoint")
            return True
        else:
            logger.error(f"Failed to remove trackpoint during undo")
            return False
    
    @property
    def description(self) -> str:
        """Get command description."""
        return f"Add Point ({self.latitude:.4f}, {self.longitude:.4f})"


class RemoveTrackpointCommand(Command):
    """Command to remove a single trackpoint."""
    
    def __init__(self, track_manager: TrackManager, track_index: int, point_index: int):
        """
        Initialize remove trackpoint command.
        
        Args:
            track_manager: TrackManager instance
            track_index: Index of track
            point_index: Index of trackpoint to remove
        """
        self.track_manager = track_manager
        self.track_index = track_index
        self.point_index = point_index
        self.removed_point: Optional[Trackpoint] = None
        self.executed = False
    
    def execute(self) -> bool:
        """Execute the remove trackpoint command."""
        
        track = self.track_manager.get_track_by_index(self.track_index)
        if not track or self.point_index >= len(track.trackpoints):
            logger.error(f"Invalid track or point index")
            return False
        
        # Store the point before deletion
        self.removed_point = track.trackpoints[self.point_index]
        
        # Remove the point - it returns the removed point, not a boolean
        removed = self.track_manager.remove_trackpoint(self.track_index, self.point_index)
        
        if removed is not None:
            self.executed = True
            logger.info(f"Executed: Removed trackpoint at index {self.point_index}")
            return True
        else:
            logger.error("Failed to remove trackpoint")
            return False
    
    def undo(self) -> bool:
        """Undo the remove trackpoint command."""
        
        if not self.removed_point:
            logger.error("No stored point to restore")
            return False
        
        # Re-add the point at the same position
        success = self.track_manager.add_trackpoint(
            self.track_index,
            self.removed_point.latitude,
            self.removed_point.longitude,
            self.removed_point.elevation,
            self.point_index
        )
        
        if success:
            self.executed = False
            logger.info(f"Undone: Re-added trackpoint at index {self.point_index}")
        else:
            logger.error(f"Failed to re-add trackpoint during undo")
        
        return success
    
    @property
    def description(self) -> str:
        """Get command description."""
        return f"Delete Point ({self.removed_point.latitude:.4f}, {self.removed_point.longitude:.4f})" if self.removed_point else "Delete Point"


class RemoveTrackpointRangeCommand(Command):
    """Command to remove a range of trackpoints."""
    
    def __init__(self, track_manager: TrackManager, track_index: int,
                 start_index: int, end_index: int):
        """
        Initialize remove range command.
        
        Args:
            track_manager: TrackManager instance
            track_index: Index of track
            start_index: First index to remove (inclusive)
            end_index: Last index to remove (inclusive)
        """
        self.track_manager = track_manager
        self.track_index = track_index
        self.start_index = start_index
        self.end_index = end_index
        self.removed_points: List[Trackpoint] = []
        self.executed = False
    
    def execute(self) -> bool:
        """Execute the remove range command."""
        
        track = self.track_manager.get_track_by_index(self.track_index)
        if not track:
            logger.error(f"Track {self.track_index} not found")
            return False
        
        # Store the points before deletion
        self.removed_points = track.trackpoints[self.start_index:self.end_index + 1].copy()
        
        # Remove from end to start to maintain indices
        for i in range(self.end_index, self.start_index - 1, -1):
            success = self.track_manager.remove_trackpoint(self.track_index, i)
            if not success:
                logger.error(f"Failed to remove point at index {i}")
                return False
        
        self.executed = True
        logger.info(f"Executed: Removed {len(self.removed_points)} trackpoints ({self.start_index}-{self.end_index})")
        return True
    
    def undo(self) -> bool:
        """Undo the remove range command."""
        
        # Re-add the points at the same positions
        for i, point in enumerate(self.removed_points):
            success = self.track_manager.add_trackpoint(
                self.track_index,
                point.latitude,
                point.longitude,
                point.elevation,
                self.start_index + i
            )
            
            if not success:
                logger.error(f"Failed to re-add point during undo")
                return False
        
        self.executed = False
        logger.info(f"Undone: Re-added {len(self.removed_points)} trackpoints")
        return True
    
    @property
    def description(self) -> str:
        """Get command description."""
        return f"Delete {len(self.removed_points)} Points ({self.start_index}-{self.end_index})"


# ============================================================================
# Command History Manager
# ============================================================================

class CommandHistory:
    """
    Manages undo/redo stacks for reversible commands.
    
    Maintains separate stacks for undo and redo operations.
    When a new command is executed, the redo stack is cleared.
    
    Example:
        >>> history = CommandHistory()
        >>> cmd = MyCommand()
        >>> history.execute(cmd)
        >>> history.undo()
        >>> history.redo()
        >>> print(f"Can undo: {history.can_undo()}")
        >>> print(f"Can redo: {history.can_redo()}")
    """
    
    def __init__(self, max_size: int = 100):
        """
        Initialize command history.
        
        Args:
            max_size: Maximum number of commands to keep in history
        """
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        self.max_size = max_size
        logger.debug(f"CommandHistory initialized (max_size={max_size})")
    
    def execute(self, command: Command) -> bool:
        """
        Execute a command and add it to history.
        
        Args:
            command: Command to execute
        
        Returns:
            bool: True if successful, False otherwise
        """
        
        # Execute the command
        success = command.execute()
        
        if success:
            # Add to undo stack
            self.undo_stack.append(command)
            
            # Enforce max size
            if len(self.undo_stack) > self.max_size:
                self.undo_stack.pop(0)
            
            # Clear redo stack
            self.redo_stack.clear()
            
            logger.debug(f"Executed command: {command.description}")
        else:
            logger.warning(f"Command execution failed: {command.description}")
        
        return success
    
    def undo(self) -> bool:
        """
        Undo the last command.
        
        Returns:
            bool: True if successful, False otherwise
        """
        
        if not self.can_undo():
            logger.warning("Nothing to undo")
            return False
        
        # Pop from undo stack
        command = self.undo_stack.pop()
        
        # Execute undo
        success = command.undo()
        
        if success:
            # Add to redo stack
            self.redo_stack.append(command)
            logger.debug(f"Undone: {command.description}")
        else:
            # Restore to undo stack if undo failed
            self.undo_stack.append(command)
            logger.warning(f"Undo failed: {command.description}")
        
        return success
    
    def redo(self) -> bool:
        """
        Redo the last undone command.
        
        Returns:
            bool: True if successful, False otherwise
        """
        
        if not self.can_redo():
            logger.warning("Nothing to redo")
            return False
        
        # Pop from redo stack
        command = self.redo_stack.pop()
        
        # Execute command again
        success = command.execute()
        
        if success:
            # Add back to undo stack
            self.undo_stack.append(command)
            logger.debug(f"Redone: {command.description}")
        else:
            # Restore to redo stack if redo failed
            self.redo_stack.append(command)
            logger.warning(f"Redo failed: {command.description}")
        
        return success
    
    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is possible."""
        return len(self.redo_stack) > 0
    
    def get_undo_description(self) -> str:
        """Get description of next undo command."""
        if self.can_undo():
            return f"Undo: {self.undo_stack[-1].description}"
        return "Undo"
    
    def get_redo_description(self) -> str:
        """Get description of next redo command."""
        if self.can_redo():
            return f"Redo: {self.redo_stack[-1].description}"
        return "Redo"
    
    def clear(self):
        """Clear all undo and redo history."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        logger.debug("Command history cleared")
    
    def get_undo_stack_size(self) -> int:
        """Get size of undo stack."""
        return len(self.undo_stack)
    
    def get_redo_stack_size(self) -> int:
        """Get size of redo stack."""
        return len(self.redo_stack)


__all__ = [
    'Command',
    'RenameTrackCommand',
    'AddTrackpointCommand',
    'RemoveTrackpointCommand',
    'RemoveTrackpointRangeCommand',
    'CommandHistory',
]
