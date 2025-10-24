import json
from typing import Any
from pkdiagram.pyqt import QPointF, QDateTime, QDate, Qt


def convertQtTypes(obj: Any) -> Any:
    if isinstance(obj, QPointF):
        if obj.isNull():
            return None
        return {"x": obj.x(), "y": obj.y()}
    elif isinstance(obj, QDateTime):
        if obj.isNull():
            return None
        return obj.toString(Qt.ISODate)
    elif isinstance(obj, QDate):
        if obj.isNull():
            return None
        return obj.toString(Qt.ISODate)
    elif isinstance(obj, dict):
        return {key: convertQtTypes(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convertQtTypes(item) for item in obj]
    else:
        return obj


def dataToJson(data: dict) -> str:
    convertedData = convertQtTypes(data)
    return json.dumps(convertedData, indent=2, sort_keys=False)


def loadFromBytes(bdata: bytes) -> dict:
    import pickle

    try:
        jsonStr = bdata.decode("utf-8")
        return json.loads(jsonStr)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return pickle.loads(bdata)
