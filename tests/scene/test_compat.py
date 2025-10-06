import os.path
import pickle

import pytest

from pkdiagram import util
from pkdiagram.models import compat

from . import data


@pytest.fixture
def version_dict():
    def _version_dict(version):
        base_dir = os.path.dirname(data.__file__)
        file_path = os.path.join(
            base_dir,
            f"UP_TO_{version}{util.DOT_EXTENSION}",
            "diagram.pickle",
        )
        return pickle.load(open(file_path, "rb"))

    return _version_dict


def test_up_to_2_0_12b1(version_dict):
    from pkdiagram.models.compat import UP_TO

    data = version_dict("2.0.12b1")
    compat.update_data(data)
    events = [x for x in data.get("items", []) if x["kind"] == "Event"]
