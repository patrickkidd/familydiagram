"""
Snapshot and screenshot utilities for UI testing.
"""

import base64
import hashlib
import io
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union, List, TYPE_CHECKING

from pkdiagram.pyqt import (
    Qt,
    QWidget,
    QQuickItem,
    QQuickWidget,
    QPixmap,
    QImage,
    QApplication,
    QScreen,
    QBuffer,
    QByteArray,
    QRect,
    QPainter,
)

if TYPE_CHECKING:
    from .app_controller import AppTestController

log = logging.getLogger(__name__)


class SnapshotManager:
    """
    Manages UI snapshots and screenshots for testing.

    Provides methods for:
    - Taking screenshots of windows, widgets, and QML items
    - Comparing snapshots for regression testing
    - Saving and loading snapshots
    - Generating snapshot diffs
    """

    def __init__(
        self,
        controller: "AppTestController",
        snapshotDir: Optional[str] = None,
    ):
        self._controller = controller
        self._snapshotDir = snapshotDir or os.path.join(os.getcwd(), "snapshots")
        self._snapshots: Dict[str, bytes] = {}

    @property
    def snapshotDir(self) -> str:
        """Get the snapshot directory path."""
        return self._snapshotDir

    @snapshotDir.setter
    def snapshotDir(self, value: str):
        """Set the snapshot directory path."""
        self._snapshotDir = value

    def _ensureSnapshotDir(self):
        """Ensure the snapshot directory exists."""
        os.makedirs(self._snapshotDir, exist_ok=True)

    # -------------------------------------------------------------------------
    # Screenshot Capture
    # -------------------------------------------------------------------------

    def captureWindow(
        self,
        window: Optional[QWidget] = None,
        format: str = "PNG",
    ) -> Optional[bytes]:
        """
        Capture a screenshot of a window.

        Args:
            window: The window to capture. Defaults to main window.
            format: Image format (PNG, JPG, BMP)

        Returns:
            Image data as bytes, or None on failure
        """
        if window is None:
            window = self._controller.mainWindow

        if window is None:
            log.error("No window available to capture")
            return None

        self._controller.processEvents()

        # Grab the window
        pixmap = window.grab()
        return self._pixmapToBytes(pixmap, format)

    def captureWidget(
        self,
        widget: Union[str, QWidget],
        format: str = "PNG",
    ) -> Optional[bytes]:
        """
        Capture a screenshot of a specific widget.

        Args:
            widget: Widget object name or QWidget instance
            format: Image format

        Returns:
            Image data as bytes, or None on failure
        """
        if isinstance(widget, str):
            widget = self._controller.findWidget(widget)

        if widget is None:
            log.error("Widget not found")
            return None

        self._controller.processEvents()
        pixmap = widget.grab()
        return self._pixmapToBytes(pixmap, format)

    def captureQmlItem(
        self,
        item: Union[str, QQuickItem],
        format: str = "PNG",
    ) -> Optional[bytes]:
        """
        Capture a screenshot of a QML item.

        Args:
            item: QML item objectName or QQuickItem instance
            format: Image format

        Returns:
            Image data as bytes, or None on failure
        """
        if isinstance(item, str):
            item = self._controller.findQmlItem(item)

        if item is None:
            log.error("QML item not found")
            return None

        self._controller.processEvents()

        # Find the containing QQuickWidget
        from .element_finder import ElementFinder

        finder = ElementFinder(self._controller)
        quickWidget = finder.findContainingQuickWidget(item)

        if quickWidget is None:
            log.error("Could not find QQuickWidget for item")
            return None

        # Get item bounds in widget coordinates
        rect = item.mapRectToScene(item.boundingRect())
        widgetRect = QRect(
            int(rect.x()),
            int(rect.y()),
            int(rect.width()),
            int(rect.height()),
        )

        # Grab the region
        pixmap = quickWidget.grab(widgetRect)
        return self._pixmapToBytes(pixmap, format)

    def captureScreen(self, format: str = "PNG") -> Optional[bytes]:
        """
        Capture the entire screen.

        Args:
            format: Image format

        Returns:
            Image data as bytes, or None on failure
        """
        screen = QApplication.primaryScreen()
        if screen is None:
            log.error("No screen available")
            return None

        pixmap = screen.grabWindow(0)
        return self._pixmapToBytes(pixmap, format)

    def captureRegion(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        window: Optional[QWidget] = None,
        format: str = "PNG",
    ) -> Optional[bytes]:
        """
        Capture a specific region of a window.

        Args:
            x: X coordinate
            y: Y coordinate
            width: Region width
            height: Region height
            window: Window to capture from (defaults to main window)
            format: Image format

        Returns:
            Image data as bytes, or None on failure
        """
        if window is None:
            window = self._controller.mainWindow

        if window is None:
            log.error("No window available")
            return None

        self._controller.processEvents()
        pixmap = window.grab(QRect(x, y, width, height))
        return self._pixmapToBytes(pixmap, format)

    def _pixmapToBytes(self, pixmap: QPixmap, format: str) -> Optional[bytes]:
        """Convert a QPixmap to bytes."""
        if pixmap.isNull():
            return None

        buffer = QByteArray()
        qbuffer = QBuffer(buffer)
        qbuffer.open(QBuffer.WriteOnly)
        pixmap.save(qbuffer, format)
        return bytes(buffer)

    # -------------------------------------------------------------------------
    # Snapshot Management
    # -------------------------------------------------------------------------

    def saveSnapshot(
        self,
        name: str,
        data: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save a snapshot to disk.

        Args:
            name: Snapshot name (without extension)
            data: Image data
            metadata: Optional metadata to save alongside

        Returns:
            Path to the saved snapshot
        """
        self._ensureSnapshotDir()

        # Save image
        imagePath = os.path.join(self._snapshotDir, f"{name}.png")
        with open(imagePath, "wb") as f:
            f.write(data)

        # Save metadata if provided
        if metadata is not None:
            metaPath = os.path.join(self._snapshotDir, f"{name}.json")
            metadata["timestamp"] = datetime.now().isoformat()
            metadata["hash"] = hashlib.md5(data).hexdigest()
            with open(metaPath, "w") as f:
                json.dump(metadata, f, indent=2)

        self._snapshots[name] = data
        log.info(f"Saved snapshot: {imagePath}")
        return imagePath

    def loadSnapshot(self, name: str) -> Optional[bytes]:
        """
        Load a snapshot from disk.

        Args:
            name: Snapshot name

        Returns:
            Image data as bytes, or None if not found
        """
        # Check cache first
        if name in self._snapshots:
            return self._snapshots[name]

        imagePath = os.path.join(self._snapshotDir, f"{name}.png")
        if not os.path.exists(imagePath):
            log.warning(f"Snapshot not found: {imagePath}")
            return None

        with open(imagePath, "rb") as f:
            data = f.read()

        self._snapshots[name] = data
        return data

    def loadSnapshotMetadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load snapshot metadata.

        Args:
            name: Snapshot name

        Returns:
            Metadata dict, or None if not found
        """
        metaPath = os.path.join(self._snapshotDir, f"{name}.json")
        if not os.path.exists(metaPath):
            return None

        with open(metaPath, "r") as f:
            return json.load(f)

    def deleteSnapshot(self, name: str) -> bool:
        """
        Delete a snapshot.

        Args:
            name: Snapshot name

        Returns:
            True if deleted successfully
        """
        imagePath = os.path.join(self._snapshotDir, f"{name}.png")
        metaPath = os.path.join(self._snapshotDir, f"{name}.json")

        deleted = False
        if os.path.exists(imagePath):
            os.remove(imagePath)
            deleted = True
        if os.path.exists(metaPath):
            os.remove(metaPath)

        if name in self._snapshots:
            del self._snapshots[name]

        return deleted

    def listSnapshots(self) -> List[str]:
        """
        List all available snapshots.

        Returns:
            List of snapshot names
        """
        if not os.path.exists(self._snapshotDir):
            return []

        snapshots = []
        for filename in os.listdir(self._snapshotDir):
            if filename.endswith(".png"):
                snapshots.append(filename[:-4])

        return sorted(snapshots)

    # -------------------------------------------------------------------------
    # Snapshot Comparison
    # -------------------------------------------------------------------------

    def compare(
        self,
        name: str,
        current: bytes,
        threshold: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Compare current screenshot with a saved snapshot.

        Args:
            name: Snapshot name to compare against
            current: Current screenshot data
            threshold: Acceptable difference threshold (0.0 - 1.0)

        Returns:
            Comparison result dict with keys:
            - match: True if images match within threshold
            - difference: Difference ratio (0.0 = identical)
            - baseline_exists: True if baseline snapshot exists
            - diff_image: Base64 encoded diff image (if different)
        """
        baseline = self.loadSnapshot(name)

        if baseline is None:
            return {
                "match": False,
                "difference": 1.0,
                "baseline_exists": False,
                "message": "Baseline snapshot does not exist",
            }

        # Load images
        baselineImage = QImage()
        baselineImage.loadFromData(baseline)

        currentImage = QImage()
        currentImage.loadFromData(current)

        # Check dimensions
        if baselineImage.size() != currentImage.size():
            return {
                "match": False,
                "difference": 1.0,
                "baseline_exists": True,
                "message": f"Size mismatch: baseline={baselineImage.size()}, current={currentImage.size()}",
            }

        # Calculate pixel difference
        difference, diffImage = self._calculateDifference(baselineImage, currentImage)

        result = {
            "match": difference <= threshold,
            "difference": difference,
            "baseline_exists": True,
            "threshold": threshold,
        }

        if difference > 0:
            # Encode diff image
            diffBytes = self._imageToBytes(diffImage)
            result["diff_image"] = base64.b64encode(diffBytes).decode("utf-8")

        return result

    def _calculateDifference(self, img1: QImage, img2: QImage) -> tuple[float, QImage]:
        """
        Calculate the difference between two images.

        Returns:
            Tuple of (difference ratio, difference image)
        """
        width = img1.width()
        height = img1.height()
        totalPixels = width * height

        # Create diff image
        diffImage = QImage(width, height, QImage.Format_ARGB32)
        diffImage.fill(Qt.transparent)

        differentPixels = 0

        for y in range(height):
            for x in range(width):
                pixel1 = img1.pixel(x, y)
                pixel2 = img2.pixel(x, y)

                if pixel1 != pixel2:
                    differentPixels += 1
                    # Mark difference in red
                    diffImage.setPixel(x, y, 0xFFFF0000)
                else:
                    # Show original with transparency
                    diffImage.setPixel(x, y, (pixel1 & 0x00FFFFFF) | 0x40000000)

        difference = differentPixels / totalPixels if totalPixels > 0 else 0.0
        return difference, diffImage

    def _imageToBytes(self, image: QImage) -> bytes:
        """Convert a QImage to bytes."""
        buffer = QByteArray()
        qbuffer = QBuffer(buffer)
        qbuffer.open(QBuffer.WriteOnly)
        image.save(qbuffer, "PNG")
        return bytes(buffer)

    def updateBaseline(self, name: str, data: bytes) -> str:
        """
        Update a baseline snapshot.

        Args:
            name: Snapshot name
            data: New image data

        Returns:
            Path to the saved snapshot
        """
        return self.saveSnapshot(
            name,
            data,
            metadata={"updated": True, "previous_hash": self._getSnapshotHash(name)},
        )

    def _getSnapshotHash(self, name: str) -> Optional[str]:
        """Get the hash of an existing snapshot."""
        data = self.loadSnapshot(name)
        if data is None:
            return None
        return hashlib.md5(data).hexdigest()

    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------

    def takeAndSave(
        self,
        name: str,
        target: Optional[Union[str, QWidget, QQuickItem]] = None,
    ) -> str:
        """
        Take a snapshot and save it.

        Args:
            name: Snapshot name
            target: Optional specific target (widget name, QWidget, or QQuickItem)
                   Defaults to main window.

        Returns:
            Path to the saved snapshot
        """
        if target is None:
            data = self.captureWindow()
        elif isinstance(target, str):
            # Try widget first, then QML
            widget = self._controller.findWidget(target)
            if widget is not None:
                data = self.captureWidget(widget)
            else:
                item = self._controller.findQmlItem(target)
                if item is not None:
                    data = self.captureQmlItem(item)
                else:
                    log.error(f"Target not found: {target}")
                    return ""
        elif isinstance(target, QQuickItem):
            data = self.captureQmlItem(target)
        else:
            data = self.captureWidget(target)

        if data is None:
            log.error("Failed to capture snapshot")
            return ""

        return self.saveSnapshot(name, data)

    def assertMatch(
        self,
        name: str,
        target: Optional[Union[str, QWidget, QQuickItem]] = None,
        threshold: float = 0.0,
        updateOnFail: bool = False,
    ) -> bool:
        """
        Assert that a current screenshot matches a baseline.

        Args:
            name: Snapshot name to compare against
            target: Optional specific target
            threshold: Acceptable difference threshold
            updateOnFail: If True, update baseline when comparison fails

        Returns:
            True if match, raises AssertionError otherwise
        """
        if target is None:
            current = self.captureWindow()
        elif isinstance(target, str):
            widget = self._controller.findWidget(target)
            if widget is not None:
                current = self.captureWidget(widget)
            else:
                item = self._controller.findQmlItem(target)
                current = self.captureQmlItem(item) if item else None
        elif isinstance(target, QQuickItem):
            current = self.captureQmlItem(target)
        else:
            current = self.captureWidget(target)

        if current is None:
            raise AssertionError("Failed to capture current screenshot")

        result = self.compare(name, current, threshold)

        if not result["match"]:
            if not result.get("baseline_exists"):
                # Create baseline on first run
                self.saveSnapshot(name, current, metadata={"auto_created": True})
                log.info(f"Created baseline snapshot: {name}")
                return True

            if updateOnFail:
                self.updateBaseline(name, current)
                log.warning(f"Updated baseline snapshot: {name}")
                return True

            # Save current for comparison
            self._ensureSnapshotDir()
            currentPath = os.path.join(self._snapshotDir, f"{name}_current.png")
            with open(currentPath, "wb") as f:
                f.write(current)

            if "diff_image" in result:
                diffPath = os.path.join(self._snapshotDir, f"{name}_diff.png")
                with open(diffPath, "wb") as f:
                    f.write(base64.b64decode(result["diff_image"]))

            raise AssertionError(
                f"Snapshot mismatch for '{name}': "
                f"difference={result['difference']:.4f}, threshold={threshold}"
            )

        return True

    def toBase64(self, data: bytes) -> str:
        """Convert image data to base64 string."""
        return base64.b64encode(data).decode("utf-8")

    def fromBase64(self, data: str) -> bytes:
        """Convert base64 string to image data."""
        return base64.b64decode(data)
