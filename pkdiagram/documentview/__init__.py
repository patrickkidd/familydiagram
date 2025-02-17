import enum


class RightDrawerView(enum.Enum):
    AddAnything = "addanything"
    Timeline = "timeline"
    Settings = "settings"
    Copilot = "copilot"


from .qmlengine import QmlEngine
from .toolbars import ItemToolBar, SceneToolBar, RightToolBar
from .dragpan import DragPanner
from .panzoom import PanZoomer
from .wheelzoom import WheelZoomer
from .helpoverlay import HelpOverlay
from .legend import Legend
from .graphicaltimelinecanvas import GraphicalTimelineCanvas
from .graphicaltimeline import GraphicalTimeline
from .graphicaltimelineview import GraphicalTimelineView
from .view import View
from .documentcontroller import DocumentController
from .documentview import DocumentView
