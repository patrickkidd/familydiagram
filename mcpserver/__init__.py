"""Test harness for the Family Diagram apps.

Two halves, imported from their own modules so that the sandbox backend never
drags Qt into a Flask process:

    from mcpserver.sandbox import Sandbox            # sandbox backend
    from mcpserver.checkouts import Checkouts        # which checkout runs
    from mcpserver.mcp_server import TestInstance    # app + backend, via MCP

    from mcpserver.app_controller import AppTestController   # in-process Qt
    from mcpserver.element_finder import ElementFinder
    from mcpserver.input_simulator import InputSimulator
    from mcpserver.snapshot import SnapshotManager

See familydiagram/doc/SANDBOX.md.
"""
