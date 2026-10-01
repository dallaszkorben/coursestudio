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
        self.body_color = self.config.get_str('Appearance.MapDisplay.TrackPath.body.color', 'FF0000')
        self.body_width = self.config.get_int('Appearance.MapDisplay.TrackPath.body.width', 3)
        self.outline_color = self.config.get_str('Appearance.MapDisplay.TrackPath.outline.color', 'FFFFFF')
        self.outline_width = self.config.get_int('Appearance.MapDisplay.TrackPath.outline.width', 1)
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
        
        logger.info(f"TrackPathSettingsWidget initialized (body_color={self.body_color}, body_width={self.body_width}, outline_color={self.outline_color}, outline_width={self.outline_width})")
    
    def _init_ui(self):
        """Initialize the user interface with grid layout for alignment."""
        
        from PyQt5.QtWidgets import QGridLayout
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # ====== BODY (Track line itself) ======
        body_label_title = QLabel("Track Body")
        body_label_title.setStyleSheet("font-weight: bold; color: white;")
        layout.addWidget(body_label_title)
        
        # Color picker for body
        self.body_color_picker = ColorPickerWidget(initial_color=self.body_color, config=self.config)
        layout.addWidget(self.body_color_picker)
        
        # Grid layout for Body Width control
        grid_body = QGridLayout()
        grid_body.setSpacing(18)
        grid_body.setContentsMargins(0, 0, 0, 0)
        grid_body.setColumnStretch(0, 0)
        grid_body.setColumnStretch(1, 1)
        
        width_label = QLabel("Width:")
        width_label.setStyleSheet("font-weight: bold; color: white;")
        width_label.setFixedWidth(70)
        grid_body.addWidget(width_label, 0, 0, Qt.AlignLeft)
        
        width_control_layout = QHBoxLayout()
        width_control_layout.setContentsMargins(0, 0, 0, 0)
        width_control_layout.setSpacing(8)
        
        self.body_width_slider = QSlider(Qt.Horizontal)
        self.body_width_slider.setMinimum(1)
        self.body_width_slider.setMaximum(9)
        self.body_width_slider.setValue(self.body_width)
        self.body_width_slider.setTickPosition(QSlider.NoTicks)
        from src.gui.widgets.slider_setting_widget import SLIDER_STYLESHEET
        self.body_width_slider.setStyleSheet(SLIDER_STYLESHEET)
        self.body_width_slider.setMinimumHeight(30)
        self.body_width_slider.valueChanged.connect(self._on_body_width_slider_changed)
        width_control_layout.addWidget(self.body_width_slider)
        
        self.body_width_spinbox = QSpinBox()
        self.body_width_spinbox.setMinimum(1)
        self.body_width_spinbox.setMaximum(9)
        self.body_width_spinbox.setValue(self.body_width)
        self.body_width_spinbox.setSuffix(" px")
        self.body_width_spinbox.setMaximumWidth(50)
        self.body_width_spinbox.valueChanged.connect(self._on_body_width_spinbox_changed)
        width_control_layout.addWidget(self.body_width_spinbox)
        
        width_control_widget = QWidget()
        width_control_widget.setLayout(width_control_layout)
        grid_body.addWidget(width_control_widget, 0, 1)
        
        layout.addLayout(grid_body)
        
        # ====== OUTLINE (Border around track line) ======
        outline_label_title = QLabel("Track Outline")
        outline_label_title.setStyleSheet("font-weight: bold; color: white; margin-top: 15px;")
        layout.addWidget(outline_label_title)
        
        # Color picker for outline
        self.outline_color_picker = ColorPickerWidget(initial_color=self.outline_color, config=self.config)
        layout.addWidget(self.outline_color_picker)
        
        # Grid layout for Outline Width control
        grid_outline = QGridLayout()
        grid_outline.setSpacing(18)
        grid_outline.setContentsMargins(0, 0, 0, 0)
        grid_outline.setColumnStretch(0, 0)
        grid_outline.setColumnStretch(1, 1)
        
        outline_width_label = QLabel("Width:")
        outline_width_label.setStyleSheet("font-weight: bold; color: white;")
        outline_width_label.setFixedWidth(70)
        grid_outline.addWidget(outline_width_label, 0, 0, Qt.AlignLeft)
        
        outline_width_control_layout = QHBoxLayout()
        outline_width_control_layout.setContentsMargins(0, 0, 0, 0)
        outline_width_control_layout.setSpacing(8)
        
        self.outline_width_slider = QSlider(Qt.Horizontal)
        self.outline_width_slider.setMinimum(0)
        self.outline_width_slider.setMaximum(5)
        self.outline_width_slider.setValue(self.outline_width)
        self.outline_width_slider.setTickPosition(QSlider.NoTicks)
        self.outline_width_slider.setStyleSheet(SLIDER_STYLESHEET)
        self.outline_width_slider.setMinimumHeight(30)
        self.outline_width_slider.valueChanged.connect(self._on_outline_width_slider_changed)
        outline_width_control_layout.addWidget(self.outline_width_slider)
        
        self.outline_width_spinbox = QSpinBox()
        self.outline_width_spinbox.setMinimum(0)
        self.outline_width_spinbox.setMaximum(5)
        self.outline_width_spinbox.setValue(self.outline_width)
        self.outline_width_spinbox.setSuffix(" px")
        self.outline_width_spinbox.setMaximumWidth(50)
        self.outline_width_spinbox.valueChanged.connect(self._on_outline_width_spinbox_changed)
        outline_width_control_layout.addWidget(self.outline_width_spinbox)
        
        outline_width_control_widget = QWidget()
        outline_width_control_widget.setLayout(outline_width_control_layout)
        grid_outline.addWidget(outline_width_control_widget, 0, 1)
        
        layout.addLayout(grid_outline)
        
        # Add stretch to push controls to top
        layout.addStretch()
    
    def _connect_signals(self):
        """Connect widget signals."""
        
        self.body_color_picker.color_changed.connect(self._on_body_color_changed)
        self.outline_color_picker.color_changed.connect(self._on_outline_color_changed)
        self.body_width_slider.valueChanged.connect(self._on_body_width_slider_changed)
        self.body_width_spinbox.valueChanged.connect(self._on_body_width_spinbox_changed)
        self.outline_width_slider.valueChanged.connect(self._on_outline_width_slider_changed)
        self.outline_width_spinbox.valueChanged.connect(self._on_outline_width_spinbox_changed)
    
    def _on_body_color_changed(self, hex_color: str):
        """Handle body color change."""
        self.body_color = hex_color
        logger.debug(f"Track body color changed to: {hex_color}")
        self.settings_changed.emit()
    
    def _on_outline_color_changed(self, hex_color: str):
        """Handle outline color change."""
        self.outline_color = hex_color
        logger.debug(f"Track outline color changed to: {hex_color}")
        self.settings_changed.emit()
    
    def _on_body_width_slider_changed(self, value: int):
        """Handle body width slider change."""
        self._updating = True
        self.body_width = value
        self.body_width_spinbox.setValue(value)
        self._updating = False
        logger.debug(f"Track body width changed to: {value}px")
        self.settings_changed.emit()
    
    def _on_body_width_spinbox_changed(self, value: int):
        """Handle body width spinbox change."""
        if hasattr(self, '_updating') and self._updating:
            return
        self._updating = True
        self.body_width = value
        self.body_width_slider.setValue(value)
        self._updating = False
        logger.debug(f"Track body width changed to: {value}px")
        self.settings_changed.emit()
    
    def _on_outline_width_slider_changed(self, value: int):
        """Handle outline width slider change."""
        self._updating = True
        self.outline_width = value
        self.outline_width_spinbox.setValue(value)
        self._updating = False
        logger.debug(f"Track outline width changed to: {value}px")
        self.settings_changed.emit()
    
    def _on_outline_width_spinbox_changed(self, value: int):
        """Handle outline width spinbox change."""
        if hasattr(self, '_updating') and self._updating:
            return
        self._updating = True
        self.outline_width = value
        self.outline_width_slider.setValue(value)
        self._updating = False
        logger.debug(f"Track outline width changed to: {value}px")
        self.settings_changed.emit()
    
    def get_body_color(self) -> str:
        """Get current track body color."""
        return self.body_color_picker.get_color()
    
    def set_body_color(self, hex_color: str):
        """Set track body color."""
        self.body_color_picker.set_color(hex_color)
    
    def get_body_width(self) -> int:
        """Get current track body width."""
        return self.body_width_slider.value()
    
    def set_body_width(self, width: int):
        """Set track body width."""
        self._updating = True
        self.body_width_slider.setValue(width)
        self.body_width_spinbox.setValue(width)
        self._updating = False
    
    def get_outline_color(self) -> str:
        """Get current track outline color."""
        return self.outline_color_picker.get_color()
    
    def set_outline_color(self, hex_color: str):
        """Set track outline color."""
        self.outline_color_picker.set_color(hex_color)
    
    def get_outline_width(self) -> int:
        """Get current track outline width."""
        return self.outline_width_slider.value()
    
    def set_outline_width(self, width: int):
        """Set track outline width."""
        self._updating = True
        self.outline_width_slider.setValue(width)
        self.outline_width_spinbox.setValue(width)
        self._updating = False
    
    def apply_to_config(self):
        """Apply current settings to configuration."""
        
        self.config.config_data['Appearance']['MapDisplay']['TrackPath']['body']['color'] = self.get_body_color()
        self.config.config_data['Appearance']['MapDisplay']['TrackPath']['body']['width'] = self.get_body_width()
        self.config.config_data['Appearance']['MapDisplay']['TrackPath']['outline']['color'] = self.get_outline_color()
        self.config.config_data['Appearance']['MapDisplay']['TrackPath']['outline']['width'] = self.get_outline_width()
        
        logger.info(f"Track path settings applied: body_color={self.get_body_color()}, body_width={self.get_body_width()}, outline_color={self.get_outline_color()}, outline_width={self.get_outline_width()}")
    
    def save_to_file(self) -> bool:
        """Save settings to file."""
        
        self.apply_to_config()
        return self.config.save_to_file()
