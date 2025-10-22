"""
Serialization utilities for Scene data.

Supports both pickle (legacy) and JSON (new) formats with automatic detection
and backward compatibility.
"""

import pickle
import json
import logging

log = logging.getLogger(__name__)


def serialize_scene_data(scene, selectionOnly=False, use_json=True):
    """
    Serialize scene data to bytes.

    Args:
        scene: Scene object to serialize
        selectionOnly: If True, only serialize selected items
        use_json: If True, use JSON format; if False, use pickle format

    Returns:
        bytes: Serialized scene data
    """
    if use_json:
        # New JSON format
        data = scene.to_json_dict(selectionOnly=selectionOnly)
        json_str = json.dumps(data, indent=2)
        return json_str.encode('utf-8')
    else:
        # Legacy pickle format
        data = scene.data(selectionOnly=selectionOnly)
        return pickle.dumps(data)


def deserialize_scene_data(bdata):
    """
    Deserialize scene data from bytes.

    Automatically detects JSON or pickle format.

    Args:
        bdata: bytes data to deserialize

    Returns:
        dict: Deserialized scene data
    """
    if not bdata:
        return {}

    # Try JSON first (new format)
    try:
        json_str = bdata.decode('utf-8')
        data = json.loads(json_str)
        if isinstance(data, dict):
            log.info("Loaded JSON format document")
            return data
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass

    # Fall back to pickle (legacy format)
    try:
        data = pickle.loads(bdata)
        log.info("Loaded pickle format document (legacy)")
        return data
    except Exception as e:
        log.error(f"Failed to deserialize data: {e}")
        raise


def load_scene_from_data(scene, data):
    """
    Load scene from deserialized data.

    Automatically handles JSON or pickle format.

    Args:
        scene: Scene object to load into
        data: Deserialized data dict

    Returns:
        Result from scene.read() or scene.from_json_dict()
    """
    if data.get("format") == "json":
        # New JSON format
        return scene.from_json_dict(data)
    else:
        # Legacy pickle format
        return scene.read(data)


def save_scene_to_file(scene, file_path, use_json=True, selectionOnly=False):
    """
    Save scene to file.

    Args:
        scene: Scene object to save
        file_path: Path to save to
        use_json: If True, use JSON format; if False, use pickle
        selectionOnly: If True, only save selected items

    Returns:
        bytes: The serialized data that was written
    """
    bdata = serialize_scene_data(scene, selectionOnly=selectionOnly, use_json=use_json)
    with open(file_path, "wb") as f:
        f.write(bdata)
    log.info(f"Saved scene to {file_path} ({len(bdata)} bytes, {'JSON' if use_json else 'pickle'} format)")
    return bdata


def load_scene_from_file(scene, file_path):
    """
    Load scene from file.

    Automatically detects JSON or pickle format.

    Args:
        scene: Scene object to load into
        file_path: Path to load from

    Returns:
        Result from scene.read() or scene.from_json_dict()
    """
    with open(file_path, "rb") as f:
        bdata = f.read()

    data = deserialize_scene_data(bdata)
    result = load_scene_from_data(scene, data)

    log.info(f"Loaded scene from {file_path} ({len(bdata)} bytes)")
    return result


# Configuration: Use JSON by default for new saves
USE_JSON_BY_DEFAULT = True
