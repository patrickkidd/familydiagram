"""
MCP Server for end-to-end testing of the Family Diagram PyQt+QML application.

This server provides tools for Claude Code to:
- Launch and control the application
- Take UI screenshots
- Send keyboard and mouse input events
- Query UI element state
- Perform visual regression testing

Usage:
    # Run standalone
    python mcp_server.py

    # Or via uv
    uv run python mcp-server/mcp_server.py

Configuration:
    Add to .mcp.json in project root to use with Claude Code.
"""

import base64
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Add parent directory to path to import pkdiagram modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("familydiagram-mcp")

# Initialize MCP server
mcp = FastMCP("familydiagram-testing")


# =============================================================================
# Data Classes for Structured Responses
# =============================================================================


@dataclass
class AppStatus:
    """Application status information."""
    running: bool
    pid: Optional[int]
    uptime_seconds: Optional[float]
    window_title: Optional[str]


@dataclass
class ScreenshotResult:
    """Screenshot capture result."""
    success: bool
    path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    base64_data: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ElementInfo:
    """UI element information."""
    found: bool
    object_name: Optional[str] = None
    class_name: Optional[str] = None
    visible: Optional[bool] = None
    enabled: Optional[bool] = None
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    text: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class ActionResult:
    """Result of an action (click, type, etc.)."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# Session Management
# =============================================================================


class TestSession:
    """
    Manages the PyQt application test session.

    This class handles:
    - Application lifecycle (launch, close)
    - Process management
    - Communication with the running app
    """

    _instance: Optional["TestSession"] = None

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.start_time: Optional[float] = None
        self.project_root = Path(__file__).parent.parent
        self._screenshot_counter = 0

    @classmethod
    def get_instance(cls) -> "TestSession":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = TestSession()
        return cls._instance

    @property
    def is_running(self) -> bool:
        """Check if the application is running."""
        if self.process is None:
            return False
        return self.process.poll() is None

    @property
    def pid(self) -> Optional[int]:
        """Get process ID if running."""
        if self.is_running:
            return self.process.pid
        return None

    @property
    def uptime(self) -> Optional[float]:
        """Get uptime in seconds."""
        if self.is_running and self.start_time:
            return time.time() - self.start_time
        return None

    def launch(
        self,
        headless: bool = False,
        extra_args: Optional[List[str]] = None,
        timeout: int = 30,
    ) -> Tuple[bool, str]:
        """
        Launch the Family Diagram application.

        Args:
            headless: Run in headless mode (for CI/testing)
            extra_args: Additional command-line arguments
            timeout: Maximum time to wait for startup

        Returns:
            Tuple of (success, message)
        """
        if self.is_running:
            return False, f"Application already running (PID: {self.pid})"

        try:
            # Build command
            cmd = ["uv", "run", "python", "-m", "pkdiagram"]

            if extra_args:
                cmd.extend(extra_args)

            # Set up environment
            env = os.environ.copy()

            if headless:
                env["QT_QPA_PLATFORM"] = "offscreen"

            # Disable GPU for stability
            env["QT_QUICK_BACKEND"] = "software"

            logger.info(f"Launching application: {' '.join(cmd)}")

            self.process = subprocess.Popen(
                cmd,
                cwd=str(self.project_root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.start_time = time.time()

            # Wait for app to start
            time.sleep(2)

            if not self.is_running:
                stderr = self.process.stderr.read().decode() if self.process.stderr else ""
                return False, f"Application failed to start: {stderr}"

            logger.info(f"Application started (PID: {self.pid})")
            return True, f"Application started successfully (PID: {self.pid})"

        except Exception as e:
            logger.exception("Failed to launch application")
            return False, f"Failed to launch: {str(e)}"

    def close(self, force: bool = False, timeout: int = 10) -> Tuple[bool, str]:
        """
        Close the application.

        Args:
            force: Force kill if graceful shutdown fails
            timeout: Timeout for graceful shutdown

        Returns:
            Tuple of (success, message)
        """
        if not self.is_running:
            return True, "Application not running"

        pid = self.pid

        try:
            # Try graceful shutdown first
            self.process.terminate()

            try:
                self.process.wait(timeout=timeout)
                logger.info(f"Application terminated gracefully (PID: {pid})")
                return True, f"Application terminated (PID: {pid})"
            except subprocess.TimeoutExpired:
                if force:
                    self.process.kill()
                    self.process.wait(timeout=5)
                    logger.warning(f"Application force killed (PID: {pid})")
                    return True, f"Application force killed (PID: {pid})"
                else:
                    return False, "Graceful shutdown timed out. Use force=True to kill."

        except Exception as e:
            logger.exception("Failed to close application")
            return False, f"Failed to close: {str(e)}"
        finally:
            self.process = None
            self.start_time = None

    def get_screenshot_path(self, name: Optional[str] = None) -> Path:
        """Get a unique screenshot path."""
        screenshot_dir = self.project_root / "screenshots"
        screenshot_dir.mkdir(exist_ok=True)

        if name:
            return screenshot_dir / f"{name}.png"

        self._screenshot_counter += 1
        timestamp = int(time.time())
        return screenshot_dir / f"screenshot_{timestamp}_{self._screenshot_counter}.png"


# =============================================================================
# MCP Tools
# =============================================================================


@mcp.tool()
def launch_app(
    headless: bool = False,
    wait_seconds: int = 3,
) -> Dict[str, Any]:
    """
    Launch the Family Diagram application.

    Args:
        headless: Run in headless mode without display (for CI/automated testing)
        wait_seconds: Seconds to wait after launch for app to initialize

    Returns:
        Status dict with success, pid, and message
    """
    session = TestSession.get_instance()
    success, message = session.launch(headless=headless)

    if success and wait_seconds > 0:
        time.sleep(wait_seconds)

    return {
        "success": success,
        "pid": session.pid,
        "message": message,
    }


@mcp.tool()
def close_app(force: bool = False) -> Dict[str, Any]:
    """
    Close the Family Diagram application.

    Args:
        force: Force kill if graceful shutdown fails

    Returns:
        Status dict with success and message
    """
    session = TestSession.get_instance()
    success, message = session.close(force=force)

    return {
        "success": success,
        "message": message,
    }


@mcp.tool()
def get_app_status() -> Dict[str, Any]:
    """
    Get the current application status.

    Returns:
        Status dict with running state, pid, uptime
    """
    session = TestSession.get_instance()

    return {
        "running": session.is_running,
        "pid": session.pid,
        "uptime_seconds": session.uptime,
    }


@mcp.tool()
def take_screenshot(
    name: Optional[str] = None,
    return_base64: bool = False,
) -> Dict[str, Any]:
    """
    Take a screenshot of the application window.

    Args:
        name: Optional name for the screenshot file (without extension)
        return_base64: If True, include base64-encoded image data in response

    Returns:
        Dict with success, path, dimensions, and optionally base64 data
    """
    session = TestSession.get_instance()

    if not session.is_running:
        return {
            "success": False,
            "error": "Application not running. Use launch_app first.",
        }

    try:
        import pyautogui
        from PIL import Image

        # Get screenshot path
        output_path = session.get_screenshot_path(name)

        # Capture screenshot
        screenshot = pyautogui.screenshot()

        # Resize if too large (to stay within MCP response limits)
        max_dimension = 1920
        if screenshot.width > max_dimension or screenshot.height > max_dimension:
            ratio = min(max_dimension / screenshot.width, max_dimension / screenshot.height)
            new_size = (int(screenshot.width * ratio), int(screenshot.height * ratio))
            screenshot = screenshot.resize(new_size, Image.Resampling.LANCZOS)

        # Save
        screenshot.save(str(output_path), "PNG")

        result = {
            "success": True,
            "path": str(output_path),
            "width": screenshot.width,
            "height": screenshot.height,
        }

        if return_base64:
            import io
            buffer = io.BytesIO()
            screenshot.save(buffer, format="PNG")
            result["base64_data"] = base64.b64encode(buffer.getvalue()).decode("utf-8")

        logger.info(f"Screenshot saved: {output_path}")
        return result

    except ImportError:
        return {
            "success": False,
            "error": "pyautogui or Pillow not installed. Run: pip install pyautogui Pillow",
        }
    except Exception as e:
        logger.exception("Screenshot failed")
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
def click(
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
) -> Dict[str, Any]:
    """
    Click at screen coordinates.

    Args:
        x: X coordinate on screen
        y: Y coordinate on screen
        button: Mouse button - "left", "right", or "middle"
        clicks: Number of clicks (1 for single, 2 for double-click)

    Returns:
        Dict with success status
    """
    session = TestSession.get_instance()

    if not session.is_running:
        return {
            "success": False,
            "error": "Application not running",
        }

    try:
        import pyautogui

        pyautogui.click(x=x, y=y, button=button, clicks=clicks)

        logger.info(f"Clicked at ({x}, {y}) with {button} button, {clicks} time(s)")
        return {
            "success": True,
            "message": f"Clicked at ({x}, {y})",
        }

    except Exception as e:
        logger.exception("Click failed")
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
def double_click(x: int, y: int) -> Dict[str, Any]:
    """
    Double-click at screen coordinates.

    Args:
        x: X coordinate on screen
        y: Y coordinate on screen

    Returns:
        Dict with success status
    """
    return click(x=x, y=y, button="left", clicks=2)


@mcp.tool()
def right_click(x: int, y: int) -> Dict[str, Any]:
    """
    Right-click at screen coordinates.

    Args:
        x: X coordinate on screen
        y: Y coordinate on screen

    Returns:
        Dict with success status
    """
    return click(x=x, y=y, button="right", clicks=1)


@mcp.tool()
def move_mouse(x: int, y: int, duration: float = 0.25) -> Dict[str, Any]:
    """
    Move mouse to screen coordinates.

    Args:
        x: X coordinate
        y: Y coordinate
        duration: Time in seconds for the movement

    Returns:
        Dict with success status
    """
    try:
        import pyautogui

        pyautogui.moveTo(x=x, y=y, duration=duration)

        return {
            "success": True,
            "message": f"Moved mouse to ({x}, {y})",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
def drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: float = 0.5,
    button: str = "left",
) -> Dict[str, Any]:
    """
    Drag from one position to another.

    Args:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        duration: Time for the drag operation
        button: Mouse button to hold during drag

    Returns:
        Dict with success status
    """
    try:
        import pyautogui

        pyautogui.moveTo(start_x, start_y)
        pyautogui.drag(
            end_x - start_x,
            end_y - start_y,
            duration=duration,
            button=button,
        )

        logger.info(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
        return {
            "success": True,
            "message": f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
def type_text(
    text: str,
    interval: float = 0.02,
) -> Dict[str, Any]:
    """
    Type text using the keyboard.

    Args:
        text: Text to type
        interval: Delay between keystrokes in seconds

    Returns:
        Dict with success status
    """
    try:
        import pyautogui

        # pyautogui.write() only works with ASCII
        # For special characters, we need to use write() for ASCII and hotkey for others
        pyautogui.write(text, interval=interval)

        logger.info(f"Typed text: {text[:50]}{'...' if len(text) > 50 else ''}")
        return {
            "success": True,
            "message": f"Typed {len(text)} characters",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
def press_key(
    key: str,
    modifiers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Press a keyboard key, optionally with modifiers.

    Args:
        key: Key to press (e.g., "enter", "tab", "escape", "a", "f1")
        modifiers: Optional list of modifier keys (e.g., ["ctrl"], ["ctrl", "shift"])

    Returns:
        Dict with success status

    Examples:
        press_key("enter")           # Press Enter
        press_key("s", ["ctrl"])     # Ctrl+S
        press_key("z", ["ctrl", "shift"])  # Ctrl+Shift+Z
    """
    try:
        import pyautogui

        if modifiers:
            # Use hotkey for key combinations
            keys = modifiers + [key]
            pyautogui.hotkey(*keys)
            logger.info(f"Pressed: {'+'.join(keys)}")
        else:
            pyautogui.press(key)
            logger.info(f"Pressed: {key}")

        return {
            "success": True,
            "message": f"Pressed {'+'.join(modifiers + [key]) if modifiers else key}",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
def hotkey(*keys: str) -> Dict[str, Any]:
    """
    Press a key combination (hotkey).

    Args:
        *keys: Keys to press together (e.g., "ctrl", "s" for Ctrl+S)

    Returns:
        Dict with success status

    Examples:
        hotkey("ctrl", "s")           # Save
        hotkey("ctrl", "shift", "z")  # Redo
        hotkey("alt", "f4")           # Close window
    """
    try:
        import pyautogui

        pyautogui.hotkey(*keys)

        combo = "+".join(keys)
        logger.info(f"Hotkey: {combo}")
        return {
            "success": True,
            "message": f"Pressed {combo}",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
def scroll(
    clicks: int,
    x: Optional[int] = None,
    y: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Scroll the mouse wheel.

    Args:
        clicks: Number of scroll clicks (positive = up, negative = down)
        x: Optional X coordinate to scroll at
        y: Optional Y coordinate to scroll at

    Returns:
        Dict with success status
    """
    try:
        import pyautogui

        pyautogui.scroll(clicks, x=x, y=y)

        direction = "up" if clicks > 0 else "down"
        logger.info(f"Scrolled {direction} {abs(clicks)} clicks")
        return {
            "success": True,
            "message": f"Scrolled {direction} {abs(clicks)} clicks",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
def wait(seconds: float) -> Dict[str, Any]:
    """
    Wait for a specified number of seconds.

    Useful for waiting for UI animations, dialogs to appear, etc.

    Args:
        seconds: Time to wait in seconds

    Returns:
        Dict with success status
    """
    time.sleep(seconds)
    return {
        "success": True,
        "message": f"Waited {seconds} seconds",
    }


@mcp.tool()
def get_screen_size() -> Dict[str, Any]:
    """
    Get the screen dimensions.

    Returns:
        Dict with width and height of the screen
    """
    try:
        import pyautogui

        size = pyautogui.size()
        return {
            "success": True,
            "width": size.width,
            "height": size.height,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
def get_mouse_position() -> Dict[str, Any]:
    """
    Get the current mouse cursor position.

    Returns:
        Dict with x and y coordinates
    """
    try:
        import pyautogui

        pos = pyautogui.position()
        return {
            "success": True,
            "x": pos.x,
            "y": pos.y,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
def locate_on_screen(
    image_path: str,
    confidence: float = 0.9,
) -> Dict[str, Any]:
    """
    Locate an image on the screen.

    This is useful for finding UI elements by their appearance.

    Args:
        image_path: Path to the image file to find on screen
        confidence: Matching confidence threshold (0.0 to 1.0)

    Returns:
        Dict with success status and location if found
    """
    try:
        import pyautogui

        location = pyautogui.locateOnScreen(image_path, confidence=confidence)

        if location:
            return {
                "success": True,
                "found": True,
                "x": location.left,
                "y": location.top,
                "width": location.width,
                "height": location.height,
                "center_x": location.left + location.width // 2,
                "center_y": location.top + location.height // 2,
            }
        else:
            return {
                "success": True,
                "found": False,
                "message": "Image not found on screen",
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
def list_screenshots() -> Dict[str, Any]:
    """
    List all saved screenshots.

    Returns:
        Dict with list of screenshot files
    """
    session = TestSession.get_instance()
    screenshot_dir = session.project_root / "screenshots"

    if not screenshot_dir.exists():
        return {
            "success": True,
            "screenshots": [],
            "directory": str(screenshot_dir),
        }

    screenshots = sorted(screenshot_dir.glob("*.png"))

    return {
        "success": True,
        "screenshots": [str(p) for p in screenshots],
        "count": len(screenshots),
        "directory": str(screenshot_dir),
    }


@mcp.tool()
def compare_screenshots(
    baseline_path: str,
    current_path: Optional[str] = None,
    threshold: float = 0.01,
) -> Dict[str, Any]:
    """
    Compare two screenshots for visual differences.

    Args:
        baseline_path: Path to the baseline screenshot
        current_path: Path to current screenshot (if None, takes a new screenshot)
        threshold: Maximum acceptable difference ratio (0.0 to 1.0)

    Returns:
        Dict with comparison results
    """
    try:
        from PIL import Image
        import io

        # Load baseline
        baseline = Image.open(baseline_path)

        # Get current (either from file or take new)
        if current_path:
            current = Image.open(current_path)
        else:
            import pyautogui
            current = pyautogui.screenshot()

        # Resize current to match baseline if needed
        if baseline.size != current.size:
            current = current.resize(baseline.size, Image.Resampling.LANCZOS)

        # Compare pixels
        baseline_data = list(baseline.getdata())
        current_data = list(current.getdata())

        if len(baseline_data) != len(current_data):
            return {
                "success": False,
                "error": "Image sizes don't match",
            }

        different_pixels = sum(1 for b, c in zip(baseline_data, current_data) if b != c)
        total_pixels = len(baseline_data)
        difference_ratio = different_pixels / total_pixels

        match = difference_ratio <= threshold

        return {
            "success": True,
            "match": match,
            "difference_ratio": difference_ratio,
            "different_pixels": different_pixels,
            "total_pixels": total_pixels,
            "threshold": threshold,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# =============================================================================
# Main Entry Point
# =============================================================================


if __name__ == "__main__":
    logger.info("Starting Family Diagram MCP Testing Server")
    mcp.run(transport="stdio")
