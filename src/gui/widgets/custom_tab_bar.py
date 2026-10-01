"""
Custom QTabBar that sizes tabs to their content width WITHOUT CLIPPING.

The root cause of text clipping: Qt's default drawText uses TextDontClip=False,
which clips text to the tab rect. We need to override paintEvent to use TextDontClip flag.
"""

from PyQt5.QtWidgets import QTabBar, QStylePainter
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QStyle, QStyleOptionTab


class ContentAwareTabBar(QTabBar):
    """QTabBar that automatically sizes each tab to fit its text content WITHOUT clipping."""
    
    def __init__(self):
        super().__init__()
        # CRITICAL: Set icon size to 0 to prevent icon space allocation
        self.setIconSize(QSize(0, 0))
    
    def paintEvent(self, event):
        """Override paint to use TextDontClip so text is never clipped."""
        painter = QStylePainter(self)
        option = QStyleOptionTab()
        
        for index in range(self.count()):
            self.initStyleOption(option, index)
            # Draw tab shape and background
            painter.drawControl(QStyle.CE_TabBarTabShape, option)
            # Draw tab text WITHOUT clipping - this is the key!
            painter.drawText(
                self.tabRect(index),
                Qt.AlignCenter | Qt.TextDontClip,  # CRITICAL: TextDontClip flag!
                self.tabText(index)
            )
    
    def tabSizeHint(self, index):
        """
        Calculate the size of a tab based on its text content.
        
        Returns the minimum size needed to display the tab text without truncation.
        
        Args:
            index: Tab index
            
        Returns:
            QSize with width calculated from text, height from style
        """
        # Get the default size (which includes style padding and borders)
        default_size = super().tabSizeHint(index)
        
        # Get the tab text
        tab_text = self.tabText(index)
        
        # Calculate width needed for the text using bounding rect
        font_metrics = QFontMetrics(self.font())
        # Use boundingRect for better accuracy
        text_rect = font_metrics.boundingRect(tab_text)
        text_width = text_rect.width()
        
        # Minimum overhead from Qt (padding + borders + margins)
        # Empirically determined: roughly 20-25 pixels minimum
        min_overhead = 25
        
        # Calculate final width: text width + overhead
        calculated_width = text_width + min_overhead
        
        # Use the greater of: calculated width or Qt's default
        final_width = max(calculated_width, default_size.width())
        
        # Height comes from default (respects stylesheet)
        height = default_size.height()
        
        return QSize(final_width, height)
