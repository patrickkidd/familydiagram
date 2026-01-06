import math
import logging
from pkdiagram.pyqt import QObject, pyqtSignal, QTimer

_log = logging.getLogger(__name__)

try:
    from PyQt5.QtSensors import QAccelerometer, QAccelerometerReading

    HAS_SENSORS = True
except ImportError:
    HAS_SENSORS = False


class ShakeDetector(QObject):
    shakeDetected = pyqtSignal()

    THRESHOLD = 15.0  # Acceleration threshold for shake
    COOLDOWN_MS = 1000  # Minimum time between shakes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = False
        self._lastShakeTime = 0
        self._cooldownTimer = QTimer(self)
        self._cooldownTimer.setSingleShot(True)
        self._cooldownTimer.timeout.connect(self._endCooldown)
        self._inCooldown = False

        if HAS_SENSORS:
            self._sensor = QAccelerometer(self)
            self._sensor.readingChanged.connect(self._onReadingChanged)
            self._prevReading = None
        else:
            self._sensor = None

    def start(self):
        if self._sensor and not self._enabled:
            self._sensor.start()
            self._enabled = True

    def stop(self):
        if self._sensor and self._enabled:
            self._sensor.stop()
            self._enabled = False

    def _onReadingChanged(self):
        if not self._sensor or self._inCooldown:
            return

        reading = self._sensor.reading()
        if not reading:
            return

        x, y, z = reading.x(), reading.y(), reading.z()

        if self._prevReading:
            px, py, pz = self._prevReading
            delta = math.sqrt((x - px) ** 2 + (y - py) ** 2 + (z - pz) ** 2)

            if delta > self.THRESHOLD:
                self._inCooldown = True
                self._cooldownTimer.start(self.COOLDOWN_MS)
                self.shakeDetected.emit()

        self._prevReading = (x, y, z)

    def _endCooldown(self):
        self._inCooldown = False
