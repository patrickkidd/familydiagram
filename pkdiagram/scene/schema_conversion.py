"""
Conversion utilities between Scene items and shared schemas.

This module provides functions to convert between:
- familydiagram Scene items (with PyQt5 types)
- btcopilot shared schemas (with JSON-compatible types)
"""

import sys
import os

# Add btcopilot to path if not already there
btcopilot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../btcopilot'))
if btcopilot_path not in sys.path:
    sys.path.insert(0, btcopilot_path)

from btcopilot.shared.schema import (
    Person as PersonSchema,
    Event as EventSchema,
    Marriage as MarriageSchema,
    Emotion as EmotionSchema,
    Layer as LayerSchema,
    PencilStroke as PencilStrokeSchema,
    Callout as CalloutSchema,
)
from btcopilot.shared.schema.types import (
    qdatetime_to_iso,
    iso_to_qdatetime,
    qcolor_to_hex,
    hex_to_qcolor,
    qpointf_to_tuple,
    tuple_to_qpointf,
)

from pkdiagram.pyqt import QDateTime
from pkdiagram import util


def person_to_schema(person) -> PersonSchema:
    """
    Convert a Scene Person to a PersonSchema.

    Args:
        person: Scene Person object

    Returns:
        PersonSchema instance with JSON-compatible types
    """
    return PersonSchema(
        id=person.id,
        name=person.name() or "",
        middle_name=person.middleName() or "",
        last_name=person.lastName() or "",
        nick_name=person.nickName() or "",
        birth_name=person.birthName() or "",
        alias=person.alias() or "",
        gender=person.gender() or "male",
        primary=person.primary() or False,
        deceased=person.deceased() or False,
        deceased_reason=person.deceasedReason() or "",
        adopted=person.adopted() or False,
        show_last_name=person.showLastName() if person.showLastName() is not None else True,
        show_middle_name=person.showMiddleName() if person.showMiddleName() is not None else True,
        show_nick_name=person.showNickName() if person.showNickName() is not None else True,
        diagram_notes=person.diagramNotes() or "",
        notes=person.notes() or "",
        tags=person.tags() or [],
        logged_date_time=qdatetime_to_iso(person.loggedDateTime()),
    )


def schema_to_person(schema: PersonSchema, scene):
    """
    Create a Scene Person from a PersonSchema.

    Args:
        schema: PersonSchema instance
        scene: Scene to add the person to

    Returns:
        Scene Person object
    """
    from pkdiagram.scene import Person

    person = Person(
        id=schema.id,
        name=schema.name,
        middleName=schema.middle_name,
        lastName=schema.last_name,
        nickName=schema.nick_name,
        birthName=schema.birth_name,
        alias=schema.alias,
        gender=schema.gender,
        primary=schema.primary,
        deceased=schema.deceased,
        deceasedReason=schema.deceased_reason,
        adopted=schema.adopted,
        showLastName=schema.show_last_name,
        showMiddleName=schema.show_middle_name,
        showNickName=schema.show_nick_name,
        diagramNotes=schema.diagram_notes,
        notes=schema.notes,
        tags=schema.tags,
        loggedDateTime=iso_to_qdatetime(schema.logged_date_time),
    )
    return person


def event_to_schema(event) -> EventSchema:
    """
    Convert a Scene Event to an EventSchema.

    Args:
        event: Scene Event object

    Returns:
        EventSchema instance with JSON-compatible types
    """
    # Get SARF variables from event's dynamic properties
    symptom = event.prop(util.ATTR_SYMPTOM).get() if event.prop(util.ATTR_SYMPTOM) else None
    anxiety = event.prop(util.ATTR_ANXIETY).get() if event.prop(util.ATTR_ANXIETY) else None
    relationship = event.prop(util.ATTR_RELATIONSHIP).get() if event.prop(util.ATTR_RELATIONSHIP) else None
    functioning = event.prop(util.ATTR_FUNCTIONING).get() if event.prop(util.ATTR_FUNCTIONING) else None

    return EventSchema(
        id=event.id,
        kind=event.kind() if isinstance(event.kind(), str) else event.kind().value,
        date_time=qdatetime_to_iso(event.dateTime()),
        end_date_time=qdatetime_to_iso(event.endDateTime()),
        unsure=event.unsure() if event.unsure() is not None else True,
        description=event.description() or "",
        nodal=event.nodal() or False,
        notes=event.notes() or "",
        color=event.color(),
        location=event.location() or "",
        include_on_diagram=event.includeOnDiagram(),
        person_id=event.person(),
        spouse_id=event.spouse(),
        child_id=event.child(),
        symptom=symptom,
        anxiety=anxiety,
        relationship=relationship,
        functioning=functioning,
        relationship_targets=event.relationshipTargets() or [],
        relationship_triangles=event.relationshipTriangles() or [],
        relationship_intensity=event.relationshipIntensity() or 3,
        tags=event.tags() or [],
        logged_date_time=qdatetime_to_iso(event.loggedDateTime()),
    )


def schema_to_event(schema: EventSchema, scene):
    """
    Create a Scene Event from an EventSchema.

    Args:
        schema: EventSchema instance
        scene: Scene to add the event to

    Returns:
        Scene Event object
    """
    from pkdiagram.scene import Event, EventKind

    # Get the EventKind enum
    kind = EventKind(schema.kind)

    event = Event(
        kind=kind,
        person=None,  # Will be set by ID later
        id=schema.id,
        dateTime=iso_to_qdatetime(schema.date_time),
        endDateTime=iso_to_qdatetime(schema.end_date_time),
        unsure=schema.unsure,
        description=schema.description,
        nodal=schema.nodal,
        notes=schema.notes,
        color=schema.color,
        location=schema.location,
        includeOnDiagram=schema.include_on_diagram,
        person=schema.person_id,
        spouse=schema.spouse_id,
        child=schema.child_id,
        relationshipTargets=schema.relationship_targets,
        relationshipTriangles=schema.relationship_triangles,
        relationshipIntensity=schema.relationship_intensity,
        tags=schema.tags,
        loggedDateTime=iso_to_qdatetime(schema.logged_date_time),
    )

    # Set SARF variables if present
    if schema.symptom and event.prop(util.ATTR_SYMPTOM):
        event.prop(util.ATTR_SYMPTOM).set(schema.symptom)
    if schema.anxiety and event.prop(util.ATTR_ANXIETY):
        event.prop(util.ATTR_ANXIETY).set(schema.anxiety)
    if schema.relationship and event.prop(util.ATTR_RELATIONSHIP):
        event.prop(util.ATTR_RELATIONSHIP).set(schema.relationship)
    if schema.functioning and event.prop(util.ATTR_FUNCTIONING):
        event.prop(util.ATTR_FUNCTIONING).set(schema.functioning)

    return event


def marriage_to_schema(marriage) -> MarriageSchema:
    """
    Convert a Scene Marriage to a MarriageSchema.

    Args:
        marriage: Scene Marriage object

    Returns:
        MarriageSchema instance with JSON-compatible types
    """
    return MarriageSchema(
        id=marriage.id,
        person_a_id=marriage.people[0].id if marriage.people[0] else None,
        person_b_id=marriage.people[1].id if marriage.people[1] else None,
        married=marriage.married() if marriage.married() is not None else True,
        separated=marriage.separated() or False,
        divorced=marriage.divorced() or False,
        custody=marriage.custody() or -1,
        diagram_notes=marriage.diagramNotes() or "",
        notes=marriage.notes() or "",
        tags=marriage.tags() or [],
        logged_date_time=qdatetime_to_iso(marriage.loggedDateTime()),
    )


def schema_to_marriage(schema: MarriageSchema, scene):
    """
    Create a Scene Marriage from a MarriageSchema.

    Args:
        schema: MarriageSchema instance
        scene: Scene to get people from

    Returns:
        Scene Marriage object
    """
    from pkdiagram.scene import Marriage

    # Get person objects from scene by ID
    person_a = scene.find(id=schema.person_a_id)
    person_b = scene.find(id=schema.person_b_id)

    marriage = Marriage(
        personA=person_a,
        personB=person_b,
        id=schema.id,
        married=schema.married,
        separated=schema.separated,
        divorced=schema.divorced,
        custody=schema.custody,
        diagramNotes=schema.diagram_notes,
        notes=schema.notes,
        tags=schema.tags,
        loggedDateTime=iso_to_qdatetime(schema.logged_date_time),
    )
    return marriage


def emotion_to_schema(emotion) -> EmotionSchema:
    """
    Convert a Scene Emotion to an EmotionSchema.

    Args:
        emotion: Scene Emotion object

    Returns:
        EmotionSchema instance with JSON-compatible types
    """
    return EmotionSchema(
        id=emotion.id,
        kind=emotion.kind() if isinstance(emotion.kind(), str) else emotion.kind().value,
        intensity=emotion.intensity() or 3,
        event_id=emotion.event(),
        person_id=emotion.person(),
        target_id=emotion.target(),
        color=emotion.color(),
        notes=emotion.notes() or "",
        tags=emotion.tags() or [],
        layers=emotion.layers() or [],
        logged_date_time=qdatetime_to_iso(emotion.loggedDateTime()),
    )


def schema_to_emotion(schema: EmotionSchema, scene):
    """
    Create a Scene Emotion from an EmotionSchema.

    Args:
        schema: EmotionSchema instance
        scene: Scene to add the emotion to

    Returns:
        Scene Emotion object
    """
    from pkdiagram.scene import Emotion, RelationshipKind

    # Get the RelationshipKind enum
    kind = RelationshipKind(schema.kind)

    emotion = Emotion(
        id=schema.id,
        kind=kind.value,
        intensity=schema.intensity,
        event=schema.event_id,
        person=schema.person_id,
        target=schema.target_id,
        color=schema.color,
        notes=schema.notes,
        tags=schema.tags,
        layers=schema.layers,
        loggedDateTime=iso_to_qdatetime(schema.logged_date_time),
    )
    return emotion


def layer_to_schema(layer) -> LayerSchema:
    """
    Convert a Scene Layer to a LayerSchema.

    Args:
        layer: Scene Layer object

    Returns:
        LayerSchema instance with JSON-compatible types
    """
    return LayerSchema(
        id=layer.id,
        name=layer.name() or "",
        description=layer.description() or "",
        order=layer.order() or -1,
        notes=layer.notes() or "",
        active=layer.active() or False,
        internal=layer.internal() or False,
        item_properties=layer.itemProperties() or {},
        store_geometry=layer.storeGeometry() or False,
        tags=layer.tags() or [],
        logged_date_time=qdatetime_to_iso(layer.loggedDateTime()),
    )


def schema_to_layer(schema: LayerSchema, scene):
    """
    Create a Scene Layer from a LayerSchema.

    Args:
        schema: LayerSchema instance
        scene: Scene to add the layer to

    Returns:
        Scene Layer object
    """
    from pkdiagram.scene import Layer

    layer = Layer(
        scene=scene,
        id=schema.id,
        name=schema.name,
        description=schema.description,
        order=schema.order,
        notes=schema.notes,
        active=schema.active,
        internal=schema.internal,
        itemProperties=schema.item_properties,
        storeGeometry=schema.store_geometry,
        tags=schema.tags,
        loggedDateTime=iso_to_qdatetime(schema.logged_date_time),
    )
    return layer
