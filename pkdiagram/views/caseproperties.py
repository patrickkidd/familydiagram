from pkdiagram.views import QmlDrawer


class CaseProperties(QmlDrawer):
    QmlDrawer.registerQmlMethods(
        [
            {"name": "inspectEvents"},
            {"name": "scrollSettingsToBottom"},
            {"name": "scrollTimelineToDateTime"},
            {"name": "isEventPropertiesShown", "return": True},
        ]
    )

    def show(self, items=[], tab=None, **kwargs):
        if items and items[0].isEvent:
            self.inspectEvents(items)
            items = []
        super().show(items, tab, **kwargs)
