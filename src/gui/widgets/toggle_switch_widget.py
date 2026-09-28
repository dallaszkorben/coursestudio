"""
Apple-style Toggle Switch Widget for CourseStudio Settings.

Provides a smooth toggle switch with animation, similar to macOS/iOS style.
"""

import logging
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen

logger = logging.getLogger(__name__)


class ToggleSwitchWidget(QWidget):
    """
    Apple-style toggle switch.
    
    Features:
    - Smooth animation between on/off states
    - Large touch-friendly size
    - Signal emits when toggled
    - Optional label on left
    """
    
    toggled = pyqtSignal(bool)  # Emits True/False state
    
    def __init__(self, title: str = "", initial_state: bool = True, parent=None):
        """
        Initialize toggle switch.
        
        Args:
            title: Optional label text (left side)
            initial_state: Initial on/off state (True = on)
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.title = title
        self.is_on = initial_state
        self._animation = None
        
        # Colors
        self.COLOR_ON = QColor(52, 144, 220)      # Blue (on)
        self.COLOR_OFF = QColor(200, 200, 200)    # Gray (off)
        self.COLOR_CIRCLE = QColor(255, 255, 255) # White circle
        
        # Dimensions
        self.SWITCH_WIDTH = 50
        self.SWITCH_HEIGHT = 28
        self.CIRCLE_RADIUS = 12
        self.MARGIN = 2
        
        # Circle position (0 = off, 1 = on)
        self.circle_position = 1.0 if initial_state else 0.0
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        
        layout = QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Optional title label - FIXED WIDTH for alignment with other controls
        if self.title:
            title_label = QLabel(f"{self.title}:")
            title_label.setStyleSheet("font-weight: bold; min-width: 60px;")
            title_label.setFixedWidth(70)  # Same width as "Size:" and "Width:" labels
            layout.addWidget(title_label)
        
        # Switch widget will be drawn in paintEvent
        layout.addStretch()
        
        # Set minimum size for the switch
        self.setMinimumHeight(self.SWITCH_HEIGHT + 4)
        self.setMaximumHeight(self.SWITCH_HEIGHT + 4)
    
    def paintEvent(self, event):
        """Paint the toggle switch."""
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Position for switch - starts after the label area (70px) + spacing (10px)
        x = 70 + 10
        y = (self.height() - self.SWITCH_HEIGHT) // 2
        
        # Draw background (rounded rectangle)
        bg_color = self.COLOR_ON if self.is_on else self.COLOR_OFF
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(x, y, self.SWITCH_WIDTH, self.SWITCH_HEIGHT, 
                               self.SWITCH_HEIGHT // 2, self.SWITCH_HEIGHT // 2)
        
        # Draw circle (white knob)
        circle_x = x + self.MARGIN + (self.circle_position * (self.SWITCH_WIDTH - 2 * self.MARGIN - 2 * self.CIRCLE_RADIUS))
        circle_y = y + (self.SWITCH_HEIGHT - 2 * self.CIRCLE_RADIUS) // 2
        
        painter.setBrush(QBrush(self.COLOR_CIRCLE))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(circle_x), int(circle_y), 2 * self.CIRCLE_RADIUS, 2 * self.CIRCLE_RADIUS)
    
    def mousePressEvent(self, event):
        """Handle mouse click to toggle state."""
        
        if event.button() == Qt.LeftButton:
            self.toggle()
    
    def toggle(self):
        """Toggle the switch state with animation."""
        
        self.is_on = not self.is_on
        
        # Animate circle position
        start_pos = self.circle_position
        end_pos = 1.0 if self.is_on else 0.0
        
        # Use direct property animation
        self._animate_to(end_pos)
        
        # Emit signal
        self.toggled.emit(self.is_on)
    
    def _animate_to(self, end_position: float):
        """Animate circle to target position."""
        
        steps = 10
        step_size = (end_position - self.circle_position) / steps
        
        for i in range(steps + 1):
            self.circle_position = self.circle_position + step_size
            self.update()
            
            # Process events to show animation
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
    
    def set_state(self, state: bool):
        """Set toggle state without animation."""
        
        self.is_on = state
        self.circle_position = 1.0 if state else 0.0
        self.update()
    
    def get_state(self) -> bool:
        """Get current toggle state."""
        return self.is_on
