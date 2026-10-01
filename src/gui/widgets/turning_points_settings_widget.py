"""
Trackpoints Settings Widget for CourseStudio Settings.

Combines color pickers, size sliders, and toggle switch for trackpoints appearance.
"""

import logging
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QWidget, QSlider, QSpinBox
from PyQt5.QtCore import pyqtSignal, Qt

from config.app_config_yaml import AppConfig
from src.gui.widgets.color_picker_widget import ColorPickerWidget
from src.gui.widgets.slider_setting_widget import SliderSettingWidget
from src.gui.widgets.toggle_switch_widget import ToggleSwitchWidget

logger = logging.getLogger(__name__)


class TurningPointsSettingsWidget(QGroupBox):
    """
    Trackpoints appearance settings section.
    
    Provides controls for:
    - Show/Hide toggle (Apple-style switch)
    - General Points: body color/size + outline color/size
    - Selected Points: body color/size + outline color/size
    - Double Selected Points: body color/size + outline color/size
    """
    
    settings_changed = pyqtSignal()  # Emitted when settings change
    show_toggled = pyqtSignal(bool)  # Emitted when show/hide toggled
    settings_applied = pyqtSignal()  # Emitted when settings are applied to config
    
    def __init__(self, config: AppConfig = None):
        """
        Initialize trackpoints settings widget.
        
        Args:
            config: AppConfig instance (optional, for loading defaults)
        """
        super().__init__("Trackpoints")
        
        self.config = config or AppConfig()
        
        # Load current values from config
        self.show = self.config.get_bool('Appearance.MapDisplay.Trackpoints.show', True)
        
        # General Points
        self.general_body_color = self.config.get_str('Appearance.MapDisplay.Trackpoints.GeneralPoints.body.color', 'FFFF00')
        self.general_body_size = self.config.get_int('Appearance.MapDisplay.Trackpoints.GeneralPoints.body.size', 4)
        self.general_outline_color = self.config.get_str('Appearance.MapDisplay.Trackpoints.GeneralPoints.outline.color', 'FFFFFF')
        self.general_outline_size = self.config.get_int('Appearance.MapDisplay.Trackpoints.GeneralPoints.outline.size', 1)
        
        # Selected Points
        self.selected_body_color = self.config.get_str('Appearance.MapDisplay.Trackpoints.SelectedPoints.body.color', '0000FF')
        self.selected_body_size = self.config.get_int('Appearance.MapDisplay.Trackpoints.SelectedPoints.body.size', 7)
        self.selected_outline_color = self.config.get_str('Appearance.MapDisplay.Trackpoints.SelectedPoints.outline.color', 'FFFFFF')
        self.selected_outline_size = self.config.get_int('Appearance.MapDisplay.Trackpoints.SelectedPoints.outline.size', 2)
        
        # Double Selected Points
        self.double_selected_body_color = self.config.get_str('Appearance.MapDisplay.Trackpoints.DoubleSelectedPoints.body.color', 'FFA500')
        self.double_selected_body_size = self.config.get_int('Appearance.MapDisplay.Trackpoints.DoubleSelectedPoints.body.size', 8)
        self.double_selected_outline_color = self.config.get_str('Appearance.MapDisplay.Trackpoints.DoubleSelectedPoints.outline.color', 'FFFFFF')
        self.double_selected_outline_size = self.config.get_int('Appearance.MapDisplay.Trackpoints.DoubleSelectedPoints.outline.size', 2)
        
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
        
        logger.info(f"TrackpointsSettingsWidget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ====================================================================
        # Show/Hide Toggle
        # ====================================================================
        
        toggle_layout = QHBoxLayout()
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(8)
        
        # Label (same fixed width as other labels for alignment)
        toggle_label = QLabel("Show:")
        toggle_label.setStyleSheet("font-weight: bold; color: white;")
        toggle_label.setFixedWidth(70)
        toggle_layout.addWidget(toggle_label, 0, Qt.AlignLeft)
        
        # Toggle switch WITHOUT title
        self.show_toggle = ToggleSwitchWidget(title="", initial_state=self.show)
        toggle_layout.addWidget(self.show_toggle, 0, Qt.AlignLeft)
        
        # Add stretch to push everything left
        toggle_layout.addStretch()
        layout.addLayout(toggle_layout)
        
        # ====================================================================
        # General Points Section
        # ====================================================================
        
        general_section = self._create_subsection("General Points")
        general_layout = QVBoxLayout()
        general_layout.setSpacing(10)
        general_layout.setContentsMargins(8, 8, 8, 8)
        
        # Body subsection
        body_label = QLabel("Body")
        body_label.setStyleSheet("font-weight: bold; color: white; text-decoration: underline;")
        general_layout.addWidget(body_label)
        
        self.general_body_color_picker = ColorPickerWidget(
            initial_color=self.general_body_color,
            config=self.config
        )
        general_layout.addWidget(self.general_body_color_picker)
        
        general_body_size_layout = QHBoxLayout()
        general_body_size_layout.setContentsMargins(0, 0, 0, 0)
        general_body_size_layout.setSpacing(18)
        general_body_size_label = QLabel("Size:")
        general_body_size_label.setStyleSheet("font-weight: bold; color: white;")
        general_body_size_label.setFixedWidth(70)
        general_body_size_layout.addWidget(general_body_size_label)
        self.general_body_size_slider = SliderSettingWidget(min_val=1, max_val=10, current_val=self.general_body_size, suffix="px", include_label=False)
        general_body_size_layout.addWidget(self.general_body_size_slider, 1)
        general_layout.addLayout(general_body_size_layout)
        
        # Outline subsection
        outline_label = QLabel("Outline")
        outline_label.setStyleSheet("font-weight: bold; color: white; text-decoration: underline; margin-top: 10px;")
        general_layout.addWidget(outline_label)
        
        self.general_outline_color_picker = ColorPickerWidget(
            initial_color=self.general_outline_color,
            config=self.config
        )
        general_layout.addWidget(self.general_outline_color_picker)
        
        general_outline_size_layout = QHBoxLayout()
        general_outline_size_layout.setContentsMargins(0, 0, 0, 0)
        general_outline_size_layout.setSpacing(18)
        general_outline_size_label = QLabel("Size:")
        general_outline_size_label.setStyleSheet("font-weight: bold; color: white;")
        general_outline_size_label.setFixedWidth(70)
        general_outline_size_layout.addWidget(general_outline_size_label)
        self.general_outline_size_slider = SliderSettingWidget(min_val=0, max_val=5, current_val=self.general_outline_size, suffix="px", include_label=False)
        general_outline_size_layout.addWidget(self.general_outline_size_slider, 1)
        general_layout.addLayout(general_outline_size_layout)
        
        general_section.setLayout(general_layout)
        layout.addWidget(general_section)
        
        # ====================================================================
        # Selected Points Section
        # ====================================================================
        
        selected_section = self._create_subsection("Selected Points")
        selected_layout = QVBoxLayout()
        selected_layout.setSpacing(10)
        selected_layout.setContentsMargins(8, 8, 8, 8)
        
        # Body subsection
        selected_body_label = QLabel("Body")
        selected_body_label.setStyleSheet("font-weight: bold; color: white; text-decoration: underline;")
        selected_layout.addWidget(selected_body_label)
        
        self.selected_body_color_picker = ColorPickerWidget(
            initial_color=self.selected_body_color,
            config=self.config
        )
        selected_layout.addWidget(self.selected_body_color_picker)
        
        selected_body_size_layout = QHBoxLayout()
        selected_body_size_layout.setContentsMargins(0, 0, 0, 0)
        selected_body_size_layout.setSpacing(18)
        selected_body_size_label = QLabel("Size:")
        selected_body_size_label.setStyleSheet("font-weight: bold; color: white;")
        selected_body_size_label.setFixedWidth(70)
        selected_body_size_layout.addWidget(selected_body_size_label)
        self.selected_body_size_slider = SliderSettingWidget(min_val=1, max_val=15, current_val=self.selected_body_size, suffix="px", include_label=False)
        selected_body_size_layout.addWidget(self.selected_body_size_slider, 1)
        selected_layout.addLayout(selected_body_size_layout)
        
        # Outline subsection
        selected_outline_label = QLabel("Outline")
        selected_outline_label.setStyleSheet("font-weight: bold; color: white; text-decoration: underline; margin-top: 10px;")
        selected_layout.addWidget(selected_outline_label)
        
        self.selected_outline_color_picker = ColorPickerWidget(
            initial_color=self.selected_outline_color,
            config=self.config
        )
        selected_layout.addWidget(self.selected_outline_color_picker)
        
        selected_outline_size_layout = QHBoxLayout()
        selected_outline_size_layout.setContentsMargins(0, 0, 0, 0)
        selected_outline_size_layout.setSpacing(18)
        selected_outline_size_label = QLabel("Size:")
        selected_outline_size_label.setStyleSheet("font-weight: bold; color: white;")
        selected_outline_size_label.setFixedWidth(70)
        selected_outline_size_layout.addWidget(selected_outline_size_label)
        self.selected_outline_size_slider = SliderSettingWidget(min_val=0, max_val=5, current_val=self.selected_outline_size, suffix="px", include_label=False)
        selected_outline_size_layout.addWidget(self.selected_outline_size_slider, 1)
        selected_layout.addLayout(selected_outline_size_layout)
        
        selected_section.setLayout(selected_layout)
        layout.addWidget(selected_section)
        
        # ====================================================================
        # Double Selected Points Section
        # ====================================================================
        
        double_selected_section = self._create_subsection("Double Selected Points")
        double_selected_layout = QVBoxLayout()
        double_selected_layout.setSpacing(10)
        double_selected_layout.setContentsMargins(8, 8, 8, 8)
        
        # Body subsection
        double_selected_body_label = QLabel("Body")
        double_selected_body_label.setStyleSheet("font-weight: bold; color: white; text-decoration: underline;")
        double_selected_layout.addWidget(double_selected_body_label)
        
        self.double_selected_body_color_picker = ColorPickerWidget(
            initial_color=self.double_selected_body_color,
            config=self.config
        )
        double_selected_layout.addWidget(self.double_selected_body_color_picker)
        
        double_selected_body_size_layout = QHBoxLayout()
        double_selected_body_size_layout.setContentsMargins(0, 0, 0, 0)
        double_selected_body_size_layout.setSpacing(18)
        double_selected_body_size_label = QLabel("Size:")
        double_selected_body_size_label.setStyleSheet("font-weight: bold; color: white;")
        double_selected_body_size_label.setFixedWidth(70)
        double_selected_body_size_layout.addWidget(double_selected_body_size_label)
        self.double_selected_body_size_slider = SliderSettingWidget(min_val=1, max_val=15, current_val=self.double_selected_body_size, suffix="px", include_label=False)
        double_selected_body_size_layout.addWidget(self.double_selected_body_size_slider, 1)
        double_selected_layout.addLayout(double_selected_body_size_layout)
        
        # Outline subsection
        double_selected_outline_label = QLabel("Outline")
        double_selected_outline_label.setStyleSheet("font-weight: bold; color: white; text-decoration: underline; margin-top: 10px;")
        double_selected_layout.addWidget(double_selected_outline_label)
        
        self.double_selected_outline_color_picker = ColorPickerWidget(
            initial_color=self.double_selected_outline_color,
            config=self.config
        )
        double_selected_layout.addWidget(self.double_selected_outline_color_picker)
        
        double_selected_outline_size_layout = QHBoxLayout()
        double_selected_outline_size_layout.setContentsMargins(0, 0, 0, 0)
        double_selected_outline_size_layout.setSpacing(18)
        double_selected_outline_size_label = QLabel("Size:")
        double_selected_outline_size_label.setStyleSheet("font-weight: bold; color: white;")
        double_selected_outline_size_label.setFixedWidth(70)
        double_selected_outline_size_layout.addWidget(double_selected_outline_size_label)
        self.double_selected_outline_size_slider = SliderSettingWidget(min_val=0, max_val=5, current_val=self.double_selected_outline_size, suffix="px", include_label=False)
        double_selected_outline_size_layout.addWidget(self.double_selected_outline_size_slider, 1)
        double_selected_layout.addLayout(double_selected_outline_size_layout)
        
        double_selected_section.setLayout(double_selected_layout)
        layout.addWidget(double_selected_section)
        
        # Add stretch to push controls to top
        layout.addStretch()
    
    def _create_subsection(self, title: str) -> QGroupBox:
        """Create a styled subsection container with gray frame."""
        section = QGroupBox(title)
        section.setStyleSheet("""
            QGroupBox {
                border: 1px solid #999999;
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
        return section
    
    def _connect_signals(self):
        """Connect widget signals."""
        
        self.show_toggle.toggled.connect(self._on_show_toggled)
        
        # General Points
        self.general_body_color_picker.color_changed.connect(self.settings_changed.emit)
        self.general_body_size_slider.value_changed.connect(self.settings_changed.emit)
        self.general_outline_color_picker.color_changed.connect(self.settings_changed.emit)
        self.general_outline_size_slider.value_changed.connect(self.settings_changed.emit)
        
        # Selected Points
        self.selected_body_color_picker.color_changed.connect(self.settings_changed.emit)
        self.selected_body_size_slider.value_changed.connect(self.settings_changed.emit)
        self.selected_outline_color_picker.color_changed.connect(self.settings_changed.emit)
        self.selected_outline_size_slider.value_changed.connect(self.settings_changed.emit)
        
        # Double Selected Points
        self.double_selected_body_color_picker.color_changed.connect(self.settings_changed.emit)
        self.double_selected_body_size_slider.value_changed.connect(self.settings_changed.emit)
        self.double_selected_outline_color_picker.color_changed.connect(self.settings_changed.emit)
        self.double_selected_outline_size_slider.value_changed.connect(self.settings_changed.emit)
    
    def _on_show_toggled(self, state: bool):
        """Handle show/hide toggle."""
        self.show = state
        logger.debug(f"Trackpoints show toggled to: {state}")
        self.show_toggled.emit(state)
        self.settings_changed.emit()
    
    def apply_to_config(self):
        """Apply current settings to configuration."""
        
        self.config.config_data['Appearance']['MapDisplay']['Trackpoints']['show'] = self.get_show()
        
        # General Points
        self.config.config_data['Appearance']['MapDisplay']['Trackpoints']['GeneralPoints']['body']['color'] = self.general_body_color_picker.get_color()
        self.config.config_data['Appearance']['MapDisplay']['Trackpoints']['GeneralPoints']['body']['size'] = self.general_body_size_slider.get_value()
        self.config.config_data['Appearance']['MapDisplay']['Trackpoints']['GeneralPoints']['outline']['color'] = self.general_outline_color_picker.get_color()
        self.config.config_data['Appearance']['MapDisplay']['Trackpoints']['GeneralPoints']['outline']['size'] = self.general_outline_size_slider.get_value()
        
        # Selected Points
        self.config.config_data['Appearance']['MapDisplay']['Trackpoints']['SelectedPoints']['body']['color'] = self.selected_body_color_picker.get_color()
        self.config.config_data['Appearance']['MapDisplay']['Trackpoints']['SelectedPoints']['body']['size'] = self.selected_body_size_slider.get_value()
        self.config.config_data['Appearance']['MapDisplay']['Trackpoints']['SelectedPoints']['outline']['color'] = self.selected_outline_color_picker.get_color()
        self.config.config_data['Appearance']['MapDisplay']['Trackpoints']['SelectedPoints']['outline']['size'] = self.selected_outline_size_slider.get_value()
        
        # Double Selected Points
        self.config.config_data['Appearance']['MapDisplay']['Trackpoints']['DoubleSelectedPoints']['body']['color'] = self.double_selected_body_color_picker.get_color()
        self.config.config_data['Appearance']['MapDisplay']['Trackpoints']['DoubleSelectedPoints']['body']['size'] = self.double_selected_body_size_slider.get_value()
        self.config.config_data['Appearance']['MapDisplay']['Trackpoints']['DoubleSelectedPoints']['outline']['color'] = self.double_selected_outline_color_picker.get_color()
        self.config.config_data['Appearance']['MapDisplay']['Trackpoints']['DoubleSelectedPoints']['outline']['size'] = self.double_selected_outline_size_slider.get_value()
        
        logger.info("Trackpoints settings applied")
        
        # Emit signal to notify map widget to reload settings
        self.settings_applied.emit()
    
    def save_to_file(self) -> bool:
        """Save settings to file."""
        
        self.apply_to_config()
        return self.config.save_to_file()
    
    # Getters
    def get_show(self) -> bool:
        """Get show state."""
        return self.show_toggle.get_state()
