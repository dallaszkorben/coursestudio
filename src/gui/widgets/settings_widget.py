"""
Settings/Configuration Widget for CourseStudio.

Provides a tabbed interface for configuring application settings:
- Map appearance (colors, sizes, line widths)
- Coordinate formats
- Performance settings
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)


class SettingsWidget(QWidget):
    """
    Settings configuration widget.
    
    Allows users to configure:
    - Map rendering settings (track colors, point sizes, etc.)
    - Coordinate format preferences
    - Performance options
    
    This widget is initially empty and will be populated step by step.
    """
    
    def __init__(self):
        """Initialize the settings widget."""
        super().__init__()
        
        self._init_ui()
        
        logger.info("SettingsWidget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Placeholder label
        placeholder = QLabel("Settings Configuration")
        placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder)
        
        # Add stretch to push content to top
        layout.addStretch()
