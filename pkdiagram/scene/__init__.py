def eventKindMenuLabel(kind: "EventKind") -> str:
    """Return the menu label for an EventKind."""
    labels = {
        EventKind.Bonded: "Bonded",
        EventKind.Married: "Married",
        EventKind.Separated: "Separated",
        EventKind.Divorced: "Divorced",
        EventKind.Moved: "Moved",
        EventKind.Birth: "Birth",
        EventKind.Adopted: "Adopted",
        EventKind.Death: "Death",
        EventKind.Shift: "Shift",
    }
    return labels[kind]


def relationshipKindMenuLabel(kind: "RelationshipKind") -> str:
    labels = {
        # self.Fusion: "Fusion",
        RelationshipKind.Conflict: "Conflict",
        RelationshipKind.Distance: "Distance",
        RelationshipKind.Overfunctioning: "Overfunctioning",
        RelationshipKind.Underfunctioning: "Underfunctioning",
        RelationshipKind.Projection: "Projection",
        RelationshipKind.DefinedSelf: "Defined Self",
        RelationshipKind.Toward: "Toward",
        RelationshipKind.Away: "Away",
        RelationshipKind.Inside: "Triangle to inside",
        RelationshipKind.Outside: "Triangle to outside",
        RelationshipKind.Cutoff: "Cutoff",
    }
    return labels[kind]


from .itemmode import ItemMode
from .property import Property
from .itemgarbage import ItemGarbage
from .variablesdatabase import VariablesDatabase
from .itemanimationhelper import ItemAnimationHelper
from .emotionalunit import EmotionalUnit
from .item import Item
from .event import Event
from .pathitem import PathItem
from .itemdetails import ItemDetails
from .layeritem import LayerItem
from .layer import Layer
from .childof import ChildOf
from .multiplebirth import MultipleBirth
from .person import Person
from .marriage import Marriage
from .emotions import Emotion
from .pencilstroke import PencilStroke
from .callout import Callout
from .scene import Scene

from . import commands
