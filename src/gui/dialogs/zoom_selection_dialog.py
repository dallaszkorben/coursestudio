"""
Zoom Selection Dialog - Let user choose which zoom levels to generate.

Shows:
- Available zoom levels (from the file)
- Missing zoom levels (gaps in the range)
- Reasonable range for generation (min_zoom-1 to max_zoom+2)
- Quality warnings for risky selections

The dialog displays ALL reasonable zoom levels (existing or not),
allowing user to:
- Select which missing zooms to generate
- Optionally regenerate existing zooms
- See quality warnings for each selection

Usage:
    >>> dialog = ZoomSelectionDialog(generator, parent)
    >>> if dialog.exec_() == QDialog.Accepted:
    ...     selected_zooms = dialog.get_selected_zooms()
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QScrollArea,
    QPushButton, QWidget, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class ZoomSelectionDialog(QDialog):
    """
    Dialog for selecting which zoom levels to generate.
    
    Shows:
    - Available zoom levels from the mbtiles file
    - Missing zoom levels (gaps in the range)
    - Reasonable range for generation (min-1 to max+2)
    - Quality warnings
    
    Allows user to select which zooms to generate.
    """
    
    def __init__(self, generator, parent=None):
        """
        Initialize zoom selection dialog.
        
        Args:
            generator: ZoomGenerator instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.generator = generator
        self.selected_zooms = []
        self.checkboxes = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create and layout UI components."""
        self.setWindowTitle("Generate Missing Zoom Levels")
        self.setModal(True)
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        
        layout = QVBoxLayout()
        
        # Title
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title = QLabel("Select Zoom Level to Generate")
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Summary info from generator
        summary = QLabel()
        try:
            summary_text = self.generator.get_summary()
            summary.setText(summary_text)
            logger.info(f"Summary: {summary_text}")
        except Exception as e:
            summary.setText(f"Error: {e}")
            logger.error(f"Error getting summary: {e}")
        layout.addWidget(summary)
        
        # Zoom levels selection (scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Get available zooms and determine reasonable range
        try:
            available_zooms = sorted(self.generator.reader.get_available_zooms())
            logger.info(f"Available zooms: {available_zooms}")
            
            if not available_zooms:
                no_data_label = QLabel("No zoom levels found in file!")
                scroll_layout.addWidget(no_data_label)
            else:
                min_zoom = min(available_zooms)
                max_zoom = max(available_zooms)
                logger.info(f"Min: Z{min_zoom}, Max: Z{max_zoom}")
                
                # Calculate reasonable range for display
                # Show from (min-1) to (max+1) to allow upsampling one level beyond max
                # Example: If max existing is Z16, show Z17 for potential generation
                # Do NOT show Z18 (+2) as that's too far beyond existing data
                display_min = max(0, min_zoom - 1)
                display_max = min(28, max_zoom + 1)
                display_range = list(range(display_min, display_max + 1))
                
                logger.info(f"Display range: Z{display_min} to Z{display_max}")
                logger.info(f"Missing zooms: {self.generator.analyze_gaps()}")
                
                # Add title label
                title_label = QLabel("Zoom Levels (select to generate or regenerate):")
                title_label_font = QFont()
                title_label_font.setBold(True)
                title_label.setFont(title_label_font)
                scroll_layout.addWidget(title_label)
                
                # Get missing zooms
                missing_zooms = self.generator.analyze_gaps()
                
                # Create checkbox for each zoom in range
                for zoom in display_range:
                    checkbox_widget = QWidget()
                    checkbox_layout = QHBoxLayout()
                    checkbox_layout.setContentsMargins(0, 0, 0, 0)
                    
                    # ⚠️ CRITICAL FIX (2026-10-20):
                    # For EXISTING zooms, show their actual tile count, NOT generation source!
                    # Bug: Was calling create_generation_plan() for existing zooms and showing
                    # "from Z15" which is wrong - existing zooms are ORIGINAL, not generated.
                    # Solution: For existing zooms, get tile count from reader directly.
                    
                    # Show if existing or missing
                    if zoom in available_zooms:
                        status = "✓ existing"
                        checkbox_label = f"Z{zoom:2d}  {status}"
                        # Get tile count from reader (find zoom_level_info for this zoom)
                        tile_count = None
                        for zinfo in self.generator.reader.zoom_levels:
                            if zinfo.zoom == zoom:
                                tile_count = zinfo.tile_count
                                break
                        if tile_count:
                            info_text = f" ({tile_count:,} tiles, ORIGINAL)"
                        else:
                            info_text = f" (ORIGINAL)"
                        info_label = QLabel(info_text)
                        logger.debug(f"Z{zoom}: {info_text}")
                        
                    elif zoom in missing_zooms:
                        status = "○ missing"
                        checkbox_label = f"Z{zoom:2d}  {status}"
                        # For missing zooms, show generation plan
                        try:
                            plan = self.generator.create_generation_plan(zoom)
                            info_text = f" ({plan.tile_count:,} tiles, from Z{plan.source_zoom})"
                            
                            if plan.quality_warning:
                                info_text += " ⚠️"
                            
                            info_label = QLabel(info_text)
                            if plan.quality_warning:
                                info_label.setToolTip(plan.quality_reason)
                            
                            logger.debug(f"Z{zoom}: {info_text}")
                        except Exception as e:
                            info_label = QLabel(f" (Cannot generate: {str(e)[:40]}...)")
                            # Don't allow selection if generation fails
                            checkbox.setEnabled(False)
                            logger.warning(f"Z{zoom}: Cannot generate - {e}")
                    else:
                        status = "⊘ outside range"
                        checkbox_label = f"Z{zoom:2d}  {status}"
                        # For outside-range zooms, show generation plan
                        try:
                            plan = self.generator.create_generation_plan(zoom)
                            info_text = f" ({plan.tile_count:,} tiles, from Z{plan.source_zoom})"
                            
                            if plan.quality_warning:
                                info_text += " ⚠️"
                            
                            info_label = QLabel(info_text)
                            if plan.quality_warning:
                                info_label.setToolTip(plan.quality_reason)
                            
                            logger.debug(f"Z{zoom}: {info_text}")
                        except Exception as e:
                            info_label = QLabel(f" (Cannot generate: {str(e)[:40]}...)")
                            # Don't allow selection if generation fails
                            checkbox.setEnabled(False)
                            logger.warning(f"Z{zoom}: Cannot generate - {e}")
                    
                    checkbox = QCheckBox(checkbox_label)
                    checkbox.zoom_level = zoom
                    self.checkboxes[zoom] = checkbox
                    
                    checkbox_layout.addWidget(checkbox)
                    checkbox_layout.addWidget(info_label)
                    checkbox_layout.addStretch()
                    checkbox_widget.setLayout(checkbox_layout)
                    
                    scroll_layout.addWidget(checkbox_widget)
                
        except Exception as e:
            logger.error(f"Error building zoom list: {e}", exc_info=True)
            error_label = QLabel(f"Error: {e}")
            scroll_layout.addWidget(error_label)
        
        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        # Info text
        info_text = QLabel(
            "✓ = Zoom already in file\n"
            "○ = Missing zoom (gap in range)\n"
            "⊘ = Outside available range\n"
            "⚠️ = Quality warning\n\n"
            "Select the zoom levels you want to generate and click OK.\n"
            "Generation may take several minutes depending on zoom level."
        )
        layout.addWidget(info_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("Generate Selected")
        ok_button.clicked.connect(self._on_ok)
        button_layout.addWidget(ok_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _on_ok(self):
        """Handle OK button click."""
        # Get selected zooms
        self.selected_zooms = [
            zoom for zoom, checkbox in self.checkboxes.items()
            if checkbox.isChecked() and checkbox.isEnabled()
        ]
        
        if not self.selected_zooms:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select at least one zoom level to generate."
            )
            return
        
        logger.info(f"User selected zooms: {sorted(self.selected_zooms)}")
        
        # Show confirmation dialog with quality warnings
        warning_text = ""
        for zoom in sorted(self.selected_zooms):
            try:
                plan = self.generator.create_generation_plan(zoom)
                if plan.quality_warning:
                    warning_text += f"• Z{zoom}: {plan.quality_reason}\n"
                    logger.warning(f"Z{zoom} quality warning: {plan.quality_reason}")
            except Exception:
                pass
        
        if warning_text:
            confirm = QMessageBox.warning(
                self,
                "Quality Warnings",
                f"⚠️ The following zooms have quality concerns:\n\n{warning_text}\n"
                "Do you want to continue anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return
        
        # Accept dialog
        self.accept()
    
    def get_selected_zooms(self):
        """
        Get list of selected zoom levels.
        
        Returns:
            List of zoom levels to generate (sorted)
        """
        return sorted(self.selected_zooms)
