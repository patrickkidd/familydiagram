import time
import logging
from typing import Callable

from PyQt5.QtCore import QObject, QCoreApplication, QEventLoop
from PyQt5.QtWidgets import QApplication

_log = logging.getLogger(__name__)


class Condition(QObject):
    """Allows you to wait for a signal to be called."""

    # triggered = pyqtSignal()

    def __init__(self, signal=None, only=None, condition=None, name=None):
        super().__init__()
        self.callCount = 0
        self.callArgs = []
        # self.senders = []
        self.testCount = 0
        self.lastCallArgs = None
        self.only = only
        self.condition = condition
        self.name = name
        self.signal = signal
        if signal:
            signal.connect(self)

    def deinit(self):
        if self.signal:
            self.signal.disconnect(self)
            self.signal = None

    def reset(self):
        self.callCount = 0
        self.callArgs = []
        # self.senders = []
        self.lastCallArgs = None

    def test(self):
        """Return true if the condition is true."""
        self.testCount += 1
        if self.condition:
            return self.condition()
        else:
            return self.callCount > 0

    def set(self, *args):
        """Set the condition to true. Alias for condition()."""
        self.callCount += 1
        # self.senders.append(QObject().sender())
        self.lastCallArgs = args
        self.callArgs.append(args)

    def __call__(self, *args):
        """Called by whatever signal that triggers the condition."""
        if self.only:
            only = self.only
            if not only(*args):
                return
        self.set(*args)
        # if self.test():
        #     self.triggered.emit()

    def wait(self, maxMS=1000, onError=None, interval=10):
        """Wait for the condition to be true. onError is a callback."""
        startTime = time.time()
        app = QCoreApplication.instance()
        # sig_or_cond = self.signal or self.condition
        while app and not self.test():
            # _log.debug(
            #     f"Condition[{sig_or_cond}].wait() still waiting... test count: {self.testCount}, interval (ms): {interval}"
            # )
            try:
                app.processEvents(QEventLoop.WaitForMoreEvents, interval)
            except KeyboardInterrupt as e:
                if onError:
                    onError()
                break
            elapsed = (time.time() - startTime) * 1000
            if elapsed >= maxMS:
                break
            # else:
            #     time.sleep(.1) # replace with some way to release loop directly from signal
        # _log.debug(f"Condition[{sig_or_cond}].wait() returned {self.test()}")
        ret = self.test()
        return ret

    def waitForCallCount(self, callCount, maxMS=1000):
        _log.info(f"Waiting for {callCount} calls to {self.signal}")
        start_time = time.time()
        ret = None
        while self.callCount < callCount:
            if time.time() - start_time > maxMS / 1000:
                ret = False
                _log.info(
                    f"Time elapsed on Condition[{self.signal}].wait() (callCount={self.callCount})"
                )
                break
            ret = self.wait(maxMS=maxMS)
            if not ret:
                _log.info(
                    f"Inner wait() returned False on Condition[{self.signal}].wait()  (callCount={self.callCount})"
                )
                break
        if ret is None:
            ret = self.callCount == callCount
            _log.info(
                f"Returning {ret} with {self.callCount}/{callCount} calls to {self.signal}"
            )
        return ret

    def assertWait(self, *args, **kwargs):
        assert self.wait(*args, **kwargs) == True


def wait(signal, maxMS=1000):
    return Condition(signal).wait(maxMS=maxMS)


def waitForCallCount(signal, callCount, maxMS=1000):
    return Condition(signal).waitForCallCount(callCount, maxMS=maxMS)


def waitForCondition(condition: Callable, maxMS=1000):
    INTERVAL_MS = 10
    startTime = time.time()

    app = QApplication.instance()
    ret = None
    while ret is None:
        app.processEvents(QEventLoop.ProcessEventsFlag.WaitForMoreEvents, INTERVAL_MS)
        bleh = condition()
        if bleh:
            _log.debug(
                f"Condition met on waitForCondition() using condition {condition}"
            )
            ret = True
        if (time.time() - startTime) > maxMS / 1000:
            _log.error(
                f"Time elapsed on waitForCondition() using condition {condition}"
            )
            ret = False
    return ret


def waitForActive(windowOrWidget, maxMS=1000):
    if not windowOrWidget.isWindow():
        window = windowOrWidget.window()
    else:
        window = windowOrWidget
    return waitForCondition(lambda: window.isActiveWindow(), maxMS=maxMS)
