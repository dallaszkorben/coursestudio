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
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QSizePolicy, QLabel, QMessageBox, 
    QFileDialog
)
from PyQt5.QtCore import Qt

from src.map_editor.core.mbtiles_reader import MBTilesReader
from src.map_editor.gui.widgets.characteristics_panel import CharacteristicsPanel
from src.map_editor.gui.widgets.map_viewer import MapViewer
from src.shared.map.mbtiles_file_loader import MBTilesFileLoader

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
            # Load default MBTiles file (from settings.yaml or fallback)
            # ================================================================
            
            # Try to load the recent mbtiles from settings
            print(f"\n🔴 LOADING MBTILES ON STARTUP 🔴\n")
            try:
                recent_mbtiles = self.config.get('appearance.tiles.recent_mbtiles')
                print(f"🔴 From settings.yaml: recent_mbtiles = '{recent_mbtiles}'")
                logger.info(f"🔴 From settings.yaml: recent_mbtiles = '{recent_mbtiles}'")
                
                # Settings stores just the filename, need to add mbtiles/ prefix
                if recent_mbtiles:
                    full_path = f"mbtiles/{recent_mbtiles}"
                    if Path(full_path).exists():
                        default_mbtiles = full_path
                        print(f"🔴 File found at: {default_mbtiles}")
                        logger.info(f"🔴 Loading recent MBTiles from settings: {default_mbtiles}")
                    else:
                        default_mbtiles = "mbtiles/Sweeden-Z6-Z15.mbtiles"
                        print(f"🔴 File NOT found at '{full_path}', using default: {default_mbtiles}")
                        logger.info(f"🔴 Recent MBTiles not found at '{full_path}', using default: {default_mbtiles}")
                else:
                    default_mbtiles = "mbtiles/Sweeden-Z6-Z15.mbtiles"
                    print(f"🔴 No recent file in settings, using default: {default_mbtiles}")
                    logger.info(f"🔴 No recent file in settings, using default: {default_mbtiles}")
            except Exception as e:
                print(f"🔴 ERROR loading from settings: {e}")
                logger.warning(f"🔴 Could not load recent MBTiles from settings: {e}")
                default_mbtiles = "mbtiles/Sweeden-Z6-Z15.mbtiles"
            
            if Path(default_mbtiles).exists():
                self.mbtiles_reader = MBTilesReader(default_mbtiles)
                self.current_mbtiles_path = default_mbtiles
                metadata = self.mbtiles_reader.get_metadata()
                
                # VERIFY BY READING DIRECTLY FROM FILE
                import sqlite3
                conn = sqlite3.connect(default_mbtiles)
                cursor = conn.cursor()
                cursor.execute("SELECT name, value FROM metadata WHERE name='name' OR name='description'")
                direct_metadata = {row[0]: row[1] for row in cursor.fetchall()}
                conn.close()
                
                print(f"\n🔴🔴🔴 STARTUP - FILE LOADED 🔴🔴🔴")
                print(f"🔴 Path requested: {default_mbtiles}")
                print(f"🔴 Path resolved: {Path(default_mbtiles).resolve()}")
                print(f"🔴 File size: {Path(default_mbtiles).stat().st_size} bytes")
                print(f"🔴 From MBTilesReader: name='{metadata.name}'")
                print(f"🔴 From DIRECT SQL: name='{direct_metadata.get('name', 'NOT_FOUND')}'")
                print(f"🔴 From MBTilesReader: desc='{metadata.description}'")
                print(f"🔴 From DIRECT SQL: desc='{direct_metadata.get('description', 'NOT_FOUND')}'")
                print(f"🔴🔴🔴 END 🔴🔴🔴\n")
                
                logger.info(f"🔴 Loaded MBTiles: {default_mbtiles}, name='{metadata.name}'")
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
    
    
    def open_mbtiles_file(self) -> None:
        """
        Open a file dialog to select new MBTiles file.
        
        When a new file is selected:
        1. Loads metadata using MBTilesReader
        2. Uses MBTilesFileLoader to determine optimal center/zoom
        3. Updates settings.yaml with new configuration
        4. Updates Characteristics Panel with new metadata
        5. Updates Map Viewer with new file
        6. Syncs with Track Editor via config signals
        """
        print(f"\n🟢🟢🟢 CTRL+SHIFT+O TRIGGERED - open_mbtiles_file() called 🟢🟢🟢\n")
        logger.info("🟢🟢🟢 CTRL+SHIFT+O TRIGGERED - open_mbtiles_file() called 🟢🟢🟢")
        try:
            # Open file dialog
            file_path, _ = QFileDialog.getOpenFileName(
                self.widget,
                "Open MBTiles File",
                "mbtiles/",
                "MBTiles Files (*.mbtiles);;All Files (*)"
            )
            
            if not file_path:
                logger.debug("File open dialog cancelled")
                return
            
            logger.info(f"🔵 User selected MBTiles file: {file_path}")
            
            # Step 1: Load MBTiles metadata
            try:
                mbtiles_reader = MBTilesReader(file_path)
            except FileNotFoundError:
                QMessageBox.critical(self.widget, "Error", f"File not found: {file_path}")
                return
            except ValueError as e:
                QMessageBox.critical(self.widget, "Error", f"Invalid MBTiles file: {e}")
                return
            
            # Step 2: Use MBTilesFileLoader to determine optimal configuration
            try:
                loader = MBTilesFileLoader(mbtiles_reader, self.config)
                config_result = loader.load_and_configure(file_path)
            except Exception as e:
                logger.error(f"Error loading mbtiles configuration: {e}", exc_info=True)
                QMessageBox.critical(self.widget, "Error", f"Error loading file configuration: {e}")
                return
            
            # Step 3: Update internal state
            self.mbtiles_reader = mbtiles_reader
            self.current_mbtiles_path = file_path
            
            # Step 4: Update Characteristics Panel
            # ✅ THIS IS THE KEY FIX - was missing before!
            new_name = mbtiles_reader.get_metadata().name
            print(f"\n🟢🟢🟢 UPDATING CHARACTERISTICS PANEL WITH: {new_name} 🟢🟢🟢\n")
            logger.info(f"🟢 Calling characteristics_panel.load_mbtiles() with: {new_name}")
            self.characteristics_panel.load_mbtiles(mbtiles_reader)
            print(f"🟢 Panel should now display: {new_name}")
            logger.info(f"🟢 ✅ Characteristics panel updated with new file metadata: {new_name}")
            
            # Step 5: Update Map Viewer with new file and position
            # Set map position from configuration result
            lat = config_result['recent_center']['lat']
            lon = config_result['recent_center']['lon']
            zoom = config_result['recent_zoom']
            
            self.map_viewer.center_lat = lat
            self.map_viewer.center_lon = lon
            self.map_viewer.zoom_level = zoom
            
            # Load new MBTiles provider with the new file
            try:
                print(f"\n🔴 UPDATING MBTILES PROVIDER: {file_path} 🔴\n")
                self.mbtiles_provider.load_mbtiles_from_path(file_path)
                self.map_viewer.set_mbtiles_provider(self.mbtiles_provider)
                logger.info(f"🔴 Map provider updated with new file: {file_path}")
            except Exception as e:
                logger.error(f"Error loading MBTiles into provider: {e}", exc_info=True)
                # Don't fail completely, characteristics panel is still updated
            
            # Step 6: Emit signal to sync with Track Editor
            # This updates both tabs to show same position
            self.config.emit_map_position_changed()
            
            # Step 7: Render map
            self.map_viewer.render_map()
            
            logger.info(f"✅ Successfully loaded new MBTiles file: {file_path}")
            logger.info(f"   Position: ({lat:.4f}, {lon:.4f}) Z{zoom}")
            logger.info(f"   Zoom range: Z{config_result['min_zoom']}-Z{config_result['max_zoom']}")
            
            QMessageBox.information(
                self.widget,
                "Success",
                f"Loaded: {mbtiles_reader.get_metadata().name}\n"
                f"Position: ({lat:.4f}, {lon:.4f}) Z{zoom}\n"
                f"Zoom range: Z{config_result['min_zoom']}-Z{config_result['max_zoom']}"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in open_mbtiles_file: {e}", exc_info=True)
            QMessageBox.critical(self.widget, "Error", f"Unexpected error: {e}")
