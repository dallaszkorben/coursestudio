"""
Settings Tab Handler for CourseStudio.

Handles the Settings tab which contains appearance and configuration options.

Classes:
    - SettingsTabHandler: Manages the Settings tab UI
"""

import logging

from src.features.settings.ui.widgets.settings_widget import SettingsWidget

logger = logging.getLogger(__name__)


class SettingsTabHandler:
    """
    Handles the Settings tab UI layout.
    
    Manages access to the SettingsWidget which provides:
    - Track path appearance settings (color, width, outline)
    - Turning points (trackpoints) settings
    - General point, single-selected, and multi-selected point colors/sizes
    """
    
    def __init__(self):
        """Initialize Settings tab handler."""
        self.widget = None
    
    def create_tab(self):
        """
        Create and return the Settings tab widget.
        
        Returns:
            SettingsWidget: The Settings tab widget
        """
        self.widget = SettingsWidget()
        
        logger.info("Settings tab created")
        
        return self.widget
    
    def get_settings_widget(self):
        """
        Get the underlying SettingsWidget.
        
        Returns:
            SettingsWidget: The settings widget instance
        """
        return self.widget
