import os
import os.path
import pickle
import time

import pytest
from unittest import mock

from pkdiagram import util
from pkdiagram.pyqt import QApplication
from pkdiagram.scene import Person, Scene
from pkdiagram.mainwindow import MainWindow, AutoSaveManager


pytestmark = [
    pytest.mark.component("MainWindow"),
    pytest.mark.depends_on("DocumentView"),
]


def test_autosave_manager_creates_folder(tmp_path, qApp):
    """Test that AutoSaveManager creates the autosave folder."""
    with mock.patch(
        "_pkdiagram.CUtil.instance"
    ) as mock_instance:
        mock_instance.return_value.documentsFolderPath.return_value = str(tmp_path)
        manager = AutoSaveManager()
        autosave_folder = os.path.join(tmp_path, AutoSaveManager.AUTOSAVE_FOLDER_NAME)
        assert os.path.isdir(autosave_folder)


def test_autosave_on_document_open(tmp_path, create_ac_mw):
    """Test that auto-save triggers immediately when a document is opened."""
    # Create a test file
    scene = Scene(items=(Person(name="Test Person"),))
    fd_path = os.path.join(tmp_path, "test.fd")
    util.touchFD(fd_path, bdata=pickle.dumps(scene.data()))

    # Create main window and track auto-saves
    ac, mw = create_ac_mw()
    autosave_paths = []

    def on_auto_saved(path):
        autosave_paths.append(path)

    mw.autoSaveManager.autoSaved.connect(on_auto_saved)

    # Open the document - should trigger immediate auto-save
    mw.open(fd_path)
    QApplication.instance().processEvents()

    # Verify auto-save was triggered
    assert len(autosave_paths) == 1
    assert os.path.isdir(autosave_paths[0])
    assert "test_autosave_" in autosave_paths[0]

    # Verify the autosaved file exists and contains pickle data
    pickle_path = os.path.join(autosave_paths[0], "diagram.pickle")
    assert os.path.isfile(pickle_path)
    # Verify it's valid pickle data
    with open(pickle_path, "rb") as f:
        pickle.loads(f.read())


def test_autosave_filename_format(tmp_path, create_ac_mw):
    """Test that auto-save filenames follow the expected format."""
    scene = Scene(items=(Person(name="Alice"),))
    fd_path = os.path.join(tmp_path, "my_family.fd")
    util.touchFD(fd_path, bdata=pickle.dumps(scene.data()))

    ac, mw = create_ac_mw()
    autosave_paths = []
    mw.autoSaveManager.autoSaved.connect(lambda path: autosave_paths.append(path))

    mw.open(fd_path)
    QApplication.instance().processEvents()

    assert len(autosave_paths) == 1
    filename = os.path.basename(autosave_paths[0])

    # Should be: my_family_autosave_YYYYMMDD_HHMMSS.fd
    assert filename.startswith("my_family_autosave_")
    assert filename.endswith(".fd")

    # Extract timestamp portion and verify format
    timestamp_part = filename.replace("my_family_autosave_", "").replace(".fd", "")
    parts = timestamp_part.split("_")
    assert len(parts) == 2  # date_time
    assert len(parts[0]) == 8  # YYYYMMDD
    assert len(parts[1]) == 6  # HHMMSS


def test_autosave_stops_when_document_closed(tmp_path, create_ac_mw):
    """Test that auto-save stops when document is closed."""
    scene = Scene(items=(Person(name="Bob"),))
    fd_path = os.path.join(tmp_path, "test.fd")
    util.touchFD(fd_path, bdata=pickle.dumps(scene.data()))

    ac, mw = create_ac_mw()
    mw.open(fd_path)
    QApplication.instance().processEvents()

    # Verify timer is running
    assert mw.autoSaveManager._timerId is not None

    # Close document
    mw.setDocument(None)
    QApplication.instance().processEvents()

    # Verify timer is stopped
    assert mw.autoSaveManager._timerId is None


def test_autosave_periodic_save(tmp_path, create_ac_mw, qtbot):
    """Test that auto-save triggers periodically (mocked timer)."""
    scene = Scene(items=(Person(name="Charlie"),))
    fd_path = os.path.join(tmp_path, "test.fd")
    util.touchFD(fd_path, bdata=pickle.dumps(scene.data()))

    ac, mw = create_ac_mw()
    autosave_count = [0]

    def on_auto_saved(path):
        autosave_count[0] += 1

    mw.autoSaveManager.autoSaved.connect(on_auto_saved)

    mw.open(fd_path)
    QApplication.instance().processEvents()

    # First auto-save on open
    assert autosave_count[0] == 1

    # Manually trigger auto-save to simulate periodic save
    mw.autoSaveManager._performAutoSave()
    QApplication.instance().processEvents()

    # Should have triggered second auto-save
    assert autosave_count[0] == 2


def test_autosave_readonly_document(tmp_path, create_ac_mw):
    """Test that auto-save skips read-only documents."""
    scene = Scene(items=(Person(name="Dave"),))
    fd_path = os.path.join(tmp_path, "test.fd")
    util.touchFD(fd_path, bdata=pickle.dumps(scene.data()))

    ac, mw = create_ac_mw()
    autosave_count = [0]

    mw.autoSaveManager.autoSaved.connect(
        lambda path: autosave_count.__setitem__(0, autosave_count[0] + 1)
    )

    mw.open(fd_path)
    QApplication.instance().processEvents()

    # First save on open
    assert autosave_count[0] == 1

    # Mark scene as read-only
    mw.scene.setReadOnly(True)

    # Try to trigger auto-save
    mw.autoSaveManager._performAutoSave()
    QApplication.instance().processEvents()

    # Should not have saved again
    assert autosave_count[0] == 1


def test_autosave_server_diagram_uses_name(tmp_path, create_ac_mw):
    """Test that server diagram autosaves use the diagram name when available."""
    from pkdiagram.server_types import Diagram
    from unittest.mock import Mock

    # Create a test file with server diagram ID as filename
    scene = Scene(items=(Person(name="Test"),))
    fd_path = os.path.join(tmp_path, "1778.fd")
    util.touchFD(fd_path, bdata=pickle.dumps(scene.data()))

    ac, mw = create_ac_mw()
    autosave_paths = []
    mw.autoSaveManager.autoSaved.connect(lambda path: autosave_paths.append(path))

    # Set up server diagram BEFORE opening
    serverDiagram = Mock(spec=Diagram)
    serverDiagram.name = "Mrs Olodort"

    # Open the document
    mw.open(fd_path)
    mw.scene.setServerDiagram(serverDiagram)
    QApplication.instance().processEvents()

    # Trigger autosave - should use server diagram name
    mw.autoSaveManager._performAutoSave()
    QApplication.instance().processEvents()

    # Verify the autosave uses the server diagram name, not the file ID
    assert len(autosave_paths) >= 1
    # Check the most recent autosave
    filename = os.path.basename(autosave_paths[-1])
    assert filename.startswith("Mrs Olodort_autosave_")
    assert not filename.startswith("1778_autosave_")
