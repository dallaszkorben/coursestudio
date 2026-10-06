# General Rules and Patterns for Development

**Purpose:** Developer guidelines for implementing features, modifying code, and fixing bugs  
**Scope:** How to work with CourseStudio codebase  
**Last Updated:** 2026-10-06

---

## 1. Signal/Slot Patterns

### When to Use Signals vs Direct Calls

**Use signals when:**
- Component A needs to notify Component B of a change
- Multiple components need to react to the same event
- You need loose coupling between components

**Use direct calls when:**
- Simple property access (getter/setter)
- No other components care about the change
- Performance critical (signals have overhead)

**Example - Correct:**
```python
# Good: UI responds to selection via signal
trackpoint_list.point_selected.connect(main_window.on_point_selected)
map_widget.point_clicked.connect(main_window.on_point_clicked)

# main_window synchronizes both views when user selects
def on_point_selected(self, track_id, index):
    self.map_widget.on_point_selected(track_id, index)
```

### Avoiding Signal Loops

**The problem:**
```python
# BAD - This creates a loop!
trackpoint_list.point_selected.connect(map_widget.on_point_selected)
map_widget.point_clicked.connect(trackpoint_list.on_point_selected)

# User clicks map → emits point_clicked → updates list → emits point_selected
# → updates map → emits point_clicked → ... infinite loop!
```

**The solution:**
- Route all signals through main_window (central hub)
- Never connect signals between peer components
- Main window is responsible for synchronization

```python
# GOOD - Single hub pattern
trackpoint_list.point_selected.connect(main_window.on_trackpoint_selected)
map_widget.point_clicked.connect(main_window.on_point_clicked)

# main_window updates OTHER components (not the one that emitted)
def on_trackpoint_selected(self, track_id, index):
    # List already updated itself (it emitted the signal)
    # Only update map
    self.map_widget.on_point_selected(track_id, index)
```

### Guard Checks for Invalid States

**Always check for -1 (no selection):**
```python
def on_trackpoint_selected(self, track_id, trackpoint_index):
    # Guard: -1 means "no selection"
    if trackpoint_index == -1:
        self.map_widget.clear_selection()
        self.trackpoint_list_widget.clear_selection()
        return
    
    # Normal case: valid selection
    self.map_widget.on_point_selected(track_id, trackpoint_index)
```

### Data Signals vs Selection Signals (CRITICAL)

**Never mix these signal types - they serve different purposes:**

**Data changed signal (track updated, distance recalculated):**
- Refresh all displays
- Keep current selection (don't change what's selected)
- Example: User deletes a point → distance changes → map refreshes but keeps selected point selected

**Selection signal (user selected something):**
- Highlight in all views
- Update UI to show this item is selected
- Example: User clicks trackpoint → select in map AND list

**BAD - Mixing signal types:**
```python
# ❌ WRONG: Data signal triggers selection update
def on_distance_recalculated(self):
    # This is a DATA change signal, not selection
    self.map_widget.on_point_selected(...)  # ← WRONG!
    # Now map might select wrong point
```

**GOOD - Separate signal types:**
```python
# Data signal: refresh display, keep selection
def on_track_updated(self, track_id):
    self.trackpoint_list_widget.refresh_trackpoints()
    self.map_widget.refresh_track_display()
    # Don't change selection!

# Selection signal: highlight in all views
def on_trackpoint_selected(self, track_id, index):
    self.map_widget.on_point_selected(track_id, index)
    self.trackpoint_list_widget.highlight_row(index)
```

---

## 2. State Management

### Keeping Map/List/Toolbar in Sync

**The fragility:** Multiple components all display state independently
- Map shows selected point as blue marker
- List shows selected row highlighted
- Toolbar shows point properties

If any get out of sync → confusing UI

**Pattern to follow:**

```python
# Single source of truth in main_window
class MainWindow:
    def __init__(self):
        self.selected_track_id = None
        self.selected_point_index = -1  # -1 = no selection
    
    def on_trackpoint_selected(self, track_id, index):
        # Update internal state
        self.selected_track_id = track_id
        self.selected_point_index = index
        
        # Sync all views (except the one that emitted signal)
        if index == -1:
            self.map_widget.clear_selection()
            self.trackpoint_list.clear_selection()
            self.toolbar.clear_properties()
        else:
            self.map_widget.highlight_point(track_id, index)
            self.trackpoint_list.highlight_row(index)
            self.toolbar.show_properties(track_id, index)
```

### Cache Invalidation (Track Distance)

**The problem:** Distance is cached for performance, but edits don't invalidate it

**Rule: After ANY edit operation, invalidate cache:**

```python
def add_trackpoint(self, track_id, lat, lon):
    track = self.tracks[track_id]
    track.trackpoints.append(TrackPoint(lat, lon))
    
    # CRITICAL: Invalidate cache
    self.recalculate_distance(track_id)
    
    # Emit signal so UI updates
    self.track_updated.emit(track_id)

def delete_trackpoint(self, track_id, index):
    track = self.tracks[track_id]
    
    if len(track.trackpoints) == 1:
        # Last point - delete entire track
        self.delete_track(track_id)
        self.track_deleted.emit(track_id)
    else:
        # Remove point
        track.trackpoints.pop(index)
        
        # CRITICAL: Invalidate cache
        self.recalculate_distance(track_id)
        
        # Emit signal
        self.track_updated.emit(track_id)

def move_trackpoint(self, track_id, index, lat, lon):
    track = self.tracks[track_id]
    track.trackpoints[index].lat = lat
    track.trackpoints[index].lon = lon
    
    # CRITICAL: Invalidate cache
    self.recalculate_distance(track_id)
    
    # Emit signal
    self.track_updated.emit(track_id)
```

**Operations that invalidate distance cache:**
1. Add trackpoint
2. Delete trackpoint
3. Move trackpoint
4. Delete entire track
5. Rename track (actually doesn't affect distance, but still recalc for safety)

### Cascading Deletions

**Rule: Deleting last point deletes entire track**

```python
def delete_trackpoint(self, track_id, index):
    track = self.tracks[track_id]
    
    if len(track.trackpoints) == 1:
        # Last point - delete entire track (cascading delete)
        self.delete_track(track_id)
        return
    
    # Normal case - just remove point
    track.trackpoints.pop(index)
    self.recalculate_distance(track_id)
```

**UI must handle track deletion:**

```python
def _delete_trackpoint(self):
    # Delete from data
    self.track_manager.delete_trackpoint(track_id, index)
    
    # Check if track still exists (might have been deleted by cascade)
    if track_id not in self.track_manager.tracks:
        # Track was deleted - clear UI
        self.current_track_id = None
        self.trackpoint_list.clear()
        self.map_widget.clear_track()
        # DON'T auto-select another track - let user choose
```

---

## 3. Coordinate Systems

### Know Which System You're In

**Four different coordinate systems in use:**

1. **GPS (lat/lon)** - What users think in
   - Latitude: -90 to +90
   - Longitude: -180 to +180
   - North is up, east is right

2. **Web Mercator (x/y)** - What map tiles use
   - Linear X: 0 to 2^zoom
   - NON-LINEAR Y: 0 to 2^zoom (but different formula)
   - North is DOWN (Y increases downward)
   - Different Y-axis from GPS!

3. **TMS (Tile Map Service, x/y)** - What MBTiles stores
   - X same as Web Mercator
   - Y INVERTED: y_tms = max_y - y_web_mercator
   - This is why TMS vs XYZ can be confusing

4. **Screen (px/py)** - What mouse clicks give
   - Pixels from top-left
   - North is up, east is right

### Conversions Must Happen at Domain Boundaries

**BAD - Conversions scattered everywhere:**
```python
# ❌ Random conversions in different files
lat = ... # GPS
web_merc_y = ... # Web Mercator
tms_y = ... # TMS
```

**GOOD - Conversions at clear boundaries:**
```python
# MapRenderer: GPS ↔ Web Mercator
class MapRenderer:
    def latlon_to_screen(self, lat, lon):
        # Step 1: GPS → Web Mercator
        # Step 2: Web Mercator → Tile
        # Step 3: Tile → Screen
        return screen_x, screen_y

# MBTilesProvider: Web Mercator ↔ TMS
class MBTilesProvider:
    def get_tile(self, lat, lon, zoom):
        # Step 1: GPS → Web Mercator (call MapRenderer)
        x_web, y_web = ...
        
        # Step 2: Web Mercator → TMS (our conversion)
        y_tms = (2 ** zoom - 1) - y_web
        
        # Step 3: Query database with TMS coordinates
        return db.query(zoom, x_web, y_tms)
```

### Y-Axis Inversion (Most Common Mistake)

**Remember: Y-axis inverts between Web Mercator and TMS**

```python
# Web Mercator: Y increases downward (north is DOWN)
# TMS: Y increases upward (north is UP)

# Formula: tms_y = max_y - web_mercator_y

# Example at zoom 10:
# max_y = 2^10 - 1 = 1023
#
# Web Mercator Y=0 (top/north) → TMS Y=1023 (top/north)
# Web Mercator Y=512 (middle) → TMS Y=511 (middle)
# Web Mercator Y=1023 (bottom/south) → TMS Y=0 (bottom/south)
```

---

## 4. Code Organization

### Where to Add New Features

**By responsibility:**

- **TrackManager** (`src/core/track_manager.py`)
  - All data operations
  - Load/save GPX
  - Add/delete/rename tracks and points
  - Distance calculations
  - Command history coordination

- **MapWidget** (`src/gui/widgets/map_widget.py`)
  - Display and interaction
  - Pan/zoom
  - Mouse clicks
  - Track visualization
  - Point highlighting

- **TrackpointListWidget** (`src/gui/widgets/trackpoint_list_widget.py`)
  - Trackpoint table display
  - Row selection
  - Coordinate format conversion

- **CommandHistory** (`src/core/command_history.py`)
  - Undo/redo stacks
  - Command execution
  - State capture

- **AppConfig** (`config/app_config.py`)
  - All configuration access
  - No hardcoded values

**Pattern: Command Pattern for user actions**

```python
# User action in UI → Create command → Execute via CommandHistory

class DeleteTrackpointCommand(Command):
    def __init__(self, track_manager, track_id, index):
        self.track_manager = track_manager
        self.track_id = track_id
        self.index = index
        self.deleted_point = None  # Store for undo
    
    def execute(self):
        self.deleted_point = self.track_manager.trackpoints[self.index]
        self.track_manager.delete_trackpoint(self.track_id, self.index)
    
    def undo(self):
        self.track_manager.add_trackpoint_at_index(
            self.track_id, 
            self.index, 
            self.deleted_point
        )
```

---

## 5. Size Constraints & Layouts

### Parent Max Must Be >= Child Min

**The rule:**
```python
# Parent's maximum size MUST BE >= Child's minimum size
# Otherwise child gets clipped/hidden!

# BAD:
parent.setMaximumHeight(250)
child.setMinimumHeight(300)  # ← Exceeds parent max, gets clipped!

# GOOD:
parent.setMaximumHeight(300)
child.setMinimumHeight(250)  # ← Fits within parent max
```

### Set Both Spacing AND Margins on Every Layout

**Critical pattern - must do BOTH:**

```python
# ❌ WRONG - Only sets spacing
layout = QVBoxLayout()
layout.setSpacing(0)
# ← Still has ~9px default margins!

# ✅ CORRECT - Sets both
layout = QVBoxLayout()
layout.setContentsMargins(0, 0, 0, 0)  # Remove default padding
layout.setSpacing(0)                    # Remove default gaps

# ✅ CORRECT for nested layouts
grid = QGridLayout()
grid.setContentsMargins(0, 0, 0, 0)
grid.setSpacing(0)
grid.setVerticalSpacing(0)              # Explicit row gaps
grid.setHorizontalSpacing(4)            # Column gaps can differ

main_layout.addLayout(grid)
```

### Nested Layouts Compound Spacing

**Remember: Spacing multiplies in nested hierarchies**

```python
# Each level adds spacing
Main Layout spacing (6px) 
  + Grid margins (9px)
    + HBox spacing (6px)
      + Widget spacing (6px)
        = 27px total invisible gap!

# Solution: Configure EVERY layout
for layout in [main, grid, hbox, ...]:
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)  # or appropriate value
```

---

## 6. Error Handling

### Pattern: try/except with Specific Types

```python
# Good - Specific exceptions
try:
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    return None, [f"File not found: {filename}"]
except json.JSONDecodeError as e:
    return None, [f"Invalid JSON in {filename}: {e}"]
except IOError as e:
    return None, [f"Cannot read {filename}: {e}"]
```

### Pattern: Validation Returns (bool, error_list)

```python
def validate_gpx_for_garmin(self, gpx_data):
    """
    Returns: (bool, [error_messages])
    - True if valid, False if invalid
    - error_list contains human-readable messages
    """
    errors = []
    
    if not gpx_data.tracks:
        errors.append("GPX file contains no tracks")
    
    for track in gpx_data.tracks:
        if not track.name:
            errors.append(f"Track at index {i} has no name")
        
        for point in track.get_points():
            if point.latitude < -90 or point.latitude > 90:
                errors.append(f"Invalid latitude: {point.latitude}")
    
    return len(errors) == 0, errors

# Usage
valid, errors = validate_gpx_for_garmin(gpx)
if not valid:
    # Show all errors to user
    for error in errors:
        show_error_dialog(error)
    return False
```

### Logging and User Feedback

```python
# Never silent failures
try:
    result = operation()
except Exception as e:
    # Log for developer
    logger.exception(f"Operation failed: {e}")
    
    # Show user-friendly message
    show_error_dialog(
        "Operation failed",
        f"Could not complete operation: {str(e)}"
    )
    
    # Return error status
    return False
```

---

## 7. Testing

### What's Expected

- 145+ unit tests currently passing
- Add tests for every new feature (unit + integration)
- Test real GPS coordinates (not fake data)
- Verify undo/redo works (Command Pattern)

### Pattern: Real GPS Test Data

```python
# Use actual GPS coordinates, not fake numbers
REAL_TEST_POINTS = [
    (57.5126, 12.2584),    # Real location in Sweden
    (57.5130, 12.2590),    # Another real point
]

def test_haversine_distance():
    distance = haversine_distance(
        REAL_TEST_POINTS[0][0], REAL_TEST_POINTS[0][1],
        REAL_TEST_POINTS[1][0], REAL_TEST_POINTS[1][1]
    )
    # Verify against known value
    assert 0.065 < distance < 0.070  # ~0.066 km
```

### Pattern: Test Undo/Redo

```python
def test_delete_trackpoint_undo():
    # Initial state
    track = track_manager.tracks[0]
    initial_count = len(track.trackpoints)
    
    # Delete
    cmd = DeleteTrackpointCommand(track_manager, 0, 0)
    command_history.execute(cmd)
    assert len(track.trackpoints) == initial_count - 1
    
    # Undo
    command_history.undo()
    assert len(track.trackpoints) == initial_count
    
    # Redo
    command_history.redo()
    assert len(track.trackpoints) == initial_count - 1
```

---

## 8. Configuration

### Rule: All Settings in settings.yaml, Nothing Hardcoded

```python
# BAD - Hardcoded value
ZOOM_LEVEL = 15

# GOOD - From configuration
zoom_level = app_config.get_int('Appearance', 'Tiles', 'initial_zoom_level')

# BAD - Hardcoded color
COLOR = "#FF0000"

# GOOD - From configuration
color = app_config.get('Appearance', 'MapDisplay', 'TrackPath', 'color')
```

### Configuration Structure

```yaml
Application:
  name, version, window settings, debug flag

Appearance:
  MapDisplay: Colors, widths (track path, turning points)
  Tiles: MBTiles file, zoom levels, center

CoordinatesDisplay:
  Format: DMS vs decimal, precision

FileHandling:
  Backup: Create backups, extension
  RecentFiles: Remember directory
  GpxExport: Validation rules

Performance:
  TrackLoading: Warning thresholds
  UndoRedo: Stack limits
  Rendering: Timer intervals

Advanced:
  Debugging: Log level, file
  Technical: Timeouts, threads
  GarminDevice: Import guide

InternalState:
  Map: Last state
  Coordinates: Last format
```

---

## 9. Git-Safe Practices

### No >>> REPL Prompts in Docstrings

**Why:** Can be confused with git merge conflict markers

```python
# BAD - Uses >>> REPL prompt
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Example:
        >>> distance = haversine_distance(57.5126, 12.2584, 57.5130, 12.2590)
        >>> print(f"{distance:.3f} km")
        0.066 km
    """

# GOOD - Plain code with comment output
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Example:
        distance = haversine_distance(57.5126, 12.2584, 57.5130, 12.2590)
        # distance ≈ 0.066 km
    """
```

### Document Why, Not What

```python
# BAD - Documents what, not why
# Track distance in kilometers
self.distance = 0.0

# GOOD - Documents why
# Track distance cached for performance (recalculated after edits)
# Critical: Must invalidate after add/delete/move operations
self.distance = 0.0
```

### Link Related Documentation

```python
# Reference related docs from docstrings
"""
Coordinate conversion from GPS to Web Mercator.

See also:
- ARCHITECTURE.md - Coordinate systems (section 5)
- HARD_PROBLEMS_AND_SOLUTIONS.md - Problem 9 (Web Mercator)
- MBTILES_ANALYSIS.md - Tile coordinates
"""
```

---

## 10. Documentation File Naming Convention

### Permanent vs Temporary Documentation

**Permanent production documentation (required reference):**
- File naming: lowercase snake_case
- Examples: `hard_problems_and_solutions.md`, `general_rules_and_patterns.md`, `architecture.md`
- Location: `doc/` root
- Status: Always kept, regularly referenced
- Content: System knowledge, patterns, solutions

**Temporary investigation/session documentation:**
- File naming: FULL UPPERCASE
- Examples: `SESSION_2026_10_06.md`, `INVESTIGATION_ZOOM.md`, `DEBUG_TRACKPOINT_SYNC.md`
- Location: `doc/tmp/`
- Status: Created for specific session, cleaned up when done
- Content: Session notes, investigations, debugging logs, drafts

### Why This Convention?

**Instant visual distinction:**
- Kiro sees `hard_problems_and_solutions.md` → "This is production, reference it"
- Kiro sees `SESSION_2026_10_06.md` → "This is temporary, from a session"

### Naming Rules

Permanent files (lowercase snake_case):
```
hard_problems_and_solutions.md
general_rules_and_patterns.md
architecture.md
mbtiles_analysis.md
```

Temporary files (FULL UPPERCASE):
```
SESSION_YYYY_MM_DD.md           ← Session summary
INVESTIGATION_TOPIC.md          ← Deep investigation
DEBUG_ISSUE_NAME.md             ← Tracking specific bug
ANALYSIS_TOPIC.md               ← Performance/code analysis
DRAFT_FEATURE_NAME.md           ← Feature exploration
REFACTORING_PLAN.md             ← Before/after notes
```

### Workflow

**Creating temporary documentation:**
1. Create file in `doc/tmp/` with UPPERCASE name
2. Add session notes, investigation findings, debugging logs
3. When done: Review if content should be integrated into permanent files
4. If valuable: Extract key insights → merge into appropriate permanent file
5. Delete temporary file when session complete

**Example workflow:**
```
Session starts:
  → Create SESSION_2026_10_06.md in doc/tmp/

During session:
  → Document findings
  → Test and debug

Session ends:
  → Extract useful patterns → Add to general_rules_and_patterns.md
  → Extract discovered problems → Add to hard_problems_and_solutions.md
  → Delete SESSION_2026_10_06.md

Result: Knowledge flows from temporary → permanent documentation
```

### Git Handling

Add to `.gitignore`:
```
doc/tmp/
```

This keeps the `doc/tmp/` folder but ignores all contents:
- Temporary files never committed
- Session notes are local only
- Production files (lowercase) always committed

---

## 11. Defensive Programming

### Always Assume Input Could Be Invalid

```python
# BAD - Assumes input is valid
def select_trackpoint(self, index):
    self.selected_index = index
    self.map_widget.highlight_point(index)

# GOOD - Validates input
def select_trackpoint(self, track_id, index):
    # Guard: -1 means no selection
    if index == -1:
        self.clear_selection()
        return
    
    # Guard: Check bounds
    if track_id not in self.tracks:
        logger.error(f"Invalid track_id: {track_id}")
        return
    
    track = self.tracks[track_id]
    if index < 0 or index >= len(track.trackpoints):
        logger.error(f"Index {index} out of bounds for track {track_id}")
        return
    
    # Safe to proceed
    self.selected_index = index
    self.map_widget.highlight_point(index)
```

### Handle Edge Cases Explicitly

```python
# What if track is empty?
# What if file doesn't exist?
# What if user cancels dialog?
# What if coordinates are invalid?

# Always have a path forward:
if not track.trackpoints:
    show_message("No trackpoints in this track")
    return False

if not os.path.exists(filename):
    show_error("File not found")
    return None

if user_cancelled:
    # Silently return, no error
    return None

if coordinates_invalid:
    show_error("Invalid coordinates")
    return False
```

---

## Summary: Before You Code

**Checklist before implementing a feature:**

- [ ] Which component owns this (TrackManager, MapWidget, etc.)?
- [ ] Will signals be needed? Is it data-change or selection-change?
- [ ] What state needs to sync (map, list, toolbar)?
- [ ] Does this invalidate any caches (distance, etc.)?
- [ ] What are the edge cases (empty, invalid, etc.)?
- [ ] Is this configurable or hardcoded?
- [ ] What errors could occur and how to handle them?
- [ ] Do I need a Command for undo/redo?
- [ ] What size constraints apply?
- [ ] What tests do I need to add?
- [ ] Did I document WHY, not just WHAT?

---

**Reference:** Detailed problems and solutions in HARD_PROBLEMS_AND_SOLUTIONS.md

