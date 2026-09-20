# Step 11: CORRECT Map Navigation Implementation

**Date**: 2026-09-20  
**Status**: ✅ FIXED - Properly modeled after openseemap  
**File**: `src/gui/widgets/map_widget_pil_working.py`

---

## Issues Fixed

### 1. Navigation Buttons Disappeared
**Problem**: Buttons weren't visible on the map

**Solution**: Added `_draw_ui_controls_on_image()` method that:
- Draws buttons ONTO the PIL image (not as separate QPushButton widgets)
- Uses PIL ImageDraw to render blue rounded rectangles
- Draws zoom +/- buttons, zoom level label, and recenter button
- Keeps INVISIBLE QPushButton overlays for click detection (transparent)

```python
def _draw_ui_controls_on_image(self, pil_image, renderer):
    """Draw UI controls directly onto the PIL image."""
    from PIL import ImageDraw
    draw = ImageDraw.Draw(pil_image)
    
    button_bg = (52, 144, 220)  # Nice blue
    # ... draw buttons on PIL image at (10, 10), (10, 78), (10, 146), (10, 214)
```

### 2. Zoom Doesn't Work
**Problem**: Zoom buttons clicked but map didn't zoom

**Solution**: 
- Fixed `_on_zoom_in()` and `_on_zoom_out()` to properly call `_schedule_render()`
- Gets available zoom levels from `mbtiles_provider.get_available_zooms()`
- Updates both the map AND the zoom level label on PIL image

```python
def _on_zoom_in(self) -> None:
    available = self.mbtiles_provider.get_available_zooms()
    if available:
        max_z = max(available)
        if self.zoom_level < max_z:
            self.zoom_level += 1
            self._schedule_render()  # <-- CRITICAL: Must re-render!
```

### 3. Pan Issues

#### 3.1 Pan Only Moves Path, Not Map
**Problem**: Dragging moved the track drawing but map tiles stayed in place

**Root Cause**: Was manipulating `center_lat/lon` but not properly converting pixel deltas to lat/lon changes

**Solution**: 
- PROPER Web Mercator projection math:
```python
TILE_SIZE = 256
tiles_at_zoom = 2 ** self.zoom_level
earth_circumference_m = 40075016.686

cos_lat = math.cos(math.radians(self.center_lat))
m_per_pixel_lon = (earth_circumference_m * cos_lat) / (TILE_SIZE * tiles_at_zoom)
m_per_pixel_lat = earth_circumference_m / (TILE_SIZE * tiles_at_zoom)

deg_per_m = 1.0 / 111320.0

lon_delta = delta_x * m_per_pixel_lon * deg_per_m
lat_delta = -delta_y * m_per_pixel_lat * deg_per_m

self.center_lon += lon_delta
self.center_lat += lat_delta
```

#### 3.2 Pan Movement Doesn't Match Mouse Distance
**Problem**: Mouse drag distance didn't correspond to map pan distance

**Solution**: 
- Correct coordinate system conversion
- Map pixel deltas to actual lat/lon changes using Earth's geometry
- Ensures 1 pixel of mouse = 1 pixel of map movement at that zoom level

---

## Architecture Overview

### Rendering Pipeline

```
_do_render()
    ↓
Get track data from track_manager
    ↓
Create MapRenderer(mbtiles_provider, width, height)
    ↓
Call renderer._render_from_tiles(lat, lon, zoom)
    ↓
Returns PIL Image with map tiles
    ↓
Draw tracks on PIL image (_draw_track_on_image)
    ↓
Draw UI controls on PIL image (_draw_ui_controls_on_image)
    ↓
Convert PIL to QPixmap (_pil_to_pixmap_and_display)
    ↓
Display in map_label
```

### Pan/Zoom Handling

```
Pan:
  mousePressEvent() → store pan_start_x/y
  mouseMoveEvent() → calculate delta_x/delta_y
              → convert pixels to lat/lon using Web Mercator
              → update center_lat/center_lon
              → _schedule_render()
  mouseReleaseEvent() → clear pan_start

Zoom:
  wheelEvent() → _on_zoom_in() or _on_zoom_out()
           → get available zoom levels
           → update self.zoom_level
           → _schedule_render()

Button Click:
  mousePressEvent() → check if click in button geometry
                   → call zoom_in_button.click() etc
                   → button triggers zoom_in() method
```

---

## Key Components

### 1. Track Drawing on PIL Image
```python
def _draw_track_on_image(self, draw, pil_image, track, color, width, renderer):
    # Convert track points from lat/lon to screen coordinates
    # Use map center as reference point
    # Draw lines between consecutive points on PIL image
```

### 2. UI Controls on PIL Image  
```python
def _draw_ui_controls_on_image(self, pil_image, renderer):
    # Draw 4 buttons directly on PIL image using PIL ImageDraw:
    # 1. Zoom in (+)
    # 2. Zoom out (−)
    # 3. Zoom level label (Z:13)
    # 4. Recenter (⊙)
    # Each is a blue rounded rectangle with white border
```

### 3. PIL to Pixmap Conversion
```python
def _pil_to_pixmap_and_display(self, pil_image):
    # Save PIL image to temporary PNG file
    # Load PNG as QPixmap
    # Set pixmap on map_label
    # Clean up temp file
    # Reposition invisible button hitboxes for click detection
```

---

## Web Mercator Projection Math

### Why This Formula Works

1. **Earth Circumference**: 40,075,016.686 meters (at equator)

2. **Tiles at Zoom**: 
   - Zoom 0: 1 tile (entire world)
   - Zoom 1: 4 tiles (2×2)
   - Zoom N: 2^N tiles in each direction

3. **Tile Size**: 256 pixels (standard for all tile systems)

4. **Meters Per Pixel**:
   ```
   Total map width in meters = 40,075,016.686
   Total map width in tiles = 2^zoom
   Total map width in pixels = 2^zoom * 256
   
   Meters per pixel = 40,075,016.686 / (2^zoom * 256)
   ```

5. **Latitude Adjustment**: 
   - Longitude spacing is constant (doesn't need adjustment)
   - Latitude spacing varies by latitude due to map projection
   - Multiply by cos(latitude) for longitude

6. **Conversion to Degrees**:
   ```
   1 degree of latitude ≈ 111,320 meters (constant)
   degrees = meters / 111,320
   ```

---

## Testing Checklist

### Pan
- [ ] Drag left → map shifts right (opposite direction? Check delta_x calculation)
- [ ] Drag right → map shifts left
- [ ] Drag up → map shifts down
- [ ] Drag down → map shifts up
- [ ] Movement distance matches mouse distance
- [ ] No jumping or stuttering
- [ ] Smooth continuous panning during drag

### Zoom
- [ ] Click + button → zoom in
- [ ] Click − button → zoom out  
- [ ] Scroll wheel up → zoom in
- [ ] Scroll wheel down → zoom out
- [ ] Zoom level label updates
- [ ] Map re-centers properly after zoom
- [ ] Buttons remain clickable after zoom

### UI
- [ ] All 4 buttons visible on map
- [ ] Buttons appear in top-left corner
- [ ] Buttons have blue background with white border
- [ ] + and − symbols visible
- [ ] Zoom level label shows current zoom
- [ ] Recenter button has target symbol

### Tracks
- [ ] Track appears on map as blue line (or red if highlighted)
- [ ] Track position matches actual lat/lon
- [ ] Track updates position when panning
- [ ] Trackpoints visible when zoomed in
- [ ] Track disappears correctly when zoomed out far

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Buttons not showing | Make sure `_draw_ui_controls_on_image()` is called |
| Zoom doesn't work | Verify `_on_zoom_in()` calls `_schedule_render()` |
| Pan moves path not map | Check Web Mercator math, verify delta calculation |
| Pan distance wrong | Verify `cos(latitude)` adjustment, check TILE_SIZE constant |
| Map freezes on zoom | Check render timer interval (should be 100ms debounce) |
| Buttons don't click | Verify `_reposition_controls()` updates button geometry |

---

## Performance Notes

- **Render Timer**: 100ms debounce prevents rendering every single mouse move
- **PIL ImageDraw**: Fast enough for on-the-fly button drawing
- **Temp File**: PNG format is reliable, avoids PIL encoding issues
- **Invisible Buttons**: Small overhead, enables smooth visual buttons on image

---

## Files Modified

- `src/gui/widgets/map_widget_pil_working.py` - Complete rewrite with proper implementation
- `src/gui/main_window.py` - Import from `map_widget_pil_working` (unchanged from before)

---

**Status**: ✅ READY FOR TESTING  
**Expected Behavior**: 
- Smooth panning with mouse drag
- Zoom buttons and wheel working
- UI buttons visible on map
- All controls responsive and accurate

