#!/usr/bin/env python3
"""
Quick UI test script - launches the application with a test GPX file.
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from PyQt5.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def main():
    """Launch the application."""
    app = QApplication(sys.argv)
    
    # Open with test GPX file
    test_file = Path(__file__).parent / 'tests' / 'gpx' / 'Karlskrona-Hallarum.gpx'
    
    if test_file.exists():
        print(f"✅ Opening test file: {test_file}")
        window = MainWindow(str(test_file))
    else:
        print(f"❌ Test file not found: {test_file}")
        window = MainWindow()
    
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
