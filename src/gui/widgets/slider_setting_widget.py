"""
Slider Setting Widget for CourseStudio Settings.

Reusable horizontal slider with:
- Title/label
- Dynamic width slider (Apple-style)
- Numeric value display
- Optional value suffix (e.g., "px", "ms")
"""

import logging
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider, QSpinBox
from PyQt5.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)

# Apple-style slider stylesheet (matching seeboard pattern)
SLIDER_STYLESHEET = """
QSlider {
    border: none;
    outline: none;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #e0e0e0;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #007AFF;
    border-radius: 3px;
}

QSlider::add-page:horizontal {
    background: #e0e0e0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    width: 18px;
    height: 18px;
    margin: -6px 0;
    background: #007AFF;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #0051D5;
}

QSlider::handle:horizontal:pressed {
    background: #003DA3;
}
"""


class SliderSettingWidget(QWidget):
    """
    Reusable horizontal slider for numeric settings.
    
    Features:
    - Title label (left)
    - Dynamic width slider (center) - Apple-style
    - Spinbox for direct input (right)
    - Value suffix display (e.g., "px", "ms")
    - Responsive layout (no hardcoded sizes)
    - Smooth, professional appearance
    """
    
    value_changed = pyqtSignal(int)  # Emits new value
    
    def __init__(self, 
                 title: str,
                 min_val: int,
                 max_val: int,
                 current_val: int = None,
                 suffix: str = "",
                 parent=None):
        """
        Initialize slider setting widget.
        
        Args:
            title: Label text (e.g., "Width", "Zoom")
            min_val: Minimum value (e.g., 1)
            max_val: Maximum value (e.g., 9)
            current_val: Initial value (default: min_val)
            suffix: Value suffix (e.g., "px", "ms")
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.title = title
        self.min_val = min_val
        self.max_val = max_val
        self.suffix = suffix
        self.current_val = current_val if current_val is not None else min_val
        self._updating = False  # Prevent recursive updates
        
        self._init_ui()
        
        logger.info(f"SliderSettingWidget initialized: {title} ({min_val}-{max_val})")
    
    def _init_ui(self):
        """Initialize the user interface."""
        
        layout = QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # ====================================================================
        # Title Label (Left)
        # ====================================================================
        
        title_label = QLabel(f"{self.title}:")
        title_label.setStyleSheet("font-weight: bold; min-width: 60px;")
        layout.addWidget(title_label)
        
        # ====================================================================
        # Horizontal Slider (Center - Dynamic Width, Apple-style)
        # ====================================================================
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(self.min_val)
        self.slider.setMaximum(self.max_val)
        self.slider.setValue(self.current_val)
        self.slider.setTickPosition(QSlider.NoTicks)
        self.slider.setStyleSheet(SLIDER_STYLESHEET)  # Apply Apple-style
        self.slider.setMinimumHeight(30)  # Ensure handle doesn't clip (18px + 6px margins)
        self.slider.valueChanged.connect(self._on_slider_changed)
        
        # Slider should take up available space
        layout.addWidget(self.slider, 1)  # Stretch factor 1
        
        # ====================================================================
        # Spinbox for Direct Input (Right)
        # ====================================================================
        
        self.spinbox = QSpinBox()
        self.spinbox.setMinimum(self.min_val)
        self.spinbox.setMaximum(self.max_val)
        self.spinbox.setValue(self.current_val)
        self.spinbox.setSuffix(f" {self.suffix}" if self.suffix else "")
        self.spinbox.setMaximumWidth(80)
        self.spinbox.valueChanged.connect(self._on_spinbox_changed)
        
        layout.addWidget(self.spinbox)
    
    def _on_slider_changed(self, value: int):
        """Handle slider value change."""
        if self._updating:
            return
        
        self._updating = True
        self.current_val = value
        self.spinbox.setValue(value)
        self._updating = False
        
        self.value_changed.emit(value)
    
    def _on_spinbox_changed(self, value: int):
        """Handle spinbox value change."""
        if self._updating:
            return
        
        self._updating = True
        self.current_val = value
        self.slider.setValue(value)
        self._updating = False
        
        self.value_changed.emit(value)
    
    def get_value(self) -> int:
        """Get current value."""
        return self.current_val
    
    def set_value(self, value: int):
        """Set value."""
        if self.min_val <= value <= self.max_val:
            self._updating = True
            self.current_val = value
            self.slider.setValue(value)
            self.spinbox.setValue(value)
            self._updating = False
    
    def set_range(self, min_val: int, max_val: int):
        """Update slider range."""
        self.min_val = min_val
        self.max_val = max_val
        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.spinbox.setMinimum(min_val)
        self.spinbox.setMaximum(max_val)
