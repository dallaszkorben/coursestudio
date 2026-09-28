"""
Track Path Settings Widget for CourseStudio Settings.

Combines color picker and width slider for track path appearance settings.
"""

import logging
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox, QWidget
from PyQt5.QtCore import Qt, pyqtSignal

from config.app_config_yaml import AppConfig
from src.gui.widgets.color_picker_widget import ColorPickerWidget

logger = logging.getLogger(__name__)


class TrackPathSettingsWidget(QGroupBox):
    """
    Track Path appearance settings section.
    
    Provides controls for:
    - Track path color (color picker with presets + RGB sliders)
    - Track path width (slider 1-9px)
    """
    
    settings_changed = pyqtSignal()  # Emitted when settings change
    
    def __init__(self, config: AppConfig = None):
        """
        Initialize track path settings widget.
        
        Args:
            config: AppConfig instance (optional, for loading defaults)
        """
        super().__init__("Track Path")
        
        self.config = config or AppConfig()
        
        # Load current values from config
        self.color = self.config.get_str('Appearance.MapDisplay.TrackPath.color', 'FF0000')
        self.width = self.config.get_int('Appearance.MapDisplay.TrackPath.width', 3)
        self._updating = False  # Flag to prevent recursive updates
        
        # Apply white frame styling (main section)
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid white;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0px 4px;
            }
        """)
        
        self._init_ui()
        self._connect_signals()
        
        logger.info(f"TrackPathSettingsWidget initialized (color={self.color}, width={self.width})")
    
    def _init_ui(self):
        """Initialize the user interface with grid layout for alignment."""
        
        from PyQt5.QtWidgets import QGridLayout
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Color picker at top
        self.color_picker = ColorPickerWidget(initial_color=self.color, config=self.config)
        layout.addWidget(self.color_picker)
        
        # Grid layout for Width control - aligned with other sliders
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setColumnStretch(0, 0)  # Label column - fixed width
        grid.setColumnStretch(1, 1)  # Control column - flexible
        
        # Width label - FIXED WIDTH to align with other "Size" labels
        width_label = QLabel("Width:")
        width_label.setStyleSheet("font-weight: bold; color: white;")
        width_label.setFixedWidth(70)  # Fixed width for cross-widget alignment
        grid.addWidget(width_label, 0, 0, Qt.AlignLeft)
        
        # Width slider + spinbox
        width_control_layout = QHBoxLayout()
        width_control_layout.setContentsMargins(0, 0, 0, 0)
        width_control_layout.setSpacing(8)
        
        self.width_slider_obj = QSlider(Qt.Horizontal)
        self.width_slider_obj.setMinimum(1)
        self.width_slider_obj.setMaximum(9)
        self.width_slider_obj.setValue(self.width)
        self.width_slider_obj.setTickPosition(QSlider.NoTicks)
        from src.gui.widgets.slider_setting_widget import SLIDER_STYLESHEET
        self.width_slider_obj.setStyleSheet(SLIDER_STYLESHEET)
        self.width_slider_obj.setMinimumHeight(30)
        self.width_slider_obj.valueChanged.connect(self._on_width_slider_changed)
        width_control_layout.addWidget(self.width_slider_obj)
        
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setMinimum(1)
        self.width_spinbox.setMaximum(9)
        self.width_spinbox.setValue(self.width)
        self.width_spinbox.setSuffix(" px")
        self.width_spinbox.setMaximumWidth(50)
        self.width_spinbox.valueChanged.connect(self._on_width_spinbox_changed)
        width_control_layout.addWidget(self.width_spinbox)
        
        width_control_widget = QWidget()
        width_control_widget.setLayout(width_control_layout)
        grid.addWidget(width_control_widget, 0, 1)
        
        layout.addLayout(grid)
        
        # Add stretch to push controls to top
        layout.addStretch()
    
    def _connect_signals(self):
        """Connect widget signals."""
        
        self.color_picker.color_changed.connect(self._on_color_changed)
        self.width_slider_obj.valueChanged.connect(self._on_width_slider_changed)
        self.width_spinbox.valueChanged.connect(self._on_width_spinbox_changed)
    
    def _on_color_changed(self, hex_color: str):
        """Handle color change."""
        self.color = hex_color
        logger.debug(f"Track path color changed to: {hex_color}")
        self.settings_changed.emit()
    
    def _on_width_slider_changed(self, value: int):
        """Handle width slider change."""
        self._updating = True
        self.width = value
        self.width_spinbox.setValue(value)
        self._updating = False
        logger.debug(f"Track path width changed to: {value}px")
        self.settings_changed.emit()
    
    def _on_width_spinbox_changed(self, value: int):
        """Handle width spinbox change."""
        if hasattr(self, '_updating') and self._updating:
            return
        self._updating = True
        self.width = value
        self.width_slider_obj.setValue(value)
        self._updating = False
        logger.debug(f"Track path width changed to: {value}px")
        self.settings_changed.emit()
    
    def get_color(self) -> str:
        """Get current track path color."""
        return self.color_picker.get_color()
    
    def set_color(self, hex_color: str):
        """Set track path color."""
        self.color_picker.set_color(hex_color)
    
    def get_width(self) -> int:
        """Get current track path width."""
        return self.width_slider_obj.value()
    
    def set_width(self, width: int):
        """Set track path width."""
        self._updating = True
        self.width_slider_obj.setValue(width)
        self.width_spinbox.setValue(width)
        self._updating = False
    
    def apply_to_config(self):
        """Apply current settings to configuration."""
        
        self.config.config_data['Appearance']['MapDisplay']['TrackPath']['color'] = self.get_color()
        self.config.config_data['Appearance']['MapDisplay']['TrackPath']['width'] = self.get_width()
        
        logger.info(f"Track path settings applied: color={self.get_color()}, width={self.get_width()}")
    
    def save_to_file(self) -> bool:
        """Save settings to file."""
        
        self.apply_to_config()
        return self.config.save_to_file()
