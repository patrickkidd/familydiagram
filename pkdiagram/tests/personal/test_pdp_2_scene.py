import json
import pickle
from datetime import datetime
from unittest.mock import patch, MagicMock

from btcopilot.schema import (
    DiagramData,
    PDP,
    Person,
    Event,
    EventKind,
    PairBond,
    asdict,
)
from pkdiagram.personal import PersonalAppController
from pkdiagram.personal.models import (
    Diagram,
)
from pkdiagram.scene import Scene


def _createBlockingRequestMock(diagram):
    def blockingRequest(verb, endpoint, data=None, bdata=None, headers=None, **kwargs):
        response = MagicMock()
        response.status_code = 200
        response.body = json.dumps({"version": diagram.version + 1}).encode("utf-8")
        return response

    return blockingRequest


def test_accept_person_updates_scene(test_user, personalApp: PersonalAppController):
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(
            asdict(
                DiagramData(
                    pdp=PDP(people=[Person(id=-1, name="NewPerson")]),
                    lastItemId=10,
                )
            )
        ),
    )

    scene = Scene()
    personalApp.scene = scene

    server = MagicMock()
    server.blockingRequest = _createBlockingRequestMock(personalApp._diagram)

    with patch.object(personalApp.session, "server", return_value=server):
        result = personalApp._doAcceptPDPItem(-1)

    assert result is True
    assert len(scene.people()) == 1
    assert scene.people()[0].name() == "NewPerson"


def test_accept_event_updates_scene(test_user, personalApp: PersonalAppController):
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(
            asdict(
                DiagramData(
                    pdp=PDP(
                        people=[Person(id=-1, name="EventPerson")],
                        events=[
                            Event(
                                id=-2,
                                kind=EventKind.Shift,
                                person=-1,
                                description="Something happened",
                            )
                        ],
                    ),
                    lastItemId=10,
                )
            )
        ),
    )

    scene = Scene()
    personalApp.scene = scene

    server = MagicMock()
    server.blockingRequest = _createBlockingRequestMock(personalApp._diagram)

    with patch.object(personalApp.session, "server", return_value=server):
        result = personalApp._doAcceptPDPItem(-2)

    assert result is True
    assert len(scene.people()) == 1
    assert len(scene.events()) == 1
    assert scene.events()[0].description() == "Something happened"


def test_accept_married_event_creates_marriage_in_scene(
    test_user, personalApp: PersonalAppController
):
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(
            asdict(
                DiagramData(
                    pdp=PDP(
                        people=[
                            Person(id=-1, name="Tom"),
                            Person(id=-2, name="Susan"),
                        ],
                        pair_bonds=[
                            PairBond(id=-10, person_a=-1, person_b=-2),
                        ],
                        events=[
                            Event(
                                id=-20,
                                kind=EventKind.Married,
                                person=-1,
                                spouse=-2,
                                description="Wedding",
                            ),
                        ],
                    ),
                    lastItemId=10,
                )
            )
        ),
    )

    scene = Scene()
    personalApp.scene = scene

    server = MagicMock()
    server.blockingRequest = _createBlockingRequestMock(personalApp._diagram)

    with patch.object(personalApp.session, "server", return_value=server):
        result = personalApp._doAcceptPDPItem(-20)

    assert result is True
    assert len(scene.people()) == 2
    assert len(scene.marriages()) == 1
    assert len(scene.events()) == 1

    # Verify marriage connects the right people
    marriage = scene.marriages()[0]
    names = {marriage.personA().name(), marriage.personB().name()}
    assert names == {"Tom", "Susan"}


def test_accept_birth_event_creates_child_with_parents(
    test_user, personalApp: PersonalAppController
):
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(
            asdict(
                DiagramData(
                    pdp=PDP(
                        people=[
                            Person(id=-1, name="Dad"),
                            Person(id=-2, name="Mom"),
                            Person(id=-3, name="Child", parents=-10),
                        ],
                        pair_bonds=[
                            PairBond(id=-10, person_a=-1, person_b=-2),
                        ],
                        events=[
                            Event(
                                id=-20,
                                kind=EventKind.Birth,
                                person=-1,
                                spouse=-2,
                                child=-3,
                                description="Child born",
                            ),
                        ],
                    ),
                    lastItemId=10,
                )
            )
        ),
    )

    scene = Scene()
    personalApp.scene = scene

    server = MagicMock()
    server.blockingRequest = _createBlockingRequestMock(personalApp._diagram)

    with patch.object(personalApp.session, "server", return_value=server):
        result = personalApp._doAcceptPDPItem(-20)

    assert result is True
    assert len(scene.people()) == 3
    assert len(scene.marriages()) == 1

    child = next(p for p in scene.people() if p.name() == "Child")
    marriage = scene.marriages()[0]
    assert child.parents() == marriage


def test_accept_pdp_preserves_existing_scene_items(
    test_user, personalApp: PersonalAppController
):
    from pkdiagram.scene import Person as ScenePerson

    scene = Scene()
    existing_person = scene.addItem(ScenePerson(name="ExistingPerson"))

    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(
            asdict(
                DiagramData(
                    people=[{"id": existing_person.id, "name": "ExistingPerson"}],
                    pdp=PDP(people=[Person(id=-1, name="NewPerson")]),
                    lastItemId=existing_person.id,
                )
            )
        ),
    )
    personalApp.scene = scene

    server = MagicMock()
    server.blockingRequest = _createBlockingRequestMock(personalApp._diagram)

    with patch.object(personalApp.session, "server", return_value=server):
        result = personalApp._doAcceptPDPItem(-1)

    assert result is True
    assert len(scene.people()) == 2
    names = {p.name() for p in scene.people()}
    assert names == {"ExistingPerson", "NewPerson"}


def test_accept_multiple_pdp_items_sequentially(
    test_user, personalApp: PersonalAppController
):
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(
            asdict(
                DiagramData(
                    pdp=PDP(
                        people=[
                            Person(id=-1, name="Person1"),
                            Person(id=-2, name="Person2"),
                            Person(id=-3, name="Person3"),
                        ],
                    ),
                    lastItemId=10,
                )
            )
        ),
    )

    scene = Scene()
    personalApp.scene = scene

    server = MagicMock()
    server.blockingRequest = _createBlockingRequestMock(personalApp._diagram)

    with patch.object(personalApp.session, "server", return_value=server):
        personalApp._doAcceptPDPItem(-1)
        assert len(scene.people()) == 1

        personalApp._doAcceptPDPItem(-2)
        assert len(scene.people()) == 2

        personalApp._doAcceptPDPItem(-3)
        assert len(scene.people()) == 3

    names = {p.name() for p in scene.people()}
    assert names == {"Person1", "Person2", "Person3"}


def test_save_reload_after_marriage_commit_preserves_marriages(
    test_user, personalApp: PersonalAppController
):
    """Verify that marriages are correctly saved/loaded after PDP commit.

    Regression test for: "None in self.marriages" warning after save/reload.
    """
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(
            asdict(
                DiagramData(
                    pdp=PDP(
                        people=[
                            Person(id=-1, name="Tom"),
                            Person(id=-2, name="Susan"),
                        ],
                        pair_bonds=[
                            PairBond(id=-10, person_a=-1, person_b=-2),
                        ],
                        events=[
                            Event(
                                id=-20,
                                kind=EventKind.Married,
                                person=-1,
                                spouse=-2,
                            ),
                        ],
                    ),
                    lastItemId=10,
                )
            )
        ),
    )

    scene = Scene()
    personalApp.scene = scene

    server = MagicMock()
    server.blockingRequest = _createBlockingRequestMock(personalApp._diagram)

    with patch.object(personalApp.session, "server", return_value=server):
        result = personalApp._doAcceptPDPItem(-20)

    assert result is True
    assert len(scene.marriages()) == 1

    # Verify marriages are set on people
    tom = next(p for p in scene.people() if p.name() == "Tom")
    susan = next(p for p in scene.people() if p.name() == "Susan")
    assert len(tom.marriages) == 1
    assert len(susan.marriages) == 1

    # Save scene to data
    data = scene.data()

    # Verify the saved data has marriage IDs in person chunks
    for person_chunk in data["people"]:
        assert "marriages" in person_chunk
        assert len(person_chunk["marriages"]) == 1

    # Verify pair_bonds has the marriage
    assert len(data["pair_bonds"]) == 1
    marriage_id = data["pair_bonds"][0]["id"]

    # Verify person chunks reference the correct marriage ID
    for person_chunk in data["people"]:
        assert person_chunk["marriages"][0] == marriage_id

    # Reload into new scene
    scene2 = Scene()
    scene2.read(data)

    # Verify no None in marriages
    for person in scene2.people():
        assert None not in person.marriages
        assert len(person.marriages) == 1

    assert len(scene2.marriages()) == 1
