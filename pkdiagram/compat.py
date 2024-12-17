import logging

from pkdiagram.pyqt import QPointF, QDateTime, QDate
from pkdiagram import version
from pkdiagram.scene import ItemDetails, Emotion

_log = logging.getLogger(__name__)


def UP_TO(data, compatVer):
    ver = data.get("version")
    if ver is None or version.lessThanOrEqual(ver, compatVer):
        return True
    else:
        return False


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
