import pickle
import datetime

import pytest

import vedana
from fdserver.extensions import db
from pkdiagram import util, Scene, AccessRightsModel, Session, HTTPResponse
import pkdiagram

from fdserver.models import Diagram, AccessRight

pytestmark = pytest.mark.component("AccessRightsModel")


@pytest.fixture
def model(flask_qnam, test_session, test_user, test_user_2):
    _model = AccessRightsModel()
    _model.scene = Scene()
    session = Session()
    session.setData(test_session.account_editor_dict())
    _model.setSession(session)

    yield _model

    session.deinit()


def test_read_rows(model, test_session, test_user, test_user_2):
    session = Session()
    session.init(test_session.account_editor_dict(), syncWithServer=False)

    data = pickle.dumps(Scene().data())
    first_diagram = Diagram(
        data=data,
        user_id=test_user.id,
    )
    db.session.add(first_diagram)
    db.session.merge(first_diagram)
    db.session.commit()
    diagram = pkdiagram.Diagram.get(first_diagram.id, session)
    model.setServerDiagram(diagram)
    assert model.rowCount() == 0

    db.session.add_all([test_user, test_user_2, first_diagram])
    first_diagram.grant_access(test_user_2, vedana.ACCESS_READ_WRITE)
    first_diagram.grant_access(test_user, vedana.ACCESS_READ_ONLY)
    db.session.commit()

    diagram = pkdiagram.Diagram.get(first_diagram.id, session)
    model.setServerDiagram(diagram)
    db.session.add_all([test_user, test_user_2, first_diagram])

    assert model.rowCount() == 2
    assert model.index(0, 0).data(model.UsernameRole) == test_user_2.username
    assert model.index(1, 0).data(model.UsernameRole) == test_user.username
    assert model.index(0, 0).data(model.RightRole) == diagram.access_rights[0].right
    assert model.index(1, 0).data(model.RightRole) == diagram.access_rights[1].right


@pytest.mark.usefixtures("blockingRequest_200")
def test_set_right(model, test_user):
    # mocker.patch.object(util, 'blockingRequest')
    diagram = Diagram(
        id=1,
        user_id=test_user.id,
        created_at=datetime.datetime.now(),
        access_rights=[
            AccessRight(id=1, user_id=5, right=vedana.ACCESS_READ_ONLY),
            AccessRight(id=2, user_id=6, right=vedana.ACCESS_READ_WRITE),
        ],
    )
    model.setServerDiagram(diagram)
    assert model.index(0, 0).data(role=model.RightRole) == vedana.ACCESS_READ_ONLY
    assert model.index(1, 0).data(role=model.RightRole) == vedana.ACCESS_READ_WRITE
    assert model.index(2, 0).data(role=model.RightRole) == None

    model.setData(model.index(0, 0), vedana.ACCESS_READ_WRITE, role=model.RightRole)
    model.setData(model.index(1, 0), vedana.ACCESS_READ_ONLY, role=model.RightRole)
    assert model.index(0, 0).data(role=model.RightRole) == vedana.ACCESS_READ_WRITE
    assert model.index(1, 0).data(role=model.RightRole) == vedana.ACCESS_READ_ONLY
    assert model.index(2, 0).data(role=model.RightRole) == None
    assert diagram.access_rights[0].right == vedana.ACCESS_READ_WRITE
    assert diagram.access_rights[1].right == vedana.ACCESS_READ_ONLY


def test_add_right(test_user_2, model):
    diagram = pkdiagram.Diagram(
        id=1, user_id=123, created_at=datetime.datetime.now(), access_rights=[]
    )
    model.setServerDiagram(diagram)
    model.addRight(test_user_2.username)
    db.session.add(test_user_2)
    assert model.index(0, 0).data(role=model.UsernameRole) == test_user_2.username
    assert model.index(0, 0).data(role=model.RightRole) == vedana.ACCESS_READ_ONLY


@pytest.mark.usefixtures("blockingRequest_200")
def test_add_right_not_exist(qtbot, model, test_session, test_user_2):
    model.setServerDiagram(
        Diagram(id=1, user_id=123, created_at=datetime.datetime.now(), access_rights=[])
    )
    qtbot.clickOkAfter(lambda: model.addRight("no@user.com"), text="does not exist")
    assert model.rowCount() == 0


@pytest.mark.usefixtures("blockingRequest_200")
def test_add_right_already_exists(qtbot, model, test_session, test_user, test_user_2):
    test_user.free_diagram.grant_access(test_user_2, vedana.ACCESS_READ_WRITE)
    diagram_json = Diagram.query.get(test_user.free_diagram.id).as_dict()
    diagram = pkdiagram.Diagram.create(diagram_json)
    model.setServerDiagram(diagram)
    qtbot.clickOkAfter(
        lambda: model.addRight(test_user_2.username), text="already exists"
    )
    assert model.rowCount() == 1


@pytest.mark.usefixtures("blockingRequest_200")
def test_delete_right(model, test_user, test_user_2):
    test_user.free_diagram.grant_access(test_user_2, vedana.ACCESS_READ_WRITE)
    free_diagram = Diagram.query.get(test_user.free_diagram_id)
    diagram = pkdiagram.Diagram.create(free_diagram.as_dict())
    model.setServerDiagram(diagram)
    model.deleteRight(0)
    assert model.rowCount() == 0
