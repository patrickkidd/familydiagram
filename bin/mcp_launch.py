"""
Test script for debugging MCP server launch with auto-login.
Run this in the debugger to step through the launch flow.
"""

import sys
import time
from pathlib import Path

# Add mcpserver to path (script is in familydiagram/bin/, mcpserver is in familydiagram/mcpserver/)
sys.path.insert(0, str(Path(__file__).parent.parent / "mcpserver"))

from mcp_server import TestSession, LoginState

# Set breakpoints in:
# - mcp_server.py: _populate_logged_in_data()
# - appconfig.py: read()
# - appcontroller.py: where lastSessionData is read (~line 115)

session = TestSession.get_instance()
print("Launching app with login_state=logged_in...")

success, msg = session.launch(
    headless=False, login_state=LoginState.LoggedIn, enable_bridge=True
)
print(f"Launch result: success={success}, msg={msg}")

if not success:
    print("Launch failed!")
    sys.exit(1)

print("Waiting for app to initialize...")
time.sleep(5)

if session._bridge:
    print("Querying app state...")
    result = session._bridge.send_command({"command": "get_app_state"})
    print(f"App state: {result}")
else:
    print("Bridge not connected!")

# Get stdout/stderr from the subprocess
session.collect_output()
print(f"\n--- App stdout ({len(session._stdout_lines)} lines) ---")
for line in session._stdout_lines[-50:]:
    print(line)
if session._stderr_lines:
    print(f"\n--- App stderr ({len(session._stderr_lines)} lines) ---")
    for line in session._stderr_lines[-20:]:
        print(line)

input("\nPress Enter to close the app...")
session.close(force=True)
print("Done.")
