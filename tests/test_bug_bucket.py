from pkdiagram import util
from pkdiagram.scene import Scene, EventKind
from pkdiagram.models import TimelineModel


# PRISCILLA_SCENE = {
#     'items': [{
#         'adopted': False,
#         'adoptedEvent': {
#             'dateTime': None,
#             'description': 'Adopted',
#             'dynamicProperties': {},
#             'id': 1526,
#             'includeOnDiagram': False,
#             'location': None,
#             'loggedDateTime': util.Date(2020, 12, 26),
#             'nodal': False,
#             'notes': None,
#             'parentName': None,
#             'tags': [],
#             'uniqueId': 'adopted',
#             'unsure': True
#         },
#         'alias': 'Annabel',
#         'bigFont': False,
#         'birthEvent': {
#             'dateTime': None,
#             'description': 'Birth',
#             'dynamicProperties': {},
#             'id': 1524,
#             'includeOnDiagram': False,
#             'location': None,
#             'loggedDateTime': util.Date(2020, 12, 26),
#             'nodal': False,
#             'notes': None,
#             'parentName': 'Elsie',
#             'tags': [],
#             'uniqueId': 'birth',
#             'unsure': False
#         },
#         'birthName': 'Harder',
#         'childOf': {},
#         'color': None,
#         'deathEvent': {
#             'dateTime': util.Date(2002, 11, 25),
#             'description': 'Death',
#             'dynamicProperties': {},
#             'id': 1525,
#             'location': None,
#             'loggedDateTime': util.Date(2020, 12, 26),
#             'nodal': False,
#             'notes': None,
#             'parentName': None,
#             'tags': [],
#             'uniqueId': 'death',
#             'unsure': False
#         },
#         'deceased': True,
#         'deceasedReason': None,
#         'detailsText': {
#             'id': 1523,
#             'itemPos': QPointF(70.0, -50.0),
#             'loggedDateTime': util.Date(2020, 12, 26),
#             'tags': []
#         },
#         'diagramNotes': None,
#         'events': []
#         'gender': 'female',
#         'hideDetails': True,
#         'id': 1527,
#         'itemOpacity': None,
#         'itemPos': QPointF(2782.64741504785, 7531.047913485266),
#         'kind': 'Person',
#         'lastName': 'Friesen',
#         'loggedDateTime': util.Date(2020, 12, 26),
#         'marriages': [],
#         'middleName': None,
#         'name': 'Elsie',
#         'nickName': None,
#         'notes': None,
#         'primary': False,
#         'showLastName': True,
#         'showMiddleName': True,
#         'showNickName': True,
#         'size': 4,
#         'tags': []
#     }
#     ],
#     'lastItemId': 8026,
# }


PRISCILLA_SCENE = {
    "lastItemId": 8026,
    "version": "1.3.0",
    "items": [
        {
            "id": 1527,
            "deathEvent": {
                "id": 1525,
                "dateTime": util.Date(2002, 11, 25),
                "parentName": None,
                "uniqueId": EventKind.Death.value,
            },
            "deceased": True,
            "kind": "Person",
            "lastName": "Friesen",
            "name": "Elsie",
        }
    ],
}


def test_parentName_not_None():
    scene = Scene()
    scene.read(PRISCILLA_SCENE)
    timelineModel = TimelineModel()
    timelineModel.scene = scene
    timelineModel.items = [scene]
    index = timelineModel.index(0, 5)
    person = scene.people()[0]
    assert index.data(timelineModel.ParentIdRole) == person.id

    # event = Event(person, description='Mine')

    # data2 = {}
    # scene.write(data2)
    # Debug(data2)

    display = index.data()
    assert display
