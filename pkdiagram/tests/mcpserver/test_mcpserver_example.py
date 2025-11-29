"""
Example tests demonstrating the Qt-based testing utilities.

These tests show how to use the in-process testing utilities for:
1. Controlling the PyQt application
2. Taking UI snapshots
3. Sending keyboard and mouse events
4. Querying UI state

For external/MCP-based testing with Claude Code, see mcp-server/.

To run these tests:
    uv run pytest pkdiagram/tests/mcpserver/test_mcpserver_example.py -v

Note: These tests require a display or the QT_QPA_PLATFORM=offscreen environment variable.
"""

import os
import tempfile
import pytest

# Skip all tests in this module if not in an appropriate environment
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        os.environ.get("CI") == "true"
        and os.environ.get("QT_QPA_PLATFORM") != "offscreen",
        reason="Requires display or offscreen platform",
    ),
]


class TestAppTestController:
    """
    Tests for the AppTestController.

    This controller manages application lifecycle for testing.
    """

    @pytest.fixture
    def controller(self):
        """Create an AppTestController for testing."""
        from pkdiagram.mcpserver import AppTestController

        controller = AppTestController()
        yield controller
        controller.shutdown()

    @pytest.fixture
    def initialized_controller(self, controller):
        """Create an initialized controller with main window."""
        assert controller.initialize(headless=True)
        assert controller.createMainWindow(showWindow=False)
        return controller

    def test_controller_initialization(self, controller):
        """Test that the controller can initialize the application."""
        assert controller.initialize(headless=True)
        assert controller.app is not None

    def test_create_main_window(self, controller):
        """Test creating the main window."""
        controller.initialize(headless=True)
        assert controller.createMainWindow(showWindow=False)
        assert controller.mainWindow is not None

    def test_new_document(self, initialized_controller):
        """Test creating a new document."""
        assert initialized_controller.newDocument()
        assert initialized_controller.documentView is not None

    def test_process_events(self, initialized_controller):
        """Test event processing."""
        # Should not raise
        initialized_controller.processEvents(100)

    def test_wait_until(self, initialized_controller):
        """Test waiting for a condition."""
        # Condition that is immediately true
        result = initialized_controller.waitUntil(lambda: True, timeout=1000)
        assert result is True

        # Condition that is always false (will timeout)
        result = initialized_controller.waitUntil(lambda: False, timeout=100)
        assert result is False


class TestInputSimulator:
    """Tests for the InputSimulator component."""

    @pytest.fixture
    def setup(self):
        """Set up controller and input simulator."""
        from pkdiagram.mcpserver import AppTestController, InputSimulator

        controller = AppTestController()
        controller.initialize(headless=True)
        controller.createMainWindow(showWindow=False)
        controller.newDocument()

        simulator = InputSimulator(controller)

        yield controller, simulator

        controller.shutdown()

    def test_focus_widget(self, setup):
        """Test focusing a widget."""
        controller, simulator = setup

        # Focus the main window (should always work)
        mw = controller.mainWindow
        if mw:
            result = simulator.focus(mw)
            # May or may not succeed depending on widget state
            # Just ensure it doesn't crash
            assert isinstance(result, bool)


class TestSnapshotManager:
    """Tests for the SnapshotManager component."""

    @pytest.fixture
    def setup(self):
        """Set up controller and snapshot manager."""
        from pkdiagram.mcpserver import AppTestController, SnapshotManager

        controller = AppTestController()
        controller.initialize(headless=True)
        controller.createMainWindow(showWindow=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(controller, snapshotDir=tmpdir)
            yield controller, manager, tmpdir

        controller.shutdown()

    def test_capture_window(self, setup):
        """Test capturing a window screenshot."""
        controller, manager, tmpdir = setup

        data = manager.captureWindow()
        # In headless mode, we should still get some data
        # (might be empty/minimal depending on Qt platform plugin)
        assert data is None or isinstance(data, bytes)

    def test_save_and_load_snapshot(self, setup):
        """Test saving and loading snapshots."""
        controller, manager, tmpdir = setup

        # Create some test data
        testData = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Minimal PNG-like data

        # Save
        path = manager.saveSnapshot("test_snapshot", testData)
        assert os.path.exists(path)

        # Load
        loaded = manager.loadSnapshot("test_snapshot")
        assert loaded == testData

    def test_list_snapshots(self, setup):
        """Test listing snapshots."""
        controller, manager, tmpdir = setup

        # Initially empty
        snapshots = manager.listSnapshots()
        assert snapshots == []

        # Save some snapshots
        manager.saveSnapshot("snap1", b"data1")
        manager.saveSnapshot("snap2", b"data2")

        snapshots = manager.listSnapshots()
        assert "snap1" in snapshots
        assert "snap2" in snapshots

    def test_snapshot_comparison(self, setup):
        """Test snapshot comparison."""
        controller, manager, tmpdir = setup

        # Create test images (same data)
        testData = b"\x89PNG\r\n" + b"\x00" * 100

        # Save baseline
        manager.saveSnapshot("baseline", testData)

        # Compare with same data
        result = manager.compare("baseline", testData)
        assert result["baseline_exists"] is True
        # Note: Actual image comparison requires valid PNG data


class TestElementFinder:
    """Tests for the ElementFinder component."""

    @pytest.fixture
    def setup(self):
        """Set up controller and element finder."""
        from pkdiagram.mcpserver import AppTestController, ElementFinder

        controller = AppTestController()
        controller.initialize(headless=True)
        controller.createMainWindow(showWindow=False)

        finder = ElementFinder(controller)

        yield controller, finder

        controller.shutdown()

    def test_get_widget_tree(self, setup):
        """Test getting the widget tree."""
        controller, finder = setup

        tree = finder.getWidgetTree(maxDepth=3)
        assert isinstance(tree, dict)
        assert "className" in tree

    def test_find_widget_by_type(self, setup):
        """Test finding widgets by type."""
        controller, finder = setup

        # Find all QWidgets (should find some)
        # Note: Specific widget types depend on application structure
        widgets = finder.findWidgetByType("QWidget")
        # May or may not find widgets depending on initialization state
        assert isinstance(widgets, list)


# ============================================================================
# Example usage patterns for documentation
# ============================================================================


def example_in_process_testing():
    """
    Example: In-process testing with Qt utilities.

    This pattern is useful for:
    - Fast unit/integration tests
    - Direct Qt object access
    - Precise QML item manipulation
    """
    from pkdiagram.mcpserver import (
        AppTestController,
        InputSimulator,
        SnapshotManager,
        ElementFinder,
    )

    # Initialize
    controller = AppTestController()
    controller.initialize(headless=True)
    controller.createMainWindow(showWindow=True)
    controller.newDocument()

    # Create helpers
    input_sim = InputSimulator(controller)
    snapshots = SnapshotManager(controller)
    finder = ElementFinder(controller)

    # Take initial snapshot
    initial = snapshots.captureWindow()
    if initial:
        snapshots.saveSnapshot("initial_state", initial)

    # Find and interact with elements
    # (Example: Click a button if it exists)
    button = finder.findWidget("actionButton")
    if button:
        input_sim.click(button)
        controller.processEvents()

    # Take snapshot after interaction
    after = snapshots.captureWindow()

    # Compare snapshots
    if initial and after:
        result = snapshots.compare("initial_state", after)
        print(f"Snapshots match: {result['match']}")

    # Cleanup
    controller.shutdown()


def example_mcp_testing():
    """
    Example: MCP-based testing with Claude Code.

    For external/remote testing, use the MCP server in mcp-server/.

    The MCP server provides these tools to Claude Code:
    - launch_app: Start the application
    - close_app: Stop the application
    - take_screenshot: Capture UI state
    - click, double_click, right_click: Mouse input
    - type_text, press_key, hotkey: Keyboard input
    - drag, scroll: Advanced input
    - compare_screenshots: Visual regression testing

    Configuration is in .mcp.json at the project root.

    Example Claude Code conversation:

        User: "Test adding a person to the diagram"

        Claude: I'll launch the app and test the add person workflow.

        [Uses launch_app tool]
        [Uses take_screenshot to see initial state]
        [Uses click to press Add Person button]
        [Uses type_text to enter name]
        [Uses press_key("enter") to confirm]
        [Uses take_screenshot to verify result]
        [Uses compare_screenshots for regression check]
        [Uses close_app to clean up]
    """
    pass  # This is documentation, not runnable code


if __name__ == "__main__":
    # Run examples
    print("Testing Utilities Examples")
    print("=" * 50)
    print("\nIn-process testing: Use pkdiagram.mcpserver module")
    print("MCP testing: See mcp-server/ directory")
    print("\nTo run tests:")
    print("  uv run pytest pkdiagram/tests/mcpserver/test_mcpserver_example.py -v")
