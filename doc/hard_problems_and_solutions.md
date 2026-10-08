# Hard Problems and Solutions

**Purpose**: Record complex, non-obvious problems encountered during development, failed attempts to solve them, root cause analysis, and final solutions. These are critical for remembering gotchas and preventing regression.

**Format**: Each problem includes:
1. **Problem Description** - What went wrong, symptoms
2. **What I Did Wrong** - Failed attempts (learn what NOT to do)
3. **Root Cause** - Why previous attempts failed
4. **Solution** - What actually worked
5. **Key Learning** - Non-obvious connection or lesson

---

## Problem 1: Trackpoint Deletion - Map/List State Inconsistency

### Problem Description

After deleting a trackpoint with Ctrl+D:
- **Expected**: No trackpoint selected (neither on map nor in list)
- **Actual**: Last trackpoint highlighted on map, list shows no selection
- **Result**: Map and list state were out of sync

This created confusion: the UI showed conflicting state.

### What I Did Wrong (Failed Attempts)

**Attempt 1**: Cleared selection in list, assumed map would auto-clear
```python
# In trackpoint_list_widget.py
self.table.clearSelection()  # Clear list
# Expected: Map would auto-clear too
```
- **Result**: ❌ Failed - Map still had last point selected
- **Why**: No signal connection to tell map to clear

**Attempt 2**: Added explicit map clearing before refresh
```python
# In map_widget
self._selected_trackpoint_index = -1  # Clear selection
# Then refresh map
self._on_track_changed(...)  # Refresh display
```
- **Result**: ❌ Failed - Something re-selected the point during refresh
- **Why**: Didn't understand the signal chain yet

**Attempt 3**: Disconnected/reconnected selection signals
```python
# Disconnect signals, do operation, reconnect signals
self.point_clicked.disconnect()
# ... delete ...
self.point_clicked.connect(handler)
```
- **Result**: ❌ Failed - Still inconsistent
- **Why**: Wasn't addressing the real root cause

**Attempt 4**: Added comprehensive logging
```python
# Log at every step of signal chain
logger.debug(f"Deletion: clearing selection")
logger.debug(f"Emitting point_selected(-1)")
logger.debug(f"Map received: {trackpoint_index}")
```
- **Result**: ✅ SUCCESS - Found the real problem!

### Root Cause Analysis

Traced the signal chain in detail:

```
User presses Ctrl+D
    ↓
_delete_trackpoint() in trackpoint_list_widget.py
    ↓
point_selected.emit(-1)  ← Emit "no selection" signal
    ↓
_on_trackpoint_selected() in main_window.py receives signal
    ↓
map_widget.on_point_selected(track_id, -1)
    ↓
on_trackpoint_selected(trackpoint_index=-1)  ← RECEIVES -1
    ↓
**BUG**: No guard check! Tries to select point at index -1
```

The `-1` (meaning "no selection") was being passed all the way through without validation. The map was trying to select a point at an invalid index, which caused undefined behavior.

### Solution

Add guard check in `main_window.py._on_trackpoint_selected()`:

```python
def _on_trackpoint_selected(self, track_id, trackpoint_index):
    """
    Guard: If trackpoint_index is -1, it means "no selection"
    This happens when user deletes a point or clears selection.
    We must NOT pass this to map_widget - it should clear, not error.
    """
    if trackpoint_index == -1:
        # No selection - clear map display
        self.map_widget.clear_selection()
        self.trackpoint_list_widget.clear_selection()
        return
    
    # Normal case: forward to map
    self.map_widget.on_point_selected(track_id, trackpoint_index)
```

**Result**: ✅ Map and list now stay in sync

### Key Learning

**Non-obvious connection**: Signal chains can hide root causes far from the symptom.
- The symptom appeared in the map (point selected when shouldn't be)
- The root cause was in main_window (no guard check on invalid index)
- The trigger was in trackpoint_list_widget (emitted -1)

**Lesson**: When debugging UI state inconsistency:
1. Don't try to fix each component separately
2. Trace the ENTIRE signal chain from trigger to effect
3. Add logging at every signal boundary
4. The root cause is rarely where the symptom appears

---

## Problem 2: Trackpoint Deletion Didn't Update Track Info

### Problem Description

When user deletes one or more trackpoints:
- **Expected**: Track distance and point count update immediately
- **Actual**: Numbers stay the same, stale data displayed
- **Result**: User sees outdated track information

### What I Did Wrong (Failed Attempts)

**Attempt 1**: Refresh only the trackpoint list
```python
# Only update the table display
self.refresh_trackpoints()
```
- **Result**: ❌ Failed - Track info in sidebar didn't update
- **Why**: Only refreshed the list table, not the track metadata

**Attempt 2**: Added track refresh after deletion
```python
# Delete trackpoint
# Then refresh track
self.track_manager.recalculate_distance()
```
- **Result**: ❌ Partial success - Data updated but not UI
- **Why**: Data recalculated but UI not notified

**Attempt 3**: Added signal emission after recalc
```python
# Recalculate
self.track_manager.recalculate_distance()
# Emit signal
self.track_updated.emit(self.current_track_id)
```
- **Result**: ✅ SUCCESS - UI updated

### Root Cause Analysis

The deletion flow had 3 independent components:
1. **Trackpoint list** - Updated by `refresh_trackpoints()`
2. **Track data** - Updated by `track_manager.recalculate_distance()`
3. **Track info display** - Updated by `track_updated` signal

They weren't connected. Deleting a trackpoint updated (1) but not (2) or (3).

### Solution

In `trackpoint_list_widget._delete_trackpoint()`:

```python
def _delete_trackpoint(self):
    """Delete currently selected trackpoint(s)"""
    # ... deletion code ...
    
    # CRITICAL: After deletion, recalculate track distance
    self.track_manager.recalculate_distance(self.current_track_id)
    
    # CRITICAL: Emit signal to update all UI displays
    self.track_updated.emit(self.current_track_id)
    
    # Refresh trackpoint list display
    self.refresh_trackpoints()
    
    # Clear selection
    self.point_selected.emit(-1)
```

**Result**: ✅ All three components stay in sync

### Key Learning

**Non-obvious connection**: Data changes and UI updates are separate concerns.
- Deleting trackpoint = data change
- Updating distance = data calculation
- Updating UI = signal emission

You must explicitly handle all three, or something falls out of sync.

**Lesson**: After any data modification:
1. Update the data model
2. Recalculate derived values
3. Emit signals to notify UI
4. Don't assume one update triggers the others

---

## Problem 3: Trackpoint Deletion Deleted Entire Track

### Problem Description

When user deleted the LAST trackpoint in a track:
- **Expected**: Track still exists (now empty) OR track is deleted
- **Actual**: Entire track deleted, next track auto-selected
- **Result**: Confusing behavior - user thought they were deleting one point

### What I Did Wrong

Not documented in detail, but the fix was:

**Initial behavior**: When last point deleted, track was removed from track list
- This caused next track to auto-select
- User couldn't undo easily
- Workflow broken

### Solution

In `track_manager.py`:

```python
def delete_trackpoint(self, track_id, trackpoint_index):
    """Delete a single trackpoint"""
    track = self.tracks[track_id]
    
    if len(track.trackpoints) == 1:
        # Last point in track - delete the entire track
        # (Don't create empty tracks)
        self.delete_track(track_id)
    else:
        # Normal case - remove just the point
        track.trackpoints.pop(trackpoint_index)
        self.recalculate_distance(track_id)
```

With corresponding GUI handling:

```python
def _delete_trackpoint(self):
    """Delete trackpoint, handle track deletion if needed"""
    # ... deletion code ...
    
    # Check if track still exists (wasn't deleted)
    if self.current_track_id not in self.track_manager.tracks:
        # Track was deleted - clear UI
        self.current_track_index = -1
        self.current_track_id = None
        self.clear_display()
        # Don't auto-select another track - let user choose
```

**Result**: ✅ Consistent behavior, undo/redo works

### Key Learning

**Non-obvious connection**: Deleting data can cascade to delete parent containers.
- Delete last point → should delete track
- But this causes cascading UI changes
- Must handle each level explicitly

**Lesson**: When deleting child data:
1. Check if parent becomes invalid (empty track)
2. Decide what to do (delete parent or keep empty)
3. Handle cascading deletions in UI
4. Clear selection carefully (don't auto-select)

---

## Problem 4: GUI Crashes When Clicking Trackpoint

### Problem Description

Selecting a trackpoint from the table would crash with error:
```
IndexError: list index out of range
```

### Root Cause

Table row index didn't match track's trackpoint list index after deletion.

When user deleted point at index 5:
- List updated (now has points 0-4, 6-10)
- But table still showed rows 0-9
- Clicking row 5 tried to access trackpoint at index 5
- But index 5 doesn't exist anymore (becomes part of index 4)

### Solution

Always refresh table after any deletion:

```python
def _delete_trackpoint(self):
    # Delete from data
    self.track.trackpoints.pop(index)
    
    # CRITICAL: Refresh entire table to sync indices
    self.refresh_trackpoints()  # Rebuilds table from scratch
    
    # Now all indices match
```

**Result**: ✅ No more crashes

### Key Learning

**Non-obvious connection**: UI table indices and data list indices can diverge.
- After deletion, table may show stale indices
- Must rebuild table completely to sync
- Partial updates not sufficient

---

## Problem 5: PyQt5 Layout Size Constraints Are Complex

### Problem Description

Trackpoint list disappeared from view after layout changes:
- **Expected**: List visible, scrollable if needed
- **Actual**: List covered by map, bottom rows invisible
- **Result**: Can't see or interact with trackpoints

### Root Cause

Conflicting size constraints:

```python
# In trackpoint_list_widget.py
self.table.setMinimumHeight(300)  # Table wants to be 300px minimum

# In container
trackpoint_widget.setMaximumHeight(250)  # Widget max is 250px
```

Problem: Table minimum (300) > Widget maximum (250)
- Qt tries to honor both constraints
- Result: Table gets clipped/hidden

### Solution

Adjust constraints to be consistent:

```python
# Widget max must be >= Table minimum
self.table.setMinimumHeight(50)      # Flexible minimum
widget.setMaximumHeight(250)         # Hard cap at 250

# For splitter arrangement:
self.splitter.setMinimumHeight(100)  # Trackpoint panel
self.splitter.setMaximumHeight(400)  # But can grow
```

**Result**: ✅ Layout works correctly

### Key Learning

**Non-obvious connection**: Parent and child size constraints interact in non-obvious ways.
- Parent max < Child min = child gets clipped
- Parent max > Child min = child expands/shrinks freely
- Qt doesn't warn or error, just does its best

**Lesson**: When debugging layout issues:
1. Check BOTH parent and child constraints
2. Ensure parent max >= child min
3. Test actual layout, not just code
4. Use splitter minimums, not maximums (more flexible)

---

## Problem 6: Splitter Handle Not Appearing

### Problem Description

Added splitter between trackpoint list and map, but handle not visible:
- **Expected**: Horizontal line between panels (drag to resize)
- **Actual**: No visible handle, can't resize
- **Result**: Layout stuck

### Root Cause

Splitter widget configuration issues:

```python
# Wrong way
splitter = QSplitter(Qt.Vertical)
splitter.addWidget(trackpoint_widget)
splitter.addWidget(map_widget)
# No: didn't set handle size or visibility

# Correct way
splitter.setHandleWidth(5)              # Make handle visible
splitter.setCollapsible(0, False)       # Don't collapse panels
splitter.setCollapsible(1, False)
splitter.setSizes([200, 500])           # Initial sizes
```

### Solution

Configure splitter properly:

```python
self.splitter = QSplitter(Qt.Vertical)

# Configure handle
self.splitter.setHandleWidth(5)  # 5px handle
self.splitter.setStyleSheet("""
    QSplitter::handle:vertical {
        background: #cccccc;
    }
""")

# Add widgets
self.splitter.addWidget(self.trackpoint_widget)
self.splitter.addWidget(self.map_widget)

# Set constraints
self.splitter.setCollapsible(0, False)  # Can't collapse list
self.splitter.setCollapsible(1, False)  # Can't collapse map
self.splitter.setMinimumHeight(400)

# Initial sizes
self.splitter.setSizes([200, 600])
```

**Result**: ✅ Splitter handle visible and functional

### Key Learning

**Non-obvious connection**: Qt components have many implicit defaults that don't show.
- Splitter handle width defaults to 0 (invisible!)
- Panels can collapse unexpectedly
- Style is separate from functionality

---

## Problem 7: Track Distance Not Recalculated

### Problem Description

Track distance shown in track list doesn't update when:
- User adds a new trackpoint (distance should increase)
- User deletes a trackpoint (distance should decrease)
- User moves a trackpoint (distance changes)

### Root Cause

Distance calculated once on file load, never recalculated after edits.

### Solution

Call recalculate at strategic points:

```python
# In track_manager.py
def add_trackpoint(self, track_id, lat, lon):
    track = self.tracks[track_id]
    track.trackpoints.append(TrackPoint(lat, lon))
    self.recalculate_distance(track_id)  # ← ADD THIS

def delete_trackpoint(self, track_id, index):
    track = self.tracks[track_id]
    track.trackpoints.pop(index)
    self.recalculate_distance(track_id)  # ← ADD THIS

def move_trackpoint(self, track_id, index, lat, lon):
    track = self.tracks[track_id]
    track.trackpoints[index].lat = lat
    track.trackpoints[index].lon = lon
    self.recalculate_distance(track_id)  # ← ADD THIS
```

Plus signal emission:

```python
# After any modification
self.track_updated.emit(track_id)  # Notify UI to refresh
```

**Result**: ✅ Distance always up-to-date

### Key Learning

**Non-obvious connection**: Cached values must be explicitly invalidated.
- Distance is cached (calculated once) for performance
- Every edit that changes distance must trigger recalc
- Easy to miss one edit operation

**Lesson**: For cached values:
1. List all operations that invalidate cache
2. Call recalculate after each operation
3. Emit signals to update UI
4. Document why caching is needed

---

## Problem 8: Signal/Slot Connection Confusion

### Problem Description

When trackpoint deleted:
- Map clears selection
- List clears selection
- But sometimes one doesn't clear
- Result: Inconsistent state

### Root Cause

Multiple signals triggering same operations, creating loops:

```
Track changed:
  → signal: track_updated
     → main_window updates list AND map
        → list selection changed signal
           → map updates selection... (loop!)
```

### Solution

Careful signal routing:

```python
# In main_window.py
class MainWindow:
    def _on_track_updated(self, track_id):
        """Track data changed - update all displays"""
        # Update list
        self.trackpoint_list_widget.refresh_trackpoints()
        
        # Update map
        self.map_widget.set_track(track_id)
        
        # Don't emit selection signals - stay consistent
        # (Only emit selection if user explicitly selected)
    
    def _on_trackpoint_selected(self, track_id, index):
        """User explicitly selected trackpoint"""
        # This is different from track_updated!
        self.map_widget.on_point_selected(track_id, index)
```

**Result**: ✅ No signal loops

### Key Learning

**Non-obvious connection**: Data changes and selection changes are different signals.
- Data change (track updated) → refresh all displays, keep selection
- Selection change (user selected) → highlight in both views
- If you mix these, you get loops

**Lesson**: Distinguish signal types:
1. Data changed → refresh display, keep selection
2. Selection changed → highlight in all views
3. Never have data signal trigger selection signal

---

## Problem 9: Web Mercator Coordinate System Confusion

### Problem Description

Map positioned incorrectly or showed wrong tiles:
- Tiles offset from actual track
- Zoom levels displayed wrong area
- Track not visible after pan

### Root Cause

Confusion between 3 coordinate systems:
- **GPS (lat/lon)**: What user thinks in
- **Web Mercator (x/y)**: What tiles use (but different Y direction!)
- **Screen (px)**: What mouse clicks use

### Non-Obvious Conversion

```python
# GPS lat/lon to Web Mercator tile coordinates
def latlon_to_tile(lat, lon, zoom):
    # Longitude: linear scale (simple)
    x = (lon + 180) / 360 * (2 ** zoom)
    
    # Latitude: NON-LINEAR (uses Mercator projection)
    # This formula is NOT intuitive!
    n = 2.0 ** zoom
    lat_rad = math.radians(lat)
    y = (1 - math.log(math.tan(lat_rad) + 1/math.cos(lat_rad)) / math.pi) / 2 * n
    
    # Y-axis INVERTED: tile(0,0) is TOP-LEFT, but math is bottom-up
    # So higher latitudes = higher y values (opposite!)
    
    return int(x), int(y)
```

**Key insight**: Latitude transformation is non-linear and inverted!

### Solution

Fully document the conversion:

```python
def latlon_to_tile(lat, lon, zoom):
    """
    Convert GPS coordinates to MBTiles tile coordinates.
    
    Web Mercator uses non-linear projection for latitude:
    - Longitude transforms linearly (proportional to degrees)
    - Latitude transforms non-linearly (flattens at poles)
    - Y-axis INVERTS: north is DOWN in tile space (but up in GPS!)
    
    Formula components:
    - x: Simple linear mapping of longitude
    - y: Mercator projection of latitude (uses atan + log)
    - Inversion: tile(0,0) is top-left corner
    """
    n = 2.0 ** zoom
    
    # Longitude: straightforward
    x = (lon + 180) / 360 * n
    
    # Latitude: Mercator projection
    lat_rad = math.radians(lat)
    merc = math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad))
    y = (1 - merc / math.pi) / 2 * n
    
    return int(x), int(y)
```

**Result**: ✅ Coordinates correct

### Key Learning

**Non-obvious connection**: Web Mercator projects spherical Earth onto flat surface.
- Longitude is linear (easy)
- Latitude is non-linear (hard) - uses hyperbolic tangent + logarithm
- Y-axis inverts between math space and tile space

**Lesson**: When working with projections:
1. Document the non-obvious transformations
2. Include WHY each formula is needed
3. Test with known locations
4. Remember axes can invert between systems

---

## Problem 10: MBTiles Tile Coordinates (TMS vs XYZ)

### Problem Description

Tile retrieval returned wrong tile or nothing:
- Some coordinates worked
- Some coordinates failed
- Same zoom level, adjacent tiles

### Root Cause

Two different tile coordinate conventions:

**XYZ (Web Mercator, Google Maps)**:
```
(0,0) = top-left
(0,n) = bottom-left
Y increases downward
```

**TMS (Tile Map Service, used by MBTiles)**:
```
(0,0) = bottom-left
(0,n) = top-left
Y increases upward
```

**The problem**: GPS ↔ XYZ conversion gave Y-up coordinates, but MBTiles used Y-down!

### Solution

Convert between systems:

```python
def get_tile(self, lat, lon, zoom):
    """Get tile from MBTiles for GPS coordinates"""
    # Step 1: Convert GPS to Web Mercator (XYZ)
    x, y_xyz = self.latlon_to_tile(lat, lon, zoom)
    
    # Step 2: Convert XYZ to TMS
    # (MBTiles stores tiles in TMS coordinate system)
    max_y = (2 ** zoom) - 1
    y_tms = max_y - y_xyz  # ← INVERT Y-AXIS
    
    # Step 3: Query database using TMS coordinates
    tile_data = self.db.execute("""
        SELECT tile_data FROM tiles 
        WHERE zoom_level=? AND tile_column=? AND tile_row=?
    """, (zoom, x, y_tms)).fetchone()
    
    return tile_data
```

**Key formula**: `y_tms = max_y - y_xyz`

### Key Learning

**Non-obvious connection**: Different systems use different coordinate conventions.
- Web Mercator (XYZ): Y increases downward
- TMS/MBTiles: Y increases upward
- Must convert between systems explicitly

**Lesson**: When integrating systems:
1. Verify coordinate conventions
2. Document which system each function uses
3. Convert at integration points
4. Test with known locations

---

## Summary: Patterns in Hard Problems

### What Causes Hard Problems?

1. **Signal/Slot Confusion**: Multiple signals triggering same operation
2. **State Sync**: Multiple components (map, list, tracker) out of sync
3. **Coordinate System Confusion**: GPS, Web Mercator, TMS, Screen pixels
4. **Implicit Defaults**: Qt components silent about configuration
5. **Cascading Changes**: One edit triggers multiple recalculations
6. **Constraint Conflicts**: Parent and child size constraints clash
7. **Cache Invalidation**: Cached values not updated after edits

### How to Debug These?

✅ **Trace signal chains**: Add logging at every signal boundary  
✅ **Check state at each step**: Print state at key points  
✅ **Verify coordinate systems**: Know which system each function uses  
✅ **Document non-obvious logic**: Write comments on why, not what  
✅ **Test known cases**: Use GPS locations you know the tiles for  
✅ **Rebuild from scratch**: Sometimes partial fixes create new bugs  

## Problem 11: Qt Layout Hidden Default Spacing

### Problem Description

When designing UI layouts in PyQt5:
- Elements appear farther apart than code suggests
- No explicit spacing code, but gaps appear anyway
- Nested layouts multiply spacing unexpectedly
- Result: Compact UI looks bloated with invisible gaps (20+ pixels)

### Root Cause

Qt has **invisible default values** that apply automatically:
- Default spacing: 6 pixels
- Default margins: 9 pixels on each side
- Nested layouts: Spacing multiplies (6px + 9px + 6px = 20+px)
- Grid layouts: Both spacing AND margins apply

**Example:**
```
Main Layout (6px default spacing)
  └─ Grid Layout (9px default margins)
      └─ HBox Layout (6px default spacing)
          └─ Widget (6px default spacing)
              └─ Total: 27px of invisible vertical gap!
```

### What I Did Wrong (Failed Attempts)

**Attempt 1**: Only set spacing, ignored margins
```python
layout.setSpacing(0)
# ← Still had 9px padding! Elements still too far apart
```

**Attempt 2**: Set spacing in main layout, forgot nested layouts
```python
main_layout.setSpacing(0)
# ← Missing in control_layout, grid layout, etc.
# ← Spacing multiplies in nested hierarchies
```

**Attempt 3**: Used default values for grid layouts
```python
grid = QGridLayout()
grid.setSpacing(0)
# ← Missing setContentsMargins! Still had 9px padding around grid
```

### Solution

**Always set BOTH spacing and margins on EVERY layout:**

```python
# Main layout
main_layout = QVBoxLayout()
main_layout.setContentsMargins(0, 0, 0, 0)  # Remove default padding
main_layout.setSpacing(0)                    # Remove default gaps
self.setLayout(main_layout)

# Grid layout (if used)
grid = QGridLayout()
grid.setContentsMargins(0, 0, 0, 0)         # Remove grid padding
grid.setSpacing(0)                           # Remove grid gaps
grid.setVerticalSpacing(0)                   # Explicit row spacing
grid.setHorizontalSpacing(4)                 # Column spacing (can differ)
main_layout.addLayout(grid)

# ALL nested layouts (same pattern)
control_layout = QHBoxLayout()
control_layout.setContentsMargins(0, 0, 0, 0)  # Remove padding
control_layout.setSpacing(8)                   # Add back where needed
control_layout.addWidget(slider)
control_layout.addWidget(spinbox)
grid.addLayout(control_layout, row, col)
```

**Critical:** Every single layout must have these calls, or defaults apply.

### Key Learning

**Non-obvious connection**: Qt's default values are invisible in code.
- No visible spacing code, but 6px applied anyway
- No margins code, but 9px padding added anyway
- Nested layouts compound this (spacing multiplies, not adds)
- You must **explicitly** set all values or Qt's defaults override you

**Lesson**: Always assume Qt has invisible defaults:
1. Set `setContentsMargins(0, 0, 0, 0)` on every layout
2. Set `setSpacing(X)` on every layout
3. Check all nested layouts (easy to miss one)
4. Debug with `setStyleSheet("background-color: red;")` to visualize spacing

### Real-World Impact

In CourseStudio UI:
- Before: ColorPickerWidget had 36px+ of unwanted vertical spacing
- After: Changed only 12 lines of code (setSpacing, setContentsMargins)
- Result: UI appears dramatically more compact
- Code change: Small, but huge visual impact

---

### Key Non-Obvious Connections to Remember

1. UI state inconsistency hides root cause far away in signal chain
2. Data changes and selection changes need different signal handling
3. Cached values need explicit invalidation after any edit
4. Size constraints interact in non-intuitive ways (parent max < child min = clipping)
5. Coordinate systems invert between different domains (GPS vs Web Mercator vs TMS)
6. Signal loops happen when data signals trigger selection signals
7. **Qt's default values are invisible** - Must explicitly set spacing/margins

---

## Problem 12: Map Panning Asymmetry - Horizontal Lag vs Vertical Lead

### Problem Description

When panning the map by dragging the mouse:
- **Horizontal (left-right)**: Map moves LESS than cursor movement (lag)
- **Vertical (up-down)**: Map moves MORE than cursor movement (lead)
- **Result**: Asymmetric panning experience; cursor doesn't follow map smoothly

The bug manifested at latitude 57°N (Sweden) where the Web Mercator distortion is significant. At lower latitudes, the effect was less noticeable.

### What I Did Wrong (Failed Attempts)

**Attempt 1**: Assumed it was a rendering issue
```python
# Added debug rendering, cleared caches
self.render_map()  # More frequent renders
```
- **Result**: ❌ Failed - Problem persisted, just got worse performance
- **Why**: Panning math was wrong, not the rendering

**Attempt 2**: Tried to adjust cos_lat factor
```python
# Thought maybe cos_lat was being applied wrong
cos_lat = math.cos(math.radians(self.center_lat))
m_per_pixel_lon = (earth_circumference_m * cos_lat) / (TILE_SIZE * tiles_at_zoom)
# Maybe increase/decrease factor?
lon_delta = delta_x * m_per_pixel_lon * deg_per_m * (1.5)  # Arbitrary fudge factor
```
- **Result**: ❌ Failed - Made it worse at different latitudes
- **Why**: Root cause was deeper; bandaid doesn't work

**Attempt 3**: Tried separately handling latitude
```python
# Maybe latitude needs special treatment?
lat_delta = -delta_y * m_per_pixel_lat * deg_per_m * cos_lat  # Add cos_lat here too
```
- **Result**: ❌ Failed - Still asymmetric, just different values
- **Why**: Didn't understand Web Mercator's non-linear latitude

### Root Cause

The panning code used a FUNDAMENTALLY WRONG conversion formula for Web Mercator:

```python
# WRONG (old code):
deg_per_m = 1.0 / 111320.0  # Linear conversion constant
lon_delta = delta_x * m_per_pixel_lon * deg_per_m
lat_delta = -delta_y * m_per_pixel_lat * deg_per_m  # Linear formula for latitude!
```

**Why this is wrong:**

1. **Web Mercator uses non-linear latitude projection**
   - Longitude is approximately linear (with cos_lat adjustment)
   - Latitude uses Mercator projection formula: `y = ln(tan(π/4 + lat/2))`
   - This formula is exponential, not linear!

2. **Linear meter-to-degree conversion breaks the math**
   - Works approximately at equator where 1° ≈ 111,320 meters
   - Breaks at latitude 57°N where Web Mercator distorts coordinates heavily
   - Latitude axis in tile space is non-linear, but code treated it as linear

3. **Why the asymmetry happened:**
   - Longitude: Had cos_lat applied, but still used wrong linear conversion → laggy
   - Latitude: Had no latitude adjustment, used wrong linear conversion → leads
   - The two errors didn't cancel; they compounded to create asymmetry

4. **Key insight:** This is a **coordinate system transformation problem**, not a UI problem
   - The error was in the math domain, not the rendering domain
   - Classic case of mixing incompatible coordinate systems

### Solution

Use Web Mercator's NATIVE coordinate system: **tile coordinates**

Tile coordinates are linear! Panning in tile space is simple vector addition.

```python
# CORRECT (new code):

# Step 1: Convert lat/lon to tile coordinates (using Web Mercator formulas)
def latlon_to_tile(lat, lon, zoom):
    n = 2.0 ** zoom
    tile_x = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    tile_y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return tile_x, tile_y

# Step 2: Calculate tile delta from pixel delta (linear and symmetric!)
tile_delta_x = delta_x / 256.0  # 256 pixels per tile
tile_delta_y = delta_y / 256.0
new_tile_x = tile_x + tile_delta_x
new_tile_y = tile_y + tile_delta_y

# Step 3: Convert back to lat/lon (using Web Mercator inverse formulas)
def tile_to_latlon(tile_x, tile_y, zoom):
    n = 2.0 ** zoom
    lon = tile_x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * tile_y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon

self.center_lat, self.center_lon = tile_to_latlon(new_tile_x, new_tile_y, self.zoom_level)
```

**Why this works:**

1. **Tile coordinates are linear** - panning is just vector addition
2. **Same scale in both directions** - no asymmetry possible
3. **Works at all latitudes** - including poles
4. **Standard formulas** - used by Google Maps, OpenStreetMap, Leaflet.js, Mapbox
5. **No fudge factors** - pure mathematics

### Impact

- **Before**: Panning was confusing, cursor didn't follow map smoothly
- **After**: Panning is smooth, symmetric, and feels natural
- **Code complexity**: Increased (added 2 helper functions), but correctness improved dramatically
- **Performance**: No impact (same operations, just correct order)

### Key Learning

**When mixing coordinate systems (pixels → meters → degrees), ensure the transformation pipeline is mathematically sound:**

1. **Identify what coordinate system each operation works in:**
   - Pixels: screen coordinates (linear)
   - Tiles: Web Mercator native (linear)
   - Degrees: geographic (non-linear in Web Mercator)

2. **Don't mix incompatible transforms:**
   - ❌ Wrong: pixels → meters → linear degrees (mixes non-linear projection with linear math)
   - ✅ Right: pixels → tiles → degrees (stays within Web Mercator until final step)

3. **When in doubt, use the native coordinate system:**
   - For Web Mercator: use tile coordinates, not lat/lon
   - For other projections: identify the native space and work there

4. **Asymmetry in vector operations signals coordinate system errors:**
   - If X and Y behave differently, you're likely mixing coordinate systems
   - Linear operations should be symmetric

---


