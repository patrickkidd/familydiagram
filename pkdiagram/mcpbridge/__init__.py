"""
Qt Test Bridge - Exposes Qt internals for external testing via MCP.

This module provides a server that runs inside the PyQt application and
exposes Qt widgets, QML items, and their properties for external testing.

The bridge communicates with the MCP server over a simple JSON protocol on TCP.

Usage:
    # In your app startup (enabled via --test-server flag)
    from pkdiagram.testbridge import TestBridgeServer

    bridge = TestBridgeServer(port=9876)
    bridge.start()

    # The MCP server can then connect and send commands like:
    # {"command": "list_elements"}
    # {"command": "click", "objectName": "saveButton"}
    # {"command": "get_property", "objectName": "textField", "property": "text"}
"""

from .server import TestBridgeServer
from .inspector import QtInspector

__all__ = ["TestBridgeServer", "QtInspector"]
