"""FD-336 / WP-C, C7/D12: a save the server refused must leave the document
dirty, so the user's work is still there to retry rather than silently lost.
"""

import pickle

import pytest

from pkdiagram.scene import Person


pytestmark = [
    pytest.mark.component("MainWindow"),
    pytest.mark.depends_on("DocumentView"),
]


def _open_server_diagram(mw):
    assert mw.serverFileModel.rowCount() == 1
    diagram = mw.serverFileModel.diagramForRow(0)
    mw.onServerFileClicked(mw.serverFileModel.pathForDiagram(diagram), diagram)
    return diagram


def test_failed_save_keeps_document_dirty(qtbot, create_ac_mw, server_response):
    ac, mw = create_ac_mw()
    diagram = _open_server_diagram(mw)

    mw.scene.addItem(Person(name="Unsaved"), undo=True)
    assert mw.scene.stack().isClean() == False

    conflict = pickle.dumps({"version": diagram.version, "data": diagram.data})
    with server_response(f"/v1/diagrams/{diagram.id}", status_code=409, body=conflict):
        qtbot.clickOkAfter(lambda: mw.save())
    assert mw.scene.stack().isClean() == False
    assert mw.ui.actionSave.isEnabled() == True

    mw.save()
    assert mw.scene.stack().isClean() == True
    assert mw.ui.actionSave.isEnabled() == False
