import enum
import logging
from dataclasses import dataclass

from PySide6.QtCore import Property, QObject
from PySide6.QtQml import qmlRegisterType

# from pkdiagram import util
# from pkdiagram.models.qobjecthelper import qobject_dataclass


_log = logging.getLogger(__name__)


@dataclass
class Response:
    message: str
    pdp: dict


# qmlRegisterType(Response, "PK.Models", 1, 0, "Response")


class SpeakerType(enum.StrEnum):
    Expert = "expert"
    Subject = "subject"


class Speaker(QObject):
    def __init__(self, id: int, person_id: int, name: str, type: SpeakerType):
        super().__init__()
        self._id = id
        self._person_id = person_id
        self._name = name
        self._type = type

    def as_dict(self) -> dict:
        return {
            "person_id": self._person_id,
            "name": self._name,
            "type": self._type.value,
        }

    @Property(int, constant=True)
    def id(self) -> int:
        return self._id

    @Property(str, constant=True)
    def name(self) -> str:
        return self._name

    @Property(str, constant=True)
    def type(self) -> str:
        return self._type


class Statement(QObject):

    def __init__(
        self,
        id: int,
        text: str,
        speaker: Speaker,
        order: int | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._id = id
        self._text = text
        self._speaker = speaker
        self._order = order if order is not None else 0

    def as_dict(self) -> dict:
        return {
            "id": self._id,
            "text": self._text,
            "speaker": self._speaker.as_dict() if self._speaker else None,
        }

    @Property(int, constant=True)
    def id(self) -> int:
        return self._id

    @Property(str, constant=True)
    def text(self) -> str:
        return self._text

    @Property(Speaker, constant=True)
    def speaker(self) -> Speaker:
        return self._speaker

    @Property(int, constant=True)
    def order(self) -> int:
        return self._order


class Discussion(QObject):
    """
    For clean exposure to Qml
    """

    def __init__(
        self,
        id: int,
        user_id: int,
        diagram_id: int,
        summary: str | None = None,
        statements: list[Statement] | None = None,
        speakers: list[Speaker] | None = None,
        extracted_through_order: int | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._id = id
        self._user_id = user_id
        self._summary = summary
        self._statements = statements if statements is not None else []
        self._diagram_id = diagram_id
        self._speakers = speakers if speakers is not None else []
        self._extracted_through_order = extracted_through_order

    def as_dict(self) -> dict:
        return {
            "id": self._id,
            "user_id": self._user_id,
            "summary": self._summary,
            "statements": [x.as_dict() for x in self._statements],
        }

    @Property(int, constant=True)
    def id(self) -> int:
        return self._id

    @Property(int, constant=True)
    def user_id(self) -> int:
        return self._user_id

    @Property(str, constant=True)
    def summary(self) -> str:
        return self._summary if self._summary else ""

    def statements(self) -> list[Statement]:
        return list(self._statements)

    @Property(int, constant=True)
    def extracted_through_order(self) -> int:
        # -1 = nothing accepted yet → every statement is dirty
        return (
            self._extracted_through_order
            if self._extracted_through_order is not None
            else -1
        )

    @staticmethod
    def create(data: dict) -> "Discussion":
        speakers = [
            Speaker(
                id=x["id"],
                person_id=x["person_id"],
                name=x["name"],
                type=SpeakerType(x["type"]),
            )
            for x in data["speakers"]
        ]
        return Discussion(
            id=data["id"],
            diagram_id=data["diagram_id"],
            user_id=data["user_id"],
            summary=data["summary"],
            statements=[
                Statement(
                    id=x["id"],
                    text=x["text"],
                    speaker=next(y for y in speakers if y.id == x["speaker_id"]),
                    order=x.get("order"),
                )
                for x in data.get("statements", [])
            ],
            speakers=speakers,
            extracted_through_order=data.get("extracted_through_order"),
        )


qmlRegisterType(Discussion, "Personal", 1, 0, "Discussion")
qmlRegisterType(Statement, "Personal", 1, 0, "Statement")
qmlRegisterType(Speaker, "Personal", 1, 0, "Speaker")
