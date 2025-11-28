"""
Qt-based testing utilities for PyQt+QML applications.

This module provides in-process testing utilities that use Qt internals
for precise UI control. These are complementary to the MCP server
(in mcp-server/) which provides external/remote testing via pyautogui.

Use Cases:
    - In-process unit/integration tests with direct Qt access
    - Precise QML item manipulation via objectName
    - Qt property inspection and modification
    - QGraphicsView item interaction

For external/MCP-based testing, see the mcp-server/ directory.

Usage:
    from pkdiagram.mcpserver import (
        AppTestController,
        InputSimulator,
        SnapshotManager,
        ElementFinder,
    )

    # In-process testing
    controller = AppTestController()
    controller.initialize(headless=True)
    controller.createMainWindow()

    simulator = InputSimulator(controller)
    snapshots = SnapshotManager(controller)
    finder = ElementFinder(controller)

    # Find and click a Qt widget
    button = finder.findWidget("saveButton")
    simulator.click(button)

    # Take and compare snapshots
    snapshots.assertMatch("expected_state")

    controller.shutdown()
"""

from .app_controller import AppTestController
from .element_finder import ElementFinder
from .input_simulator import InputSimulator
from .snapshot import SnapshotManager

__all__ = [
    "AppTestController",
    "ElementFinder",
    "InputSimulator",
    "SnapshotManager",
]
