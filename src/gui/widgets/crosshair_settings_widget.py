"""
Crosshair appearance settings widget.

Allows user to customize the crosshair cursor appearance with:
- On/Off toggle
- Body color and size
- Outline color and width
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal, Qt

from config.app_config_yaml import AppConfig
from src.gui.widgets.color_picker_widget import ColorPickerWidget
from src.gui.widgets.slider_setting_widget import SliderSettingWidget
from src.gui.widgets.toggle_switch_widget import ToggleSwitchWidget

logger = logging.getLogger(__name__)


class CrosshairSettingsWidget(QWidget):
    """
    Settings widget for crosshair appearance.
    
    Provides controls for:
    - On/Off toggle
    - Body color and size
    - Outline color and width
    """
    
    settings_changed = pyqtSignal()
    
    def __init__(self, config: AppConfig):
        """
        Initialize crosshair settings widget.
        
        Args:
            config: AppConfig instance
        """
        super().__init__()
        
        self.config = config
        
        # Load current values from config
        self.enabled = self.config.get_bool(
            'appearance.map_display.crosshair.enabled', 
            True  # Default: ON
        )
        self.body_color = self.config.get_str(
            'appearance.map_display.crosshair.body.color', 
            'FF0000'  # Red
        )
        self.body_size = self.config.get_int(
            'appearance.map_display.crosshair.body.size', 
            4
        )
        self.outline_color = self.config.get_str(
            'appearance.map_display.crosshair.outline.color', 
            'FFFFFF'  # White
        )
        self.outline_width = self.config.get_int(
            'appearance.map_display.crosshair.outline.width', 
            1
        )
        
        self._init_ui()
        self._connect_signals()
        
        logger.info("CrosshairSettingsWidget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ====================================================================
        # Enable/Disable Toggle (top)
        # ====================================================================
        
        enable_layout = QHBoxLayout()
        enable_layout.setContentsMargins(0, 0, 0, 0)
        enable_layout.setSpacing(15)
        
        enable_label = QLabel("Show Crosshair:")
        enable_label.setStyleSheet("font-weight: bold; color: white;")
        enable_label.setFixedWidth(120)
        enable_layout.addWidget(enable_label)
        
        self.enable_toggle = ToggleSwitchWidget(title="", initial_state=self.enabled)
        self.enable_toggle.toggled.connect(self._on_enabled_changed)
        enable_layout.addWidget(self.enable_toggle, 0, Qt.AlignLeft)
        enable_layout.addStretch()
        
        layout.addLayout(enable_layout)
        
        # Add separator
        layout.addSpacing(10)
        
        # ====================================================================
        # Body Section
        # ====================================================================
        
        body_label = QLabel("Body")
        body_label.setStyleSheet("font-weight: bold; color: white; text-decoration: underline;")
        layout.addWidget(body_label)
        
        # Body color picker
        self.body_color_picker = ColorPickerWidget(
            initial_color=self.body_color,
            config=self.config
        )
        self.body_color_picker.color_changed.connect(self._on_settings_changed)
        layout.addWidget(self.body_color_picker)
        
        # Body size slider
        body_size_layout = QHBoxLayout()
        body_size_layout.setContentsMargins(0, 0, 0, 0)
        body_size_layout.setSpacing(15)
        body_size_label = QLabel("Size:")
        body_size_label.setStyleSheet("font-weight: bold; color: white;")
        body_size_label.setFixedWidth(70)
        body_size_layout.addWidget(body_size_label)
        
        self.body_size_slider = SliderSettingWidget(
            min_val=5, 
            max_val=30, 
            current_val=self.body_size, 
            suffix="px", 
            include_label=False
        )
        self.body_size_slider.value_changed.connect(self._on_settings_changed)
        body_size_layout.addWidget(self.body_size_slider, 1)
        layout.addLayout(body_size_layout)
        
        # ====================================================================
        # Outline Section
        # ====================================================================
        
        outline_label = QLabel("Outline")
        outline_label.setStyleSheet("font-weight: bold; color: white; text-decoration: underline;")
        layout.addWidget(outline_label)
        
        # Outline color picker
        self.outline_color_picker = ColorPickerWidget(
            initial_color=self.outline_color,
            config=self.config
        )
        self.outline_color_picker.color_changed.connect(self._on_settings_changed)
        layout.addWidget(self.outline_color_picker)
        
        # Outline width slider
        outline_width_layout = QHBoxLayout()
        outline_width_layout.setContentsMargins(0, 0, 0, 0)
        outline_width_layout.setSpacing(15)
        outline_width_label = QLabel("Width:")
        outline_width_label.setStyleSheet("font-weight: bold; color: white;")
        outline_width_label.setFixedWidth(70)
        outline_width_layout.addWidget(outline_width_label)
        
        self.outline_width_slider = SliderSettingWidget(
            min_val=0, 
            max_val=5, 
            current_val=self.outline_width, 
            suffix="px", 
            include_label=False
        )
        self.outline_width_slider.value_changed.connect(self._on_settings_changed)
        outline_width_layout.addWidget(self.outline_width_slider, 1)
        layout.addLayout(outline_width_layout)
        
        # Add stretch
        layout.addStretch()
    
    def _connect_signals(self):
        """Connect signals for settings changes."""
        pass
    
    def _on_enabled_changed(self, state: bool):
        """Handle enabled/disabled toggle."""
        self.enabled = state
        logger.debug(f"Crosshair enabled: {state}")
        self._on_settings_changed()
    
    def _on_settings_changed(self):
        """Handle settings change."""
        self.settings_changed.emit()
    
    def apply_to_config(self):
        """Apply current settings to config."""
        body_color = self.body_color_picker.get_color()
        body_size = self.body_size_slider.get_value()
        outline_color = self.outline_color_picker.get_color()
        outline_width = self.outline_width_slider.get_value()
        
        self.config.set('appearance.map_display.crosshair.enabled', self.enabled)
        self.config.set('appearance.map_display.crosshair.body.color', body_color)
        self.config.set('appearance.map_display.crosshair.body.size', body_size)
        self.config.set('appearance.map_display.crosshair.outline.color', outline_color)
        self.config.set('appearance.map_display.crosshair.outline.width', outline_width)
        
        logger.info(f"Crosshair settings applied: enabled={self.enabled}, body_color={body_color}, body_size={body_size}, "
                   f"outline_color={outline_color}, outline_width={outline_width}")
