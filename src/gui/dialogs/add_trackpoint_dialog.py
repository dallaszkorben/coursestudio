"""Add Trackpoint Dialog for mangpx.

Provides a user interface for adding new trackpoints to a track.
Supports both DMS and Decimal coordinate formats.
"""

import logging
from typing import Optional, Tuple
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QMessageBox, QGroupBox, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt

from src.utils.coordinate_formatter import (
    parse_coordinate, dms_to_decimal
)


logger = logging.getLogger(__name__)


class AddTrackpointDialog(QDialog):
    """
    Dialog for adding a new trackpoint to a track.
    
    Allows user to:
    - Input latitude and longitude (DMS or Decimal format)
    - Input optional altitude
    - Choose insert position (at end or at specific index)
    
    Example:
        >>> dialog = AddTrackpointDialog(parent, max_index=100)
        >>> if dialog.exec_() == QDialog.Accepted:
        ...     lat, lon, alt, pos = dialog.get_trackpoint()
        ...     print(f"Adding point at {lat}, {lon}")
    """
    
    def __init__(self, parent=None, max_index: int = 0):
        """
        Initialize the Add Trackpoint Dialog.
        
        Args:
            parent: Parent widget
            max_index: Maximum index in the track (for position validation)
        """
        super().__init__(parent)
        self.max_index = max_index
        self.setWindowTitle("Add Trackpoint")
        self.setGeometry(400, 400, 500, 450)
        
        self._setup_ui()
        self._connect_signals()
        
        logger.debug(f"AddTrackpointDialog initialized (max_index={max_index})")
    
    def _setup_ui(self):
        """Set up the user interface."""
        
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Coordinate format group
        format_group = QGroupBox("Coordinate Format")
        format_layout = QHBoxLayout()
        
        self.format_buttons = QButtonGroup()
        self.decimal_radio = QRadioButton("Decimal")
        self.decimal_radio.setChecked(True)
        self.dms_radio = QRadioButton("DMS (Degrees, Minutes, Seconds)")
        
        self.format_buttons.addButton(self.decimal_radio, 0)
        self.format_buttons.addButton(self.dms_radio, 1)
        
        format_layout.addWidget(self.decimal_radio)
        format_layout.addWidget(self.dms_radio)
        format_group.setLayout(format_layout)
        main_layout.addWidget(format_group)
        
        # Latitude section
        lat_layout = QHBoxLayout()
        lat_layout.addWidget(QLabel("Latitude:"))
        
        self.lat_input = QLineEdit()
        self.lat_input.setPlaceholderText("e.g., 57.5126 or 57°30'45.5\"N")
        self.lat_input.setToolTip("Decimal: 57.5126 | DMS: 57°30'45.5\"N or 57-30-45.5N")
        lat_layout.addWidget(self.lat_input)
        main_layout.addLayout(lat_layout)
        
        # Longitude section
        lon_layout = QHBoxLayout()
        lon_layout.addWidget(QLabel("Longitude:"))
        
        self.lon_input = QLineEdit()
        self.lon_input.setPlaceholderText("e.g., 12.2584 or 12°15'30.2\"E")
        self.lon_input.setToolTip("Decimal: 12.2584 | DMS: 12°15'30.2\"E or 12-15-30.2E")
        lon_layout.addWidget(self.lon_input)
        main_layout.addLayout(lon_layout)
        
        # Altitude section (optional)
        alt_layout = QHBoxLayout()
        alt_layout.addWidget(QLabel("Altitude (optional):"))
        
        self.alt_spin = QDoubleSpinBox()
        self.alt_spin.setRange(-100, 10000)
        self.alt_spin.setValue(0)
        self.alt_spin.setSuffix(" m")
        self.alt_spin.setToolTip("Leave at 0 if not known")
        alt_layout.addWidget(self.alt_spin)
        alt_layout.addStretch()
        main_layout.addLayout(alt_layout)
        
        # Position section
        position_group = QGroupBox("Insert Position")
        position_layout = QVBoxLayout()
        
        self.end_radio = QRadioButton(f"At end of track ({self.max_index} total points)")
        self.end_radio.setChecked(True)
        position_layout.addWidget(self.end_radio)
        
        # At specific index option
        index_layout = QHBoxLayout()
        self.index_radio = QRadioButton("At specific index:")
        self.index_radio.setChecked(False)
        index_layout.addWidget(self.index_radio)
        
        self.index_spin = QSpinBox()
        self.index_spin.setRange(0, self.max_index)
        self.index_spin.setValue(0)
        self.index_spin.setEnabled(False)
        index_layout.addWidget(self.index_spin)
        index_layout.addStretch()
        position_layout.addLayout(index_layout)
        
        position_group.setLayout(position_layout)
        main_layout.addWidget(position_group)
        
        # Button section
        button_layout = QHBoxLayout()
        
        ok_button = QPushButton("Add Point")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self._validate_and_accept)
        button_layout.addWidget(ok_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        main_layout.addLayout(button_layout)
        
        logger.debug("AddTrackpointDialog UI set up")
    
    def _connect_signals(self):
        """Connect internal signals."""
        
        self.index_radio.toggled.connect(self.index_spin.setEnabled)
        self.dms_radio.toggled.connect(self._on_format_changed)
        self.decimal_radio.toggled.connect(self._on_format_changed)
    
    def _on_format_changed(self):
        """Handle coordinate format change."""
        
        if self.dms_radio.isChecked():
            self.lat_input.setPlaceholderText("e.g., 57°30'45.5\"N or 57-30-45.5N")
            self.lon_input.setPlaceholderText("e.g., 12°15'30.2\"E or 12-15-30.2E")
        else:
            self.lat_input.setPlaceholderText("e.g., 57.5126")
            self.lon_input.setPlaceholderText("e.g., 12.2584")
    
    def _validate_and_accept(self):
        """Validate input and accept the dialog."""
        
        try:
            lat, lon, alt, pos = self.get_trackpoint()
            self.accept()
        except ValueError as e:
            QMessageBox.critical(self, "Invalid Input", str(e))
            logger.warning(f"Validation error: {e}")
    
    def get_trackpoint(self) -> Tuple[float, float, Optional[float], Optional[int]]:
        """
        Get the trackpoint data from the dialog.
        
        Returns:
            Tuple[float, float, Optional[float], Optional[int]]: 
            (latitude, longitude, altitude, position)
            
        Raises:
            ValueError: If input is invalid
        """
        
        # Parse latitude
        lat_text = self.lat_input.text().strip()
        if not lat_text:
            raise ValueError("Latitude is required")
        
        try:
            latitude = parse_coordinate(lat_text, is_longitude=False)
        except ValueError as e:
            raise ValueError(f"Invalid latitude: {e}")
        
        # Parse longitude
        lon_text = self.lon_input.text().strip()
        if not lon_text:
            raise ValueError("Longitude is required")
        
        try:
            longitude = parse_coordinate(lon_text, is_longitude=True)
        except ValueError as e:
            raise ValueError(f"Invalid longitude: {e}")
        
        # Get altitude (0 if not specified)
        altitude = self.alt_spin.value()
        altitude = altitude if altitude != 0 else None
        
        # Get position
        position = None
        if self.index_radio.isChecked():
            position = self.index_spin.value()
        
        logger.debug(f"Trackpoint created: lat={latitude}, lon={longitude}, alt={altitude}, pos={position}")
        
        return latitude, longitude, altitude, position


__all__ = ['AddTrackpointDialog']
