# Recent Improvements - September 20-21, 2026

## Summary
Major layout improvements and feature enhancements to make the UI more intuitive and responsive.

## Changes

### 1. Layout Issue Fixed - Track List No Longer Covered
**Problem**: Bottom of trackpoint list was being covered by the map widget.

**Root Cause**: Conflicting size constraints:
- TrackpointListWidget: `setMaximumHeight(250)`
- Internal table: `setMinimumHeight(300)`
- The table's minimum (300px) exceeded the widget's maximum (250px)

**Solution**: 
- Reduced table minimum height from 300px to 50px
- Widget maximum height of 250px now controls the size properly
- Table expands/shrinks gracefully within the widget constraints

**Result**: ✅ Full trackpoint list now visible without any clipping

---

### 2. Resizable Layout with Splitter Handle
**Feature**: Added vertical splitter between trackpoint list and map

**Implementation**:
- Replaced fixed `QVBoxLayout` with `QSplitter(Qt.Vertical)`
- Trackpoint list and map are now independently resizable
- Splitter handle appears as a horizontal line between them

**How to Use**:
1. Move mouse to horizontal line between panels
2. Cursor changes to resize cursor (↕)
3. Click and drag up/down to resize
4. Drag DOWN → More space for trackpoints, less for map
5. Drag UP → Less space for trackpoints, more for map

**Constraints**:
- Trackpoint list: minimum 100px (can't collapse)
- Map: minimum 300px (can't collapse)
- Both panels are non-collapsible for safety

**Benefits**:
- Flexible layout based on workflow
- Users can see more trackpoints or more map details as needed
- Natural workflow: adjust layout to fit current task

**Files Modified**:
- `src/gui/main_window.py` - _create_central_widget()
- `src/gui/widgets/trackpoint_list_widget.py` - _setup_ui()

---

### 3. Mouse Wheel Zoom - Cursor-Centered (Major UX Improvement!)
**Feature**: Mouse wheel zoom now centers on cursor position instead of screen center

**Problem**: Original mouse wheel zoom was jumping to unpredictable centers, not screen center or cursor position.

**Solution**: 
1. Get GPS coordinates under cursor BEFORE zooming
2. Change zoom level
3. Calculate new map center so that GPS point stays under cursor
4. The point that was under your cursor stays there after zoom

**How It Works**:
```
Before zoom:        After wheel zoom in:
[●●●]               [●●●●●●●●●●●]
↑cursor             ↑cursor (same spot, zoomed in)
Same GPS point stays under cursor!
```

**Implementation Steps**:
```python
1. cursor_lat, cursor_lon = current_renderer.screen_to_gps(mouse_x, mouse_y)
2. Zoom to new_zoom level
3. new_renderer = MapRenderer(..., cursor_lat, cursor_lon, new_zoom)
4. Calculate offset to keep point under mouse
5. Adjust center: self.center_lat, self.center_lon = adjusted values
6. render_map()
```

**Why This is Better**:
- ✅ Zoom to where you're looking (like Google Maps)
- ✅ No need to pan after zooming
- ✅ Natural, intuitive behavior
- ✅ Professional UX

**Comparison**:
| Zoom Method | Center | Best For |
|------------|--------|----------|
| + Button | Screen center | Quick zoom |
| - Button | Screen center | Quick zoom |
| Mouse wheel ⭐ | Cursor | Precise zooming |

**Files Modified**:
- `src/gui/widgets/map_widget.py` - wheelEvent()

---

### 4. Comprehensive User Documentation
**Files Created**:

#### USER_GUIDE.md (12 KB)
Complete user guide covering:
- Getting started
- Opening/saving files
- Map navigation (all zoom methods)
- Layout control (splitter handle usage)
- Track and trackpoint management
- Coordinate format switching
- Undo/redo
- Turning points (trackpoints on map)
- Keyboard shortcuts reference
- Status bar interpretation
- Tips and tricks
- Troubleshooting
- Advanced topics

#### QUICK_REFERENCE.md (5.4 KB)
Quick reference guide for:
- ⭐ Mouse wheel zooming (most important feature!)
- Splitter handle usage (with visual guide)
- Quick tips for all operations
- File operations
- Coordinate format reference
- Show/hide trackpoints
- Splitter behavior constraints
- Common workflows with step-by-step
- Complete keyboard shortcuts list
- Where to get help

**Files Modified**:
- `README.md` - Added documentation references

---

## Technical Details

### Constraint Resolution
**Before** (broken):
```python
# In main_window.py
trackpoint_list_widget.setMaximumHeight(250)

# In trackpoint_list_widget.py
table_widget.setMinimumHeight(300)  # ❌ Exceeds maximum!
```

**After** (fixed):
```python
# In trackpoint_list_widget.py
table_widget.setMinimumHeight(50)  # ✅ Fits within widget bounds
```

### Splitter Configuration
```python
right_splitter = QSplitter(Qt.Vertical)
right_splitter.addWidget(trackpoint_list_widget)
right_splitter.addWidget(map_widget)
right_splitter.setSizes([400, 600])  # Initial: 40% trackpoints, 60% map
right_splitter.setCollapsible(0, False)  # Can't hide trackpoints
right_splitter.setCollapsible(1, False)  # Can't hide map
```

### Mouse Wheel Zoom Implementation
```python
def wheelEvent(self, event):
    # 1. Remember GPS point under cursor
    cursor_lat, cursor_lon = current_renderer.screen_to_gps(mouse_x, mouse_y)
    
    # 2. Calculate new zoom level
    new_zoom = ...
    
    # 3. Create renderer at new zoom centered on cursor GPS point
    new_renderer = MapRenderer(..., cursor_lat, cursor_lon, new_zoom)
    
    # 4. Find where cursor point appears at screen center
    screen_center_lat, screen_center_lon = new_renderer.screen_to_gps(width/2, height/2)
    
    # 5. Calculate offset to keep point under mouse
    mouse_pos_lat, mouse_pos_lon = new_renderer.screen_to_gps(mouse_x, mouse_y)
    
    # 6. Adjust center
    self.center_lat = cursor_lat + (screen_center_lat - mouse_pos_lat)
    self.center_lon = cursor_lon + (screen_center_lon - mouse_pos_lon)
    
    self.render_map()
```

---

## Testing

### All Tests Pass
```
145 passed in 1.27s ✅

- test_track_manager.py: All passing
- test_add_trackpoint.py: All passing
- test_command_history.py: All passing
- test_track_manager_history.py: All passing
```

### Manual Testing
- ✅ App starts cleanly
- ✅ GPX files load correctly
- ✅ Trackpoint list displays without clipping
- ✅ Splitter handle drags smoothly
- ✅ Mouse wheel zoom centers on cursor
- ✅ + / - buttons zoom to screen center
- ✅ All operations (add/delete/rename) work
- ✅ Undo/redo fully functional

---

## User-Facing Improvements

### Before
- ❌ Trackpoint list bottom was clipped/covered by map
- ❌ No way to adjust trackpoint/map height ratio
- ❌ Mouse wheel zoom center was unpredictable
- ❌ No comprehensive user documentation

### After
- ✅ Full trackpoint list always visible
- ✅ Drag splitter to adjust layout to your workflow
- ✅ Mouse wheel zoom centers exactly on cursor (like Google Maps)
- ✅ Complete user guide and quick reference
- ✅ Professional UX that feels polished

---

## Documentation Updates

### What Users Should Know
1. **See USER_GUIDE.md** for complete feature documentation
2. **See QUICK_REFERENCE.md** for quick tips and keyboard shortcuts
3. **Key Features**:
   - Mouse wheel zoom is now the recommended zoom method
   - Splitter handle allows flexible layout management
   - All operations are undoable with Ctrl+Z

### Key Sections
- **Mouse Wheel Zooming**: Most important new feature
- **Splitter Handle**: How to resize trackpoint/map areas
- **All Keyboard Shortcuts**: Complete reference
- **Troubleshooting**: Common issues and solutions

---

## Version Impact

### No Breaking Changes
- ✅ All existing GPX files work identically
- ✅ All keyboard shortcuts unchanged
- ✅ Configuration files unchanged
- ✅ Backward compatible with all saved layouts

### Purely Additive
- ✅ Layout improvements are transparent to users
- ✅ New documentation doesn't affect functionality
- ✅ Zoom improvements are backward compatible

---

## Next Steps (Recommendations)

### Immediate
- ✅ Users should read USER_GUIDE.md for full feature list
- ✅ Power users should bookmark QUICK_REFERENCE.md

### Future
- Consider adding in-app tooltips for splitter handle
- Consider adding zoom mode indicator in UI
- Consider remembering last splitter position in config

### Documentation
- USER_GUIDE.md is comprehensive and current
- QUICK_REFERENCE.md provides quick access
- Both integrate well with existing documentation

---

## Files Changed

### Modified Files
- `src/gui/main_window.py` - Splitter implementation, imports
- `src/gui/widgets/map_widget.py` - Mouse wheel zoom logic
- `src/gui/widgets/trackpoint_list_widget.py` - Table minimum height fix
- `README.md` - Added documentation references

### New Files
- `doc/USER_GUIDE.md` - Complete user guide (12 KB)
- `doc/QUICK_REFERENCE.md` - Quick reference (5.4 KB)
- `doc/RECENT_IMPROVEMENTS.md` - This file

### Unchanged (No impact)
- All test files pass
- All core functionality preserved
- All configuration files work unchanged

---

## Conclusion

Three major improvements that make mangpx significantly more professional and user-friendly:

1. **Fixed Layout** - No more clipped widgets
2. **Resizable Layout** - Flexible workspace management
3. **Smart Zoom** - Intuitive cursor-centered mouse wheel zoom

Plus comprehensive documentation so users know about and understand all these features!

**Result**: mangpx now feels like a polished, professional mapping application.

---
