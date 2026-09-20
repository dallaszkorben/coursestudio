# mangpx Quick Reference

## Zooming with Mouse Wheel ⭐

### The Most Important Feature!

**Point your cursor at a spot on the map and scroll:**
- **Scroll UP** → Zoom IN (that spot gets bigger, stays under cursor)
- **Scroll DOWN** → Zoom OUT (that spot gets smaller, stays under cursor)

The GPS location under your cursor **stays under your cursor** while you zoom. Just like Google Maps!

### Why This is Better Than + / - Buttons
- **Buttons**: Zoom to center of screen (fixed)
- **Mouse wheel**: Zoom to where your cursor is (natural, intuitive)
- **Result**: You can zoom into any part of the map without panning first

---

## Resizable Layout with Splitter Handle

### The Horizontal Line Between Trackpoints and Map

This is the **splitter handle** - a movable divider that controls panel heights.

### How to Use It
1. Move mouse to the horizontal line (between trackpoint table and map)
2. Cursor changes to resize cursor (↕)
3. Click and drag:
   - **UP** → More space for map, less for trackpoints
   - **DOWN** → More space for trackpoints, less for map
4. Release to keep the new size

### When to Use It
- **Many trackpoints to view?** Drag DOWN
- **Need to see map details?** Drag UP
- **Just editing metadata?** Keep trackpoints large

### Visual Guide
```
Splitter handle looks like this:
┌────────────────────────────┐
│   Trackpoint List (rows)   │
├────────────────────────────┤  ← SPLITTER HANDLE
│                            │     (drag this up/down)
│   Map Widget (interactive) │
│                            │
└────────────────────────────┘
```

---

## Quick Tips

### Zoom
| Method | Zoom Center | Best For |
|--------|----------|----------|
| Mouse wheel ⭐ | Cursor position | Precise zooming into details |
| + button | Screen center | Quick zoom without moving cursor |
| - button | Screen center | Quick zoom out |
| Ctrl+Plus | Screen center | Keyboard-only zoom |
| Ctrl+Minus | Screen center | Keyboard-only zoom |

### Pan
| Method | How |
|--------|-----|
| Click & drag | Click on map and drag left/right/up/down |
| Arrow keys | Hold arrow key to pan smoothly |
| Home key | Return to initial position |

### Edit
| Operation | Shortcut |
|-----------|----------|
| Add point | Ctrl+N |
| Delete point | Delete key |
| Rename track | F2 |
| Undo | Ctrl+Z |
| Redo | Ctrl+Y |

---

## File Operations

| Operation | Shortcut | Notes |
|-----------|----------|-------|
| Open | Ctrl+O | Load .gpx file |
| Save | Ctrl+S | Save to current file (creates backup) |
| Save As | Ctrl+Shift+S | Save with new name |

---

## Coordinate Formats

**DMS (Degrees Minutes Seconds)**
- Format: 57°30'45.5"N 12°15'30.2"E
- Pros: Precise, traditional
- Cons: More text to read

**Decimal**
- Format: 57.5126°N 12.2584°E
- Pros: Concise, easier calculations
- Cons: Less intuitive at first

Switch formats in the trackpoint list dropdown: "Format: [DMS/Decimal]"

---

## Trackpoints: Show or Hide

**Dropdown**: "Show points: [Yes/No]"

- **Yes** - See all points as yellow circles on map (default)
- **No** - Hide point markers (useful for cleaner map view)

Click any point circle on map to select it in the table.

---

## Splitter Behavior

### What Can't Happen
- ❌ Trackpoint list can't collapse completely (minimum 100px)
- ❌ Map can't collapse completely (minimum 300px)
- ❌ Can't resize beyond window boundaries

### What Can Happen
- ✅ Drag splitter anywhere between limits
- ✅ Position remembered in current session
- ✅ Smooth dragging, no stuttering
- ✅ Can resize while map is rendering

---

## Status Bar Info

Bottom of window shows:
```
Ready | Points: 519 | Distance: 19.12km | Zoom: 15
```

- **Status**: Current operation or "Ready"
- **Points**: How many trackpoints in current track
- **Distance**: Total kilometers of current track
- **Zoom**: Current zoom level (10-16 available)

---

## Common Workflows

### Workflow 1: Zoom into a Specific Area
1. Point cursor at area on map
2. Scroll mouse wheel up (zoom in)
3. Scroll more to get closer
4. Position stays under cursor naturally ✓

### Workflow 2: See More Trackpoints
1. Drag splitter DOWN
2. Trackpoint list gets taller
3. Can now see more rows without scrolling

### Workflow 3: Focus on Map Details
1. Drag splitter UP
2. Map gets taller, trackpoint list shorter
3. Better view of map features

### Workflow 4: Add New Point
1. Ctrl+N to open add dialog
2. Enter coordinates (DMS or Decimal)
3. Choose position (at end or specific index)
4. Click OK
5. Ctrl+Z to undo if needed

---

## Keyboard Shortcuts - All of Them

```
FILE OPERATIONS
Ctrl+O        Open GPX file
Ctrl+S        Save file
Ctrl+Shift+S  Save as

EDITING
Ctrl+Z        Undo
Ctrl+Y        Redo
Ctrl+N        Add trackpoint
Ctrl+D        Delete trackpoint
Delete        Delete selected point
F2            Rename track

MAP NAVIGATION
Mouse Wheel   Zoom (cursor-centered) ⭐
Ctrl+Plus     Zoom in
Ctrl+Minus    Zoom out
Home          Return to initial position
Ctrl+Home     Recenter to track
Arrow Keys    Pan in all directions

VIEW
Ctrl+Plus     Zoom in
Ctrl+Minus    Zoom out
```

---

## Need Help?

- **Full Guide**: See `USER_GUIDE.md`
- **Architecture**: See `ARCHITECTURE.md`
- **Configuration**: See `CONFIGURATION_GUIDE.md`
- **Known Issues**: See `README.md`

---
