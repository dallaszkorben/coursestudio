"""
Track Editor Tab Handler for CourseStudio.

Handles the Track Editor tab which contains:
- Track List (left panel)
- Trackpoint List (top-right panel)
- Map Widget (bottom-right panel)

Classes:
    - TrackEditorTabHandler: Manages the Track Editor tab UI and layout
"""

import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QSizePolicy
)
from PyQt5.QtCore import Qt

from src.track_editor.gui.widgets.track_list_widget import TrackListWidget
from src.track_editor.gui.widgets.trackpoint_list_widget import TrackpointListWidget
from src.gui.widgets.map_widget import MapWidget

logger = logging.getLogger(__name__)


class TrackEditorTabHandler:
    """
    Handles the Track Editor tab UI layout and widget creation.
    
    Manages the creation and setup of:
    - Track List Widget (left panel)
    - Trackpoint List Widget (top-right)
    - Map Widget (bottom-right)
    - Splitter layout for resizable panels
    """
    
    def __init__(self, track_manager, mbtiles_provider, config):
        """
        Initialize Track Editor tab handler.
        
        Args:
            track_manager: Core TrackManager instance
            mbtiles_provider: MBTilesProvider for map tiles
            config: AppConfig instance
        """
        self.track_manager = track_manager
        self.mbtiles_provider = mbtiles_provider
        self.config = config
        
        # Will be set by create_tab()
        self.widget = None
        self.track_list_widget = None
        self.trackpoint_list_widget = None
        self.map_widget = None
    
    def create_tab(self):
        """
        Create and return the Track Editor tab widget.
        
        Returns:
            QWidget: The Track Editor tab widget with all sub-widgets configured
        """
        # Main container widget
        self.widget = QWidget()
        track_editor_layout = QVBoxLayout()
        self.widget.setLayout(track_editor_layout)
        track_editor_layout.setContentsMargins(0, 0, 0, 0)
        track_editor_layout.setSpacing(0)
        
        # ====================================================================
        # Main Horizontal Splitter: Track List (left) vs Trackpoints+Map (right)
        # ====================================================================
        
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel: Track List Widget
        self.track_list_widget = TrackListWidget(self.track_manager)
        self.track_list_widget.setMinimumWidth(80)
        self.track_list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        main_splitter.addWidget(self.track_list_widget)
        
        # Right Panel: Vertical splitter with Trackpoints and Map
        right_splitter = QSplitter(Qt.Vertical)
        
        # Trackpoint List Widget (top)
        self.trackpoint_list_widget = TrackpointListWidget(self.track_manager, None)
        self.trackpoint_list_widget.setMinimumHeight(50)
        self.trackpoint_list_widget.setMinimumWidth(1)  # Allow horizontal shrinking
        self.trackpoint_list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        right_splitter.addWidget(self.trackpoint_list_widget)
        
        # Map Widget (bottom)
        self.map_widget = MapWidget(mbtiles_provider=self.mbtiles_provider, config=self.config)
        self.map_widget.setMinimumHeight(150)
        self.map_widget.setMinimumWidth(1)  # Allow horizontal shrinking
        self.map_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.map_widget.set_track_manager(self.track_manager)
        
        # Update trackpoint list widget with map widget reference
        self.trackpoint_list_widget.map_widget = self.map_widget
        
        right_splitter.addWidget(self.map_widget)
        
        # Set initial sizes (40% trackpoints, 60% map)
        right_splitter.setSizes([400, 600])
        
        # Make splitter draggable - neither side can collapse
        right_splitter.setCollapsible(0, False)  # Trackpoint list can't collapse
        right_splitter.setCollapsible(1, False)  # Map can't collapse
        
        # Add right splitter to main horizontal splitter
        main_splitter.addWidget(right_splitter)
        
        # Set initial sizes for main splitter (30% tracks, 70% trackpoints+map)
        main_splitter.setSizes([300, 700])
        
        # Make main splitter draggable - neither side can collapse
        main_splitter.setCollapsible(0, False)  # Track list can't collapse
        main_splitter.setCollapsible(1, False)  # Trackpoints+Map can't collapse
        
        track_editor_layout.addWidget(main_splitter)
        
        logger.info("Track Editor tab created with Track List, Trackpoint List, and Map widgets")
        
        return self.widget
    
    def get_track_list_widget(self):
        """Get the Track List Widget."""
        return self.track_list_widget
    
    def get_trackpoint_list_widget(self):
        """Get the Trackpoint List Widget."""
        return self.trackpoint_list_widget
    
    def get_map_widget(self):
        """Get the Map Widget."""
        return self.map_widget
