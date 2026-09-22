#!/usr/bin/env python3
"""
CourseStudio - GPX File Manipulator

Main entry point for the CourseStudio application.
Initializes the application and launches the PyQt5 GUI.

Usage:
    python src/main.py [--file path/to/file.gpx] [--debug]

Author: Development Team
Date: 2026-09-20
"""

import sys
import argparse
import os
import logging
import traceback
from pathlib import Path

# Add project root to path so imports work correctly
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import QApplication
from config.app_config_yaml import AppConfig
from src.gui.main_window import MainWindow


# ============================================================================
# Logging Configuration
# ============================================================================

def setup_logging(debug: bool = False):
    """
    Configure logging for the application.
    
    Args:
        debug (bool): Enable debug level logging
    
    Returns:
        logging.Logger: Configured logger instance
    """
    
    log_level = logging.DEBUG if debug else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/tmp/CourseStudio.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured at level: {logging.getLevelName(log_level)}")
    return logger


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """
    Main entry point for CourseStudio application.
    
    1. Parse command-line arguments
    2. Load configuration
    3. Initialize logging
    4. Initialize PyQt5 application
    5. Create and show main window
    6. Start event loop
    """
    
    # ====================================================================
    # Parse command-line arguments
    # ====================================================================
    
    parser = argparse.ArgumentParser(
        description='CourseStudio - GPX File Manipulator',
        epilog='For help, visit: doc/USER_GUIDE.md'
    )
    parser.add_argument(
        '--file',
        type=str,
        default=None,
        help='GPX file to open on startup (optional)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/settings.yaml',
        help='Configuration file path (default: config/settings.yaml)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with verbose output'
    )
    
    args = parser.parse_args()
    
    # ====================================================================
    # Setup logging
    # ====================================================================
    
    logger = setup_logging(args.debug)
    
    # Print startup banner
    print("\n" + "="*70)
    print("Starting CourseStudio - GPX File Manipulator")
    print("="*70 + "\n")
    
    logger.info("Starting CourseStudio application")
    
    # ====================================================================
    # Load configuration
    # ====================================================================
    
    try:
        config = AppConfig(args.config)
        app_name = config.get_str('Application.name', 'CourseStudio')
        version = config.get_str('Application.version', '1.0.0')
        logger.info(f"Configuration loaded: {app_name} v{version}")
        print(f"✅ Application: {app_name} v{version}")
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        print(f"❌ Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}")
        print(f"❌ Unexpected Error: {e}")
        sys.exit(1)
    
    # ====================================================================
    # Validate file argument if provided
    # ====================================================================
    
    gpx_file_to_open = None
    if args.file:
        if os.path.exists(args.file):
            gpx_file_to_open = args.file
            logger.info(f"GPX file to open: {gpx_file_to_open}")
            print(f"✅ GPX file to open: {gpx_file_to_open}")
        else:
            logger.warning(f"Specified file not found: {args.file}")
            print(f"⚠️  File not found: {args.file}")
            print("   Will start with empty project")
    
    # ====================================================================
    # Create and configure PyQt5 application
    # ====================================================================
    
    try:
        app = QApplication(sys.argv)
        app.setApplicationName(app_name)
        app.setApplicationVersion(version)
        
        logger.info("PyQt5 Application created successfully")
        print("✅ PyQt5 Application created")
    
    except Exception as e:
        logger.error(f"Error creating PyQt5 application: {e}")
        print(f"❌ PyQt5 Error: {e}")
        sys.exit(1)
    
    # ====================================================================
    # Create main window
    # ====================================================================
    
    try:
        main_window = MainWindow(gpx_file_to_open)
        
        logger.info("Main window created successfully")
        print("✅ Main window created")
    
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error creating main window: {e}\n{tb}")
        print(f"❌ Error creating main window: {e}")
        print("\nFull traceback:")
        print(tb)
        sys.exit(1)
    
    # ====================================================================
    # Show main window and start event loop
    # ====================================================================
    
    try:
        main_window.show()
        
        logger.info("Main window displayed")
        print("✅ Main window displayed")
        print("\n" + "="*70)
        print(f"{app_name} is ready!")
        print("="*70 + "\n")
        
        logger.info("Starting Qt event loop")
        
        # Start the Qt event loop
        exit_code = app.exec_()
        
        logger.info(f"Application closed with exit code: {exit_code}")
        sys.exit(exit_code)
    
    except Exception as e:
        logger.error(f"Error during event loop: {e}")
        print(f"❌ Error during event loop: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
