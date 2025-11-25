"""
Map Server - End-to-end testing server for PyQt+QML applications.

This module provides a server that allows external code to:
- Launch and control the PyQt application
- Take UI snapshots/screenshots
- Send keyboard and mouse events
- Query UI state and element properties
- Wait for UI conditions

Usage:
    from pkdiagram.mapserver import MapServer, MapClient

    # Server side (typically in a subprocess)
    server = MapServer(port=8765)
    server.run()

    # Client side (in your test code)
    client = MapClient(port=8765)
    client.launch_app()
    client.click("buttonName")
    snapshot = client.snapshot()
    client.shutdown()
"""

from .server import MapServer
from .client import MapClient
from .app_controller import AppTestController
from .element_finder import ElementFinder
from .input_simulator import InputSimulator
from .snapshot import SnapshotManager

__all__ = [
    "MapServer",
    "MapClient",
    "AppTestController",
    "ElementFinder",
    "InputSimulator",
    "SnapshotManager",
]
