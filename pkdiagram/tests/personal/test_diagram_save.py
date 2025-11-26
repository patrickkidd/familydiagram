"""
Tests for Diagram.save() with personal app endpoint (/personal/diagrams).

Uses flask_qnam fixture to test Qt <-> Flask HTTP communication.

NOTE: Optimistic locking conflict handling is tested in backend tests
(btcopilot/tests/personal/test_diagrams.py::test_diagrams_optimistic_locking_conflict).
Testing it here with flask_qnam has issues with 409 response body preservation.
"""
import pickle
from datetime import datetime

import pytest

from pkdiagram.server_types import Diagram as FEDiagram, Server
from btcopilot.pro.models import Diagram as DBDiagram, User
from btcopilot.schema import DiagramData, PDP, Person, asdict
from btcopilot.extensions import db


def test_diagram_save_json_format(test_user, flask_app):
    """Test that diagram.save() works with JSON format (personal app endpoint)."""

    # Create backend diagram with PDP data
    initial_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="TestPerson")]))

    with flask_app.app_context():
        db_diagram = DBDiagram(
            user_id=test_user.id,
            data=pickle.dumps(asdict(initial_data)),
        )
        db.session.add(db_diagram)
        db.session.commit()
        diagram_id = db_diagram.id
        initial_version = db_diagram.version

    # Create User proxy for frontend (has secret encoded)
    from pkdiagram.server_types import User as FEUser
    fe_user = FEUser(
        id=test_user.id,
        username=test_user.username,
        first_name="Test",
        last_name="User",
        roles=[test_user.roles],
        secret=test_user.secret.encode("utf-8"),  # Frontend expects bytes
    )

    # Create frontend diagram instance
    fe_diagram = FEDiagram(
        id=diagram_id,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_data)),
        version=initial_version,
    )

    # Create server instance with user
    server = Server(user=fe_user)

    # Test successful save
    def applyChange(diagramData: DiagramData):
        diagramData.last_id = 999

    def stillValidAfterRefresh(diagramData: DiagramData):
        return True

    success = fe_diagram.save(server, applyChange, stillValidAfterRefresh, useJson=True)

    assert success is True
    assert fe_diagram.version == initial_version + 1
    assert fe_diagram.getDiagramData().last_id == 999

    server.deinit()
