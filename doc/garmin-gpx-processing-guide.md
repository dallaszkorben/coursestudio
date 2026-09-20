# Garmin GPX/ADM File Processing Guide

## Session Summary: Karlskrona-Hallarum Track Cleaning

### Source Data
- **Device:** Garmin echoMAP 50s
- **SD Card Location:** `/media/akoel/F43B-5EF51/GARMIN/`
- **Files processed:**
  - `UserData/EXPORT FROM GPSM.ADM` (1.1 MB - binary ADM disk image)
  - `UserData/A.GPX` (1.8 MB - XML with 6 marine navigation tracks)
  - `GPX/` folder (multiple individual track GPX files)

---

## Key Problem Solved

### Issue: ADM File Multiple Tracks Not Extractable
**Problem:** Garmin USERDATA.TRK binary file contains 7 track names but only first track visible via parsetrk tool
- **Names found:** Hallarum-Simrishamn, Hallarum-Stadsmarina, KARLSKRONA-HALLARUM, Simrishamn-Hallarum, Tormhamn-Hallarum, TR-ASP, TR-HALLARUM 26-08-09

**Solution:** Skip ADM parsing entirely - use A.GPX file instead
- A.GPX contains all 6 tracks in readable XML format
- Much easier to work with than binary TRK format

### Tools Attempted vs What Actually Worked

❌ **Did NOT work:**
- `gpsbabel` - Doesn't support ADM/TRK binary format directly
- `parsetrk` (from parsefsh) - Only extracts first track sequentially
- Manual binary parsing - Garmin format undocumented

✅ **What WORKED:**
- Extract from A.GPX file directly (XML format, human-readable)
- Regex pattern matching to find and modify specific tracks
- Python ElementTree for XML validation

---

## A.GPX File Structure

### 6 Tracks in A.GPX:
1. **KARLSKRONA-HALLARUM** - 519 points (cleaned, was 536 with return jump)
2. **ORIGINAL MIKAEL** - 1,787 points (large archive track)
3. **Simrishamn-Hallarum** - 3,323 points (longest)
4. **Tormhamn-Hallarum** - 1,155 points
5. **TR-ASP 26-06-14** - 638 points (date-coded)
6. **TR-HALLARUM 26-08-09** - 1,787 points (date-coded)

### File Format
- XML-based GPX 1.1 format
- Contains waypoints (wpt), routes (rte), and tracks (trk)
- Uses Garmin extensions (gpxx namespace)
- CRLF line terminators
- Some tracks have null bytes/encoding issues (e.g., "TR-ASP" has embedded special char)

---

## Track Cleaning Process: Karlskrona-Hallarum Example

### Problem Identified
- Original track: 536 points, 34.32 km
- Recording continued after arrival at Hallarum
- Device turned off, then turned back on at Karlskrona
- Result: 14.81 km jump from Hallarum back to Karlskrona
- Points 519-535: Return journey data (17 points)

### Solution Steps
1. Parse A.GPX and find KARLSKRONA-HALLARUM track
2. Extract all trackpoints (lat/lon pairs)
3. Analyze distances between consecutive points to find jumps
4. Identified large jump at point 518→519 (14.81 km)
5. Keep points 0-518 (Hallarum endpoint), discard 519-535
6. Result: 19.12 km clean track from Karlskrona to Hallarum

### Files Generated
- `/tmp/KARLSKRONA-HALLARUM.gpx` - Original extracted track (536 points)
- `/tmp/KARLSKRONA-HALLARUM-CLEANED.gpx` - Cleaned version (519 points)
- `/tmp/KARLSKRONA-HALLARUM-CLEANED-MAP.html` - Interactive Leaflet.js map

### Updated Original
- Modified `/media/akoel/F43B-5EF51/GARMIN/UserData/A.GPX` in-place
- Used direct string replacement (not regex - more reliable)
- Replaced old `<trkseg>...</trkseg>` section with cleaned trackpoints
- Verified: 519 trackpoints in updated file

---

## Code Patterns That Worked

### Reading GPX Files (Reliable Method)
```python
with open('/path/to/file.gpx', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# For XML parsing (with namespace handling):
import xml.etree.ElementTree as ET
ET.register_namespace('', 'http://www.topografix.com/GPX/1/1')
tree = ET.parse(file)
```

### Finding and Extracting Trackpoints
```python
trkpt_pattern = r'<trkpt lat="([^"]+)" lon="([^"]+)"\s*/>'
trackpoints = re.findall(trkpt_pattern, content)
lats = [float(p[0]) for p in trackpoints]
lons = [float(p[1]) for p in trackpoints]
```

### Detecting Track Anomalies
```python
def haversine(lat1, lon1, lat2, lon2):
    # Calculate distance between consecutive points
    # Large gaps (>1-5 km) indicate problems or intentional jumps
```

### Updating GPX Files (Direct String Replacement)
```python
# Find exact section to replace:
start_idx = content.find('<trkseg>', track_start_idx)
end_idx = content.find('</trkseg>', start_idx) + len('</trkseg>')
old_section = content[start_idx:end_idx]

# Build new section:
new_section = '<trkseg>\n' + ''.join(f'<trkpt lat="{lat}" lon="{lon}"/>\n' for lat, lon in new_points) + '</trkseg>'

# Replace and write:
updated = content.replace(old_section, new_section)
```

---

## Lessons Learned

### ADM/TRK Binary Format
- Undocumented and proprietary
- parsetrk tool treats multi-track files as single mega-track
- Not recommended for batch processing
- Better to export to GPX first

### Working with Garmin A.GPX Files
- Prefer direct XML parsing over regex (more robust)
- Handle encoding issues gracefully (`errors='replace'`)
- Use ElementTree namespace registration for clean XML output
- Direct string replacement more reliable than regex for large structures
- Always verify point counts after modifications

### Large Track Datasets
- 6 tracks, 9,200+ points = manageable with Python
- XML files up to 1.8 MB load fine in memory
- Regex searches perform well on entire content
- ElementTree can validate XML after modifications

### User Location Data
- All tracks are marine navigation around Swedish archipelago
- Mikael's personal sailing data (6 separate voyages)
- Timestamps range from June-August 2026
- High-precision GPS (sub-meter accuracy)

---

## Future References

### For Similar Tasks
1. Always check for A.GPX first - easier to work with than binary formats
2. Use Haversine formula to detect recording anomalies
3. Interactive maps (Leaflet.js) for visualization
4. ElementTree with namespace handling for XML modifications
5. String replacement (not regex) for track segment updates

### When Issues Occur
- If XML won't parse: Check for null bytes or encoding issues (`errors='replace'`)
- If regex fails: Switch to ElementTree for structured XML handling
- If updates don't persist: Use direct file write, not string methods
- Always keep backups before modifying original files

### Tools That Work
- ✅ Python regex for pattern extraction
- ✅ ElementTree for XML validation
- ✅ Leaflet.js + OpenStreetMap for visualization
- ✅ Haversine calculation for distance analysis
- ✅ Direct file I/O for modifications

---

## Garmin Import Issue & Solution

### Problem: "Track Imported" But Not in Saved Tracks Menu
When importing individual GPX files to a Garmin device, the device may say "Track imported successfully" but the tracks don't appear in the Saved Tracks menu.

### Root Cause
GPX files inherited corrupted metadata from the source A.GPX file, making them unreadable by the Garmin device.

### Solution: Clean GPX Structure
Export GPX files with **minimal, clean metadata** only:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<gpx creator="Garmin echoMAP 50s" version="1.1" 
     xmlns="http://www.topografix.com/GPX/1/1" 
     xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3" 
     xmlns:wptx1="http://www.garmin.com/xmlschemas/WaypointExtension/v1" 
     xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" 
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
     xsi:schemaLocation="...">
  <metadata>
    <link href="http://www.garmin.com">
      <text>Garmin</text>
    </link>
  </metadata>
  <trk>
    <name>Track Name</name>
    <trkseg>
      <trkpt lat="..." lon=""/>
      ...
    </trkseg>
  </trk>
</gpx>
```

### Critical Requirements
1. **Valid XML** - No corruption, well-formed structure
2. **Minimal metadata** - Only essential Garmin namespaces
3. **Proper namespaces** - Include all Garmin extension namespaces
4. **Single track per file** - One `<trk>` element per GPX file
5. **Clean trackpoints** - Extract only `<trkpt lat="" lon=""/>` elements

### Python Implementation
```python
# Use clean header with all Garmin namespaces
header = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx creator="Garmin echoMAP 50s" version="1.1" 
     xmlns="http://www.topografix.com/GPX/1/1" 
     xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3" 
     xmlns:wptx1="http://www.garmin.com/xmlschemas/WaypointExtension/v1" 
     xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" 
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
     xsi:schemaLocation="...">
  <metadata>
    <link href="http://www.garmin.com">
      <text>Garmin</text>
    </link>
  </metadata>
'''

# Extract ONLY clean trackpoints from source
trkpt_pattern = r'<trkpt lat="([^"]+)" lon="([^"]+)"\s*/>'
trackpoints = re.findall(trkpt_pattern, trkseg_content)

# Build GPX file
gpx_content = header + '\n'
gpx_content += f'  <trk>\n    <name>{trackname}</name>\n    <trkseg>\n'
for lat, lon in trackpoints:
    gpx_content += f'      <trkpt lat="{lat}" lon="{lon}"/>\n'
gpx_content += '    </trkseg>\n  </trk>\n</gpx>'
```

### Testing the Fix
After recreating GPX files with clean structure:
1. Connect Garmin to computer or SD card reader
2. Copy cleaned GPX files to `/GARMIN/GPX/` directory
3. On device: **Saved Tracks → Import from SD card**
4. Select GPX file - should now appear in Saved Tracks menu

---

## Session Metadata
- **Date:** 2026-09-20
- **User:** Mikael (personal GPS data)
- **Location:** Swedish archipelago (Blekinge coast)
- **Device:** Garmin echoMAP 50s
- **Result:** Successfully cleaned KARLSKRONA-HALLARUM track, renamed all tracks, and created import-ready GPX files
