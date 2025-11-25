"""
Application test controller for managing PyQt application lifecycle.
"""

import logging
import os
import tempfile
from typing import Optional, Any, Callable

from pkdiagram.pyqt import (
    QApplication,
    QMainWindow,
    QWidget,
    QQuickItem,
    QQuickWidget,
    QTimer,
    QEventLoop,
    Qt,
)


log = logging.getLogger(__name__)


class AppTestController:
    """
    Controls the PyQt application for testing purposes.

    This controller manages:
    - Application initialization in test mode
    - MainWindow creation and lifecycle
    - Access to DocumentView and QML components
    - Event loop management for synchronous testing
    """

    def __init__(self):
        self._app: Optional[QApplication] = None
        self._mainWindow: Optional[QMainWindow] = None
        self._appController = None
        self._initialized = False
        self._tempDir: Optional[str] = None

    @property
    def app(self) -> Optional[QApplication]:
        """Get the QApplication instance."""
        return self._app

    @property
    def mainWindow(self) -> Optional[QMainWindow]:
        """Get the main window."""
        return self._mainWindow

    @property
    def documentView(self):
        """Get the DocumentView from the main window."""
        if self._mainWindow is None:
            return None
        return getattr(self._mainWindow, "documentView", None)

    @property
    def scene(self):
        """Get the current Scene from DocumentView."""
        dv = self.documentView
        if dv is None:
            return None
        return dv.scene

    @property
    def qmlEngine(self):
        """Get the QmlEngine from DocumentView."""
        dv = self.documentView
        if dv is None:
            return None
        return getattr(dv, "qmlEngine", None)

    def initialize(self, headless: bool = False) -> bool:
        """
        Initialize the test application.

        Args:
            headless: If True, run in offscreen mode (no display required)

        Returns:
            True if initialization was successful
        """
        if self._initialized:
            log.warning("Application already initialized")
            return True

        try:
            # Set up test environment
            self._setupTestEnvironment(headless)

            # Import after environment setup
            from pkdiagram import util, version
            from pkdiagram.app import Application

            # Configure test mode
            util.IS_TEST = True
            util.ENABLE_OPENGL = False
            util.ANIM_DURATION_MS = 0
            util.LAYER_ANIM_DURATION_MS = 0
            util.QML_LAZY_DELAY_INTERVAL_MS = 0
            version.IS_ALPHA = False
            version.IS_BETA = False

            # Create application
            self._app = Application.instance()
            if self._app is None:
                self._app = Application([], Application.Type.Test)

            self._initialized = True
            log.info("Application initialized successfully")
            return True

        except Exception as e:
            log.error(f"Failed to initialize application: {e}")
            return False

    def _setupTestEnvironment(self, headless: bool):
        """Set up environment variables for testing."""
        # Create temp directory for test data
        self._tempDir = tempfile.mkdtemp(prefix="mapserver_test_")

        # Set environment for headless mode
        if headless:
            os.environ["QT_QPA_PLATFORM"] = "offscreen"

        # Disable GPU acceleration for stability
        os.environ["QT_QUICK_BACKEND"] = "software"

    def createMainWindow(self, showWindow: bool = True) -> bool:
        """
        Create and show the main window.

        Args:
            showWindow: If True, show the window after creation

        Returns:
            True if window was created successfully
        """
        if not self._initialized:
            log.error("Application not initialized. Call initialize() first.")
            return False

        try:
            from pkdiagram.app import AppController
            from pkdiagram.mainwindow import MainWindow

            # Create app controller and main window
            self._appController = AppController(self._app)
            self._mainWindow = MainWindow(appController=self._appController)
            self._mainWindow.init()

            if showWindow:
                self._mainWindow.show()
                self.processEvents()
                self.waitUntil(lambda: self._mainWindow.isVisible(), timeout=5000)

            log.info("MainWindow created successfully")
            return True

        except Exception as e:
            log.error(f"Failed to create MainWindow: {e}")
            return False

    def loadFile(self, filePath: str) -> bool:
        """
        Load a diagram file.

        Args:
            filePath: Path to the .fd file to load

        Returns:
            True if file was loaded successfully
        """
        if self._mainWindow is None:
            log.error("MainWindow not created")
            return False

        try:
            self._mainWindow.open(filePath)
            self.processEvents()
            return True
        except Exception as e:
            log.error(f"Failed to load file: {e}")
            return False

    def newDocument(self) -> bool:
        """
        Create a new empty document.

        Returns:
            True if document was created successfully
        """
        if self._mainWindow is None:
            log.error("MainWindow not created")
            return False

        try:
            self._mainWindow.new()
            self.processEvents()
            return True
        except Exception as e:
            log.error(f"Failed to create new document: {e}")
            return False

    def processEvents(self, timeout: int = 100):
        """
        Process pending Qt events.

        Args:
            timeout: Maximum time in ms to process events
        """
        if self._app is None:
            return

        loop = QEventLoop()
        QTimer.singleShot(timeout, loop.quit)
        loop.exec()

    def waitUntil(
        self,
        condition: Callable[[], bool],
        timeout: int = 5000,
        interval: int = 50,
    ) -> bool:
        """
        Wait until a condition is met.

        Args:
            condition: Callable that returns True when condition is met
            timeout: Maximum time to wait in ms
            interval: Check interval in ms

        Returns:
            True if condition was met, False if timeout
        """
        elapsed = 0
        while elapsed < timeout:
            self.processEvents(interval)
            if condition():
                return True
            elapsed += interval
        return False

    def shutdown(self):
        """Shutdown the application and clean up."""
        try:
            if self._mainWindow is not None:
                self._mainWindow.close()
                self._mainWindow.deinit()
                self._mainWindow = None

            if self._appController is not None:
                self._appController = None

            # Clean up temp directory
            if self._tempDir and os.path.exists(self._tempDir):
                import shutil
                shutil.rmtree(self._tempDir, ignore_errors=True)

            self._initialized = False
            log.info("Application shutdown complete")

        except Exception as e:
            log.error(f"Error during shutdown: {e}")

    def findWidget(self, objectName: str) -> Optional[QWidget]:
        """
        Find a widget by object name.

        Args:
            objectName: The objectName of the widget to find

        Returns:
            The widget if found, None otherwise
        """
        if self._mainWindow is None:
            return None

        return self._mainWindow.findChild(QWidget, objectName)

    def findQmlItem(self, objectName: str) -> Optional[QQuickItem]:
        """
        Find a QML item by object name.

        Args:
            objectName: The objectName of the QML item to find

        Returns:
            The QQuickItem if found, None otherwise
        """
        dv = self.documentView
        if dv is None:
            return None

        # Search through all QML drawers and views
        from pkdiagram.mapserver.element_finder import ElementFinder
        finder = ElementFinder(self)
        return finder.findQmlItem(objectName)

    def getProperty(self, objectName: str, propertyName: str) -> Any:
        """
        Get a property value from a widget or QML item.

        Args:
            objectName: The objectName of the item
            propertyName: The name of the property to get

        Returns:
            The property value, or None if not found
        """
        # Try widget first
        widget = self.findWidget(objectName)
        if widget is not None:
            return widget.property(propertyName)

        # Try QML item
        item = self.findQmlItem(objectName)
        if item is not None:
            return item.property(propertyName)

        return None

    def setProperty(self, objectName: str, propertyName: str, value: Any) -> bool:
        """
        Set a property value on a widget or QML item.

        Args:
            objectName: The objectName of the item
            propertyName: The name of the property to set
            value: The value to set

        Returns:
            True if property was set successfully
        """
        # Try widget first
        widget = self.findWidget(objectName)
        if widget is not None:
            return widget.setProperty(propertyName, value)

        # Try QML item
        item = self.findQmlItem(objectName)
        if item is not None:
            return item.setProperty(propertyName, value)

        return False
