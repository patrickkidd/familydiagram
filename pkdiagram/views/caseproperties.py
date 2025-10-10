from pkdiagram.scene import Event
from pkdiagram.views import QmlDrawer


class CaseProperties(QmlDrawer):
    QmlDrawer.registerQmlMethods(
        [
            {"name": "scrollSettingsToBottom"},
            {"name": "scrollTimelineToDateTime"},
        ]
    )

    # def show(self, items=[], tab=None, **kwargs):
    #     if items and items[0].isEvent:
    #         self.inspectEvents(items)
    #         items = []
    #     super().show(items, tab, **kwargs)

    def selectedEvents(self) -> list[Event]:
        return self.rootProp("timelineView").property("selectedEvents")
