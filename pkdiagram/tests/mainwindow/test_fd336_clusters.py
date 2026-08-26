"""FD-336 / F-007: cluster detection persists on a Pro server case.

C2: Learn in Pro's case drawer is the Personal Learn tab, so a detection it
runs has to land on the row like every other write. Left in the local cache
only, the paid detection is re-run on every reopen and no other client ever
sees it.
"""

import json
import pickle

import pytest

from btcopilot.extensions import db
from btcopilot.pro.models import Diagram
from btcopilot.schema import EventKind

from pkdiagram import util
from pkdiagram.pyqt import QDate, QDateTime
from pkdiagram.scene import Event, Person


pytestmark = [
    pytest.mark.component("MainWindow"),
    pytest.mark.depends_on("DocumentView"),
]


CACHE_KEY = "cluster-cache-key"


@pytest.fixture
def ownedCase(test_activation, test_user, test_user_diagrams, create_ac_mw):
    for diagram in test_user_diagrams:
        db.session.add(diagram)
    diagram_id = next(x.id for x in test_user_diagrams if x.user_id == test_user.id)
    db.session.commit()

    ac, mw = create_ac_mw()
    util.wait(mw.serverFileModel.updateFinished)
    diagram = mw.serverFileModel.findDiagram(diagram_id)
    mw.onServerFileClicked(mw.serverFileModel.pathForDiagram(diagram), diagram)
    return mw, diagram_id


def _row(diagram_id) -> Diagram:
    """The app writes over its own request session, so this session's copy of
    the row is stale until expired."""
    db.session.expire_all()
    return Diagram.query.get(diagram_id)


def _datedEvent(scene) -> Event:
    """A dated event, added without undo so the document stays clean: a
    detection on saved work is the case under test."""
    person = Person(name="Connie")
    scene.addItem(person, undo=False)
    event = Event(
        kind=EventKind.Shift, person=person, dateTime=QDateTime(QDate(2024, 1, 15))
    )
    scene.addItem(event, undo=False)
    return event


def test_detected_clusters_land_on_the_row(ownedCase, server_response):
    mw, diagram_id = ownedCase
    event = _datedEvent(mw.scene)
    clusters = [
        {
            "id": "c1",
            "title": "The move",
            "startDate": "2024-01-15",
            "eventIds": [event.id],
        }
    ]
    version = _row(diagram_id).version
    assert mw.scene.stack().isClean()

    with server_response(
        f"/personal/diagrams/{diagram_id}/clusters",
        body=json.dumps({"clusters": clusters, "cacheKey": CACHE_KEY}),
    ):
        mw.proPersonal().clusterModel.detect()
        assert util.waitForCondition(
            lambda: mw.proPersonal().clusterModel.hasClusters, maxMS=5000
        )

    row = _row(diagram_id)
    stored = pickle.loads(row.data)
    assert stored["clusters"] == mw.proPersonal().clusterModel.clusters
    assert stored["clusterCacheKey"] == CACHE_KEY
    assert row.version == version + 1

    assert mw.scene.stack().isClean()
