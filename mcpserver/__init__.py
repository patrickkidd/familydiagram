"""
Qt-based testing utilities for PyQt+QML applications.

This module provides:
1. In-process testing utilities using Qt internals for precise UI control
2. MCP server for Claude Code integration (mcp_server.py)

Use Cases:
    - In-process unit/integration tests with direct Qt access
    - Precise QML item manipulation via objectName
    - Qt property inspection and modification
    - QGraphicsView item interaction
    - Claude Code MCP-based testing via socket bridge

Usage:
    from mcpserver import (
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
