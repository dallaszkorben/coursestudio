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
        
        # ✅ NEW: Callback to refresh other widgets when zoom generation completes
        self.on_zoom_generated_callback = None
        
        logger.debug("MapEditorTabHandler initialized")
    
    def set_on_zoom_generated_callback(self, callback):
        """Set a callback to be called after zoom generation completes."""
        self.on_zoom_generated_callback = callback
    
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
            # Get MBTiles reader from provider (already loaded by main window)
            # ================================================================
            
            if not self.mbtiles_provider or not self.mbtiles_provider.is_loaded():
                logger.warning("MBTiles provider not loaded, showing placeholder")
                self._create_error_widget(main_layout, "No MBTiles file loaded. Use Track Editor to load a file.")
                return self.widget
            
            # Get the recent mbtiles from config
            recent_mbtiles = self.config.get('appearance.tiles.recent_mbtiles')
            if not recent_mbtiles:
                logger.warning("No recent mbtiles in config")
                self._create_error_widget(main_layout, "MBTiles file not in config.")
                return self.widget
            
            # Config stores full path, extract just filename if needed
            # If it's already a full path, use it directly
            # If it's just a filename, prepend mbtiles/
            if '/' in recent_mbtiles or '\\' in recent_mbtiles:
                # It's a full path
                mbtiles_path = recent_mbtiles
            else:
                # It's just a filename, prepend mbtiles/
                mbtiles_path = f"mbtiles/{recent_mbtiles}"
            
            logger.info(f"🟢 Attempting to load mbtiles: {mbtiles_path}")
            
            if not Path(mbtiles_path).exists():
                logger.warning(f"MBTiles file not found: {mbtiles_path}")
                self._create_error_widget(main_layout, f"MBTiles file not found: {mbtiles_path}")
                return self.widget
            
            self.mbtiles_reader = MBTilesReader(mbtiles_path)
            self.current_mbtiles_path = mbtiles_path
            metadata = self.mbtiles_reader.get_metadata()
            
            available_zooms = self.mbtiles_reader.get_available_zooms()
            logger.info(f"🟢 MapEditor using MBTiles from provider: {mbtiles_path}")
            logger.info(f"🟢 Metadata: {metadata.name}")
            logger.info(f"🟢 Available zooms: {available_zooms}")
            
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
            
            # Connect Update button signal to handler
            self.characteristics_panel.update_center_requested.connect(
                self._on_update_center_requested
            )
            
            # Connect Generate Zoom Levels button signal to handler
            self.characteristics_panel.generate_zoom_levels_requested.connect(
                self._on_generate_zoom_levels_requested
            )
            
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
            
            # ✅ Set MBTiles reader for accurate zoom queries (queries database directly)
            # This is critical for zoom bounds to be updated after generating new zooms
            self.map_viewer.set_mbtiles_reader(self.mbtiles_reader)
            
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
    
    def _on_update_center_requested(self) -> None:
        """
        Handle Update button click from characteristics panel.
        
        Implementation of specification section (e):
        - Write current_center/current_zoom to mbtiles file (update mbtiles_center/mbtiles_zoom in metadata)
        - Update default_center/default_zoom in settings.yaml from current_center/current_zoom
        """
        logger.info("\n" + "="*60)
        logger.info("🔵 UPDATE BUTTON HANDLER CALLED 🔵")
        logger.info("="*60)
        
        try:
            if not self.map_viewer or not self.mbtiles_provider:
                logger.error("Map viewer or mbtiles provider not initialized")
                QMessageBox.warning(self.widget, "Error", "Map viewer not ready")
                return
            
            # Get current map position from MapViewer
            current_lon = self.map_viewer.center_lon
            current_lat = self.map_viewer.center_lat
            current_zoom = self.map_viewer.zoom_level
            
            logger.info(f"🔵 Current map position: ({current_lon:.4f}, {current_lat:.4f}) Z{current_zoom}")
            
            # Step 1: Update mbtiles file metadata
            logger.info(f"🔵 Updating mbtiles metadata...")
            success = self.mbtiles_provider.update_mbtiles_center(
                current_lon, current_lat, current_zoom
            )
            
            if not success:
                logger.error("❌ Failed to update mbtiles metadata")
                QMessageBox.critical(self.widget, "Error", "Failed to update mbtiles file")
                return
            
            logger.info(f"✅ mbtiles metadata updated successfully")
            
            # Step 2: Update settings.yaml with new default center/zoom
            logger.info(f"🔵 Updating settings.yaml...")
            self.config.set_silent('appearance.tiles.default_center.lat', current_lat)
            self.config.set_silent('appearance.tiles.default_center.lon', current_lon)
            self.config.set_silent('appearance.tiles.default_zoom', current_zoom)
            self.config.save_to_file()
            
            logger.info(f"✅ settings.yaml updated successfully")
            logger.info(f"   - default_center.lat = {current_lat}")
            logger.info(f"   - default_center.lon = {current_lon}")
            logger.info(f"   - default_zoom = {current_zoom}")
            
            # Step 3: Reload characteristics panel to show updated center
            logger.info(f"🔵 Reloading characteristics panel...")
            self.characteristics_panel.load_mbtiles(self.mbtiles_reader)
            logger.info(f"✅ Characteristics panel reloaded")
            
            # Step 4: Emit config signal to sync with Track Editor
            logger.info(f"🔵 Emitting map_position_changed signal...")
            self.config.emit_map_position_changed()
            logger.info(f"✅ Signal emitted")
            
            # Show success message
            QMessageBox.information(
                self.widget,
                "Success",
                f"Updated mbtiles center and default position:\n"
                f"({current_lon:.4f}, {current_lat:.4f}) at Z{current_zoom}\n\n"
                f"Changes saved to:\n"
                f"- mbtiles file metadata\n"
                f"- settings.yaml"
            )
            
            logger.info("="*60)
            logger.info("✅ UPDATE BUTTON HANDLER COMPLETED SUCCESSFULLY ✅")
            logger.info("="*60 + "\n")
            
        except Exception as e:
            logger.error(f"Error in update center handler: {e}", exc_info=True)
            QMessageBox.critical(self.widget, "Error", f"Update failed: {e}")
    
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
            # Get correct position from MBTilesFileLoader (which reads mbtiles metadata)
            lat = config_result['recent_center']['lat']
            lon = config_result['recent_center']['lon']
            zoom = config_result['recent_zoom']
            
            logger.info(f"🔵 Setting MapViewer position from load_and_configure(): ({lat:.4f}, {lon:.4f}) Z{zoom}")
            self.map_viewer.center_lat = lat
            self.map_viewer.center_lon = lon
            self.map_viewer.zoom_level = zoom
            
            # Load new MBTiles provider with the new file
            # ⚠️ CRITICAL: Do NOT call set_mbtiles_provider()
            # That method has its own initialization logic that can override the position
            # we just set from load_and_configure()
            try:
                logger.info(f"🔵 Loading new MBTiles provider: {file_path}")
                self.mbtiles_provider.load_mbtiles_from_path(file_path)
                
                # Update MapViewer's provider reference WITHOUT reinitializing position
                self.map_viewer.mbtiles_provider = self.mbtiles_provider
                
                # Update zoom bounds from the new provider
                available_zooms = self.mbtiles_provider.get_available_zooms()
                if available_zooms:
                    self.map_viewer.min_zoom = min(available_zooms)
                    self.map_viewer.max_zoom = max(available_zooms)
                    
                    # Clamp current zoom to valid range for new provider
                    if self.map_viewer.zoom_level < self.map_viewer.min_zoom:
                        old_zoom = self.map_viewer.zoom_level
                        self.map_viewer.zoom_level = self.map_viewer.min_zoom
                        logger.info(f"🔵 Clamped zoom Z{old_zoom} → Z{self.map_viewer.min_zoom} (new min)")
                    elif self.map_viewer.zoom_level > self.map_viewer.max_zoom:
                        old_zoom = self.map_viewer.zoom_level
                        self.map_viewer.zoom_level = self.map_viewer.max_zoom
                        logger.info(f"🔵 Clamped zoom Z{old_zoom} → Z{self.map_viewer.max_zoom} (new max)")
                
                # Store metadata center for reference (for Recenter and Update buttons)
                metadata = self.mbtiles_provider.get_metadata()
                if metadata and metadata.center:
                    self.map_viewer.metadata_center_lon = metadata.center[0]
                    self.map_viewer.metadata_center_lat = metadata.center[1]
                    self.map_viewer.metadata_center_zoom = metadata.center[2]
                    logger.info(f"🔵 Stored metadata_center: ({metadata.center[1]:.4f}, {metadata.center[0]:.4f}), Z{metadata.center[2]}")
                
                logger.info(f"🔵 ✅ Provider updated with position preserved: ({self.map_viewer.center_lat:.4f}, {self.map_viewer.center_lon:.4f}) Z{self.map_viewer.zoom_level}")
            except Exception as e:
                logger.error(f"Error loading MBTiles into provider: {e}", exc_info=True)
                # Don't fail completely, characteristics panel is still updated
            
            # Step 6: Render map
            # Note: Signal already emitted by load_and_configure(), no need to repeat
            # The config already has P1 set, just render the updated provider
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
    
    def _on_generate_zoom_levels_requested(self) -> None:
        """
        Handle Generate Zoom Levels button click from characteristics panel.
        
        Implementation:
        - Create ZoomGenerator
        - Show zoom selection dialog (NO pre-checks for missing zooms)
        - Start zoom generation in background thread
        - Show progress dialog
        - Update characteristics panel when done
        
        Note: User can generate missing zooms, regenerate existing zooms,
        or generate outside current range - all controlled by the dialog.
        """
        logger.info("\n" + "="*60)
        logger.info("🟢 GENERATE ZOOM LEVELS BUTTON HANDLER CALLED 🟢")
        logger.info("="*60)
        
        try:
            if not self.mbtiles_reader:
                logger.error("No mbtiles reader available")
                QMessageBox.warning(self.widget, "Error", "No mbtiles file loaded")
                return
            
            # Import here to avoid circular imports
            from src.core.zoom_generator import ZoomGenerator
            from src.gui.dialogs.zoom_selection_dialog import ZoomSelectionDialog
            
            logger.info("🟢 Creating zoom generator...")
            generator = ZoomGenerator(self.mbtiles_reader)
            
            # ✅ Get summary (for logging only)
            available_zooms = sorted(generator.reader.get_available_zooms())
            missing_zooms = generator.analyze_gaps()
            logger.info(f"🟢 Available zooms: {available_zooms}")
            logger.info(f"🟢 Missing zooms: {missing_zooms}")
            
            # ✅ REMOVED: Don't check for missing zooms
            # Users can regenerate existing zooms or generate outside range
            # The dialog shows all reasonable options
            
            # Show zoom selection dialog
            logger.info("🟢 Showing zoom selection dialog...")
            dialog = ZoomSelectionDialog(
                generator=generator,
                parent=self.widget
            )
            
            if dialog.exec_() != dialog.Accepted:
                logger.info("🟢 User cancelled zoom generation")
                return
            
            selected_zooms = dialog.get_selected_zooms()
            logger.info(f"🟢 User selected zooms for generation: {selected_zooms}")
            
            if not selected_zooms:
                logger.warning("🟢 No zooms selected")
                return
            
            # Start zoom generation in background thread
            logger.info(f"🟢 Starting zoom generation for: {selected_zooms}")
            self._start_zoom_generation_threaded(generator, selected_zooms)
            
            logger.info("="*60)
            logger.info("🟢 GENERATE ZOOM LEVELS HANDLER COMPLETED 🟢")
            logger.info("="*60 + "\n")
            
        except Exception as e:
            logger.error(f"Error in zoom generation handler: {e}", exc_info=True)
            QMessageBox.critical(self.widget, "Error", f"Error: {e}")
    
    def _start_zoom_generation_threaded(self, generator, selected_zooms: list) -> None:
        """
        Start zoom generation sequence (one zoom at a time).
        
        Maps to MapLoom's approach: Generate zooms sequentially, each in its own thread.
        
        Args:
            generator: ZoomGenerator instance
            selected_zooms: List of zoom levels to generate
        """
        logger.info(f"🟢 Starting generation sequence for {len(selected_zooms)} zoom levels: {sorted(selected_zooms)}")
        
        # Store state for sequential generation
        self.zoom_generator = generator
        self.zoom_selected_zooms = selected_zooms
        self.zoom_index = 0
        
        # Disable Generate button during entire generation process
        self.characteristics_panel.generate_zoom_button.setEnabled(False)
        logger.info("🟢 Disabled Generate Zoom Levels button (generation in progress)")
        
        # Generate first zoom
        self._generate_next_zoom()
    
    def _generate_next_zoom(self) -> None:
        """Generate the next zoom in the sequence."""
        if self.zoom_index >= len(self.zoom_selected_zooms):
            # All zooms generated successfully
            logger.info("🟢 All zoom levels generated successfully")
            
            # Show completion message
            QMessageBox.information(
                self.widget,
                "Generation Complete",
                f"Successfully generated {len(self.zoom_selected_zooms)} zoom levels."
            )
            
            # Refresh characteristics panel with new zoom levels
            if self.characteristics_panel and self.mbtiles_reader:
                self.characteristics_panel.load_mbtiles(self.mbtiles_reader)
                logger.info("🟢 Refreshed characteristics panel")
            
            # Refresh map viewer
            if self.map_viewer:
                self.map_viewer._update_zoom_bounds_from_provider()
                logger.info("🟢 Updated map viewer zoom bounds")
            
            # Re-enable Generate button
            self.characteristics_panel.generate_zoom_button.setEnabled(True)
            logger.info("🟢 Re-enabled Generate Zoom Levels button")
            
            logger.info("="*60)
            logger.info("🟢 ZOOM GENERATION SEQUENCE COMPLETE 🟢")
            logger.info("="*60 + "\n")
            return
        
        # Get next zoom to generate
        target_zoom = self.zoom_selected_zooms[self.zoom_index]
        self.zoom_index += 1
        
        logger.info(f"🟢 Generating zoom {self.zoom_index}/{len(self.zoom_selected_zooms)}: Z{target_zoom}")
        
        # Generate single zoom
        self._generate_single_zoom_threaded(target_zoom)
    
    def _generate_single_zoom_threaded(self, target_zoom: int) -> None:
        """
        Generate a single zoom level in background thread.
        
        Args:
            target_zoom: Zoom level to generate
        """
        try:
            from src.core.tile_processor import TileProcessor
            from src.core.zoom_generation_worker import ZoomGenerationWorker
            from src.gui.dialogs.zoom_generation_progress_dialog import ZoomGenerationProgressDialog
            from PyQt5.QtCore import QThread
            
            logger.info(f"🟢 Creating generation plan for Z{target_zoom}")
            
            # Create generation plan
            plan = self.zoom_generator.create_generation_plan(target_zoom)
            logger.info(f"🟢 Plan: source=Z{plan.source_zoom}, tiles={plan.tile_count}, "
                       f"strategy={plan.source_type}, warning={plan.quality_warning}")
            
            # Create processor
            processor = TileProcessor(self.mbtiles_reader, self.current_mbtiles_path)
            logger.info("🟢 Created TileProcessor")
            
            # Create progress dialog
            progress_dialog = ZoomGenerationProgressDialog(parent=self.widget)
            logger.info("🟢 Created progress dialog")
            
            # Create worker and thread
            worker = ZoomGenerationWorker(processor, plan, target_zoom)
            thread = QThread()
            worker.moveToThread(thread)
            logger.info("🟢 Created worker and thread")
            
            # Connect signals
            worker.progress.connect(progress_dialog.update_progress)
            worker.finished.connect(lambda: self._on_single_zoom_finished(thread, progress_dialog, target_zoom))
            worker.error.connect(lambda err: self._on_single_zoom_error(thread, progress_dialog, err, target_zoom))
            worker.cancelled.connect(lambda: self._on_single_zoom_cancelled(thread, progress_dialog, target_zoom))
            
            logger.info("🟢 Connected worker signals to progress dialog")
            
            # Connect thread
            thread.started.connect(worker.run)
            
            # Store references
            self.zoom_generation_thread = thread
            self.zoom_generation_worker = worker
            self.zoom_progress_dialog = progress_dialog
            
            # Start thread
            thread.start()
            logger.info(f"🟢 Started generation thread for Z{target_zoom}")
            
            # Show progress dialog (modal - blocks until generation complete or user cancels)
            progress_dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error starting zoom generation for Z{target_zoom}: {e}", exc_info=True)
            QMessageBox.critical(self.widget, "Error", f"Error starting generation:\n{str(e)}")
            # Re-enable button on error
            self.characteristics_panel.generate_zoom_button.setEnabled(True)
    
    def _on_single_zoom_finished(self, thread: 'QThread', progress_dialog, target_zoom: int) -> None:
        """Handle successful single zoom generation completion."""
        logger.info(f"🟢 Z{target_zoom} generation finished successfully")
        
        # Stop thread
        thread.quit()
        thread.wait()
        logger.info(f"🟢 Thread cleanup for Z{target_zoom}")
        
        # Close progress dialog
        progress_dialog.close()
        logger.info(f"🟢 Closed progress dialog for Z{target_zoom}")
        
        # Mark zoom as generated in reader
        if self.mbtiles_reader:
            self.mbtiles_reader.mark_zoom_as_generated(target_zoom)
            logger.info(f"🟢 Marked Z{target_zoom} as generated in reader")
        
        # Refresh reader's cached zoom levels
        if self.mbtiles_reader:
            self.mbtiles_reader.refresh_zoom_levels()
            logger.info(f"🟢 Refreshed reader zoom levels after Z{target_zoom}")
        
        # ✅ CRITICAL: Refresh provider's metadata to pick up new zoom levels
        # This is essential because provider's get_available_zooms() uses cached metadata
        if self.mbtiles_provider:
            self.mbtiles_provider.refresh_metadata()
            logger.info(f"🟢 Refreshed MBTilesProvider metadata after Z{target_zoom}")
        
        # ✅ CRITICAL: Update map viewer's zoom bounds from provider (now refreshed)
        if self.map_viewer:
            self.map_viewer._update_zoom_bounds_from_provider()
            logger.info(f"🟢 Updated MapViewer zoom bounds: Z{self.map_viewer.min_zoom}-Z{self.map_viewer.max_zoom}")
        
        # ✅ NEW: Call callback to refresh other widgets (e.g., TrackEditor's map_widget)
        if self.on_zoom_generated_callback:
            self.on_zoom_generated_callback()
            logger.info(f"🟢 Called zoom generation callback to sync other widgets")
        
        # Generate next zoom
        self._generate_next_zoom()
    
    def _on_single_zoom_error(self, thread: 'QThread', progress_dialog, error_msg: str, target_zoom: int) -> None:
        """Handle single zoom generation error."""
        logger.error(f"🔴 Error generating Z{target_zoom}: {error_msg}")
        
        # Stop thread
        thread.quit()
        thread.wait()
        
        # Close progress dialog
        progress_dialog.close()
        
        # Show error message
        response = QMessageBox.critical(
            self.widget,
            "Generation Error",
            f"Error generating Z{target_zoom}:\n\n{error_msg}\n\n"
            "Would you like to continue with the next zoom level?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if response == QMessageBox.Yes:
            # Continue to next zoom
            self._generate_next_zoom()
        else:
            # Stop generation and re-enable button
            self.characteristics_panel.generate_zoom_button.setEnabled(True)
            logger.info("🟢 Generation cancelled by user after error")
    
    def _on_single_zoom_cancelled(self, thread: 'QThread', progress_dialog, target_zoom: int) -> None:
        """Handle single zoom generation cancellation."""
        logger.info(f"🟢 Z{target_zoom} generation cancelled by user")
        
        # Stop thread
        thread.quit()
        thread.wait()
        
        # Close progress dialog
        progress_dialog.close()
        
        # Stop entire generation process
        self.characteristics_panel.generate_zoom_button.setEnabled(True)
        logger.info("🟢 Generation stopped, button re-enabled")

