import pytest, mock

import vedana
from pkdiagram import util, version
from pkdiagram.app import AppController

from btcopilot.extensions import db
from btcopilot.pro.models import Activation, License, Policy, Machine, User, Session
from btcopilot import pro


def test_hide_account_dialog(create_ac_mw):
    ac, mw = create_ac_mw()
    mw.ui.actionShow_Account.trigger()
    assert mw.accountDialog.isShown() == True

    mw.accountDialog.mouseClick("doneButton")
    assert mw.accountDialog.isShown() == False


def test_logout_no_server(test_activation, qtbot, create_ac_mw, server_down):
    """Logout button should be enabled and should work."""
    with server_down():
        ac, mw = create_ac_mw()
        assert mw.session.activeFeatures() == vedana.licenses_features(
            [test_activation.license.as_dict(include="policy")]
        )

        mw.showAccount()
        assert mw.accountDialog.isShown() == True
        assert mw.accountDialog.itemProp("logoutButton", "enabled") == True

        changed = util.Condition(mw.session.changed)
        qtbot.clickYesAfter(lambda: mw.accountDialog.mouseClick("logoutButton"))
        assert changed.wait() == True
        assert mw.session.activeFeatures() == []


def test_last_stored_license_expired_when_not_logged_in(test_license, create_ac_mw):
    test_license.canceled = True
    test_license.active = False
    db.session.commit()

    ac, mw = create_ac_mw()
    assert mw.session.activeFeatures() == [vedana.LICENSE_FREE]


@pytest.mark.parametrize("version_attr", ["IS_ALPHA", "IS_BETA", "IS_RELEASE"])
@pytest.mark.parametrize(
    "license_type",
    [vedana.LICENSE_ALPHA, vedana.LICENSE_BETA, vedana.LICENSE_PROFESSIONAL],
)
def test_enabled_disabled_all_licenses(
    test_session, test_machine, test_user, create_ac_mw, version_attr, license_type
):
    """TODO: Add free license support."""
    test_user = User.query.get(test_user.id)
    test_machine = Machine.query.get(test_machine.id)
    test_session = Session.query.get(test_session.id)
    session = db.session
    policy = Policy(
        code=license_type,
        product=license_type,
        name="Unit Test Alpha",
        interval="month",
        amount=0.99,
        maxActivations=2,
        active=True,
        public=True,
    )
    db.session.add(policy)
    license = License(user=test_user, policy=policy)
    db.session.add(license)
    activation = Activation(license=license, machine=test_machine)
    db.session.add(activation)
    db.session.commit()

    with mock.patch.object(version, version_attr, True):
        ac, mw = create_ac_mw(session=test_session)
        if version.IS_ALPHA and ac.session.hasFeature(vedana.LICENSE_ALPHA):
            assert mw.fileManager.isEnabled() == True
            assert mw.documentView.isEnabled() == True
        elif version.IS_BETA and ac.session.hasFeature(vedana.LICENSE_BETA):
            assert mw.fileManager.isEnabled() == True
            assert mw.documentView.isEnabled() == True
        elif (
            not version.IS_ALPHA
            and not version.IS_BETA
            and ac.session.hasFeature(vedana.LICENSE_PROFESSIONAL)
        ):
            assert mw.fileManager.isEnabled() == True
            assert mw.documentView.isEnabled() == True
        else:
            assert mw.fileManager.isEnabled() == False
            assert mw.documentView.isEnabled() == False


def test_version_deactivated_while_logged_in(test_license, qtbot, create_ac_mw):
    with mock.patch.object(
        pro,
        "DEACTIVATED_VERSIONS",
        list(pro.DEACTIVATED_VERSIONS) + [version.VERSION],
    ):
        ac, mw = create_ac_mw(init=False)
        qtbot.clickOkAfter(
            lambda: ac._pre_event_loop(mw), contains=AppController.S_VERSION_DEACTIVATED
        )
        assert mw.session.activeFeatures() == []


def test_import_license(test_session, test_policy, qtbot, create_ac_mw):

    license = License(policy=test_policy)
    db.session.add(license)
    db.session.commit()
    assert License.query.filter_by(user_id=test_session.user_id).count() == 0

    ac, mw = create_ac_mw(init=False)
    license_key = license.key
    dlg = mw.accountDialog
    # licenseImported = util.Condition(dlg.qml.rootObject().licenseImported, name='test_import_license.licenseImported')

    ac._pre_event_loop(mw)

    mw.ui.actionShow_Account.trigger()
    assert mw.accountDialog.isShown() == True
    dlg.mouseClick("licenseListPurchaseButton")
    assert dlg.itemProp("slideView", "currentIndex") == 1

    qtbot.clickOkAfter(
        lambda: qtbot.clickOkAfter(
            lambda: dlg.keyClicks(
                "addLicenseKeyField", license_key, returnToFinish=True
            )
        ),
        contains=AppController.S_UPGRADED_TO_PRO_LICENSE,
    )

    # qtbot.clickOkAfter(lambda: licenseImported.wait())
    assert dlg.itemProp("slideView", "currentIndex") == 2
    assert License.query.filter_by(user_id=test_session.user_id).count() == 1
    assert mw.fileManager.isEnabled() == True
    assert mw.documentView.isEnabled() == True
