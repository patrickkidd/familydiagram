import pytest
import vedana
from pkdiagram import util
from pkdiagram.mainwindow import MainWindow

from btcopilot.extensions import db


pytestmark = [
    pytest.mark.component("MainWindow"),
    pytest.mark.depends_on("DocumentView", "AccountDialog"),
]


@pytest.mark.parametrize("is_server_down", [True, False])
def test_init_not_logged_in(create_ac_mw, server_down, is_server_down):
    with server_down(is_server_down):
        ac, mw = create_ac_mw(session=False)
        assert mw.session.activeFeatures() == []
        assert mw.fileManager.isVisible() == False
        assert mw.accountDialog.isShown() == True
        assert mw.isFreeDiagramOpen() == False


@pytest.mark.parametrize("is_server_down", [True, False])
def test_init_with_free_license(qtbot, create_ac_mw, server_down, is_server_down):
    with server_down(is_server_down):
        ac, mw = create_ac_mw(init=False)
        if is_server_down:
            qtbot.clickOkAfter(
                lambda: ac._pre_event_loop(mw),
                contains=MainWindow.S_NO_FREE_DIAGRAM_NO_SERVER,
            )
        else:
            ac._pre_event_loop(mw)
        assert mw.session.activeFeatures() == [vedana.LICENSE_FREE]
        assert mw.accountDialog.isShown() == False
        assert mw.isFreeDiagramOpen() == (not is_server_down)  # just when not cached


@pytest.mark.parametrize("is_server_down", [True, False])
def test_dont_show_account_with_session_pro_license(
    test_license, test_activation, create_ac_mw, server_down, is_server_down
):
    with server_down(is_server_down):
        ac, mw = create_ac_mw()
        assert mw.session.activeFeatures() == [
            vedana.LICENSE_PROFESSIONAL
        ]  # vedana.licenses_features([test_license.as_dict(include='policy')])
        assert mw.accountDialog.isShown() == False


@pytest.mark.parametrize("is_server_down", [True, False])
def test_logout(
    test_license, test_activation, qtbot, create_ac_mw, server_down, is_server_down
):
    with server_down(is_server_down):
        ac, mw = create_ac_mw()
        db.session.add(test_activation)
        assert mw.session.activeFeatures() == vedana.licenses_features(
            [test_activation.license.as_dict(include="policy")]
        )

        # Logout
        mw.showAccount()
        changed = util.Condition(mw.session.changed)
        qtbot.clickYesAfter(lambda: mw.accountDialog.mouseClick("logoutButton"))
        assert changed.wait() == True
        assert mw.accountDialog.isShown() == True
        assert mw.session.activeFeatures() == []
        assert mw.fileManager.isVisible() == False


def test_dont_logout_when_show_account_with_session_pro_license(
    test_license, test_activation, create_ac_mw, server_down
):
    with server_down():
        ac, mw = create_ac_mw()
        pre_features = vedana.licenses_features(
            [test_license.as_dict(include="policy")]
        )
        mw.showAccount()
        assert mw.session.activeFeatures() == pre_features
        assert mw.accountDialog.isShown() == True
