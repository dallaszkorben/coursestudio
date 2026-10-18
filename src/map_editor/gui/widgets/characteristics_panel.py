"""
Characteristics Panel Widget

Displays MBTiles file information and zoom levels.
Scrollable left panel showing metadata and statistics.

Author: Development Team
Date: 2026-10-11
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel, QFrame,
    QGroupBox, QGridLayout, QListWidget, QListWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QIcon
from src.map_editor.core.mbtiles_reader import MBTilesReader, MBTilesMetadata
import logging


logger = logging.getLogger(__name__)

# ✅ Configuration for coordinate display
COORDINATE_FORMAT = 'dms'  # 'dms' for degree/minute/second, 'dd' for decimal degrees
DECIMAL_PLACES = 6  # Used when coordinate_format='dd'


def format_coordinate(value: float, format_type: str = 'dms', decimals: int = 6) -> str:
    """
    Format a coordinate value as DMS or decimal degrees.
    
    Args:
        value: Coordinate value in decimal degrees
        format_type: 'dms' for degree/minute/second, 'dd' for decimal degrees
        decimals: Number of decimal places (used for 'dd' format)
        
    Returns:
        Formatted coordinate string
    """
    if format_type == 'dd':
        return f"{value:.{decimals}f}°"
    else:  # dms
        # Convert decimal degrees to DMS
        sign = 1 if value >= 0 else -1
        value = abs(value)
        degrees = int(value)
        minutes_float = (value - degrees) * 60
        minutes = int(minutes_float)
        seconds = (minutes_float - minutes) * 60
        
        return f"{sign * degrees}°{minutes}'{seconds:.2f}\""


class ZoomLevelItem(QListWidgetItem):
    """Custom list item for zoom level display."""
    
    def __init__(self, zoom_level_info):
        """
        Initialize zoom level item.
        
        Args:
            zoom_level_info: ZoomLevelInfo object with zoom, tile_count, is_original
        """
        super().__init__()
        
        self.zoom_info = zoom_level_info
        
        # Format display text
        zoom = zoom_level_info.zoom
        tiles = zoom_level_info.tile_count
        status = "✓ Original" if zoom_level_info.is_original else "◆ Generated"
        
        text = f"Z{zoom:2d}  {tiles:>6,} tiles  {status}"
        
        # Create a label widget with center alignment
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        
        # Set font
        font = QFont("Courier", 9)
        if not zoom_level_info.is_original:
            font.setItalic(True)
        label.setFont(font)
        
        # Set color
        color = "#FFFFFF" if zoom_level_info.is_original else "#66CCFF"
        label.setStyleSheet(f"QLabel {{ color: {color}; }}")
        
        self.setText("")  # Clear item text, will use widget instead
        
        # Store zoom for later retrieval
        self.setData(Qt.UserRole, zoom)


class CharacteristicsPanel(QWidget):
    """
    Left panel displaying MBTiles file characteristics.
    
    Responsibilities:
        - Display file metadata (name, description, format, etc.)
        - Show zoom levels with indicators (original vs generated)
        - Display file statistics
        - Scrollable for all content
    """
    
    zoom_selected = pyqtSignal(int)  # Emitted when zoom level is selected
    center_requested = pyqtSignal(float, float)  # Emitted when center button clicked (lon, lat)
    recenter_requested = pyqtSignal(float, float, int)  # Emitted when recenter button clicked (lon, lat, zoom)
    metadata_updated = pyqtSignal()  # Emitted when name/description is updated
    update_center_requested = pyqtSignal()  # Emitted when Update button clicked (to save current map position)
    
    def __init__(self, parent=None):
        """Initialize characteristics panel."""
        super().__init__(parent)
        
        self.mbtiles_reader: Optional[MBTilesReader] = None
        
        self._setup_ui()
        logger.debug("CharacteristicsPanel initialized")
    
    
    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Set dark background for the widget
        self.setStyleSheet("""
            CharacteristicsPanel {
                background-color: #2b2b2b;
                color: #FFFFFF;
            }
            QGroupBox {
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px 0 3px;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)
        
        # Create scroll area for all content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #2b2b2b; }")
        
        # Container widget inside scroll
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container.setStyleSheet("background-color: #2b2b2b;")
        
        # Title
        title = QLabel("File Characteristics")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #FFFFFF;")
        container_layout.addWidget(title)
        
        # File Info Section
        file_info_group = QGroupBox("File Information")
        file_info_layout = QGridLayout(file_info_group)
        
        # Name row with Save button
        name_widget = QWidget()
        name_layout = QHBoxLayout(name_widget)
        name_layout.setContentsMargins(0, 0, 0, 0)
        
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #FFFFFF;
                border: 1px solid #444444;
                padding: 4px;
            }
        """)
        
        self.save_name_button = QPushButton("Save")
        self.save_name_button.setMaximumWidth(50)
        self.save_name_button.clicked.connect(self._on_save_name)
        
        name_layout.addWidget(self.name_input)
        name_layout.addWidget(self.save_name_button)
        
        # Description row with Save button
        desc_widget = QWidget()
        desc_layout = QHBoxLayout(desc_widget)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        
        self.description_input = QLineEdit()
        self.description_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #FFFFFF;
                border: 1px solid #444444;
                padding: 4px;
            }
        """)
        
        self.save_description_button = QPushButton("Save")
        self.save_description_button.setMaximumWidth(50)
        self.save_description_button.clicked.connect(self._on_save_description)
        
        desc_layout.addWidget(self.description_input)
        desc_layout.addWidget(self.save_description_button)
        
        self.format_label = self._create_info_label()
        self.type_label = self._create_info_label()
        self.version_label = self._create_info_label()
        
        file_info_layout.addWidget(QLabel("Name:"), 0, 0, Qt.AlignRight)
        file_info_layout.addWidget(name_widget, 0, 1)
        file_info_layout.addWidget(QLabel("Description:"), 1, 0, Qt.AlignRight)
        file_info_layout.addWidget(desc_widget, 1, 1)
        file_info_layout.addWidget(QLabel("Format:"), 2, 0, Qt.AlignRight)
        file_info_layout.addWidget(self.format_label, 2, 1)
        file_info_layout.addWidget(QLabel("Type:"), 3, 0, Qt.AlignRight)
        file_info_layout.addWidget(self.type_label, 3, 1)
        file_info_layout.addWidget(QLabel("Version:"), 4, 0, Qt.AlignRight)
        file_info_layout.addWidget(self.version_label, 4, 1)
        
        file_info_layout.setColumnStretch(1, 1)
        container_layout.addWidget(file_info_group)
        
        # Map Bounds Section
        bounds_group = QGroupBox("Map Bounds")
        bounds_layout = QGridLayout(bounds_group)
        
        self.bounds_label = self._create_info_label()
        
        # Center layout with label and button
        center_widget = QWidget()
        center_item_layout = QHBoxLayout(center_widget)
        center_item_layout.setContentsMargins(0, 0, 0, 0)
        
        self.center_label = self._create_info_label()
        self.recenter_button = QPushButton("Update")
        self.recenter_button.setMaximumWidth(60)
        self.recenter_button.setEnabled(True)  # Always enabled so user can save current map position
        self.recenter_button.clicked.connect(self._on_update_center_clicked)
        
        center_item_layout.addWidget(self.center_label)
        center_item_layout.addWidget(self.recenter_button)
        
        bounds_layout.addWidget(QLabel("Bounds:"), 0, 0, Qt.AlignRight)
        bounds_layout.addWidget(self.bounds_label, 0, 1)
        bounds_layout.addWidget(QLabel("Default Center:"), 1, 0, Qt.AlignRight)
        bounds_layout.addWidget(center_widget, 1, 1)
        
        bounds_layout.setColumnStretch(1, 1)
        container_layout.addWidget(bounds_group)
        
        # Zoom Levels Section
        zoom_group = QGroupBox("Zoom Levels")
        zoom_layout = QVBoxLayout(zoom_group)
        
        self.zoom_list = QListWidget()
        self.zoom_list.setMinimumHeight(150)
        self.zoom_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #FFFFFF;
                border: 1px solid #444444;
            }
            QListWidget::item {
                padding: 2px;
            }
        """)
        self.zoom_list.itemSelectionChanged.connect(self._on_zoom_selected)
        zoom_layout.addWidget(self.zoom_list)
        
        container_layout.addWidget(zoom_group)
        
        # Statistics Section
        stats_group = QGroupBox("Statistics")
        stats_layout = QGridLayout(stats_group)
        
        self.total_tiles_label = self._create_info_label()
        self.zoom_range_label = self._create_info_label()
        self.file_size_label = self._create_info_label()
        self.missing_zooms_label = self._create_info_label()
        
        stats_layout.addWidget(QLabel("Total Tiles:"), 0, 0, Qt.AlignRight)
        stats_layout.addWidget(self.total_tiles_label, 0, 1)
        stats_layout.addWidget(QLabel("Zoom Range:"), 1, 0, Qt.AlignRight)
        stats_layout.addWidget(self.zoom_range_label, 1, 1)
        stats_layout.addWidget(QLabel("File Size:"), 2, 0, Qt.AlignRight)
        stats_layout.addWidget(self.file_size_label, 2, 1)
        stats_layout.addWidget(QLabel("Missing Zooms:"), 3, 0, Qt.AlignRight)
        stats_layout.addWidget(self.missing_zooms_label, 3, 1)
        
        stats_layout.setColumnStretch(1, 1)
        container_layout.addWidget(stats_group)
        
        # Stretch remaining space
        container_layout.addStretch()
        
        # Add container to scroll area
        scroll.setWidget(container)
        
        # Add scroll area to main layout
        layout.addWidget(scroll)
        
        logger.debug("UI setup complete")
    
    
    def _create_info_label(self) -> QLabel:
        """Create a styled info label."""
        label = QLabel("—")
        label.setWordWrap(True)
        label.setStyleSheet("color: #FFFFFF; font-family: monospace; background-color: #1e1e1e; padding: 2px;")
        return label
    
    
    def load_mbtiles(self, reader: MBTilesReader) -> None:
        """
        Load and display MBTiles file information.
        
        Args:
            reader (MBTilesReader): MBTiles reader with loaded file
        """
        logger.info(f"🔵 load_mbtiles() called with reader for: {reader.get_metadata().name}")
        
        self.mbtiles_reader = reader
        
        # Get metadata
        metadata = reader.get_metadata()
        logger.info(f"🔵 Metadata retrieved: name='{metadata.name}', desc='{metadata.description}'")
        
        # CLEAR ALL FIELDS FIRST - ensure old values are gone
        logger.info("🔵 Clearing all fields...")
        self.name_input.clear()
        self.description_input.clear()
        self.format_label.clear()
        self.type_label.clear()
        self.version_label.clear()
        self.bounds_label.clear()
        self.center_label.clear()
        self.total_tiles_label.clear()
        self.zoom_range_label.clear()
        self.file_size_label.clear()
        self.missing_zooms_label.clear()
        self.zoom_list.clear()
        logger.info("🔵 All fields cleared")
        
        # Update file info (populate editable fields)
        self.name_input.blockSignals(True)
        self.name_input.setText(metadata.name or "")
        self.name_input.blockSignals(False)
        logger.info(f"🔵 name_input set to: '{self.name_input.text()}'")
        
        self.description_input.blockSignals(True)
        self.description_input.setText(metadata.description or "")
        self.description_input.blockSignals(False)
        logger.info(f"🔵 description_input set to: '{self.description_input.text()}'")
        
        self.format_label.setText(metadata.format or "unknown")
        self.type_label.setText(metadata.type or "baselayer")
        self.version_label.setText(metadata.version if metadata.version else "(not set in file)")
        
        # Update bounds (formatted according to coordinate_format)
        if metadata.bounds:
            west, south, east, north = metadata.bounds
            west_str = format_coordinate(west, COORDINATE_FORMAT, DECIMAL_PLACES)
            south_str = format_coordinate(south, COORDINATE_FORMAT, DECIMAL_PLACES)
            east_str = format_coordinate(east, COORDINATE_FORMAT, DECIMAL_PLACES)
            north_str = format_coordinate(north, COORDINATE_FORMAT, DECIMAL_PLACES)
            self.bounds_label.setText(f"W:{west_str} S:{south_str} E:{east_str} N:{north_str}")
        else:
            self.bounds_label.setText("(not set in file)")
        
        # Update center (formatted according to coordinate_format)
        if metadata.center:
            lon, lat, zoom = metadata.center
            lon_str = format_coordinate(lon, COORDINATE_FORMAT, DECIMAL_PLACES)
            lat_str = format_coordinate(lat, COORDINATE_FORMAT, DECIMAL_PLACES)
            self.center_label.setText(f"({lon_str}, {lat_str}) at Z{zoom}")
        else:
            self.center_label.setText("(not set in file)")
        
        # Update zoom levels
        self.zoom_list.clear()
        for zoom_info in reader.get_zoom_levels():
            item = ZoomLevelItem(zoom_info)
            self.zoom_list.addItem(item)
            
            # Create centered label widget
            zoom = zoom_info.zoom
            tiles = zoom_info.tile_count
            status = "✓ Original" if zoom_info.is_original else "◆ Generated"
            text = f"Z{zoom:2d}  {tiles:>6,} tiles  {status}"
            
            label = QLabel(text)
            label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            
            font = QFont("Courier", 9)
            if not zoom_info.is_original:
                font.setItalic(True)
            label.setFont(font)
            
            color = "#FFFFFF" if zoom_info.is_original else "#66CCFF"
            label.setStyleSheet(f"QLabel {{ color: {color}; padding: 8px; }}")
            
            # Set fixed item height for consistent spacing
            item.setSizeHint(QSize(400, 32))
            
            # Set the label as the item widget
            self.zoom_list.setItemWidget(item, label)
        
        # Update statistics
        stats = reader.get_file_statistics()
        self.total_tiles_label.setText(f"{stats['total_tiles']:,}")
        
        min_z, max_z = stats['zoom_range']
        self.zoom_range_label.setText(f"Z{min_z} - Z{max_z}")
        
        file_size_mb = stats['file_size_mb']
        if file_size_mb < 1:
            size_text = f"{stats['file_size'] / 1024:.1f} KB"
        else:
            size_text = f"{file_size_mb:.1f} MB"
        self.file_size_label.setText(size_text)
        
        missing = reader.get_missing_zooms()
        if missing:
            missing_str = ", ".join(f"Z{z}" for z in missing[:10])
            if len(missing) > 10:
                missing_str += f", ... ({len(missing) - 10} more)"
            self.missing_zooms_label.setText(missing_str)
        else:
            self.missing_zooms_label.setText("—")
        
        logger.info(f"Loaded characteristics for: {metadata.name}")
        
        # Force UI refresh
        self.update()
        self.repaint()
    
    
    def _on_zoom_selected(self) -> None:
        """Handle zoom level selection."""
        current = self.zoom_list.currentItem()
        if current:
            zoom = current.data(Qt.UserRole)
            if zoom:
                self.zoom_selected.emit(zoom)
                logger.debug(f"Zoom selected: {zoom}")
    
    def _on_save_name(self) -> None:
        """Handle save button click for Name field."""
        if self.mbtiles_reader:
            self.mbtiles_reader.metadata.name = self.name_input.text()
            if self.mbtiles_reader.save_metadata():
                logger.info(f"Name saved: {self.name_input.text()}")
                self.metadata_updated.emit()
            else:
                logger.error("Failed to save name")
    
    def _on_save_description(self) -> None:
        """Handle save button click for Description field."""
        if self.mbtiles_reader:
            self.mbtiles_reader.metadata.description = self.description_input.text()
            if self.mbtiles_reader.save_metadata():
                logger.info(f"Description saved: {self.description_input.text()}")
                self.metadata_updated.emit()
            else:
                logger.error("Failed to save description")
    
    def _on_update_center_clicked(self) -> None:
        """
        Handle Update button click.
        
        Emits signal to request updating mbtiles center with current map position.
        The tab handler receives this signal and:
        1. Gets current_center/current_zoom from MapViewer
        2. Writes to mbtiles metadata
        3. Updates default_center/default_zoom in settings.yaml
        """
        logger.info("Update button clicked - requesting center update")
        self.update_center_requested.emit()
    
    def clear(self) -> None:
        """Clear all displayed information."""
        self.mbtiles_reader = None
        
        self.name_input.setText("—")
        self.description_input.setText("—")
        self.format_label.setText("—")
        self.type_label.setText("—")
        self.version_label.setText("—")
        
        self.bounds_label.setText("—")
        self.center_label.setText("—")
        
        self.zoom_list.clear()
        
        self.total_tiles_label.setText("—")
        self.zoom_range_label.setText("—")
        self.file_size_label.setText("—")
        self.missing_zooms_label.setText("—")
        
        logger.debug("Cleared characteristics panel")
