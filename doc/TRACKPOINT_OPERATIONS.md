# Trackpoint Operations Guide

Complete documentation for all trackpoint navigation, selection, and deletion operations in CourseStudio.

## Table of Contents

1. [Trackpoint Selection](#trackpoint-selection)
2. [Trackpoint Movement](#trackpoint-movement)
3. [Trackpoint Deletion](#trackpoint-deletion)
4. [Range Selection](#range-selection)
5. [Real-Time Feedback](#real-time-feedback)
6. [Undo/Redo Support](#undoredo-support)
7. [Performance Considerations](#performance-considerations)

---

## Trackpoint Selection

### Single Point Selection (Map)

**How to use:**
- Left-click on a trackpoint (yellow circle) on the map
- The point turns blue to indicate selection
- The corresponding row in the trackpoint list is highlighted

**What happens:**
1. `map_widget.mousePressEvent()` detects click at screen coordinates (x, y)
2. `_find_turning_point_at_click(x, y)` searches for nearby points:
   - Creates bounding box around click (30×30 pixel search area)
   - Only checks trackpoints within search rectangle (performance optimization)
   - Calculates distance to each candidate point
   - Returns index of closest point within 10-pixel tolerance
3. Sets `selected_trackpoint_index` to clicked point's index
4. Clears any range selection: `selected_trackpoint_range = None`
5. Emits `point_clicked` signal with track_id and point_index
6. Main window updates trackpoint list selection
7. Map re-renders with point in blue

**Performance:**
- Instant response even with 1000+ point tracks
- Uses bounding box optimization to skip 99% of off-screen/distant points
- Only checks points that could reasonably be close to click

### Single Point Selection (List)

**How to use:**
- Click on a row in the trackpoint list table
- Point turns blue on map
- Coordinates shown in list highlight

**What happens:**
1. User clicks table row with point index
2. `trackpoint_list_widget._on_point_selected()` is called
3. Sets map_widget's `selected_trackpoint_index`
4. Clears range selection
5. Emits `point_clicked` signal
6. Map widget updates visual representation

---

## Trackpoint Movement

### Drag to Move

**How to use:**
1. Left-click on a trackpoint (any point on map, whether selected or not)
2. Hold mouse button down
3. Drag to new position - point follows cursor
4. Release mouse button to save

**What happens during drag:**

1. **On mouse press** (`mousePressEvent`):
   - Click detected on trackpoint
   - `dragging_trackpoint = True`
   - `dragged_trackpoint_index` = clicked point's index
   - Store original coordinates: `drag_original_lat`, `drag_original_lon`
   - Store initial cursor position: `drag_start_x`, `drag_start_y`

2. **During drag** (`mouseMoveEvent`):
   - Current cursor position: (x, y)
   - Convert screen coordinates to GPS: `screen_to_gps(x, y)`
   - Update trackpoint coordinates in memory (no save yet)
   - Emit `trackpoint_dragging(index, lat, lon)` signal
   - Main window updates trackpoint list with new coordinates (real-time)
   - Call `render_map()` to show point moving on map
   - **Point moves smoothly following cursor**

3. **On mouse release** (`mouseReleaseEvent`):
   - Get final trackpoint coordinates from memory
   - Call `track_manager.move_trackpoint_with_history()`:
     - Creates `MoveTrackpointCommand` for undo/redo
     - Saves new coordinates to track data structure
     - Adds command to undo stack
   - Emit `point_clicked` signal
   - Exit drag mode: clear drag state variables
   - **NO re-render** (map already shows correct position from last drag motion)

**Real-time feedback:**
- Trackpoint coordinates update in list while dragging
- Point position updates on map while dragging
- Responsive and smooth movement

**Coordinates format:**
- List shows coordinates in current format:
  - **DMS format**: 57°30'45.5"N 12°15'30.2"E
  - **Decimal format**: 57.5126° 12.2584°

---

## Trackpoint Deletion

### Delete Single Point

**How to use:**
1. Right-click on trackpoint on map
2. Select "Delete Trackpoint" from context menu
3. Confirmation dialog appears (if enabled in settings)
4. Click "Yes" to confirm deletion
5. Point removed from map and list

**Configuration:**
- Setting: `FileHandling.DeleteConfirmation.require_delete_confirmation`
- Default: `true` (confirmation dialog shown)
- Set to `false` to delete without confirmation

**Deletion flow:**
1. User right-clicks on point
2. Context menu shows: "Delete Trackpoint"
3. Click triggers `_on_delete_trackpoint_from_map()`
4. If confirmation enabled:
   - Dialog shown: "Delete this trackpoint?"
   - "Yes" button is default
   - User confirms
5. Call `track_manager.delete_trackpoint_selected_with_history()`:
   - Creates `DeleteTrackpointCommand` for undo
   - Removes point from track data
   - Adds command to undo stack
6. Refresh trackpoint list
7. Re-render map
8. Point no longer visible

### Delete from List

**How to use:**
1. Right-click on row in trackpoint list
2. Select "Delete Trackpoint"
3. Confirmation dialog appears
4. Click "Yes" to confirm

**Same behavior as map deletion** - point removed with undo support

### Delete Multiple Points (Range)

**How to use:**
1. Select 2 neighboring points with Shift+click on map
2. Right-click
3. Select "Delete Selected Range"
4. Confirmation dialog
5. Click "Yes"

**Deletion flow:**
1. `selected_trackpoint_range = (start_idx, end_idx)`
2. User selects delete action
3. Confirmation dialog shown
4. Both points deleted together:
   - Creates delete command(s)
   - Removes both from track
   - Updates undo stack
5. List and map updated

---

## Range Selection

### Select Range (Shift+Click on Map)

**How to use:**
1. Left-click on first trackpoint (normal selection)
2. Hold Shift and left-click on neighboring trackpoint
3. Both points highlighted in blue
4. Range selection shown in list

**Behavior:**
- Can **only select consecutive neighboring points** (i±1)
- Shift+click on point 5, then Shift+click on point 6 → **OK** ✅
- Shift+click on point 5, then Shift+click on point 8 → **Rejected** ❌
- Shift+click to extend or modify range

**What happens:**
1. First Shift+click creates range:
   - Sets `selected_trackpoint_range = (min_idx, max_idx)`
   - Clears single selection: `selected_trackpoint_index = None`
   - Emits `range_selection_changed` signal
   - Map re-renders with both points in blue (double-selected color)

2. Second Shift+click modifies range:
   - Calculates new min/max including clicked point
   - If still consecutive neighbors: **update range**
   - If not consecutive: **no change**

**Visual feedback:**
- Range points shown in "double selected" color (default: Dodger Blue)
- Size configurable: `Appearance.MapDisplay.TurningPoints.doubleSelected.size`
- Color configurable: `Appearance.MapDisplay.TurningPoints.doubleSelected.color`

### Insert Between Range

**How to use:**
1. Select 2 neighboring points (Shift+click on map)
2. Menu → "Insert Trackpoint Between Selected" OR right-click → Insert
3. New point created at midpoint between the two
4. New point inserted at index = start_idx + 1

**What happens:**
1. Verify range selection exists: `selected_trackpoint_range`
2. Get coordinates of both points
3. Calculate midpoint GPS coordinates:
   - `mid_lat = (point1.lat + point2.lat) / 2`
   - `mid_lon = (point1.lon + point2.lon) / 2`
   - `mid_alt = (point1.alt + point2.alt) / 2` (if both have elevation)
4. Insert via `track_manager.add_trackpoint_with_history()`:
   - Creates `AddTrackpointCommand` for undo
   - Inserts at position between the two points
   - Updates track data structure
   - Adds to undo stack
5. Refresh list and map
6. **New point automatically selected**

---

## Real-Time Feedback

### Trackpoint List Updates During Drag

**What happens:**
- While dragging a trackpoint, its coordinates update in the list in real-time
- Updates happen every mouse move event
- Shows both DMS and decimal formats

**Implementation:**
1. `mouseMoveEvent()` emits `trackpoint_dragging(index, lat, lon)` signal
2. Main window handler: `_on_trackpoint_dragging()`
3. Calls `trackpoint_list_widget.update_trackpoint_row(index, lat, lon)`
4. Updates only that ONE row (not entire table)
5. Converts coordinates to appropriate format
6. User sees live coordinate updates while dragging

**Performance:**
- Only one row updated (not entire table of 1000 rows)
- Instant response even during drag
- Smooth visual feedback

### Map Visual Feedback

**Point states:**
- **Unselected**: Yellow circle (configurable)
- **Selected (single)**: Blue circle (configurable)
- **Selected (range - both endpoints)**: Dodger Blue (configurable, larger by default)

**Size settings:**
- General points: `Appearance.MapDisplay.TurningPoints.size` (default: 3px)
- Selected point: `Appearance.MapDisplay.TurningPoints.selected.size` (default: 5px)
- Range endpoints: `Appearance.MapDisplay.TurningPoints.doubleSelected.size` (default: 8px)

**Visibility:**
- All points visible if `Appearance.MapDisplay.TurningPoints.show = true`
- If false: only selected point visible
- Toggle in UI: Trackpoints panel "Show points" dropdown

---

## Undo/Redo Support

### Command Types

**1. MoveTrackpointCommand**
- Stores original and new coordinates
- User drags point to new position and releases
- Undo: restore original coordinates
- Redo: apply new coordinates

**2. DeleteTrackpointCommand**
- Stores deleted point's index and data
- User deletes a point
- Undo: restore point at original index
- Redo: delete again

**3. AddTrackpointCommand**
- Stores inserted point's coordinates and index
- User inserts point (via range or other method)
- Undo: remove inserted point
- Redo: re-insert point

### Using Undo/Redo

**How to use:**
- Menu → Edit → Undo (or Ctrl+Z)
- Menu → Edit → Redo (or Ctrl+Y)

**Undo stack:**
- Configured: `Performance.UndoRedo.max_undo_redo_stack` (default: 50 commands)
- Configured: `Performance.UndoRedo.max_history_memory_mb` (default: 500 MB)
- After max limit, oldest commands discarded

**What gets tracked:**
- All point movements
- All point deletions
- All point insertions
- Changes saved to file

---

## Performance Considerations

### Trackpoint Selection Optimization

**Problem:** With 1000+ point tracks, clicking to find a point was slow.

**Solution:** Bounding box optimization in `_find_turning_point_at_click()`:
1. Create search rectangle around click: 30×30 pixels
2. Skip all points outside search rectangle (99% of them!)
3. Only calculate distance for points in rectangle
4. Return closest point within tolerance

**Result:** Instant response even with 1000+ point tracks

### Drag Release Optimization

**Problem:** After releasing a dragged point, GUI froze for seconds while re-rendering 1000+ points.

**Solution:** Skip `render_map()` on release:
- Map already shows correct point position from last `mouseMoveEvent`
- No need to re-render entire map
- Just save the coordinates (instant)

**Result:** Immediate response when releasing, no freezing

### Table Refresh Optimization

**Problem:** After moving a point, the entire 1000-row table was refreshed.

**Solution:** Only update the one row that changed:
- Before: `refresh_trackpoints()` → loops through all 1000 rows
- After: `update_trackpoint_row(index, lat, lon)` → updates 1 row only

**Result:** Instant list update even with large tracks

---

## Configuration Reference

### Trackpoint Display Settings

```yaml
Appearance:
  MapDisplay:
    TurningPoints:
      show: true                    # Show all points
      color: 00BA00                 # Unselected: green
      size: 3                       # Unselected: 3px radius
      selected:
        color: 000080               # Selected: dark blue
        size: 5                     # Selected: 5px radius
      doubleSelected:
        color: 1E90FF               # Range: dodger blue
        size: 5                     # Range endpoints: 8px radius
```

### Deletion Settings

```yaml
FileHandling:
  DeleteConfirmation:
    require_delete_confirmation: false  # Require yes/no dialog
```

### Performance Settings

```yaml
Performance:
  UndoRedo:
    max_undo_redo_stack: 50        # Max commands to keep
    max_history_memory_mb: 500     # Max memory for undo stack
```

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Undo | Ctrl+Z |
| Redo | Ctrl+Y |
| Select trackpoint | Click on map |
| Range select | Shift+Click on map |
| Delete | Right-click → Delete |
| Insert between | Shift+Click range → Menu → Insert |

---

## Troubleshooting

### Selection doesn't respond quickly
- **Cause**: Large track (1000+ points) without optimization
- **Check**: Version should have bounding box optimization
- **Fix**: Update to latest version

### Dragging is slow
- **Cause**: Real-time list updates with 1000+ rows
- **Check**: Ensure `update_trackpoint_row()` is used, not `refresh_trackpoints()`
- **Fix**: Verify map_widget release handler doesn't call full refresh

### Freezing after release
- **Cause**: `render_map()` being called unnecessarily on release
- **Check**: Should skip render on release (map already updated)
- **Fix**: Verify mouseReleaseEvent doesn't call render_map()

### Points not updating in list
- **Cause**: List might be showing wrong track
- **Check**: Verify correct track is selected in track list
- **Fix**: Select track from track list panel

### Undo not working
- **Cause**: Command not added to history
- **Check**: Verify `*_with_history()` methods are used
- **Fix**: Ensure all modifications use history-aware methods

---

## Summary

CourseStudio provides a smooth, responsive trackpoint editing experience with:
- ✅ Instant point selection (even with 1000+ points)
- ✅ Real-time drag feedback
- ✅ Immediate release response (no freezing)
- ✅ Full undo/redo support for all operations
- ✅ Configurable visual styles and behaviors
- ✅ Range selection for batch operations

All operations are optimized for performance with large track datasets.
