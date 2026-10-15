"""Command Pattern & History Stack for CourseStudio.

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
    
    Implements the Command Pattern to support undo/redo functionality.
    Every track modification must be a Command subclass that can:
    1. Execute the operation
    2. Undo (reverse) the operation
    
    Why Command Pattern?
    - Encapsulates operations as objects (decouples UI from logic)
    - Enables undo/redo stacks (history of operations)
    - Allows operation logging and replay
    - Makes operations atomic (all-or-nothing)
    
    All command subclasses must implement:
    - execute() - Perform the operation
    - undo() - Reverse the operation
    - description property - Human-readable name for menus
    
    State Capture:
    - Commands capture state needed to reverse operations
    - Examples:
      - RenameTrackCommand: captures old name, new name, track index
      - AddTrackpointCommand: captures point data, insertion index
      - RemoveTrackpointCommand: captures removed point (to restore)
    
    Example:
        class MyCommand(Command):
            def execute(self) -> bool:
                # Perform operation
                return True
            
            def undo(self) -> bool:
                # Reverse operation
                return True
            
            @property
            def description(self) -> str:
                return "My Operation"
    """
    
    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the command.
        
        Called by CommandHistory when user performs operation.
        Should modify state and return True/False for success.
        
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """
        Reverse the command (undo operation).
        
        Called by CommandHistory.undo() to reverse last operation.
        Must restore state to before execute() was called.
        
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Get human-readable description for undo/redo menu.
        
        Used to display in UI menu:
        - "Undo: Rename Track"
        - "Redo: Delete Point"
        - "Undo: Add Trackpoint"
        
        Returns:
            str: Description like "Rename Track", "Delete Point"
        """
        pass


# ============================================================================
# Concrete Command Classes
# ============================================================================

class RenameTrackCommand(Command):
    """
    Command to rename a track.
    
    State Captured:
    - track_index: Which track to rename
    - old_name: Original name (for undo)
    - new_name: New name (for redo)
    
    Undo Behavior:
    - execute(): track.name = new_name, mark dirty
    - undo(): track.name = old_name, mark dirty
    
    Example Flow:
    1. User renames "Track A" to "Track B"
    2. execute() called → track.name = "Track B"
    3. User presses Ctrl+Z
    4. undo() called → track.name = "Track A"
    5. User presses Ctrl+Y
    6. execute() called again → track.name = "Track B"
    
    Note: Both execute and undo mark track as dirty (unsaved changes)
    """
    
    def __init__(self, track_manager: TrackManager, track_index: int,
                 old_name: str, new_name: str):
        """
        Initialize rename command.
        
        Captures state needed to reverse the operation.
        
        Args:
            track_manager: TrackManager instance
            track_index: Index of track to rename
            old_name: Original track name (stored for undo)
            new_name: New track name (stored for redo)
        """
        self.track_manager = track_manager
        self.track_index = track_index
        self.old_name = old_name
        self.new_name = new_name
        self.executed = False
    
    def execute(self) -> bool:
        """
        Execute the rename command.
        
        Updates track name to new_name and marks track as dirty.
        
        Returns:
            bool: True if track found and renamed, False if track not found
        """
        
        track = self.track_manager.get_track_by_index(self.track_index)
        if not track:
            logger.error(f"Track {self.track_index} not found")
            return False
        
        # Update track name
        track.name = self.new_name
        # Mark as having unsaved changes
        track.is_dirty = True
        self.executed = True
        logger.info(f"Executed: Renamed track {self.track_index} from '{self.old_name}' to '{self.new_name}'")
        return True
    
    def undo(self) -> bool:
        """
        Undo the rename command.
        
        Restores track name to old_name and marks track as dirty.
        This is called when user presses Ctrl+Z.
        
        Returns:
            bool: True if track found and reverted, False if track not found
        """
        
        track = self.track_manager.get_track_by_index(self.track_index)
        if not track:
            logger.error(f"Track {self.track_index} not found")
            return False
        
        # Restore original name
        track.name = self.old_name
        # Mark as having unsaved changes
        track.is_dirty = True
        self.executed = False
        logger.info(f"Undone: Renamed track {self.track_index} back to '{self.old_name}'")
        return True
    
    @property
    def description(self) -> str:
        """
        Get command description for UI menu.
        
        Returns string like:
        - "Undo: Rename to 'New Name'"
        - "Redo: Rename to 'New Name'"
        """
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


class MoveTrackpointCommand(Command):
    """Command to move (relocate) a trackpoint."""
    
    def __init__(self, track_manager: TrackManager, track_index: int, point_index: int,
                 latitude: float, longitude: float, altitude: Optional[float] = None):
        """
        Initialize move trackpoint command.
        
        Args:
            track_manager: TrackManager instance
            track_index: Index of track
            point_index: Index of trackpoint to move
            latitude: New latitude in decimal degrees
            longitude: New longitude in decimal degrees
            altitude: New elevation in meters (optional)
        """
        self.track_manager = track_manager
        self.track_index = track_index
        self.point_index = point_index
        self.new_latitude = latitude
        self.new_longitude = longitude
        self.new_altitude = altitude
        
        # Store original coordinates for undo
        track = track_manager.get_track_by_index(track_index)
        if track and point_index < len(track.trackpoints):
            point = track.trackpoints[point_index]
            self.original_latitude = point.latitude
            self.original_longitude = point.longitude
            self.original_altitude = point.elevation
        else:
            self.original_latitude = None
            self.original_longitude = None
            self.original_altitude = None
        
        self.executed = False
    
    def execute(self) -> bool:
        """Execute the move trackpoint command."""
        
        success = self.track_manager.move_trackpoint(
            self.track_index, self.point_index,
            self.new_latitude, self.new_longitude, self.new_altitude
        )
        
        if success:
            self.executed = True
            logger.info(f"Executed: Moved trackpoint to ({self.new_latitude}, {self.new_longitude})")
        else:
            logger.error(f"Failed to move trackpoint")
        
        return success
    
    def undo(self) -> bool:
        """Undo the move trackpoint command."""
        
        if self.original_latitude is None or self.original_longitude is None:
            logger.error("Original coordinates not available for undo")
            return False
        
        success = self.track_manager.move_trackpoint(
            self.track_index, self.point_index,
            self.original_latitude, self.original_longitude, self.original_altitude
        )
        
        if success:
            self.executed = False
            logger.info(f"Undone: Moved trackpoint back to ({self.original_latitude}, {self.original_longitude})")
            return True
        else:
            logger.error(f"Failed to undo move trackpoint")
            return False
    
    @property
    def description(self) -> str:
        """Get command description."""
        return f"Move Point to ({self.new_latitude:.4f}, {self.new_longitude:.4f})"


class RemoveTrackpointCommand(Command):
    """
    Command to remove a single trackpoint.
    
    State Capture & Restoration:
    - Captures: track_index, point_index, and FULL POINT DATA (lat/lon/elevation)
    - Why: Must store the entire point because undo() needs to restore it exactly
    - GOTCHA: Point data must be captured in __init__ (before execute), not during execute
    
    Special Behavior - Track Deletion:
    - When removing the LAST trackpoint, the entire track is deleted
    - This is intentional: empty tracks are not allowed in CourseStudio
    - Undo correctly restores: the track AND the point
    - Example:
      - Track has 1 point
      - Remove that point → Track is deleted entirely
      - Undo → Track is restored with that point
    
    Distance Recalculation:
    - After removing a point, track distance becomes STALE
    - CRITICAL: Call track_manager.recalculate_distance() after undo
    - Without this, UI shows WRONG distance for modified tracks
    
    Index Stability During Undo:
    - Re-insertion uses same point_index as removal
    - Assumes no other commands between remove and undo
    - Safe within CommandHistory pattern (sequential execution)
    """
    
    def __init__(self, track_manager: TrackManager, track_index: int, point_index: int):
        """
        Initialize remove trackpoint command.
        
        IMPORTANT: Point data captured NOW (during init), not during execute().
        This ensures we have exact state needed for undo even if track state changes.
        
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
        """
        Execute the remove trackpoint command.
        
        PIPELINE:
        1. Verify point exists in track
        2. Store point data (for undo restoration)
        3. Call track_manager.remove_trackpoint() which:
           - Removes point from trackpoint list
           - Updates track info (point count, distance)
           - Deletes entire track if last point removed
           - Marks track as dirty (unsaved changes)
        4. Return success/failure
        
        State After Execution:
        - Track distance is RECALCULATED automatically (inside remove_trackpoint)
        - Track is marked DIRTY (unsaved)
        - UI must refresh to show updated state
        """
        
        track = self.track_manager.get_track_by_index(self.track_index)
        if not track or self.point_index >= len(track.trackpoints):
            logger.error(f"Invalid track or point index")
            return False
        
        # Store the point before deletion (needed for undo)
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
        """
        Undo the remove trackpoint command.
        
        RESTORATION PIPELINE:
        1. Verify point data was stored during execute
        2. Re-add point at same index using track_manager.add_trackpoint()
        3. This triggers:
           - Point inserted into trackpoint list
           - Track info updated (point count increases)
           - Track distance RECALCULATED (was 0 for single-point track, now includes full path)
           - Track marked DIRTY
        
        CRITICAL GOTCHA: Track Restoration
        - If removing the last point deleted the entire track
        - Undo must create a NEW track with this point
        - The new track should have minimal info (set by add_trackpoint internally)
        - This works correctly because track_manager handles track creation if needed
        
        Index Restoration:
        - Re-insertion at same point_index ensures exact restoration
        - Assumes no structural changes between remove and undo
        - Safe within CommandHistory (sequential, atomic operations)
        
        Returns:
            bool: True if re-added successfully, False otherwise
        """
        
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
    """
    Command to remove a range of trackpoints.
    
    Why Range Deletion?
    - User selects multiple trackpoints in UI (e.g., points 5-12)
    - Delete all selected at once (more intuitive than one-by-one)
    - Single command in history (undo once removes all)
    
    CRITICAL: Remove from End to Start
    - When removing indices 5-12, must remove 12 first, then 11, 10, etc.
    - Why: After removing index 12, indices don't shift down (13+ unchanged)
    - If removed start-to-end (5, 6, 7...), indices shift and we delete wrong points
    - Example:
      - Track has 15 points, want to remove 5-7
      - Remove[5]: indices 6-7 shift down to 5-6, track has 14 points
      - Remove[5] again: removes what was originally index 7 (WRONG)
      - Remove[6] again: removes what was originally index 8 (WRONG)
    
    State Capture:
    - Stores ALL removed point data (needed for undo)
    - Order preserved: removed_points[0] = point at start_index
    - Re-insertion must reverse this: add back start to end
    
    Performance Note:
    - Removing range takes O(n) operations (n = number of points removed)
    - Each removal triggers distance recalculation in track_manager
    - For large ranges (100+ points), may be slow
    - Acceptable trade-off for undo safety
    
    Distance Recalculation:
    - After each point removal, distance is recalculated
    - After removing 50 points, distance recalculated 50 times
    - Optimization possible but not priority (user rarely deletes 50+ points)
    """
    
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
        """
        Execute the remove range command.
        
        ALGORITHM:
        1. Get track and validate
        2. Capture ALL points in range [start_index:end_index+1]
        3. Iterate BACKWARDS from end_index to start_index
           - This is CRITICAL to preserve indices (see docstring)
        4. For each point, call remove_trackpoint()
        5. If ANY removal fails, stop and return False (command is ATOMIC)
        
        Atomicity:
        - Either ALL points removed or NONE
        - If removal at index 8 fails, indices 9+ already removed (state damaged)
        - Prevention: fail fast, don't attempt to recover partial removals
        - Note: May leave track in inconsistent state if underlying remove fails
        
        State After Execution:
        - Track distance RECALCULATED (after each point removal)
        - Track marked DIRTY
        - Track may be deleted entirely if ALL points removed
        
        Example (Remove points 5-7 from 15-point track):
        - Capture points 5, 6, 7
        - Remove index 7 (track: 14 points)
        - Remove index 6 (track: 13 points)  ← indices didn't shift!
        - Remove index 5 (track: 12 points)  ← removed exactly 5-7
        """
        
        track = self.track_manager.get_track_by_index(self.track_index)
        if not track:
            logger.error(f"Track {self.track_index} not found")
            return False
        
        # Store the points before deletion (in order start to end)
        self.removed_points = track.trackpoints[self.start_index:self.end_index + 1].copy()
        
        # Remove from end to start to maintain indices (CRITICAL)
        for i in range(self.end_index, self.start_index - 1, -1):
            success = self.track_manager.remove_trackpoint(self.track_index, i)
            if not success:
                logger.error(f"Failed to remove point at index {i}")
                return False
        
        self.executed = True
        logger.info(f"Executed: Removed {len(self.removed_points)} trackpoints ({self.start_index}-{self.end_index})")
        return True
    
    def undo(self) -> bool:
        """
        Undo the remove range command.
        
        RESTORATION PIPELINE:
        1. Iterate through removed_points (in order from start to end)
        2. Re-add each point at position start_index + i
        3. This restores points in correct sequence
        
        Index Calculation Example:
        - If removed points 5-7 (stored in removed_points[0], [1], [2])
        - Re-add: point[0] at index 5, point[1] at index 6, point[2] at index 7
        - Formula: add position = start_index + i
        
        Atomicity (Partial Failure):
        - If re-add fails at point 2 of 3, already restored point 1
        - Track now has INCONSISTENT state (partially restored)
        - Current implementation doesn't recover from partial undo
        - Acceptable risk: failures rare in normal operation
        
        State After Undo:
        - Track distance RECALCULATED (after each point added)
        - Track recreated if all points removed then undone
        - Track marked DIRTY
        
        Returns:
            bool: True if all points re-added successfully, False otherwise
        """
        
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
    
    Implements the standard undo/redo stack pattern:
    - Maintain two stacks: undo_stack and redo_stack
    - When command executed: add to undo_stack, clear redo_stack
    - When user presses Ctrl+Z: move command from undo to redo, call undo()
    - When user presses Ctrl+Y: move command from redo to undo, call execute()
    
    Stack Behavior:
    1. User performs operation A: undo=[A], redo=[]
    2. User performs operation B: undo=[A,B], redo=[]
    3. User presses Ctrl+Z (undo): undo=[A], redo=[B], B.undo() called
    4. User performs operation C: undo=[A,C], redo=[] (redo stack cleared!)
    
    This matches standard behavior (e.g., Word, Photoshop, VS Code)
    
    Size Limits:
    - Max stack size can be set to prevent memory growth
    - Oldest operations removed when limit exceeded
    - Default: 100 operations (configurable)
    
    Example:
        history = CommandHistory(max_size=50)
        cmd = RenameTrackCommand(manager, 0, "Old", "New")
        history.execute(cmd)
        # Can undo: True, Can redo: False
        history.undo()
        # Can undo: False, Can redo: True
        history.redo()
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
        
        EXECUTION PIPELINE:
        1. Call command.execute() to perform the operation
        2. If successful:
           a. Add command to undo_stack (enables future undo)
           b. Check size limit (prevent infinite memory growth)
           c. Clear redo_stack (new operation invalidates redo history)
        3. Return success/failure
        
        Why Clear Redo Stack?
        - User scenario: Undo 3 times (removes points), then edits differently
        - History before edit: undo=[A,B,C,D], redo=[E,F,G]
        - User performs new operation (H)
        - Expected: Can undo H, but NOT redo back to E,F,G (different branch)
        - Result: undo=[A,B,C,D,H], redo=[]
        - This matches behavior in Word, Excel, VS Code
        
        Size Limit Enforcement:
        - Prevents unbounded memory growth from many operations
        - Removes OLDEST operations first (FIFO from undo_stack)
        - Default max_size=100 (typically sufficient)
        - Example: If history has 100 items, 101st causes removal of item 0
        
        Args:
            command: Command to execute
        
        Returns:
            bool: True if successful, False otherwise
        """
        
        # Execute the command
        success = command.execute()
        
        if success:
            # Add to undo stack (so we can undo this operation later)
            self.undo_stack.append(command)
            
            # Enforce max size (prevent unbounded memory growth)
            if len(self.undo_stack) > self.max_size:
                # Remove oldest operation (first element)
                self.undo_stack.pop(0)
            
            # Clear redo stack when new command executed
            # This ensures redo only works for undone commands
            self.redo_stack.clear()
            
            logger.debug(f"Executed command: {command.description}")
        else:
            logger.warning(f"Command execution failed: {command.description}")
        
        return success
    
    def undo(self) -> bool:
        """
        Undo the last command.
        
        UNDO PIPELINE:
        1. Verify undo_stack not empty (can_undo check)
        2. Pop command from TOP of undo_stack
        3. Call command.undo() to reverse the operation
        4. If successful:
           a. Push command to redo_stack (enables redo)
           b. Log the undo action
        5. If failed:
           a. Restore command to undo_stack (maintain state consistency)
           b. Log warning
        6. Return success/failure
        
        CRITICAL: Stack Order
        - undo_stack = [cmd1, cmd2, cmd3]  ← TOP is cmd3 (most recent)
        - Pop removes cmd3 (last executed)
        - Push to redo_stack for later redo
        - undo_stack = [cmd1, cmd2]
        - redo_stack = [cmd3]
        - Next undo removes cmd2, redo_stack = [cmd3, cmd2]
        
        Error Recovery:
        - If undo() returns False, command restored to undo_stack
        - Maintains consistency: If undo fails, state wasn't changed
        - Example: Point index out of bounds (track changed externally)
        - Result: Command stays in undo_stack, user can try again
        
        Called by User:
        - Ctrl+Z in UI
        - "Undo" menu item click
        - Keyboard shortcut binding
        
        Returns:
            bool: True if successful or no commands to undo, False if undo failed
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
        
        REDO PIPELINE:
        1. Verify redo_stack not empty (can_redo check)
        2. Pop command from TOP of redo_stack
        3. Call command.execute() to re-perform the operation
        4. If successful:
           a. Push command back to undo_stack
           b. Log the redo action
        5. If failed:
           a. Restore command to redo_stack
           b. Log warning
        6. Return success/failure
        
        Why Re-Execute Instead of Undo?
        - Redo uses execute() not undo()
        - Why: Changes may have happened since original execute
        - Example:
          - Execute: Add point at index 5
          - Meanwhile: Delete track (external change)
          - Redo: Can't re-add to deleted track
          - Better to re-execute with same params and let add_trackpoint handle it
        
        CRITICAL: Stack Order During Redo
        - undo_stack = [cmd1, cmd2], redo_stack = [cmd3]
        - Redo pops cmd3, executes, pushes back to undo_stack
        - undo_stack = [cmd1, cmd2, cmd3], redo_stack = []
        - User can undo cmd3 again if desired
        
        Returns:
            bool: True if successful, False otherwise
        """
        
        if not self.can_redo():
            logger.warning("Nothing to redo")
            return False
        
        # Pop from redo stack
        command = self.redo_stack.pop()
        
        # Execute command again (not command.undo)
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
