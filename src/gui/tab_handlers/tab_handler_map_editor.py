"""
Map Editor Tab Handler for CourseStudio.

Handles the Map Editor tab which provides MBTiles file editing capabilities:
- Display MBTiles file metadata and characteristics
- Interactive map viewer with pan/zoom
- Zoom level management (original vs generated)
- Zoom level generation with progress tracking

Classes:
    - MapEditorTabHandler: Manages the Map Editor tab UI and layout
"""

import logging
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QSizePolicy, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt

from src.map_editor.core.mbtiles_reader import MBTilesReader
from src.map_editor.gui.widgets.characteristics_panel import CharacteristicsPanel
from src.map_editor.gui.widgets.map_viewer import MapViewer

logger = logging.getLogger(__name__)


class MapEditorTabHandler:
    """
    Handles the Map Editor tab UI layout and widget creation.
    
    Manages the creation and setup of:
    - Characteristics Panel (left): File metadata, zoom levels, statistics
    - Map Viewer (right): Interactive map display with pan/zoom controls
    - Splitter layout for resizable panels
    - MBTiles file loading and state management
    
    State Synchronization:
    - Shares map center/zoom with Track Editor via config
    - Both editors use same Map.center.lat, Map.center.lon, Map.zoom values
    """
    
    def __init__(self, mbtiles_provider, config):
        """
        Initialize Map Editor tab handler.
        
        Args:
            mbtiles_provider: MBTilesProvider instance for tile serving
            config: AppConfig instance (shared with Track Editor)
        """
        self.mbtiles_provider = mbtiles_provider
        self.config = config
        
        # Widgets - will be created in create_tab()
        self.widget = None
        self.characteristics_panel = None
        self.map_viewer = None
        
        # State
        self.mbtiles_reader = None
        self.current_mbtiles_path = None
        
        logger.debug("MapEditorTabHandler initialized")
    
    def create_tab(self) -> QWidget:
        """
        Create and return the Map Editor tab widget.
        
        Layout:
        ┌──────────────────────────────────────┐
        │ Main Widget (QWidget)                │
        ├──────────────────────────────────────┤
        │ Splitter (Horizontal)                │
        ├─────────────────┬─────────────────────┤
        │ Characteristics │ Map Viewer          │
        │ Panel (Left)    │ (Right)             │
        │ - File Info     │ - Interactive Map   │
        │ - Zoom List     │ - Pan/Zoom Controls │
        │ - Statistics    │                     │
        └─────────────────┴─────────────────────┘
        
        Returns:
            QWidget: The Map Editor tab widget
        """
        # Main container
        self.widget = QWidget()
        main_layout = QVBoxLayout()
        self.widget.setLayout(main_layout)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        try:
            # ================================================================
            # Load default MBTiles file
            # ================================================================
            
            default_mbtiles = "mbtiles/Sweeden-Z6-Z15.mbtiles"
            if Path(default_mbtiles).exists():
                self.mbtiles_reader = MBTilesReader(default_mbtiles)
                self.current_mbtiles_path = default_mbtiles
                logger.info(f"Loaded MBTiles: {default_mbtiles}")
            else:
                logger.warning(f"Default MBTiles not found: {default_mbtiles}")
                self._create_error_widget(main_layout, f"MBTiles file not found: {default_mbtiles}")
                return self.widget
            
            # ================================================================
            # Create Characteristics Panel (Left)
            # ================================================================
            
            self.characteristics_panel = CharacteristicsPanel()
            self.characteristics_panel.setMinimumWidth(250)
            self.characteristics_panel.setSizePolicy(
                QSizePolicy.Expanding, 
                QSizePolicy.Expanding
            )
            
            # Load file metadata into characteristics panel
            self.characteristics_panel.load_mbtiles(self.mbtiles_reader)
            
            # ================================================================
            # Create Map Viewer (Right)
            # ================================================================
            
            self.map_viewer = MapViewer(config=self.config)
            self.map_viewer.setMinimumWidth(300)
            self.map_viewer.setSizePolicy(
                QSizePolicy.Expanding,
                QSizePolicy.Expanding
            )
            
            # Set MBTiles provider for tile serving
            self.map_viewer.set_mbtiles_provider(self.mbtiles_provider)
            
            # Load MBTiles provider into map viewer for tile serving
            # The map viewer will display tiles from the provider
            self.map_viewer.load_mbtiles(self.mbtiles_provider)
            
            # ================================================================
            # Create Splitter Layout (Left | Right)
            # ================================================================
            
            splitter = QSplitter(Qt.Horizontal)
            splitter.addWidget(self.characteristics_panel)
            splitter.addWidget(self.map_viewer)
            
            # Set initial split sizes (30% characteristics, 70% map)
            splitter.setSizes([300, 700])
            
            # Neither side can collapse
            splitter.setCollapsible(0, False)  # Characteristics panel can't collapse
            splitter.setCollapsible(1, False)  # Map viewer can't collapse
            
            main_layout.addWidget(splitter)
            
            logger.info("Map Editor tab created successfully with CharacteristicsPanel and MapViewer")
            
        except Exception as e:
            error_msg = f"Error creating Map Editor tab: {e}"
            logger.error(error_msg, exc_info=True)
            self._create_error_widget(main_layout, error_msg)
        
        return self.widget
    
    def _create_error_widget(self, layout: QVBoxLayout, error_msg: str) -> None:
        """
        Create error display widget.
        
        Args:
            layout: Parent layout to add error widget to
            error_msg: Error message to display
        """
        error_label = QLabel(error_msg)
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("color: #ff4444; font-size: 12px;")
        layout.addWidget(error_label, alignment=Qt.AlignCenter)
        logger.error(f"Error widget created: {error_msg}")
    
    def get_characteristics_panel(self) -> CharacteristicsPanel:
        """Get the Characteristics Panel widget."""
        return self.characteristics_panel
    
    def get_map_viewer(self) -> MapViewer:
        """Get the Map Viewer widget."""
        return self.map_viewer
    
    def get_mbtiles_reader(self) -> MBTilesReader:
        """Get the MBTiles reader instance."""
        return self.mbtiles_reader
