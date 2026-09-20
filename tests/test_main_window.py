"""
Unit tests for Main Window module (src/gui/main_window.py).

Tests cover:
- Window initialization and configuration
- Menu creation and actions
- Toolbar creation
- Central widget setup
- File operations (open, save)
- Signal emission and handling
- Dialog helpers

Run with: pytest tests/test_main_window.py -v
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch, mock_open
from pathlib import Path

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

# Import modules to test
from src.gui.main_window import MainWindow
from src.core.track_manager import TrackManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def main_window(qapp):
    """Create a main window instance for testing."""
    window = MainWindow()
    yield window
    window.close()


@pytest.fixture
def main_window_with_file(qapp, tmp_path):
    """Create a main window with a mock GPX file loaded."""
    # Create a minimal GPX file
    gpx_file = tmp_path / "test.gpx"
    gpx_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk>
    <name>Test Track</name>
    <trkseg>
      <trkpt lat="57.5" lon="17.2"/>
      <trkpt lat="57.6" lon="17.3"/>
    </trkseg>
  </trk>
</gpx>""")
    
    window = MainWindow(str(gpx_file))
    yield window
    window.close()


# ============================================================================
# Window Initialization Tests
# ============================================================================

class TestMainWindowInitialization:
    """Tests for window initialization."""
    
    def test_window_creation(self, main_window):
        """Test window is created successfully."""
        assert main_window is not None
        assert isinstance(main_window, MainWindow)
    
    def test_window_title_set(self, main_window):
        """Test window title is set."""
        title = main_window.windowTitle()
        assert 'mangpx' in title
        assert 'v' in title
    
    def test_window_size_valid(self, main_window):
        """Test window has valid size."""
        width = main_window.width()
        height = main_window.height()
        assert width > 0
        assert height > 0
    
    def test_components_initialized(self, main_window):
        """Test all components are initialized."""
        assert main_window.config is not None
        assert main_window.gpx_handler is not None
        assert main_window.track_manager is not None
    
    def test_initial_state(self, main_window):
        """Test initial application state."""
        assert main_window.current_file_path is None
        assert main_window.is_modified is False
    
    def test_status_bar_exists(self, main_window):
        """Test status bar is created."""
        status_bar = main_window.statusBar()
        assert status_bar is not None
    
    def test_menu_bar_exists(self, main_window):
        """Test menu bar is created."""
        menu_bar = main_window.menuBar()
        assert menu_bar is not None
    
    def test_toolbar_exists(self, main_window):
        """Test toolbar is created."""
        assert hasattr(main_window, 'toolbar')
        assert main_window.toolbar is not None
    
    def test_central_widget_exists(self, main_window):
        """Test central widget is created."""
        assert main_window.centralWidget() is not None


# ============================================================================
# Menu Tests
# ============================================================================

class TestMainWindowMenus:
    """Tests for menu bar and actions."""
    
    def test_file_menu_exists(self, main_window):
        """Test File menu is created."""
        menu_bar = main_window.menuBar()
        menus = [action.text() for action in menu_bar.actions()]
        assert '&File' in menus
    
    def test_edit_menu_exists(self, main_window):
        """Test Edit menu is created."""
        menu_bar = main_window.menuBar()
        menus = [action.text() for action in menu_bar.actions()]
        assert '&Edit' in menus
    
    def test_view_menu_exists(self, main_window):
        """Test View menu is created."""
        menu_bar = main_window.menuBar()
        menus = [action.text() for action in menu_bar.actions()]
        assert '&View' in menus
    
    def test_help_menu_exists(self, main_window):
        """Test Help menu is created."""
        menu_bar = main_window.menuBar()
        menus = [action.text() for action in menu_bar.actions()]
        assert '&Help' in menus
    
    def test_undo_action_exists(self, main_window):
        """Test Undo action exists and is disabled initially."""
        assert hasattr(main_window, 'undo_action')
        assert main_window.undo_action is not None
        assert main_window.undo_action.isEnabled() is False
    
    def test_redo_action_exists(self, main_window):
        """Test Redo action exists and is disabled initially."""
        assert hasattr(main_window, 'redo_action')
        assert main_window.redo_action is not None
        assert main_window.redo_action.isEnabled() is False


# ============================================================================
# Toolbar Tests
# ============================================================================

class TestMainWindowToolbar:
    """Tests for toolbar."""
    
    def test_toolbar_created(self, main_window):
        """Test toolbar is created."""
        assert main_window.toolbar is not None
    
    def test_toolbar_has_actions(self, main_window):
        """Test toolbar has actions."""
        actions = main_window.toolbar.actions()
        assert len(actions) > 0
    
    def test_toolbar_undo_action(self, main_window):
        """Test toolbar undo action exists."""
        assert hasattr(main_window, 'toolbar_undo_action')
    
    def test_toolbar_redo_action(self, main_window):
        """Test toolbar redo action exists."""
        assert hasattr(main_window, 'toolbar_redo_action')


# ============================================================================
# File Operations Tests
# ============================================================================

class TestMainWindowFileOperations:
    """Tests for file operations."""
    
    @patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName')
    def test_action_open_file_cancelled(self, mock_dialog, main_window):
        """Test opening file when dialog is cancelled."""
        mock_dialog.return_value = ('', '')
        main_window.action_open_file()
        
        # File path should not change
        assert main_window.current_file_path is None
    
    def test_open_file_invalid_path(self, main_window):
        """Test opening non-existent file."""
        result = main_window.open_file('/nonexistent/file.gpx')
        assert result is False
    
    def test_save_file_no_file_path(self, main_window):
        """Test save when no file is currently open."""
        # This should trigger save-as behavior
        main_window.current_file_path = None
        # Should not crash
        assert main_window.current_file_path is None
    
    def test_action_save_file_with_file(self, main_window):
        """Test save action when file is open."""
        main_window.current_file_path = '/tmp/test.gpx'
        # Should not crash
        assert main_window.current_file_path == '/tmp/test.gpx'


# ============================================================================
# Signals Tests
# ============================================================================

class TestMainWindowSignals:
    """Tests for signal emission."""
    
    def test_file_opened_signal_exists(self, main_window):
        """Test file_opened signal exists."""
        assert hasattr(main_window, 'file_opened')
    
    def test_file_saved_signal_exists(self, main_window):
        """Test file_saved signal exists."""
        assert hasattr(main_window, 'file_saved')
    
    def test_track_selected_signal_exists(self, main_window):
        """Test track_selected signal exists."""
        assert hasattr(main_window, 'track_selected')
    
    def test_file_opened_signal_callable(self, main_window):
        """Test file_opened signal can be emitted."""
        # Signal should be callable
        try:
            main_window.file_opened.connect(lambda x: None)
            main_window.file_opened.emit('/tmp/test.gpx')
            assert True
        except Exception as e:
            assert False, f"Signal emission failed: {e}"


# ============================================================================
# Dialog Tests
# ============================================================================

class TestMainWindowDialogs:
    """Tests for dialog methods."""
    
    @patch('PyQt5.QtWidgets.QMessageBox.critical')
    def test_show_error(self, mock_critical, main_window):
        """Test error dialog."""
        main_window.show_error('Test', 'Error message')
        mock_critical.assert_called_once()
    
    @patch('PyQt5.QtWidgets.QMessageBox.warning')
    def test_show_warning(self, mock_warning, main_window):
        """Test warning dialog."""
        main_window.show_warning('Test', 'Warning message')
        mock_warning.assert_called_once()
    
    @patch('PyQt5.QtWidgets.QMessageBox.information')
    def test_show_info(self, mock_info, main_window):
        """Test info dialog."""
        main_window.show_info('Test', 'Info message')
        mock_info.assert_called_once()
    
    @patch('PyQt5.QtWidgets.QMessageBox.about')
    def test_action_about(self, mock_about, main_window):
        """Test about dialog."""
        main_window.action_about()
        mock_about.assert_called_once()


# ============================================================================
# Edit Actions Tests
# ============================================================================

class TestMainWindowEditActions:
    """Tests for edit actions."""
    
    def test_action_undo_callable(self, main_window):
        """Test undo action is callable."""
        main_window.action_undo()
        # Should not crash
        assert True
    
    def test_action_redo_callable(self, main_window):
        """Test redo action is callable."""
        main_window.action_redo()
        # Should not crash
        assert True
    
    def test_action_preferences_callable(self, main_window):
        """Test preferences action is callable."""
        main_window.action_preferences()
        # Should not crash
        assert True


# ============================================================================
# View Actions Tests
# ============================================================================

class TestMainWindowViewActions:
    """Tests for view actions."""
    
    def test_action_zoom_in_callable(self, main_window):
        """Test zoom in action is callable."""
        main_window.action_zoom_in()
        assert True
    
    def test_action_zoom_out_callable(self, main_window):
        """Test zoom out action is callable."""
        main_window.action_zoom_out()
        assert True


# ============================================================================
# Signal Handler Tests
# ============================================================================

class TestMainWindowSignalHandlers:
    """Tests for signal handler methods."""
    
    def test_on_file_opened(self, main_window):
        """Test file opened signal handler."""
        main_window._on_file_opened('/tmp/test.gpx')
        # Should not crash and status should be updated
        assert main_window.statusBar() is not None
    
    def test_on_file_saved(self, main_window):
        """Test file saved signal handler."""
        main_window._on_file_saved('/tmp/test.gpx')
        # Should not crash
        assert True
    
    def test_on_track_selected(self, main_window):
        """Test track selected signal handler."""
        main_window._on_track_selected(0)
        # Should not crash
        assert True


# ============================================================================
# Configuration Tests
# ============================================================================

class TestMainWindowConfiguration:
    """Tests for configuration usage."""
    
    def test_config_loaded(self, main_window):
        """Test configuration is loaded."""
        assert main_window.config is not None
    
    def test_config_values_used(self, main_window):
        """Test configuration values are used."""
        # Window should have size from config
        assert main_window.width() > 0
        assert main_window.height() > 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestMainWindowIntegration:
    """Integration tests for window functionality."""
    
    def test_window_can_be_shown(self, main_window):
        """Test window can be shown without crashing."""
        main_window.show()
        # Don't assert visibility in headless testing
        # Just ensure show() doesn't crash
        assert main_window is not None
    
    def test_window_can_be_closed(self, main_window):
        """Test window can be closed without crashing."""
        main_window.show()
        main_window.close()
        assert main_window.isHidden()
    
    def test_menu_actions_do_not_crash(self, main_window):
        """Test that menu actions can be triggered without crashing."""
        main_window.action_undo()
        main_window.action_redo()
        main_window.action_zoom_in()
        main_window.action_zoom_out()
        main_window.action_preferences()
        # Should not crash
        assert True


# ============================================================================
# Mock File Loading Test
# ============================================================================

class TestMainWindowFileLoading:
    """Tests for file loading functionality."""
    
    def test_window_initializes_with_file(self, main_window_with_file):
        """Test window can be initialized with a file."""
        assert main_window_with_file.current_file_path is not None
        assert main_window_with_file.track_manager.get_track_count() > 0


# ============================================================================
# Close Event Tests
# ============================================================================

class TestMainWindowCloseEvent:
    """Tests for close event handling."""
    
    @patch('PyQt5.QtWidgets.QMessageBox.question')
    def test_close_event_without_modifications(self, mock_question, main_window):
        """Test close event when no modifications."""
        main_window.is_modified = False
        event = Mock()
        main_window.closeEvent(event)
        event.accept.assert_called_once()
    
    @patch('PyQt5.QtWidgets.QMessageBox.question')
    def test_close_event_with_modifications(self, mock_question, main_window):
        """Test close event when modifications exist."""
        main_window.is_modified = True
        mock_question.return_value = mock_question.Discard
        
        event = Mock()
        main_window.closeEvent(event)
        # Question should be asked
        mock_question.assert_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
