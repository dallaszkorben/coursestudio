# mangpx User Guide

## Overview
mangpx is a PyQt5-based desktop application for viewing, editing, and manipulating GPX (GPS Exchange Format) files with interactive map visualization. This guide covers all features and how to use them.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Opening and Saving Files](#opening-and-saving-files)
3. [Map Navigation](#map-navigation)
4. [Layout Control](#layout-control)
5. [Track Management](#track-management)
6. [Trackpoint Management](#trackpoint-management)
7. [Coordinate Formats](#coordinate-formats)
8. [Undo/Redo](#undoredo)

---

## Getting Started

### Starting the Application
```bash
python src/main.py
```

The application window displays:
- **Left Panel**: Track list
- **Right Panel (Top)**: Trackpoint list
- **Right Panel (Bottom)**: Interactive map

---

## Opening and Saving Files

### Open a GPX File
**Menu**: File → Open GPX File...  
**Shortcut**: Ctrl+O

1. Click "Open GPX File..." or press Ctrl+O
2. Select a .gpx file from the file browser
3. File loads automatically
4. All tracks appear in the left panel
5. Select a track to view its details

### Save File
**Menu**: File → Save  
**Shortcut**: Ctrl+S

- Saves changes to the currently loaded file
- Creates automatic backup before saving (filename_BACKUP.gpx)
- Status bar confirms save completion

### Save As
**Menu**: File → Save As  
**Shortcut**: Ctrl+Shift+S

- Save the current file with a new name
- Backup created with original name

---

## Map Navigation

### Zoom Controls

#### Method 1: Zoom Buttons
Located in the bottom-left corner of the map:
- **+ Button**: Zoom in one level
- **- Button**: Zoom out one level
- **Zoom center**: Middle of screen (no change in center point)

#### Method 2: Mouse Wheel (Cursor-Centered Zoom) ⭐
**This is the recommended way to zoom!**

**How it works:**
1. **Point your mouse cursor** at any location on the map
2. **Scroll the mouse wheel**:
   - **Scroll UP** → Zoom IN (that spot gets bigger, stays under cursor)
   - **Scroll DOWN** → Zoom OUT (that spot gets smaller, stays under cursor)
3. The GPS location under your cursor **remains under your cursor** while zooming

**Example:**
```
Before zoom:     After zoom in:
┌─────────────┐  ┌─────────────┐
│   [●●●]     │  │[●●●●●●●●●●●]│
│    ↑cursor  │  │   ↑cursor   │
└─────────────┘  └─────────────┘
Same point stays under cursor!
```

**Advantages:**
- Zoom into specific areas naturally
- Zoom is centered where you're looking, not middle of screen
- Works like Google Maps, OpenStreetMap, all modern mapping apps
- Much more intuitive than fixed center zooming

#### Method 3: Keyboard
- **Ctrl+Plus** (Ctrl+=): Zoom in
- **Ctrl+Minus** (Ctrl+-): Zoom out

### Pan (Move Map)
**How to pan:**
1. **Click and drag** on the map with left mouse button
2. Map follows your mouse movement
3. Release to stop panning

**Keyboard:**
- **Arrow Keys**: Pan in each direction
- **Home**: Return to default map position (initial track center)

### Recenter Map
**Button**: ⊙ button in bottom-left corner (or **Ctrl+Home**)

Resets map to the initial center position of the loaded track.

---

## Layout Control

### Resizable Panels with Splitter Handle

The right side of the window has a **horizontal splitter handle** between the trackpoint list and map.

#### What is the Splitter Handle?
A movable divider line that lets you adjust the size of the panels above and below it.

#### How to Use It:
1. **Locate the splitter handle**: Look for a horizontal line between the trackpoint list and map
2. **Move your mouse to the handle**: Cursor changes to a resize cursor (↕)
3. **Click and drag**:
   - **Drag UP** → Trackpoint list gets smaller, map gets bigger
   - **Drag DOWN** → Trackpoint list gets bigger, map gets smaller
4. **Release** to lock the new size

#### Visual Guide:
```
Before:                          After dragging down:
┌─────────────────────────────┐  ┌─────────────────────────────┐
│    Trackpoints (400px)      │  │  Trackpoints (250px)        │
├─────────────────────────────┤  ├─────────────────────────────┤
│ ↑ DRAG HANDLE HERE          │  │ Map (550px)                 │
│                             │  │                             │
│      Map (600px)            │  │                             │
│                             │  │                             │
│                             │  │                             │
└─────────────────────────────┘  └─────────────────────────────┘
```

#### Why Use It?
- **Many trackpoints?** → Drag DOWN to see full table
- **Need to see map details?** → Drag UP to maximize map area
- **Flexible layout** → Adjust to your workflow

#### Constraints:
- Trackpoint list: minimum 100px, no maximum
- Map: minimum 300px, no maximum
- Together must fit in window height
- Neither panel can collapse completely

---

## Track Management

### View Track List
**Left Panel**: Displays all tracks in loaded file

Each track shows:
- Track name
- Total distance (km)
- Number of points

### Select a Track
**Left Click** on track name

Selected track:
- Highlighted in list
- Trackpoints appear in right panel
- Track path displays on map (red line)
- All trackpoints visible (if "Show points: Yes")

### Rename Track
**Menu**: Edit → (Right-click track) → Rename  
**Shortcut**: F2 (when track selected)

1. Select track in list
2. Choose rename option
3. Enter new name
4. Press Enter to confirm

### Delete Track
**Right-click** on track → Delete

⚠️ **Warning**: This cannot be undone without using File → Revert

### Add Trackpoint
**Menu**: Edit → Add Trackpoint  
**Shortcut**: Ctrl+N

Opens dialog to add new point to track:
1. Enter latitude (DMS or Decimal format)
2. Enter longitude (DMS or Decimal format)
3. Optional: Enter elevation in meters
4. Choose position: "At end" or "At specific index"
5. Click OK to add

---

## Trackpoint Management

### Trackpoint List
**Right Panel (Top)**: Table of all trackpoints in selected track

Columns:
- **#**: Point index (0-based)
- **Latitude**: In selected format (DMS or Decimal)
- **Longitude**: In selected format (DMS or Decimal)
- **Elevation**: Height in meters (if available)
- **Timestamp**: Date/time recorded (if available)

### Select a Trackpoint
**Click row** in trackpoint table

Selected point:
- Highlighted in table (blue background)
- Highlighted on map (blue circle)
- Details shown in status bar

### Delete Trackpoint
**Right-click** on trackpoint → Delete  
**Shortcut**: Delete key (when point selected)

Options:
- **Delete** - Remove single point
- **Delete from Start** - Remove all points up to selected
- **Delete from End** - Remove selected point to end

### Coordinate Format

#### DMS (Degrees, Minutes, Seconds) Format
**Example**: 57°30'45.5"N 12°15'30.2"E

Default format. Shows precise coordinates with degree symbol (°), minute ('), and second (") notation.

#### Decimal Format
**Example**: 57.5126°N 12.2584°E

Shows latitude/longitude as decimal numbers. More concise, easier for calculations.

#### Change Format
**Dropdown**: Format selector in right panel (top)

1. Select "DMS" or "Decimal"
2. Table updates immediately
3. Format preference saved for next session

---

## Undo/Redo

### Undo
**Menu**: Edit → Undo  
**Shortcut**: Ctrl+Z

Reverses last operation:
- Add trackpoint → removed
- Delete trackpoint → restored
- Rename track → original name restored

Menu shows: "Undo: [Operation]" (e.g., "Undo: Add Point")

### Redo
**Menu**: Edit → Redo  
**Shortcut**: Ctrl+Y

Reapplies operation that was undone.

Menu shows: "Redo: [Operation]"

### History
- Unlimited undo/redo (up to 100 operations by default)
- Operations include: add point, delete point, delete range, rename track
- History cleared when saving file
- Each operation is fully reversible

---

## Turning Points (Trackpoints on Map)

### Show/Hide Points
**Dropdown**: "Show points" selector in trackpoint list panel

- **Yes** - Display all trackpoints as circles on map
- **No** - Hide trackpoint markers

### Point Appearance
- **Default color**: Yellow circles
- **Selected point**: Blue circle (larger)
- **Track path**: Red line connecting all points

### Clicking Points on Map
Click any point circle on map:
- Corresponding row highlights in table
- Point details shown in status bar
- Point selected for operations (delete, etc.)

---

## Keyboard Shortcuts Reference

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open GPX file |
| Ctrl+S | Save file |
| Ctrl+Shift+S | Save as new file |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+N | Add trackpoint |
| Ctrl+D | Delete trackpoint |
| Delete | Delete selected trackpoint |
| Ctrl++ | Zoom in |
| Ctrl+- | Zoom out |
| Ctrl+Home | Recenter map |
| Home | Go to default position |
| Arrow Keys | Pan map |
| F2 | Rename track (when selected) |
| Mouse Scroll | Zoom (cursor-centered) |

---

## Status Bar

Bottom of window shows:
- **Ready** / Operation status
- **Points: N** - Total trackpoints in current track
- **Distance: Nkm** - Total track distance
- **Zoom: Z** - Current zoom level

Click on any trackpoint to see detailed coordinates in status bar.

---

## Tips and Tricks

### Zooming Tips
- **Use mouse wheel for best zoom experience** - naturally centers on cursor
- **Use + / - buttons for fixed center zoom** (middle of screen)
- **Combine with panning** - wheel zoom + drag = very natural navigation

### Layout Tips
- **Large tracks with many points?** → Drag splitter down to see more trackpoints
- **Need to see map details?** → Drag splitter up for larger map
- **Frequently change?** → Splitter position is remembered in sessions

### Editing Tips
- **Always Save before closing** → Changes lost otherwise (except undo within session)
- **Check distance after editing** → Status bar shows updated distance
- **Use undo liberally** → No cost to experimenting with Ctrl+Z

### Navigation Tips
- **Zoom wheel** → Most intuitive zoom
- **Click and drag** → Quickest panning
- **Keyboard arrows** → Precise panning control
- **Home key** → Quick return to track start

---

## Troubleshooting

### Map Won't Display
- Ensure mbtiles file exists in `mbtiles/` directory
- Check `config/settings.yaml` for correct filename
- Verify zoom level is supported by tileset
- Try zooming to a different level

### Trackpoints Not Showing
- Check "Show points" dropdown is set to "Yes"
- Verify track is selected in left panel
- Try panning/zooming to refresh view

### Performance Issues with Large Tracks
- Set "Show points: No" to hide point markers
- Reduce number of points (delete unnecessary ones)
- Zoom to see only relevant section

### File Won't Save
- Ensure file is writable (check permissions)
- Verify disk space available
- Check path doesn't contain invalid characters

---

## Advanced Topics

### Configuration
See `config/settings.ini` for customization options:
- Track path color and width
- Turning point colors and sizes
- Default zoom level
- Coordinate format defaults

### Map Data
- Current map: Sweden-Raster-Z10-Z16.mbtiles
- Coverage: Swedish archipelago
- Zoom levels: 10-16 (15 most detailed)

To use different maps, place .mbtiles file in `mbtiles/` and update settings.

---

## Getting Help

- **Questions?** Check this guide or README.md
- **Bug reports**: See CONTRIBUTING.md
- **Feature requests**: Open GitHub issue
- **Documentation**: See `doc/` folder

---

## Version Information

- **Application**: mangpx v1.0.0
- **Last Updated**: 2026-09-21
- **Python**: 3.8+
- **Framework**: PyQt5

---
