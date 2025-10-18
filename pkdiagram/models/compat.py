import logging

from pkdiagram.pyqt import QPointF, QDateTime, QDate
from pkdiagram import version, util
from pkdiagram.scene import ItemDetails, Emotion, RelationshipKind, EventKind, Emotion

_log = logging.getLogger(__name__)


def UP_TO(data, compatVer):
    ver = data.get("version")
    if ver is None or version.lessThanOrEqual(ver, compatVer):
        return True
    else:
        return False


def find_parents_from_childof(person_chunk, data):
    """Extract parent Marriage IDs from childOf relationship.

    Returns tuple of (parent1_id, parent2_id, marriage_id) or (None, None, None).
    """
    childOf = person_chunk.get("childOf", {})
    if not childOf or not childOf.get("parents"):
        return None, None, None

    marriage_id = childOf["parents"]
    for marriage_chunk in data.get("marriages", []):
        if marriage_chunk["id"] == marriage_id:
            return (
                marriage_chunk.get("person_a"),
                marriage_chunk.get("person_b"),
                marriage_id,
            )

    return None, None, None


def update_data(data):

    if UP_TO(data, "1.0.0b5"):
        for chunk in data.get("items", []):
            if chunk["kind"] == "Emotion":
                if chunk.get("person", None) is not None:
                    chunk["person_a"] = chunk["person"]
                    chunk["person_b"] = None

    if UP_TO(data, "1.0.0b7"):
        for chunk in data.get("items", []):
            if chunk["kind"] == "Person":
                if "pos" in chunk and not "nonLayerPos" in chunk:
                    chunk["nonLayerPos"] = QPointF(chunk["pos"][0], chunk["pos"][1])

    if UP_TO(data, "1.0.0a16"):

        # have to match up all the birthPartner lists and create new, unique MultipleBirth entries
        def getMultipleBirthId(marriageId, birthPartners):
            if not birthPartners:
                return None
            ret = None
            matchingChunk = None
            for id, chunk in getMultipleBirthId.newMultipleBirths.items():
                for childId in chunk["children"]:
                    for bpId in birthPartners:
                        if bpId == childId:
                            matchingChunk = chunk
                            ret = chunk["id"]
                            break
                    if matchingChunk:
                        break
            if not matchingChunk:
                getMultipleBirthId.lastItemId += 1
                getMultipleBirthId.newMultipleBirths[getMultipleBirthId.lastItemId] = {
                    "kind": "MultipleBirth",
                    "id": getMultipleBirthId.lastItemId,
                    "children": list(birthPartners),
                    "parents": marriageId,
                }
                ret = getMultipleBirthId.lastItemId
            return ret

        getMultipleBirthId.lastItemId = data.get("lastItemId", 1)
        getMultipleBirthId.newMultipleBirths = {}

        for chunk in data.get("items", []):
            if chunk["kind"] in ("Person", "Marriage"):
                if not "detailsText" in chunk:
                    chunk["detailsText"] = {"itemPos": QPointF()}
                if "detailsPos" in chunk:
                    chunk["detailsText"]["itemPos"] = chunk["detailsPos"]
                    del chunk["detailsPos"]
                elif (
                    not "itemPos" in chunk["detailsText"]
                    and "nonLayerPos" in chunk["detailsText"]
                ):
                    chunk["detailsText"]["itemPos"] = chunk["detailsText"][
                        "nonLayerPos"
                    ]
                if "layerPos" in chunk["detailsText"]:
                    del chunk["detailsText"]["layerPos"]
                if "nonLayerPos" in chunk["detailsText"]:
                    del chunk["detailsText"]["nonLayerPos"]
                if "separationIndicatorPos" in chunk:
                    chunk["separationIndicator"] = {
                        "itemPos": chunk["separationIndicatorPos"]
                    }
                    del chunk["separationIndicatorPos"]
                # some corrupted diagrams in dev ( turn into assert later)
                if chunk["detailsText"]["itemPos"].x() > 15000:
                    chunk["detailsText"]["itemPos"] = QPointF()
                if (
                    "separationIndicator" in chunk
                    and chunk["separationIndicator"]["itemPos"].x() > 100000
                ):
                    chunk["separationIndicator"]["itemPos"] = QPointF()

            if "layerPos" in chunk:
                del chunk["layerPos"]

            if chunk["kind"] == "Marriage":
                if "nonLayerPos" in chunk:
                    del chunk["nonLayerPos"]

            if chunk["kind"] == "Person":
                if "nonLayerPos" in chunk:
                    chunk["itemPos"] = chunk["nonLayerPos"]
                    del chunk["nonLayerPos"]
                if not "childOf" in chunk:
                    if chunk.get("parents") is not None:
                        chunk["childOf"] = {
                            "person": chunk["id"],
                            "parents": chunk["parents"],
                            "multipleBirth": None,
                        }
                        if chunk.get("birthPartners"):
                            chunk["childOf"]["multipleBirth"] = getMultipleBirthId(
                                chunk["parents"], [chunk["id"]] + chunk["birthPartners"]
                            )
                    else:
                        chunk["childOf"] = {}

            elif chunk["kind"] in ("Callout", "PencilStroke"):
                chunk["itemPos"] = QPointF(chunk["pos"][0], chunk["pos"][1])
                del chunk["pos"]

            elif chunk["kind"] == "Layer":
                for id, itemEntry in chunk["itemProperties"].items():
                    if "layerPos" in data:
                        data["itemPos"] = data["layerPos"]
                        del data["layerPos"]
                    if "layerSize" in data:
                        data["size"] = data["layerSize"]
                        del data["layerSize"]
                    if "layerOpacity" in data:
                        data["itemOpacity"] = data["layerOpacity"]
                        del data["layerOpacity"]

        data["lastItemId"] = getMultipleBirthId.lastItemId
        for id, chunk in getMultipleBirthId.newMultipleBirths.items():
            data["items"].append(chunk)

    if UP_TO(data, "1.1.4a7"):

        for chunk in data.get("items", []):
            if chunk["kind"] == "Marriage":
                marriedEvent = chunk["marriedEvent"]
                separatedEvent = chunk["separatedEvent"]
                divorcedEvent = chunk["divorcedEvent"]
                del chunk["marriedEvent"]
                del chunk["separatedEvent"]
                del chunk["divorcedEvent"]
                if marriedEvent["date"]:
                    chunk["events"].append(marriedEvent)
                if separatedEvent["date"]:
                    chunk["events"].append(separatedEvent)
                if divorcedEvent["date"]:
                    chunk["events"].append(divorcedEvent)

    if UP_TO(data, "1.2.8"):

        layerChunks = [x for x in data.get("items", []) if x["kind"] == "Layer"]

        data["currentDateTime"] = data.pop("currentDate", QDateTime.currentDateTime())
        data["showAliases"] = data.pop("hideNames", False)

        for chunk in data.get("items", []):

            # Change Toward|Away to Inside|Outside
            if chunk["kind"] == "Toward":
                chunk["kind"] = "Inside"
            elif chunk["kind"] == "Away":
                chunk["kind"] = "Outside"

            # Transform Event.date to Event.dateTime
            if chunk["kind"] == "Event":
                chunk["dateTime"] = QDateTime(chunk.pop("date", QDate()))

            # Transform Person and Marriage event dates
            if chunk["kind"] in ("Person", "Marriage"):
                for eventChunk in chunk.get("events", []):
                    date = eventChunk.pop("date", None)
                    if not date:
                        date = QDate()
                    eventChunk["dateTime"] = QDateTime(date)

            # General person upgrades
            if chunk["kind"] == "Person":

                # Built-in events
                birthEvent = chunk.get("birthEvent")
                if birthEvent:
                    birthDate = birthEvent.pop("date", None)
                    birthEvent["dateTime"] = QDateTime(
                        birthDate if birthDate else QDateTime()
                    )

                adoptedEvent = chunk.get("adoptedEvent")
                if adoptedEvent:
                    adoptedDate = adoptedEvent.pop("date", None)
                    adoptedEvent["dateTime"] = QDateTime(
                        adoptedDate if adoptedDate else QDateTime()
                    )

                deathEvent = chunk.get("deathEvent")
                if deathEvent:
                    deceasedDate = deathEvent.pop("date", None)
                    deathEvent["dateTime"] = QDateTime(
                        deceasedDate if deceasedDate else QDateTime()
                    )

                # Reassign people to layers based on tag matching
                personTags = chunk.pop("tags", [])
                if personTags:
                    for layerChunk in layerChunks:
                        layerTags = layerChunk.get("tags", [])
                        if layerTags and set(personTags) & set(layerTags):
                            chunk.setdefault("layers", []).append(layerChunk["id"])

            # Migrate Emotion.startDate|endDate to startEvent|endEvent
            if chunk["kind"] in Emotion.kindSlugs():
                startDate = chunk.pop("startDate", None)
                chunk["startEvent"] = {
                    "dateTime": QDateTime(startDate if startDate else QDateTime()),
                    "unsure": chunk.get("startDateUnsure"),
                    "uniqueId": "emotionStartEvent",
                    "notes": chunk.get("notes"),
                }
                endDate = chunk.pop("endDate", None)
                chunk["endEvent"] = {
                    "dateTime": QDateTime(endDate if endDate else QDateTime()),
                    "unsure": chunk.get("endDateUnsure"),
                    "uniqueId": "emotionEndEvent",
                }

    if UP_TO(data, "1.4.5"):

        # Coalesce all emotion events on each other.
        for chunk in data.get("items", []):
            if chunk["kind"] in Emotion.kindSlugs():
                itemTags = sorted(
                    list(
                        set(
                            chunk.get("tags", [])
                            + chunk["startEvent"].get("tags", [])
                            + chunk["endEvent"].get("tags", [])
                        )
                    )
                )
                chunk["tags"] = list(itemTags)
                chunk["startEvent"]["tags"] = list(itemTags)
                chunk["endEvent"]["tags"] = list(itemTags)

    if UP_TO(data, "2.0.0"):
        for chunk in data.get("items", []):
            if chunk["kind"] in Emotion.kindSlugs():

                # Maintain mirror between emotion.notes and emotion.startEvent.notes
                if (
                    chunk["notes"]
                    and chunk["startEvent"]["dateTime"]
                    and not chunk["startEvent"]["notes"]
                ):
                    _log.warning(
                        f"Migrating emotion.notes to emotion.startEvent.notes for {chunk['id']}"
                    )
                    chunk["startEvent"]["notes"] = chunk["notes"]
                elif (
                    chunk["startEvent"]["dateTime"]
                    and chunk["startEvent"]["notes"]
                    and not chunk["notes"]
                ):
                    _log.warning(
                        f"Migrating emotion.startEvent.notes to emotion.notes for {chunk['id']}"
                    )
                    chunk["notes"] = chunk["startEvent"]["notes"]

    if UP_TO(data, "2.0.12b1"):
        # Normalize emotion kind strings to match convention Old format used
        # capitalized strings like "Conflict", "Reciprocity" These need to stay
        # as-is for the initial splitting phase

        # Phase 6.1: Split mixed items into separate top-level arrays
        # Initialize typed arrays
        data.setdefault("people", [])
        data.setdefault("marriages", [])
        data.setdefault("emotions", [])
        data.setdefault("events", [])
        data.setdefault("layerItems", [])
        data.setdefault("layers", [])
        data.setdefault("multipleBirths", [])

        if "items" in data:
            # Keep remaining items array for any unknown types
            remaining_items = []

            for chunk in data["items"]:
                kind = chunk.get("kind")
                if kind == "Person":
                    data["people"].append(chunk)
                elif kind == "Marriage":
                    data["marriages"].append(chunk)
                elif kind and (
                    kind.lower() in [s.lower() for s in Emotion.kindSlugs()]
                    or kind in ("DefinedSelf", "Reciprocity")
                ):  # All emotion types (case-insensitive)
                    data["emotions"].append(chunk)
                elif kind == "Event":
                    data["events"].append(chunk)
                elif kind == "Layer":
                    data["layers"].append(chunk)
                elif kind in ("Callout", "PencilStroke"):
                    data["layerItems"].append(chunk)
                elif kind == "MultipleBirth":
                    data["multipleBirths"].append(chunk)
                else:
                    # Unknown item type - keep in items array
                    remaining_items.append(chunk)

            # Replace items with only unknown types (if any)
            if remaining_items:
                data["items"] = remaining_items
            else:
                # Remove items array entirely if empty
                del data["items"]

        # Phase 6.2: Migrate Event Properties
        # Track next available ID for new events
        next_id = data.get("lastItemId", -1) + 1

        # Collect all events from nested locations
        all_events = []

        # 1a. Extract Person built-in events (birthEvent, adoptedEvent, deathEvent)
        for person_chunk in data.get("people", []):
            for event_attr in ["birthEvent", "adoptedEvent", "deathEvent"]:
                if event_attr in person_chunk:
                    event_chunk = person_chunk.pop(event_attr)
                    if not event_chunk.get("dateTime"):
                        continue

                    # Migrate uniqueId → kind
                    if "uniqueId" in event_chunk:
                        uid = event_chunk.pop("uniqueId")
                        if uid == "birth":
                            event_chunk["kind"] = EventKind.Birth.value
                        elif uid == "adopted":
                            event_chunk["kind"] = EventKind.Adopted.value
                        elif uid == "death":
                            event_chunk["kind"] = EventKind.Death.value
                        elif uid in ("CustomIndividual", "", None):
                            event_chunk["kind"] = EventKind.Shift.value
                        else:
                            event_chunk["kind"] = uid

                    # Ensure kind is set (fallback if no uniqueId)
                    if "kind" not in event_chunk:
                        if event_attr == "birthEvent":
                            event_chunk["kind"] = EventKind.Birth.value
                        elif event_attr == "deathEvent":
                            event_chunk["kind"] = EventKind.Death.value
                        elif event_attr == "adoptedEvent":
                            event_chunk["kind"] = EventKind.Adopted.value

                    # Ensure event has ID
                    if "id" not in event_chunk:
                        event_chunk["id"] = next_id
                        next_id += 1

                    # Set person/child references based on event type
                    if event_attr in ["birthEvent", "adoptedEvent"]:
                        # Birth/Adopted are pair-bond (offspring) events
                        event_chunk["child"] = person_chunk["id"]

                        # Try to find existing parents
                        parent1_id, parent2_id, marriage_id = find_parents_from_childof(
                            person_chunk, data
                        )

                        if parent1_id and parent2_id:
                            # Use existing parents
                            event_chunk["person"] = parent1_id
                            event_chunk["spouse"] = parent2_id
                        else:
                            # Create inferred parents
                            child_size = person_chunk.get(
                                "size", util.DEFAULT_PERSON_SIZE
                            )
                            parent_size = max(child_size - 1, 1)  # One size smaller
                            child_pos = person_chunk.get("itemPos", {"x": 0, "y": 0})
                            child_layers = person_chunk.get("layers", [])

                            # Use shared utility to ensure parents exist
                            parents = util.ensureInferredParents(
                                child_pos, parent_size, child_layers, next_id
                            )

                            # Update next_id based on created items
                            if parents.created_male:
                                next_id += 1
                            if parents.created_female:
                                next_id += 1
                            if parents.created_marriage:
                                next_id += 1

                            # Add newly created items to data
                            if parents.male_data:
                                data["people"].append(parents.male_data)
                            if parents.female_data:
                                data["people"].append(parents.female_data)
                            if parents.marriage_data:
                                data["marriages"].append(parents.marriage_data)

                            # Link child to parents via childOf
                            person_chunk["childOf"] = {
                                "person": person_chunk["id"],
                                "parents": parents.marriage_id,
                                "multipleBirth": None,
                            }

                            # Set event references
                            event_chunk["person"] = parents.male_id
                            event_chunk["spouse"] = parents.female_id
                    else:
                        # Death event - just set person reference
                        event_chunk["person"] = person_chunk["id"]

                    all_events.append(event_chunk)

        # 1b. Extract custom events from Person.events array
        for person_chunk in data.get("people", []):
            if "events" in person_chunk:
                for event_chunk in person_chunk["events"]:
                    # Migrate uniqueId → kind
                    if "uniqueId" in event_chunk:
                        uid = event_chunk.pop("uniqueId")
                        if uid == "birth":
                            event_chunk["kind"] = EventKind.Birth.value
                        elif uid == "adopted":
                            event_chunk["kind"] = EventKind.Adopted.value
                        elif uid == "death":
                            event_chunk["kind"] = EventKind.Death.value
                        elif uid in (
                            "CustomIndividual",
                            "emotionStartEvent",
                            "emotionEndEvent",
                            "",
                            None,
                        ):
                            event_chunk["kind"] = EventKind.Shift.value
                        else:
                            event_chunk["kind"] = uid

                    # Ensure event has ID
                    if "id" not in event_chunk:
                        event_chunk["id"] = next_id
                        next_id += 1

                    # Set person/child references based on event type
                    event_kind = event_chunk.get("kind")
                    if event_kind in [EventKind.Birth.value, EventKind.Adopted.value]:
                        # Birth/Adopted are pair-bond (offspring) events
                        event_chunk["child"] = person_chunk["id"]

                        # Try to find existing parents
                        parent1_id, parent2_id, marriage_id = find_parents_from_childof(
                            person_chunk, data
                        )

                        if parent1_id and parent2_id:
                            # Use existing parents
                            event_chunk["person"] = parent1_id
                            event_chunk["spouse"] = parent2_id
                        else:
                            # Create inferred parents
                            child_size = person_chunk.get(
                                "size", util.DEFAULT_PERSON_SIZE
                            )
                            parent_size = max(child_size - 1, 1)  # One size smaller
                            child_pos = person_chunk.get("itemPos", {"x": 0, "y": 0})
                            child_layers = person_chunk.get("layers", [])

                            # Use shared utility to ensure parents exist
                            parents = util.ensureInferredParents(
                                child_pos, parent_size, child_layers, next_id
                            )

                            # Update next_id based on created items
                            if parents.created_male:
                                next_id += 1
                            if parents.created_female:
                                next_id += 1
                            if parents.created_marriage:
                                next_id += 1

                            # Add newly created items to data
                            if parents.male_data:
                                data["people"].append(parents.male_data)
                            if parents.female_data:
                                data["people"].append(parents.female_data)
                            if parents.marriage_data:
                                data["marriages"].append(parents.marriage_data)

                            # Link child to parents via childOf
                            person_chunk["childOf"] = {
                                "person": person_chunk["id"],
                                "parents": parents.marriage_id,
                                "multipleBirth": None,
                            }

                            # Set event references
                            event_chunk["person"] = parents.male_id
                            event_chunk["spouse"] = parents.female_id
                    else:
                        # Other events (death, shift, etc.) - just set person reference
                        event_chunk["person"] = person_chunk["id"]

                    all_events.append(event_chunk)

                # Remove events from person
                del person_chunk["events"]

        # 2. Extract events from Marriage.events
        for marriage_chunk in data.get("marriages", []):
            if "events" in marriage_chunk:
                for event_chunk in marriage_chunk["events"]:
                    # Migrate uniqueId → kind
                    if "uniqueId" in event_chunk:
                        uid = event_chunk.pop("uniqueId")
                        if uid == "married":
                            event_chunk["kind"] = EventKind.Married.value
                        elif uid == "bonded":
                            event_chunk["kind"] = EventKind.Bonded.value
                        elif uid == "separated":
                            event_chunk["kind"] = EventKind.Separated.value
                        elif uid == "divorced":
                            event_chunk["kind"] = EventKind.Divorced.value
                        elif uid == "moved":
                            event_chunk["kind"] = EventKind.Moved.value
                        else:
                            event_chunk["kind"] = EventKind.Shift.value

                    if "id" not in event_chunk:
                        event_chunk["id"] = next_id
                        next_id += 1

                    # Marriage events: person = personA, spouse = personB
                    event_chunk["person"] = marriage_chunk["person_a"]
                    event_chunk["spouse"] = marriage_chunk["person_b"]

                    all_events.append(event_chunk)

                del marriage_chunk["events"]

        # 3. Extract and merge Emotion start/end events
        for emotion_chunk in data.get("emotions", []):
            # Phase 6.3: Migrate Emotion.kind string to RelationshipKind enum value
            # Convert old capitalized string kinds to RelationshipKind enum values
            if "kind" in emotion_chunk and isinstance(emotion_chunk["kind"], str):
                old_kind = emotion_chunk["kind"]
                # Map old capitalized strings to RelationshipKind enum values
                STRING_2_ENUM_VALUE = {
                    "Fusion": RelationshipKind.Fusion.value,  # "fusion"
                    "Cutoff": RelationshipKind.Cutoff.value,  # "cutoff"
                    "Conflict": RelationshipKind.Conflict.value,  # "conflict"
                    "Projection": RelationshipKind.Projection.value,  # "projection"
                    "Distance": RelationshipKind.Distance.value,  # "distance"
                    "DefinedSelf": RelationshipKind.DefinedSelf.value,  # "defined-self"
                    "Toward": RelationshipKind.Toward.value,  # "toward"
                    "Away": RelationshipKind.Away.value,  # "away"
                    "Inside": RelationshipKind.Inside.value,  # "inside"
                    "Outside": RelationshipKind.Outside.value,  # "outside"
                    "Reciprocity": RelationshipKind.Underfunctioning.value,  # "underfunctioning" (default for reciprocity)
                    "Overfunctioning": RelationshipKind.Overfunctioning.value,  # "overfunctioning"
                    "Underfunctioning": RelationshipKind.Underfunctioning.value,  # "underfunctioning"
                }
                if old_kind in STRING_2_ENUM_VALUE:
                    emotion_chunk["kind"] = STRING_2_ENUM_VALUE[old_kind]
                    if old_kind != STRING_2_ENUM_VALUE[old_kind]:
                        _log.info(
                            f"Migrated emotion kind from '{old_kind}' to '{emotion_chunk['kind']}'"
                        )
                elif old_kind not in [rk.value for rk in RelationshipKind]:
                    # If it's not already a valid enum value, default to conflict
                    _log.warning(
                        f"Unknown emotion kind: '{old_kind}', defaulting to 'conflict'"
                    )
                    emotion_chunk["kind"] = RelationshipKind.Conflict.value

            if "startEvent" in emotion_chunk and emotion_chunk["startEvent"].get(
                "dateTime"
            ):
                start_event = emotion_chunk.pop("startEvent")
                end_event = emotion_chunk.pop("endEvent", None)

                if not "dynamicProperties" in start_event:
                    start_event["dynamicProperties"] = {}
                if end_event is not None and not "dynamicProperties" in end_event:
                    end_event["dynamicProperties"] = {}

                # Migrate startEvent uniqueId
                if "uniqueId" in start_event:
                    uid = start_event.pop("uniqueId")
                    if uid in ("emotionStartEvent", "CustomIndividual", "", None):
                        start_event["kind"] = EventKind.Shift.value
                    else:
                        start_event["kind"] = uid

                # Ensure kind is set
                if "kind" not in start_event:
                    start_event["kind"] = EventKind.Shift.value

                if "id" not in start_event:
                    start_event["id"] = next_id
                    next_id += 1

                # Set person from emotion
                if "person_a" in emotion_chunk:
                    start_event["person"] = emotion_chunk["person_a"]

                # Migrate emotion properties to event
                if "intensity" in emotion_chunk:
                    start_event["relationshipIntensity"] = emotion_chunk.pop(
                        "intensity"
                    )
                if "notes" in emotion_chunk:
                    start_event["notes"] = emotion_chunk.pop("notes")

                # Set relationship targets
                if "person_b" in emotion_chunk and emotion_chunk["person_b"]:
                    start_event["relationshipTargets"] = [emotion_chunk["person_b"]]
                else:
                    start_event["relationshipTargets"] = []

                # Set relationship field matching emotion kind
                if "kind" in emotion_chunk:
                    # Convert emotion kind (e.g., "Conflict" or "conflict") to lowercase
                    emotion_kind = emotion_chunk["kind"]
                    if isinstance(emotion_kind, str):
                        start_event["dynamicProperties"][
                            "relationship"
                        ] = emotion_kind.lower()

                # Handle endEvent/isDateRange
                if end_event and end_event.get("dateTime"):
                    start_event["endDateTime"] = end_event["dateTime"]
                elif emotion_chunk.get("isDateRange"):
                    # Mark that this event should have an endDateTime
                    start_event["endDateTime"] = None

                all_events.append(start_event)

                # Update emotion to reference the event
                emotion_chunk["event"] = start_event["id"]

                # Migrate person_b → target
                if "person_b" in emotion_chunk:
                    emotion_chunk["target"] = emotion_chunk.pop("person_b")

                # Clean up old fields
                emotion_chunk.pop("person_a", None)
                emotion_chunk.pop("isDateRange", None)
                emotion_chunk.pop("isSingularDate", None)

        # 4. Process existing events already in data["events"]
        for event_chunk in data.get("events", []):
            # Migrate uniqueId → kind
            if "uniqueId" in event_chunk:
                uid = event_chunk.pop("uniqueId")
                if uid == "birth":
                    event_chunk["kind"] = EventKind.Birth.value
                elif uid == "adopted":
                    event_chunk["kind"] = EventKind.Adopted.value
                elif uid == "death":
                    event_chunk["kind"] = EventKind.Death.value
                elif uid == "married":
                    event_chunk["kind"] = EventKind.Married.value
                elif uid == "bonded":
                    event_chunk["kind"] = EventKind.Bonded.value
                elif uid == "separated":
                    event_chunk["kind"] = EventKind.Separated.value
                elif uid == "divorced":
                    event_chunk["kind"] = EventKind.Divorced.value
                elif uid == "moved":
                    event_chunk["kind"] = EventKind.Moved.value
                elif uid in (
                    "CustomIndividual",
                    "emotionStartEvent",
                    "emotionEndEvent",
                    "",
                    None,
                ):
                    event_chunk["kind"] = EventKind.Shift.value
                else:
                    event_chunk["kind"] = EventKind.Shift.value

            # Ensure kind is never None
            if not event_chunk.get("kind"):
                event_chunk["kind"] = EventKind.Shift.value

            all_events.append(event_chunk)

        # 5. Add all collected events to data["events"]
        data["events"] = all_events

        # 6. Update lastItemId
        data["lastItemId"] = next_id - 1

        # Event.

    ## Add more version fixes here
    # if ....


def update_scene(scene, data):

    if UP_TO(data, "1.0.0b6"):
        # fix people details texts
        for item in scene.items():
            if isinstance(item, ItemDetails):
                item.setPos(item.pos() + QPointF(60, 0))

    ## Add more version fixes here
    # elif ...
