from pkdiagram.pyqt import QObject
from pkdiagram.models import QObjectHelper

import btcopilot


def find_global_type(attr):
    value = getattr(btcopilot, attr)
    if isinstance(value, int):  # true for int's and PyQt enums
        return int
    else:
        return type(value)


class QmlBTCopilot(QObject, QObjectHelper):
    """The btcopilot module exposed to qml."""

    CONSTANTS = [
        "LICENSE_FREE",
        "LICENSE_ALPHA",
        "LICENSE_BETA",
        "LICENSE_CLIENT",
        "LICENSE_PROFESSIONAL",
        "LICENSE_PROFESSIONAL_MONTHLY",
        "LICENSE_PROFESSIONAL_ANNUAL",
        "LICENSE_RESEARCHER",
        "LICENSE_RESEARCHER_MONTHLY",
        "LICENSE_RESEARCHER_ANNUAL",
        "ACCESS_READ_ONLY",
        "ACCESS_READ_WRITE",
    ]

    QObjectHelper.registerQtProperties(
        [
            {
                "attr": attr,
                "global": True,
                # 'constant': True,
                "type": find_global_type(attr),
            }
            for attr in CONSTANTS
        ],
        globalContext=btcopilot.__dict__,
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("btcopilot]")
        self.initQObjectHelper()
