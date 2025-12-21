import contextlib
import logging
import datetime

import pytest
from mock import patch
import flask_mail

import btcopilot
from pkdiagram.pyqt import QApplication, QMessageBox
from pkdiagram import util
from pkdiagram.views import AccountDialog
from pkdiagram.pyqt import QMessageBox

from btcopilot.extensions import mail
from btcopilot.extensions import db
from btcopilot.pro.models import License, User, Policy

# def _logout(dlg, qtbot):
#     assert dlg.isShown() == True

#     qtbot.clickYesAfter(lambda: dlg.mouseClick('logoutButton'))
#     sessionDataChanged = util.Condition(dlg.qml.rootObject().sessionDataChanged)
#     assert sessionDataChanged.wait() == True
#     assert dlg.isLoggedIn() == False


_log = logging.getLogger(__name__)

# pytest.skip("AccountDialog tests are broken in CI/CD", allow_module_level=True)


@pytest.fixture
def create_dlg(qtbot, flask_qnam, request, qmlEngine):

    created = []

    def _create_dlg(session=True):
        dlg = AccountDialog(qmlEngine)
        # dlg.sceneModel.scene = Scene()
        dlg.init()
        dlg.show()
        qtbot.addWidget(dlg)
        qtbot.waitActive(dlg)

        if session:
            test_session = request.getfixturevalue("test_session")
            db.session.add(test_session)
            qmlEngine.session.init(sessionData=test_session.account_editor_dict())
            assert qmlEngine.session.isLoggedIn() == True

        created.append(dlg)
        return dlg

    yield _create_dlg

    QApplication.processEvents()
    for dlg in created:
        dlg.deinit()
        dlg.hide()


def test_init_not_logged_in(create_dlg, qmlEngine):
    dlg = create_dlg(session=False)
    qmlEngine.session.init()
    assert dlg.itemProp("slideView", "currentIndex") == 0


def test_init_logged_in(create_dlg, qmlEngine):
    dlg = create_dlg()
    qmlEngine.session.init()
    assert dlg.itemProp("slideView", "currentIndex") == 1


def test_saved_session_no_licenses(flask_app, test_session, create_dlg):
    flask_app.config["STRIPE_ENABLED"] = False
    dlg = create_dlg()
    assert len(test_session.user.licenses) == 0
    assert dlg.itemProp("slideView", "currentIndex") == 1
    assert test_session.user.username in dlg.itemProp("accountUsername", "text")


def test_saved_session_one_license(flask_app, test_session, test_license, create_dlg):
    flask_app.config["STRIPE_ENABLED"] = False
    dlg = create_dlg()
    assert len(test_session.user.licenses) == 1
    assert dlg.itemProp("slideView", "currentIndex") == 2
    assert test_session.user.username in dlg.itemProp("accountUsername", "text")


@pytest.mark.real_passwords
def test_register(flask_app, qtbot, create_dlg, qmlEngine):

    # 1. Enter email

    flask_app.config["STRIPE_ENABLED"] = False
    ARGS = {
        "username": "patrickkidd@gmail.com",
        "password": "bleh",
        "first_name": "Unit",
        "last_name": "Tester",
    }

    dlg = create_dlg(session=False)
    authStateChanged = util.Condition(dlg.qml.rootObject().authStateChanged)
    sentResetEmail = util.Condition(dlg.qml.rootObject().sentResetEmail)
    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("uuid.uuid4", return_value="a568655e-072e-459c-b352-871a559426e6")
        )
        send = stack.enter_context(
            patch.object(flask_mail.Mail, "send", wraps=mail.send)
        )
        dlg.keyClicks("authUsernameField", ARGS["username"], returnToFinish=False)

        question = stack.enter_context(
            patch("PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes)
        )
        information = stack.enter_context(
            patch(
                "PyQt5.QtWidgets.QMessageBox.information", return_value=QMessageBox.Yes
            )
        )
        dlg.mouseClick("authSubmitButton")
        util.waitALittle(100)
        assert "No account exists for " in question.call_args[0][2]
        assert "An email was sent with " in information.call_args[0][2]

    _log.info("sentResetEmail.wait()")
    assert dlg.itemProp("authForm", "state") == "code"
    assert send.call_count == 1

    # 2. Enter emailed code

    message = send.call_args[0][0]
    authStateChanged.reset()
    dlg.keyClicks("authCodeField", message.__code, returnToFinish=False)
    dlg.mouseClick("authSubmitButton")
    assert authStateChanged.wait() == True
    assert dlg.itemProp("authForm", "state") == "update"

    # 3. Enter account details + auto log in

    authStateChanged.reset()
    dlg.keyClicks("authFirstNameField", ARGS["first_name"], returnToFinish=False)
    dlg.keyClicks("authLastNameField", ARGS["last_name"], returnToFinish=False)
    dlg.keyClicks("authNewPasswordField", ARGS["password"], returnToFinish=False)
    dlg.keyClicks("authConfirmPasswordField", ARGS["password"], returnToFinish=False)
    dlg.mouseClick("authSubmitButton")
    assert util.wait(qmlEngine.session.changed)
    # assert dlg.itemProp('authForm', 'state') == 'email'  # Doesn't really make sense any more?
    assert dlg.itemProp("slideView", "currentIndex") == 1
    assert qmlEngine.session.isLoggedIn() == True
    # Refresh the session to see changes made by the HTTP request
    db.session.expire_all()
    user = User.query.filter_by(username=ARGS["username"]).first()
    assert user != None
    assert user.check_password(ARGS["password"])
    assert user.status == "confirmed"


@pytest.mark.real_passwords
def test_register_pending(flask_app, test_user, qtbot, create_dlg, qmlEngine):
    flask_app.config["STRIPE_ENABLED"] = False
    test_user.status = "pending"
    db.session.commit()

    ARGS = {
        "username": test_user.username,
        "password": "bleh",
        "first_name": "Unit",
        "last_name": "Tester",
    }
    dlg = create_dlg(session=False)
    authStateChanged = util.Condition(dlg.qml.rootObject().authStateChanged)
    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("uuid.uuid4", return_value="a568655e-072e-459c-b352-871a559426e6")
        )
        send = stack.enter_context(
            patch.object(flask_mail.Mail, "send", wraps=mail.send)
        )
        dlg.keyClicks("authUsernameField", ARGS["username"], returnToFinish=False)
        dlg.mouseClick("authSubmitButton")
        assert authStateChanged.wait() == True
        assert dlg.itemProp("authForm", "state") == "code"

        sentResetEmail = util.Condition(dlg.qml.rootObject().sentResetEmail)
        qtbot.clickOkAfter(lambda: dlg.mouseClick("authResendCodeButton"))
        assert sentResetEmail.wait() == True
        assert send.call_count == 1

    # 2. Enter emailed code

    message = send.call_args[0][0]
    authStateChanged.reset()
    dlg.keyClicks("authCodeField", message.__code, returnToFinish=False)
    dlg.mouseClick("authSubmitButton")
    assert authStateChanged.wait() == True
    assert dlg.itemProp("authForm", "state") == "update"

    # 3. Enter account details + auto log in

    authStateChanged.reset()
    dlg.keyClicks("authFirstNameField", ARGS["first_name"], returnToFinish=False)
    dlg.keyClicks("authLastNameField", ARGS["last_name"], returnToFinish=False)
    dlg.keyClicks("authNewPasswordField", ARGS["password"], returnToFinish=False)
    dlg.keyClicks("authConfirmPasswordField", ARGS["password"], returnToFinish=False)
    dlg.mouseClick("authSubmitButton")
    assert util.wait(qmlEngine.session.changed)
    # assert dlg.itemProp('authForm', 'state') == 'email' # Doesn't make sense any more?
    assert dlg.itemProp("slideView", "currentIndex") == 1
    assert qmlEngine.session.isLoggedIn() == True
    # Refresh the session to see changes made by the HTTP request
    db.session.expire_all()
    user = User.query.filter_by(username=ARGS["username"]).first()
    assert user != None
    assert user.check_password(ARGS["password"])
    assert user.status == "confirmed"


@pytest.mark.real_passwords
def test_reset_password(flask_app, test_user, qtbot, create_dlg, qmlEngine):
    flask_app.config["STRIPE_ENABLED"] = False

    ARGS = {
        "username": test_user.username,
        "password": "some new password",
        "first_name": "Unit",
        "last_name": "Tester",
    }
    dlg = create_dlg(session=False)
    authStateChanged = util.Condition(dlg.qml.rootObject().authStateChanged)

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("uuid.uuid4", return_value="a568655e-072e-459c-b352-871a559426e6")
        )
        send = stack.enter_context(
            patch.object(flask_mail.Mail, "send", wraps=mail.send)
        )
        dlg.keyClicks("authUsernameField", ARGS["username"], returnToFinish=False)
        dlg.mouseClick("authSubmitButton")
        assert authStateChanged.wait(4000) == True
        assert dlg.itemProp("authForm", "state") == "password"

        sentResetEmail = util.Condition(dlg.qml.rootObject().sentResetEmail)
        dlg.keyClicks("authUsernameField", ARGS["username"], returnToFinish=False)
        dlg.mouseClick("authResetPasswordLink")
        qtbot.clickOkAfter(
            lambda: sentResetEmail.wait(), text="An email was sent with "
        )
        assert dlg.itemProp("authForm", "state") == "code"
        assert send.call_count == 1

    message = send.call_args[0][0]
    authStateChanged.reset()
    dlg.keyClicks("authCodeField", message.__code, returnToFinish=False)
    dlg.mouseClick("authSubmitButton")
    assert authStateChanged.wait() == True
    assert dlg.itemProp("authForm", "state") == "update"
    assert dlg.itemProp("authFirstNameField", "text") == test_user.first_name
    assert dlg.itemProp("authLastNameField", "text") == test_user.last_name

    authStateChanged.reset()
    dlg.keyClicks("authFirstNameField", ARGS["first_name"], returnToFinish=False)
    dlg.keyClicks("authLastNameField", ARGS["last_name"], returnToFinish=False)
    dlg.keyClicks("authNewPasswordField", ARGS["password"], returnToFinish=False)
    dlg.keyClicks("authConfirmPasswordField", ARGS["password"], returnToFinish=False)
    dlg.mouseClick("authSubmitButton")
    assert util.wait(qmlEngine.session.changed)
    # assert dlg.itemProp('authForm', 'state') == 'email' # Doesn't make sense any more?
    assert dlg.itemProp("slideView", "currentIndex") == 1
    assert qmlEngine.session.isLoggedIn() == True
    # Refresh the session to see changes made by the HTTP request
    db.session.expire_all()
    user = User.query.filter_by(username=ARGS["username"]).first()
    assert user != None
    assert user.check_password(ARGS["password"])
    assert user.status == "confirmed"


def test_edit_user(flask_app, test_user, create_dlg):
    flask_app.config["STRIPE_ENABLED"] = False
    was_first_name = test_user.first_name
    was_last_name = test_user.last_name
    ARGS = {
        "username": test_user.username,
        "first_name": "Someother",
        "last_name": "Name",
    }

    dlg = create_dlg()
    dlg.mouseClick("editAccountButton")
    assert dlg.itemProp("slideView", "currentIndex") == 0
    assert dlg.itemProp("authForm", "state") == "update"

    userUpdated = util.Condition(dlg.qml.rootObject().userUpdated)
    dlg.keyClicks("authFirstNameField", ARGS["first_name"], returnToFinish=False)
    dlg.keyClicks("authLastNameField", ARGS["last_name"], returnToFinish=False)
    dlg.mouseClick("authSubmitButton")
    assert userUpdated.wait(4000) == True
    # assert dlg.itemProp('authForm', 'state') == 'email' # Doesn't make sense any more?
    assert dlg.itemProp("slideView", "currentIndex") == 2
    db.session.expire_all()
    user = User.query.filter_by(username=ARGS["username"]).first()
    assert user.first_name == ARGS["first_name"]
    assert user.last_name == ARGS["last_name"]


@pytest.mark.parametrize("ccv", ["4242", "012"])
def test_purchase(test_session, qtbot, create_dlg, qmlEngine, ccv):
    p1 = Policy(
        code=btcopilot.LICENSE_PROFESSIONAL_MONTHLY,
        product=btcopilot.LICENSE_PROFESSIONAL,
        name="Professional Monthly",
        amount=100,
        public=True,
        active=True,
    )
    p2 = Policy(
        code=btcopilot.LICENSE_PROFESSIONAL_ANNUAL,
        product=btcopilot.LICENSE_PROFESSIONAL,
        name="Professioal Annual",
        amount=100,
        public=True,
        active=True,
    )
    db.session.add(p1)
    db.session.add(p2)
    db.session.commit()

    dlg = create_dlg()
    dlg.mouseClick("licenseListPurchaseButton")
    assert dlg.itemProp("slideView", "currentIndex") == 1

    hidden = util.Condition(dlg.hidden)
    purchasedLicense = util.Condition(dlg.qml.rootObject().purchasedLicense)
    loggedIn = util.Condition(qmlEngine.session.changed)
    purchaseButton = dlg.rootProp("purchaseButtons").toVariant()[0]
    dlg.mouseClickItem(purchaseButton)
    assert dlg.itemProp("authForm", "visible")
    assert License.query.filter_by(user=test_session.user).count() == 0

    dlg.keyClicks("ccNumField", "4242424242424242")
    dlg.keyClicks("ccExpMonthField", "12")
    dlg.keyClicks("ccExpYearField", str(datetime.datetime.now().year + 1))
    dlg.keyClicks("ccCVCField", ccv)
    # dlg.keyClicks('ccZipField', '20016')
    qtbot.clickYesAfter(lambda: dlg.mouseClick("purchaseSubmitButton"))
    qtbot.clickOkAfter(lambda: purchasedLicense.assertWait(maxMS=4000))
    assert License.query.filter_by(user=test_session.user).count() == 1
    assert hidden.wait() == True
    assert dlg.itemProp("ccNumField", "text") == ""
    assert dlg.itemProp("ccExpMonthField", "text") == ""
    assert dlg.itemProp("ccExpYearField", "text") == ""
    assert dlg.itemProp("ccCVCField", "text") == ""


# @pytest.mark.skip("Must refactor")
# def test_cancel(qtbot, dlg, test_session, test_license):
#     _login(dlg, test_session)
#     #
#     cancelButton = None
#     for item in dlg.rootProp("purchaseButtons").toVariant():
#         if "Cancel" in item.property("text"):
#             cancelButton = item
#     qtbot.clickYesAfter(lambda: dlg.mouseClickItem(cancelButton))
#     db.session.merge(test_license)
#     assert test_license.active == False


def test_freeVersionCTA_visible_free_license(create_dlg, qmlEngine):
    dlg = create_dlg()
    userLicenses = dlg.rootProp("userLicenses").toVariant()
    hasAnyPaidFeature = qmlEngine.session.hasAnyPaidFeature()
    assert dlg.itemProp("freeVersionCTA", "visible") == True


def test_freeVersionCTA_visible_pro_license(test_activation, create_dlg, qmlEngine):
    dlg = create_dlg()
    userLicenses = dlg.rootProp("userLicenses").toVariant()
    hasAnyPaidFeature = qmlEngine.session.hasAnyPaidFeature()
    assert dlg.itemProp("freeVersionCTA", "visible") == False


def test_freeVersionCTA_visible_with_licenses(create_dlg):
    dlg = create_dlg()
    assert dlg.itemProp("freeVersionCTA", "visible") == True


def test_freeVersionCTA_visible_with_licenses_no_activation(test_license, create_dlg):
    dlg = create_dlg()
    assert dlg.itemProp("freeVersionCTA", "visible") == False
