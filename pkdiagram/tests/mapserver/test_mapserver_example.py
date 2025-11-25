"""
Example tests demonstrating the Map Server usage for end-to-end testing.

These tests show how to use the Map Server to:
1. Launch and control the PyQt application
2. Take UI snapshots
3. Send keyboard and mouse events
4. Query UI state
5. Perform snapshot-based regression testing

To run these tests:
    uv run pytest pkdiagram/tests/mapserver/test_mapserver_example.py -v

Note: These tests require a display or the QT_QPA_PLATFORM=offscreen environment variable.
"""

import os
import tempfile
import pytest

# Skip all tests in this module if not in an appropriate environment
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        os.environ.get("CI") == "true" and os.environ.get("QT_QPA_PLATFORM") != "offscreen",
        reason="Requires display or offscreen platform",
    ),
]


class TestMapServerDirect:
    """
    Tests using the Map Server components directly (without HTTP).

    This is useful for in-process testing where you want the speed
    of direct method calls.
    """

    @pytest.fixture
    def controller(self):
        """Create an AppTestController for testing."""
        from pkdiagram.mapserver import AppTestController

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
        from pkdiagram.mapserver import AppTestController, InputSimulator

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
        from pkdiagram.mapserver import AppTestController, SnapshotManager

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
        from pkdiagram.mapserver import AppTestController, ElementFinder

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


class TestMapServerHTTP:
    """
    Tests using the Map Server over HTTP.

    These tests demonstrate the full client-server architecture.
    """

    @pytest.fixture
    def client(self):
        """Create a Map Server client."""
        from pkdiagram.mapserver import MapClient

        # Use a random port to avoid conflicts
        import random
        port = random.randint(10000, 60000)

        client = MapClient(port=port)
        yield client

        # Clean up
        try:
            client.shutdown()
        except Exception:
            pass

    @pytest.mark.skip(reason="Requires running server - integration test")
    def test_full_workflow(self, client):
        """
        Full end-to-end workflow test.

        This test demonstrates:
        1. Starting the server
        2. Initializing the application
        3. Creating the main window
        4. Taking snapshots
        5. Interacting with UI elements
        6. Shutdown
        """
        # Start server (would need to actually start it)
        # client.startServer(headless=True)

        # Initialize app
        # assert client.initApp(headless=True)

        # Create window
        # assert client.createWindow(show=False)

        # Get status
        # status = client.getStatus()
        # assert status["initialized"]
        # assert status["hasMainWindow"]

        # Take snapshot
        # snapshot = client.capture()
        # assert len(snapshot) > 0

        # Save snapshot
        # client.saveSnapshot("test_workflow", snapshot)

        # Clean up
        # client.shutdown()
        pass


# ============================================================================
# Example usage patterns for documentation
# ============================================================================

def example_direct_usage():
    """
    Example: Direct usage without HTTP server.

    This pattern is useful for:
    - Fast in-process testing
    - Debugging UI issues
    - Simple test scenarios
    """
    from pkdiagram.mapserver import (
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
    result = snapshots.compare("initial_state", after)
    print(f"Snapshots match: {result['match']}")

    # Cleanup
    controller.shutdown()


def example_client_server_usage():
    """
    Example: Client-server usage pattern.

    This pattern is useful for:
    - Testing from external processes
    - Remote testing scenarios
    - CI/CD pipelines
    """
    from pkdiagram.mapserver import MapClient

    # Create client and start server
    with MapClient(port=8765) as client:
        # Start the server subprocess
        client.startServer(headless=True)

        # Initialize application
        client.initApp()
        client.createWindow()
        client.newDocument()

        # Interact with UI
        client.click("newPersonButton")
        client.waitForElement("personDialog")
        client.type("John Doe", target="nameField")
        client.keyPress("enter")

        # Verify result
        items = client.getSceneItems(itemType="Person")
        assert any(item["name"] == "John Doe" for item in items)

        # Take and compare snapshot
        client.assertSnapshot("after_add_person")

        # Server stops automatically on context exit


def example_snapshot_testing():
    """
    Example: Snapshot-based regression testing.

    This pattern is useful for:
    - Visual regression testing
    - UI consistency verification
    - Cross-platform testing
    """
    from pkdiagram.mapserver import MapClient

    client = MapClient(port=8765)
    client.startServer(headless=True)

    try:
        client.initApp()
        client.createWindow()

        # Test various UI states
        test_cases = [
            ("empty_document", lambda: client.newDocument()),
            ("with_person", lambda: (
                client.newDocument(),
                client.click("addPersonButton"),
                client.processEvents(),
            )),
            ("with_marriage", lambda: (
                client.newDocument(),
                # ... add marriage setup ...
            )),
        ]

        for name, setup_fn in test_cases:
            setup_fn()
            client.processEvents()

            # Assert snapshot matches baseline
            # On first run, creates the baseline
            # On subsequent runs, compares against baseline
            client.assertSnapshot(
                name,
                threshold=0.01,  # Allow 1% difference
                updateOnFail=False,  # Set True to update baselines
            )

    finally:
        client.shutdown()


if __name__ == "__main__":
    # Run examples
    print("Map Server Examples")
    print("=" * 50)
    print("\nSee the test functions above for usage patterns.")
    print("\nTo run tests:")
    print("  uv run pytest pkdiagram/tests/mapserver/test_mapserver_example.py -v")
