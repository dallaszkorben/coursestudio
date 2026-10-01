# UI Debugging: Hard Problems and Solutions

## Overview

This guide documents complex UI problems encountered in CourseStudio and the systematic approach to solving them. It emphasizes the importance of investigation before implementation and learning from existing patterns.

## Problem 1: Trackpoint Deletion - Map/List State Inconsistency

### The Problem

After deleting a trackpoint with Ctrl+D:
- **Expected**: No trackpoint selected (neither on map nor in list)
- **Actual**: Last trackpoint highlighted on map, list shows no selection

This created an inconsistency: the map and list were out of sync.

### What I Did Wrong (4 Failed Attempts)

1. **Attempt 1**: Cleared selection in list, assumed map would auto-clear
   - Failed because signals weren't properly disconnected
   
2. **Attempt 2**: Added explicit map clearing before refresh
   - Failed because something was re-selecting the point during refresh
   
3. **Attempt 3**: Disconnected/reconnected selection signals
   - Failed because the root cause wasn't understood

4. **Attempt 4**: Added logging to trace the issue
   - Finally found the real cause

### Root Cause Analysis

Added logging to `map_widget.on_trackpoint_selected()`:

```
[MAP] on_trackpoint_selected called: track_id=2, trackpoint_index=-1
Call stack:
  _delete_trackpoint() → point_selected.emit(-1)
  → _on_trackpoint_selected() in main_window.py
  → map_widget.on_point_selected()
  → map_widget.on_trackpoint_selected()
```

**The real issue**: When trackpoint_list_widget emitted `point_selected.emit(-1)` (meaning "no selection"), it triggered `_on_trackpoint_selected()` in main_window.py, which then called `map_widget.on_point_selected(track_id, -1)`.

The `-1` was being passed to `on_trackpoint_selected()` without checking if it was valid, causing the map to still try to select a point.

### The Solution

In `main_window.py._on_trackpoint_selected()`, add a guard at the beginning:

```python
def _on_trackpoint_selected(self, point_index: int):
    # If point_index is -1, it means no selection - clear map selection
    if point_index < 0:
        self._current_point_index = -1
        if hasattr(self, 'map_widget'):
            self.map_widget.selected_trackpoint_index = None
            self.map_widget.selected_trackpoint_range = None
            self.map_widget.render_map()
        return
    
    # ... rest of the method
```

**Key insight**: The signal handler must validate input and handle "no selection" as a first-class case, not let invalid values propagate.

### Lessons Learned

1. **Add logging to understand signal flow** - Don't guess where a value comes from
2. **Check boundaries** - If a value can be -1 (or None), handle it explicitly
3. **Signals must be defensive** - Signal handlers should validate and sanitize input
4. **Map/List state must stay in sync** - Use a single source of truth or explicit synchronization

---

## Problem 2: Toggle Switch Alignment - Button Covering Title

### The Problem

In Settings tab under Trackpoints:
- "Show Points:" title was covered/overlapped by the toggle button
- Button appeared centered instead of to the right of the title

### What I Did Wrong (3 Failed Attempts)

1. **Attempt 1**: Added `addStretch()` to push button left
   - Didn't work - button still overlapped

2. **Attempt 2**: Set `setMaximumWidth(200)` on the widget
   - Didn't work - overlap remained

3. **Attempt 3**: Modified internal toggle_switch_widget.py paintEvent()
   - Changed x position from centered to x=0
   - Still didn't work - fundamental misunderstanding of the problem

### Root Cause Analysis

Instead of guessing, I should have looked at how it works correctly in the **Editor tab**:

In `trackpoint_list_widget.py` (line 215-217):

```python
header_layout.addWidget(QLabel("Show points:"))  # Separate label
self.show_points_switch = ToggleSwitchWidget(initial_state=self.show_points)  # NO title parameter
header_layout.addWidget(self.show_points_switch)
```

**The pattern**:
- Create a separate QLabel with fixed width (70px)
- Pass empty string (no title) to ToggleSwitchWidget
- Add them sequentially to the layout
- Qt's layout manager handles spacing automatically

### The Solution

In `turning_points_settings_widget.py`:

```python
# Create label separately
toggle_label = QLabel("Show:")
toggle_label.setStyleSheet("font-weight: bold; color: white;")
toggle_label.setFixedWidth(70)  # Fixed width for alignment with other labels
toggle_layout.addWidget(toggle_label, 0, Qt.AlignLeft)

# Create toggle WITHOUT title parameter
self.show_toggle = ToggleSwitchWidget(title="", initial_state=self.show)
toggle_layout.addWidget(self.show_toggle, 0, Qt.AlignLeft)

# Add stretch to prevent expansion
toggle_layout.addStretch()
```

### Lessons Learned

1. **Look at existing working code FIRST** - Don't try to fix by guessing
2. **Follow established patterns** - The pattern already existed in the codebase
3. **Understand the architecture** - ToggleSwitchWidget was designed optionally
4. **Don't modify working code** - toggle_switch_widget.py didn't need changes
5. **The solution was already in the codebase** - Just needed to be copied

---

## Problem 4: Silent State Desynchronization - Unselect Signal Lost

### The Problem

When you clicked on empty space on the map to unselect a trackpoint:
- **Visual result**: Map showed point unselected ✅
- **Internal state**: Trackpoint list's `current_selection` still held the old point index ❌
- **Result**: Pressing Delete would delete the "phantom" unselected point

The map and trackpoint list were out of sync, and the bug was **completely silent** - no error messages.

### Debugging Journey (6+ Failed Attempts)

1. **Attempt 1**: Added ESC handler to trackpoint list widget
   - Didn't work - ESC wasn't the issue
   
2. **Attempt 2**: Handled ESC in custom table widget
   - Still didn't work - ESC wasn't being pressed in this scenario
   
3. **Attempt 3**: Added click handler for empty space in table widget
   - Helped but didn't solve it - the real problem was elsewhere

4. **Attempt 4-6**: Multiple attempts to trace signal flow
   - Added logging everywhere but the actual bug location
   - Realized the bug was in the **signal chain between map and trackpoint list**

### Root Cause Analysis

The bug chain:
1. **User clicks empty space on map** → map clears selection and emits `point_clicked(track_id, -1)`
2. **Main window receives signal** → calls `trackpoint_list_widget.select_point(-1)` to sync
3. **select_point() method** → **had no handler for -1!**
   ```python
   def select_point(self, point_index: int) -> bool:
       if not 0 <= point_index < self.table_widget.rowCount():
           logger.warning(f"Invalid point index: {point_index}")
           return False  # ← Just returns, doesn't clear selection!
   ```
4. **Result**: `current_selection` never cleared, stays at old value
5. **User presses Delete** → checks `current_selection >= 0` → deletes phantom point

**Why it was hard to find:**
- **Silent failure**: No exceptions, no visible errors
- **Edge case not designed for**: `select_point()` wasn't expected to receive -1
- **Asymmetric behavior**: Map cleared properly, but list didn't sync
- **Multi-layer bug**: Involved 3 different components (map, main window, trackpoint list)

### The Solution

In `trackpoint_list_widget.select_point()`, add explicit handler for unselection:

```python
def select_point(self, point_index: int) -> bool:
    """
    Select a trackpoint by index.
    
    Args:
        point_index (int): Index of point to select (0-based), or -1 to clear selection
    
    Returns:
        bool: True if selected successfully, False otherwise
    """
    
    # Handle unselection (-1)
    if point_index < 0:
        self.clear_selection()
        return True
    
    # Normal selection for valid indices
    if not 0 <= point_index < self.table_widget.rowCount():
        logger.warning(f"Invalid point index: {point_index}")
        return False
    
    self._updating_from_map = True
    self.table_widget.selectRow(point_index)
    self._updating_from_map = False
    self.current_selection = point_index
    return True
```

**Key insight**: Methods that accept negative indices as "unselect" signals must explicitly handle them, not treat them as errors.

### Lessons Learned

1. **Always handle edge cases explicitly** - Negative values, zero, None should all be considered
2. **Be careful with signal chains** - When signals pass through multiple handlers, ensure EVERY handler knows how to deal with the values
3. **Silent failures are dangerous** - A method returning False without doing anything is worse than raising an exception
4. **Test signal asymmetry** - When two components need to stay in sync, test both directions of update
5. **Document expected values** - If a method accepts -1 as "unselect", document it in the docstring and handle it
6. **Async state sync is fragile** - Relying on signals to keep two state variables in sync is error-prone; consider a single source of truth

### Step 1: Investigate Before Implementing

**DO THIS FIRST:**
- Look for similar features that already work correctly
- Read how they solve the same problem
- Understand the pattern

**EXAMPLE**: Instead of trying to fix toggle alignment from scratch, look at:
- How is "Show points:" displayed in Editor tab?
- What pattern does it use?
- Can I copy that pattern?

### Step 2: Add Logging to Understand Flow

When state is inconsistent between components:
1. Add logging to signal handlers
2. Capture the call stack to see what's triggering updates
3. Check what values are being passed through signals

```python
def on_trackpoint_selected(self, track_id, trackpoint_index):
    logger.info(f"[MAP] on_trackpoint_selected: track_id={track_id}, point_index={trackpoint_index}")
    import traceback
    logger.info(f"[MAP] Call stack:\n{''.join(traceback.format_stack()[-4:-1])}")
```

### Step 3: Find the Root Cause

- Don't fix symptoms - find why the problem occurs
- Check if input validation is missing (like point_index < 0)
- Verify signals are connected to the right handlers
- Ensure all signal paths are tested

### Step 4: Implement Defensive Code

- Check for -1, None, and invalid values
- Handle "no selection" explicitly
- Synchronize state between related components
- Always validate signal input

---

## Key Principles

### 1. Look Before You Leap

✅ **Good**: Check existing code that works, copy the pattern
❌ **Bad**: Try to fix without understanding how it should work

### 2. Signals Must Be Defensive

✅ **Good**: `if point_index < 0: [clear]; return`
❌ **Bad**: Pass -1 through without checking

### 3. Keep Related State in Sync

✅ **Good**: When clearing map selection, also clear list selection
❌ **Bad**: Let map and list get out of sync

### 4. Add Logging to Understand Flow

✅ **Good**: Add logging to see signal chain and values
❌ **Bad**: Guess where values come from

### 5. Validate Input at Boundaries

✅ **Good**: Check input in signal handlers
❌ **Bad**: Assume values are valid

---

## CourseStudio-Specific Patterns

### Pattern: Trackpoint Selection Sync

When trackpoint selection changes, both map AND list must update:

```python
# In trackpoint_list_widget.py
if point_index < 0:
    self.table_widget.clearSelection()
    self.current_selection = -1
    # Also notify map
    if self.map_widget:
        self.map_widget.selected_trackpoint_index = None
        self.map_widget.render_map()
```

### Pattern: Settings Control Layout

Aligning controls with labels in Settings tab:

```python
# Label with fixed width
label = QLabel("Title:")
label.setFixedWidth(70)  # Align with other labels
layout.addWidget(label)

# Control (no title, let label handle it)
control = SomeWidget()
layout.addWidget(control)

# Stretch to prevent expansion
layout.addStretch()
```

### Pattern: Signal Validation

Always validate in signal handlers:

```python
def handler(self, value):
    # Check for invalid/empty values FIRST
    if value < 0 or value is None:
        self._handle_no_selection()
        return
    
    # Then handle valid case
    self._handle_valid_selection(value)
```

---

## Checklist for Debugging UI State Issues

- [ ] Add logging to signal handlers involved
- [ ] Capture call stacks to see what's triggering updates
- [ ] Check if input is being validated (< 0, None, etc.)
- [ ] Look for similar working features in codebase
- [ ] Verify all signal connections are correct
- [ ] Ensure all related state is updated together (map + list sync)
- [ ] Test the fix with the exact reproduction steps
- [ ] Check that it doesn't break other scenarios

---

---

## Problem 3: QTabBar Text Clipping - Text Cut From Both Sides

### The Problem

Tab text was being clipped from both beginning and end:
- "Track Path" → "T" missing, "t" missing
- "General Track Point" → "G" missing, "t" missing  
- "Single-Selected Track Point" → "Si" missing, "nt" missing
- "Multi-Selected Track Point" → "M" missing, "nt" missing

Text appeared to show only middle characters, not elided in center but clipped on edges.

### What I Did Wrong (Many Failed Attempts)

Spent dozens of iterations trying:
- Fixing tab sizes and width constraints
- Adjusting CSS padding and margins
- Overriding `tabSizeHint()` with different calculations
- Setting `setExpanding(True/False)` variations
- Setting `setElideMode(Qt.ElideNone)`
- Checking `iconSize` allocation
- Trying different QSizePolicy settings
- Adjusting `min-width` in stylesheets

**None of it worked because the root cause wasn't in layout/sizing - it was in rendering.**

### Root Cause Analysis

The problem was at the **paint/rendering layer**, not the layout layer. Qt's default behavior is to clip text to the tab rectangle using the `Qt.TextClip` flag (default, invisible). This flag is applied during `paintEvent()` when drawing the tab text.

### The Solution

Override `paintEvent()` in a custom QTabBar class and use `Qt.TextDontClip` flag:

```python
from PyQt5.QtWidgets import QTabBar, QStylePainter, QStyle, QStyleOptionTab
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFontMetrics


class ContentAwareTabBar(QTabBar):
    """QTabBar that renders tab text WITHOUT clipping."""
    
    def __init__(self):
        super().__init__()
        self.setIconSize(QSize(0, 0))  # Prevent icon space allocation
    
    def paintEvent(self, event):
        """Override to use Qt.TextDontClip flag - CRITICAL."""
        painter = QStylePainter(self)
        option = QStyleOptionTab()
        
        for index in range(self.count()):
            self.initStyleOption(option, index)
            painter.drawControl(QStyle.CE_TabBarTabShape, option)
            # KEY: Use Qt.TextDontClip to prevent text clipping
            painter.drawText(
                self.tabRect(index),
                Qt.AlignCenter | Qt.TextDontClip,
                self.tabText(index)
            )
    
    def tabSizeHint(self, index):
        """Calculate tab size based on text width."""
        default_size = super().tabSizeHint(index)
        tab_text = self.tabText(index)
        font_metrics = QFontMetrics(self.font())
        text_width = font_metrics.boundingRect(tab_text).width()
        
        min_overhead = 25
        calculated_width = text_width + min_overhead
        final_width = max(calculated_width, default_size.width())
        
        return QSize(final_width, default_size.height())
```

### Lessons Learned

1. **Look at rendering layer, not just layout** - When text appears clipped, check `paintEvent()` and rendering flags
2. **Some flags are invisible by default** - `Qt.TextClip` is the default with no visible indication
3. **Symptoms can be misleading** - Text clipping from edges looks like a sizing problem but isn't
4. **Search for exact symptoms** - Finding someone else with identical problem was the breakthrough
5. **Investigate deeper when stuck** - The user's hint "investigate an attribute you don't use" pointed to checking what's actually being rendered

### Key Attributes

- `Qt.TextClip` - Default flag that clips text (invisible, causes the problem)
- `Qt.TextDontClip` - The fix: render text without clipping to rectangle
- `paintEvent()` - Must override this to control rendering flags
- `QStylePainter` - Use for proper style-aware rendering
- `setIconSize(QSize(0, 0))` - Prevent unused icon space allocation

---

## Summary

Hard UI problems usually have simple root causes once you find them:

1. **Inconsistent state** → Missing synchronization between components
2. **Wrong behavior** → Existing pattern not followed or signal not validated
3. **Unexpected selection** → Input validation missing (handle -1, None)
4. **Text clipping/rendering** → Check paint layer and rendering flags, not just layout

**The key**: Investigate existing code first, add logging, search for others with same problem, then fix at the root cause - not symptoms. When stuck in layout/sizing, check the rendering layer.
