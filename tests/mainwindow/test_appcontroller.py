import os.path
import pickle

import mock
import pytest

import vedana
from pkdiagram import version, util
from pkdiagram.scene import Scene, Person
from pkdiagram.app import AppController
from btcopilot import pro


pytestmark = [
    pytest.mark.component("AppController"),
    pytest.mark.depends_on("MainWindow"),
]


SCENE_NAME = "Some Scene"


def test_login_loads_free_diagram(create_ac_mw):
    ac, mw = create_ac_mw()
    assert mw.session.hasFeature(
        vedana.LICENSE_FREE
    ), "Active features should just be the free license."
    assert (
        mw.serverFileModel.rowCount() == 1
    ), "Free license should only have one file in server file model."
    assert mw.document, "MainWindow did not load diagram"


def test_login_loads_server_view(test_user_diagrams, test_activation, create_ac_mw):
    ac, mw = create_ac_mw()
    util.wait(mw.serverFileModel.updateFinished)
    assert (
        mw.serverFileModel.rowCount() == 6
    ), "Server file model hasn't syncronously updated on login."


def test_login_loads_last_loaded_diagram(tmp_path, test_activation, create_ac_mw):

    data = Scene(items=[Person(name="Patrick")]).data()
    filePath = os.path.join(tmp_path, "test.fd")
    util.touchFD(filePath, bdata=pickle.dumps(data))

    ac1, mw1 = create_ac_mw()
    mw1.open(filePath)
    assert mw1.document
    assert len(mw1.scene.people())
    assert mw1.scene.people()[0].name() == "Patrick"

    ac2, mw2 = create_ac_mw()
    assert mw1.scene.people()[0].name() == "Patrick"


def test_appconfig_tampered_with_should_just_log_out(qtbot, data_root, create_ac_mw):
    # Write appconfig that was tampered with
    tamperedFPath = os.path.join(data_root, "cherries_high_sierra")
    acFPath = os.path.join(util.appDataDir(), "cherries")
    with open(tamperedFPath, "rb") as infile:
        with open(acFPath, "wb") as outfile:
            outfile.write(infile.read())
    with open(acFPath + ".protect", "wb") as f:
        f.write(b"invalid-hash")

    ac, mw = create_ac_mw(init=False)
    qtbot.clickOkAfter(
        lambda: ac._pre_event_loop(mw), contains=AppController.S_APPCONFIG_TAMPERED_WITH
    )
    assert ac.session.isLoggedIn() == False
    assert mw.accountDialog.isShown() == True
    assert mw.accountDialog.itemProp("authForm", "state") == "email"


def test_free_license_when_no_licenses_activated(create_ac_mw):
    ac, mw = create_ac_mw()
    util.wait(mw.serverFileModel.updateFinished)
    assert mw.atHome() == False
    assert mw.session.activeFeatures() == [vedana.LICENSE_FREE]
    assert mw.scene.serverDiagram().isFreeDiagram()


def test_version_deactivated(test_license, qtbot, create_ac_mw):
    da = list(pro.DEACTIVATED_VERSIONS) + [version.VERSION]
    with mock.patch.object(pro, "DEACTIVATED_VERSIONS", da):
        ac, mw = create_ac_mw(init=False)
        qtbot.clickOkAfter(
            lambda: ac._pre_event_loop(mw), contains=AppController.S_VERSION_DEACTIVATED
        )
        assert mw.session.activeFeatures() == []
