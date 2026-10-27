"""
Help dialogs for CourseStudio - displaying user help for different features.
"""

import logging
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QTabWidget, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class HelpDialog(QDialog):
    """Main help dialog with tabbed interface for different topics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CourseStudio Help")
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout()
        
        # Create tab widget for different help topics
        tabs = QTabWidget()
        
        # Add help tabs
        tabs.addTab(self._create_getting_started_tab(), "Getting Started")
        tabs.addTab(self._create_track_editor_tab(), "Track Editor")
        tabs.addTab(self._create_map_editor_tab(), "Map Editor")
        tabs.addTab(self._create_file_operations_tab(), "File Operations")
        tabs.addTab(self._create_map_navigation_tab(), "Map Navigation")
        tabs.addTab(self._create_trackpoint_management_tab(), "Trackpoint Management")
        tabs.addTab(self._create_settings_tab(), "Settings")
        tabs.addTab(self._create_keyboard_shortcuts_tab(), "Keyboard Shortcuts")
        
        layout.addWidget(tabs)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
    
    def _create_text_widget(self, text):
        """Helper to create a text widget with help content."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setText(text)
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Monospace", 10))
        
        layout.addWidget(text_edit)
        widget.setLayout(layout)
        return widget
    
    def _create_getting_started_tab(self):
        """Getting Started help tab."""
        text = """GETTING STARTED WITH COURSESTUDIO

CourseStudio has two main tabs:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRACK EDITOR TAB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For viewing and editing GPX track files:
   • Opens and displays GPX files with tracks and trackpoints
   • Shows track list, trackpoint details, and interactive map
   • Edit trackpoints (move, add, delete)
   • Visualize routes with customizable colors
   • Save and manage GPX files

Start Here:
   1. Click File → Open to load a GPX file
   2. Select a track from the track list
   3. View trackpoints in the list
   4. See the track on the map

See "Track Editor" tab for detailed information.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAP EDITOR TAB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For interactive map tile editing:
   • Load base MBTiles map (Swedish archipelago data)
   • Paint and draw on the map
   • Save edited tiles to create custom map data
   • Zoom and pan the map while editing

Start Here:
   1. Click the "Map Editor" tab
   2. Click "Load Base Map" to load the MBTiles file
   3. Use drawing tools to paint on the map
   4. Click "Save Map" to save your changes

See "Map Editor" tab for detailed information.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GENERAL INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SETTINGS
   • Click Settings tab to configure appearance
   • Customize colors, sizes, and display options
   • Settings auto-save and persist between sessions

LAYOUT
   • Drag splitter handles to resize panels
   • Adjust layout to your preference
   • Window size and position are remembered

For more details, see other help tabs:
   • "Track Editor" - GPX file editing guide
   • "Map Editor" - Map tile editing guide
   • "File Operations" - Saving and managing files
   • "Keyboard Shortcuts" - Quick keys and hotkeys
"""
        return self._create_text_widget(text)
    
    def _create_track_editor_tab(self):
        """Track Editor help tab."""
        text = """TRACK EDITOR TAB

The Track Editor allows you to view and edit GPX files with tracks and trackpoints.

OPENING A GPX FILE
   • Click File → Open or press Ctrl+O
   • Select your GPX file from the file browser
   • The tracks and trackpoints will load automatically

VIEWING TRACKS
   • Select a track from the Track List (left panel)
   • The track will appear on the map
   • All trackpoints are displayed as circles

LAYOUT
   • The window has two splitters:
     - HORIZONTAL: Resize between Track List and Map/Trackpoints
     - VERTICAL: Resize between Trackpoints list and Map
   • Drag the splitter handles to adjust panel sizes

COORDINATE FORMATS
   • Two formats are supported:
     - DMS (Degrees Minutes Seconds): 57°30'45.5"N 12°15'30.2"E
     - Decimal: 57.5126°N 12.2584°E
   • Switch formats using the Format dropdown in Trackpoints list

EDITING TRACKPOINTS
   • Double-click a trackpoint in the list to edit it
   • Or drag it on the map to reposition
   • Changes apply immediately

ADDING TRACKPOINTS
   • Click on the map between two existing points
   • A new point will be inserted
   • Drag immediately to position it

DELETING TRACKPOINTS
   • Select a trackpoint in the list
   • Press Delete or Ctrl+D
   • Or right-click → Delete
   • The point is removed immediately

MULTI-SELECTION
   • Shift+Click to select a range of trackpoints
   • Both points appear selected on the map

SETTINGS
   • Click Settings tab to configure appearance
   • Customize track colors, point sizes, and more
   • Changes apply immediately to the map
   • Settings are auto-saved

For more details:
   • See "File Operations" for saving and managing files
   • See "Map Navigation" to learn map controls
   • See "Trackpoint Management" for editing details
   • See "Keyboard Shortcuts" for quick keys
"""
        return self._create_text_widget(text)
    
    def _create_map_editor_tab(self):
        """Map Editor help tab."""
        text = """MAP EDITOR TAB

The Map Editor allows you to edit MBTiles map data interactively.

GETTING STARTED
   1. Click the "Map Editor" tab at the top
   2. Click "Load Base Map" button to load the MBTiles file
   3. Wait for the map to display (Swedish archipelago base map)
   4. Use the drawing tools to edit the map
   5. Click "Save Map" to save your changes

MAP DISPLAY
   • The map shows the Swedish archipelago data
   • Pan by clicking and dragging
   • Zoom with scroll wheel or +/- buttons
   • Recenter with the circular button

DRAWING ON THE MAP
   • Use the available drawing tools to paint
   • Changes appear on the map in real-time
   • Multiple drawing modes available:
     - Pen/Brush tool
     - Eraser tool
     - Color selection
     - Line drawing
     - Shapes

COLORS AND SETTINGS
   • Click color buttons to change drawing color
   • Adjust brush size with sliders
   • Preview your changes on the map immediately

SAVING YOUR CHANGES
   • Click "Save Map" to write changes to the MBTiles file
   • A backup is automatically created
   • You can close and reopen the file with your edits preserved

ZOOM LEVELS
   • The map supports multiple zoom levels
   • Different zoom levels may have different tile data
   • You can edit at any supported zoom level

UNDO/REDO
   • Use Ctrl+Z to undo changes
   • Use Ctrl+Y to redo undone changes

TIPS
   • Start with base map loaded to see existing map data
   • Use different colors to mark different features
   • Save frequently to preserve your work
   • You can always load a fresh base map to start over

For map controls and keyboard shortcuts:
   • See "Map Navigation" for pan and zoom controls
   • See "Keyboard Shortcuts" for detailed hotkeys
"""
        return self._create_text_widget(text)
    
    def _create_file_operations_tab(self):
        """File Operations help tab."""
        text = """FILE OPERATIONS

OPENING FILES
   • File → Open (Ctrl+O)
     Opens a GPX file for viewing and editing
   
   • File → Merge GPX File
     Merges tracks from another GPX file into the current file

SAVING FILES
   • File → Save (Ctrl+S)
     Saves changes to the current file
     A backup is automatically created before saving
   
   • File → Save As (Ctrl+Shift+S)
     Saves the file with a new name

CLOSING FILES
   • File → Close GPX File (Ctrl+W)
     Closes the current GPX file
     You'll be prompted to save if there are unsaved changes

RECENT FILES
   • File → Recent Files
     Quick access to recently opened files

UNDO/REDO
   • Edit → Undo (Ctrl+Z)
     Undo the last change
   
   • Edit → Redo (Ctrl+Y)
     Redo the last undone change

TRACK MANAGEMENT
   • Right-click on a track to:
     - Rename the track
     - Delete the track
     - View track properties

IMPORTANT
   • Always save your work (Ctrl+S)
   • Changes are NOT saved automatically
   • A backup is created before saving
"""
        return self._create_text_widget(text)
    
    def _create_map_navigation_tab(self):
        """Map Navigation help tab."""
        text = """MAP NAVIGATION

PANNING (MOVING THE MAP)
   • Left-click and drag the map to pan
   • The map will smoothly follow your mouse

ZOOMING
   • Scroll wheel up: Zoom in (centered on cursor)
   • Scroll wheel down: Zoom out (centered on cursor)
   • Click the + button: Zoom in
   • Click the - button: Zoom out

RECENTER
   • Click the ⊙ button to return to the default position

TRACK VISUALIZATION
   • Tracks are displayed as colored lines
   • Default color: Red (configurable in Settings)
   • Outline effect adds visual depth

TRACKPOINTS
   • Trackpoints are displayed as circles
   • General points: Yellow (configurable)
   • Selected point: Blue (configurable)
   • Multi-selected: Orange (configurable)
   • Show/hide all points with toggle in Trackpoints list

SELECTING TRACKPOINTS
   • Click on the map to select a trackpoint
   • Or click on a row in the Trackpoints list
   • Selected trackpoint highlights in blue on the map
   • Click on list header to clear selection

MULTI-SELECTION
   • Shift+Click: Select a range of points
   • Shows both points selected on the map

INSERTING TRACKPOINTS
   • Click between two points on the map to insert a new point
   • Drag immediately to position it
   • New point appears in the Trackpoints list

SETTINGS
   • Go to Settings tab to customize:
     - Track path color and width
     - Track outline color and width
     - Trackpoint colors and sizes
     - Changes apply immediately
"""
        return self._create_text_widget(text)
    
    def _create_trackpoint_management_tab(self):
        """Trackpoint Management help tab."""
        text = """TRACKPOINT MANAGEMENT

VIEWING TRACKPOINTS
   • Select a track to see its trackpoints in the list
   • Each row shows: Latitude, Longitude, Elevation (if available)
   • Scroll up/down to view all points

SELECTING TRACKPOINTS
   • Click on a row to select that trackpoint
   • The point highlights in blue on the map
   • Coordinates update in the Details section

COORDINATE FORMATS
   • DMS (Degrees Minutes Seconds)
     Format: 57°30'45.5"N 12°15'30.2"E
   
   • Decimal Degrees
     Format: 57.5126°N 12.2584°E
   
   • Switch between formats using Format dropdown

EDITING TRACKPOINTS
   • Double-click a trackpoint in the list to edit it
   • Or drag it on the map to reposition
   • Changes apply immediately

ADDING TRACKPOINTS
   • Click on the map between two existing points
   • A new point will be inserted
   • Drag immediately to position it
   • Or use Insert menu for precise control

DELETING TRACKPOINTS
   • Select a trackpoint in the list
   • Press Delete or Ctrl+D
   • Or right-click → Delete
   • The point is removed immediately

MULTI-SELECTION
   • Shift+Click to select a range
   • Both points appear selected on the map

CLEARING SELECTION
   • Click the "Clear Selection" button
   • Or click elsewhere on the map

STATISTICS
   • Track distance is shown at the bottom
   • Updates automatically when trackpoints change
   • Shows total track length in kilometers
"""
        return self._create_text_widget(text)
    
    def _create_settings_tab(self):
        """Settings help tab."""
        text = """SETTINGS & APPEARANCE

SETTINGS TAB
   • Click the "Settings" tab to customize appearance
   • All changes apply immediately to the map
   • Settings are auto-saved to config/settings.yaml

APPEARANCE TAB - SUB-TABS

1. TRACK PATH
   • Configure the track line (the route line)
   • Body:
     - Color: Click to choose the track line color
     - Width: Adjust line thickness (1-9 pixels)
   • Outline:
     - Color: Click to choose outline color
     - Width: Adjust outline thickness (0-5 pixels)

2. GENERAL TRACK POINT
   • Settings for unselected trackpoints
   • Body:
     - Color: Click to choose point color
     - Size: Adjust point radius (1-10 pixels)
   • Outline:
     - Color: Click to choose outline color
     - Width: Adjust outline thickness (0-5 pixels)

3. SINGLE-SELECTED TRACK POINT
   • Settings for a single selected trackpoint
   • Body:
     - Color: Click to choose color when selected
     - Size: Adjust point radius (1-15 pixels)
   • Outline:
     - Color: Click to choose outline color
     - Width: Adjust outline thickness (0-5 pixels)

4. MULTI-SELECTED TRACK POINT
   • Settings for multiple selected trackpoints (Shift+Click)
   • Body:
     - Color: Click to choose color for multi-select
     - Size: Adjust point radius (1-15 pixels)
   • Outline:
     - Color: Click to choose outline color
     - Width: Adjust outline thickness (0-5 pixels)

GLOBAL CONTROLS
   • Show Trackpoints: Toggle to show/hide all points
   • Affects the entire map display

COLOR PICKER
   • Click any color box to open the color picker
   • Choose from preset colors or enter hex code
   • Preview shows the selected color

SLIDERS
   • Drag sliders to adjust width and size
   • Values update in real-time
   • Map updates immediately

AUTO-SAVE
   • All settings are automatically saved
   • No need to manually save configuration
   • Settings persist when you close and reopen the app
"""
        return self._create_text_widget(text)
    
    def _create_keyboard_shortcuts_tab(self):
        """Keyboard Shortcuts help tab."""
        text = """KEYBOARD SHORTCUTS

FILE OPERATIONS
   Ctrl+O               Open GPX file
   Ctrl+S               Save current file
   Ctrl+Shift+S         Save As (new filename)
   Ctrl+W               Close GPX file

EDIT OPERATIONS
   Ctrl+Z               Undo last change
   Ctrl+Y               Redo last undone change
   Ctrl+D               Delete selected trackpoint

MAP OPERATIONS
   Arrow Keys           Pan map in that direction
   + (Plus)             Zoom in
   - (Minus)            Zoom out
   Scroll Wheel         Zoom in/out (centered on cursor)

SELECTION
   Click                Select single trackpoint
   Shift+Click          Select range of trackpoints
   Escape               Clear selection

TABS
   Ctrl+Tab             Switch to next tab
   Ctrl+Shift+Tab       Switch to previous tab

MOUSE ACTIONS
   Left-Click           Select trackpoint
   Left-Click+Drag      Pan map
   Double-Click         Edit trackpoint
   Right-Click          Context menu
   Scroll Wheel         Zoom map

ON MAP
   Click between points Insert new trackpoint
   Drag point           Move trackpoint
   Shift+Click+Drag     Multi-select and drag

TIPS
   • Most operations can be done via menu or keyboard
   • Keyboard shortcuts are faster for repetitive tasks
   • Tooltips show shortcuts when you hover over buttons
   • Settings are in the Settings tab, not menu
"""
        return self._create_text_widget(text)
