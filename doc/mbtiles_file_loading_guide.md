# MBTiles File Loading - State Management Guide

**Date:** 2026-10-18  
**Component:** `src/shared/map/mbtiles_file_loader.py`  
**Purpose:** Intelligent state reset and configuration when loading new mbtiles files

---

## Overview

When a user opens a new mbtiles file in the Map Editor:

1. **All previous map state is cleared** (recent_zoom, recent_center, recent_mbtiles)
2. **Metadata is read** from the new mbtiles file (center, bounds, zoom levels)
3. **Optimal initial position is determined** using priority logic
4. **settings.yaml is updated** with new configuration
5. **Map Editor UI is updated** with File Characteristics

---

## Priority Logic for Initial Position

When determining where to center the map, this priority is used:

### Case 1: Both center AND zoom exist in mbtiles metadata
```yaml
available_center: true
available_zoom: true
→ Use center + zoom from metadata
```

**Example:**
- mbtiles has `center: [15.5, 56.14, 13]`
- Zoom 13 is available in tileset
- **Result:** Use center (56.14°N, 15.5°E) at zoom 13

### Case 2: Center exists but zoom doesn't
```yaml
available_center: true
available_zoom: false
→ Use center + lowest available zoom
```

**Example:**
- mbtiles has `center: [15.5, 56.14, 13]`
- Zoom 13 is NOT available (only Z11, Z12, Z14, Z15, Z16)
- **Result:** Use center (56.14°N, 15.5°E) at zoom 11

### Case 3: Zoom exists but center doesn't
```yaml
available_center: false
available_zoom: true
→ Try old center at new zoom, OR find any available tile
```

**Example A (old center still valid):**
- Previous center: (56.14°N, 15.5°E)
- New zoom level: 14
- Previous center has tiles at zoom 14
- **Result:** Keep (56.14°N, 15.5°E) at zoom 14

**Example B (old center invalid):**
- Previous center: (56.14°N, 15.5°E)
- New zoom level: 14
- Previous center does NOT have tiles at zoom 14
- Find ANY tile at zoom 14, use its position
- **Result:** Move to valid position at zoom 14

### Case 4: Neither center nor zoom exist
```yaml
available_center: false
available_zoom: false
→ Use lowest zoom + first available tile
```

**Example:**
- mbtiles has no center or zoom metadata
- Lowest available zoom: 8
- Query database: Find first tile at zoom 8
- **Result:** Use that tile's center position at zoom 8

---

## State Reset Process

When loading a new mbtiles file, all previous state is cleared:

| Setting | Before | After |
|---------|--------|-------|
| `recent_mbtiles` | old-file.mbtiles | new-file.mbtiles |
| `recent_zoom` | 13 | [determined from logic above] |
| `recent_center.lat` | 56.14 | [determined from logic above] |
| `recent_center.lon` | 15.50 | [determined from logic above] |
| `default_zoom` | 14 | [same as recent_zoom] |
| `default_center.lat` | 56.17 | [same as recent_center.lat] |
| `default_center.lon` | 15.59 | [same as recent_center.lon] |

**Key:** default_zoom and default_center are set equal to recent_zoom and recent_center.

---

## Integration Points

### 1. File Browser or File Dialog

When user selects new mbtiles file:

```python
from src.shared.map.mbtiles_file_loader import MBTilesFileLoader
from src.map_editor.core.mbtiles_reader import MBTilesReader

# User selected: /path/to/new_file.mbtiles
new_file_path = "/path/to/new_file.mbtiles"

# Load mbtiles metadata
reader = MBTilesReader(new_file_path)

# Determine optimal configuration
loader = MBTilesFileLoader(reader, self.config)
config_result = loader.load_and_configure(new_file_path)

# config_result contains:
# - recent_mbtiles: file path
# - recent_zoom: calculated zoom
# - recent_center: dict with lat/lon
# - default_zoom: same as recent_zoom
# - default_center: same as recent_center
# - available_zooms: list of all available zoom levels
# - metadata: MBTilesMetadata object
# - min_zoom, max_zoom: extent of available zooms
```

### 2. Map Editor Characteristics Panel

Update File Characteristics to show:

```python
characteristics = {
    'File': config_result['recent_mbtiles'],
    'Name': config_result['metadata'].name,
    'Format': config_result['metadata'].format,
    'Version': config_result['metadata'].version,
    'Zoom Range': f"Z{config_result['min_zoom']}-Z{config_result['max_zoom']}",
    'Center': f"{config_result['recent_center']['lat']:.4f}, {config_result['recent_center']['lon']:.4f}",
    'Zoom': config_result['recent_zoom'],
    'Total Tiles': sum(zl.tile_count for zl in reader.zoom_levels),
}
```

### 3. Map Display

Update map to show new position:

```python
# Get new configuration
lat = config_result['recent_center']['lat']
lon = config_result['recent_center']['lon']
zoom = config_result['recent_zoom']

# Update map display
self.map_widget.center_lat = lat
self.map_widget.center_lon = lon
self.map_widget.zoom_level = zoom
self.map_widget.render_map()

# Emit signal to sync other tabs
self.config.emit_map_position_changed()
```

---

## Settings.yaml Structure

Before loading new file:
```yaml
appearance:
  tiles:
    recent_mbtiles: old_file.mbtiles
    recent_zoom: 13
    recent_center:
      lat: 56.14340022
      lon: 15.50019145
    default_zoom: 14
    default_center:
      lat: 56.16818152
      lon: 15.58868289
```

After loading new file (via MBTilesFileLoader):
```yaml
appearance:
  tiles:
    recent_mbtiles: new_file.mbtiles
    recent_zoom: 11  # calculated from metadata or tiles
    recent_center:
      lat: 57.2345  # from metadata or found tile
      lon: 12.5678
    default_zoom: 11  # same as recent_zoom
    default_center:
      lat: 57.2345  # same as recent_center
      lon: 12.5678
```

---

## Implementation Checklist

- [ ] **MBTilesFileLoader class created** ✅
- [ ] **Integrate into Map Editor file selection** - TODO
- [ ] **Update File Characteristics panel** - TODO
- [ ] **Update map display on file load** - TODO
- [ ] **Test Case 1:** Both center and zoom available
- [ ] **Test Case 2:** Center only
- [ ] **Test Case 3:** Zoom only (old center valid)
- [ ] **Test Case 3b:** Zoom only (old center invalid)
- [ ] **Test Case 4:** Neither available
- [ ] **Test with multiple mbtiles files** - Different zoom ranges, different bounds
- [ ] **Verify settings.yaml correctly updated**
- [ ] **Verify sync between Track Editor and Map Editor** - Both show same position

---

## Error Handling

| Situation | Behavior |
|-----------|----------|
| File not found | MBTilesReader raises FileNotFoundError before loader runs |
| Invalid mbtiles format | MBTilesReader raises ValueError before loader runs |
| No metadata | Use Case 4 (lowest zoom + first available tile) |
| No tiles in file | Fallback to world center (0, 0) at lowest zoom |
| Database query fails | Log error, return fallback position |
| settings.yaml not writable | Log warning, continue (UI updates will be lost on restart) |

---

## Logging

All operations are logged at appropriate levels:

```
INFO: MBTilesFileLoader initialized
DEBUG: Available zoom levels: [8, 9, 10, 11, 12, 13, 14, 15, 16]
DEBUG: Metadata center: (15.5, 56.14, 13)
INFO: Clearing previous map state
INFO: Determining initial position using priority logic
INFO: Case 2: Using center (56.14, 15.5) with lowest zoom 11
INFO: Determined initial position: Z11 @ (56.1434, 15.5002)
INFO: Updating settings.yaml with new mbtiles configuration
INFO: Settings.yaml updated and saved
```

Enable by setting `advanced.debugging.log_level: DEBUG` in settings.yaml.

---

## Future Enhancements

- [ ] **Zoom history:** Remember zoom levels used for different mbtiles files
- [ ] **Bookmarks:** Save favorite positions within a mbtiles file
- [ ] **Quick switch:** Dropdown to quickly switch between recently-opened mbtiles
- [ ] **Metadata editor:** Allow user to edit center/bounds/name within app
- [ ] **Validation:** Verify new file actually contains tiles before committing to settings

---

**Related Files:**
- `src/shared/map/mbtiles_file_loader.py` - Implementation
- `src/map_editor/core/mbtiles_reader.py` - Metadata reading
- `config/app_config_yaml.py` - Settings management
- `config/settings.yaml` - Configuration file
