import logging

from pkdiagram.pyqt import QQuickItem, QApplication
from pkdiagram import util
from pkdiagram.widgets import QmlWidgetHelper

_log = logging.getLogger(__name__)


class CopilotView:

    def __init__(self, view: QmlWidgetHelper, item: QQuickItem):
        assert item is not None, "CopilotView item is None"
        self.view = view
        self.item = item
        self.textInput = item.property("textInput")
        self.sendButton = item.property("sendButton")
        self.chatModel = item.property("chatModel")

        self.chatBubbleAdded = util.Condition(item.chatBubbleAdded)
        self.chatBubbleRemoved = util.Condition(item.chatBubbleRemoved)

    def inputMessage(self, message: str):
        self.view.keyClicksItem(self.textInput, message)
        self.view.mouseClickItem(self.sendButton)
        assert self.chatBubbleAdded.wait() == True
