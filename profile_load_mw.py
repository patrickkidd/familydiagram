#!/usr/bin/env python3
"""Profile diagram loading performance with full mainwindow."""

import cProfile
import pstats
import sys
import os
from io import StringIO

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pkdiagram.pyqt import QTimer
from pkdiagram.app.application import Application


def main():
    filepath = "/Users/patrick/Library/Mobile Documents/iCloud~com~vedanamedia~familydiagram/Documents/FD Presentations/Guiterrez.fd"

    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return 1

    print(f"Profiling load of: {filepath}")
    print("=" * 80)

    # Create full application
    app = Application(sys.argv)
    mw = app.mw

    profiler = cProfile.Profile()

    def start_load():
        """Start profiling and trigger file load."""
        # Trigger start profile action
        profiler.enable()

        # Open the file - this triggers all UI updates
        mw.open(filePath=filepath)

        # Stop profiling after load completes
        # Use a short timer to ensure UI updates are captured
        QTimer.singleShot(100, stop_profile)

    def stop_profile():
        """Stop profiling and print results."""
        profiler.disable()

        scene = mw.scene
        if scene:
            print(
                f"Loaded {len(scene.people())} people, {len(scene.events())} events, {len(scene.emotions())} emotions"
            )

        # Print stats
        s = StringIO()
        stats = pstats.Stats(profiler, stream=s)
        stats.strip_dirs()
        stats.sort_stats("cumulative")

        print("\n" + "=" * 80)
        print("Top 50 functions by cumulative time:")
        print("=" * 80)
        stats.print_stats(50)
        print(s.getvalue())

        # Print callers for slow functions
        print("\n" + "=" * 80)
        print("Callers for setDocument and related methods:")
        print("=" * 80)
        stats.print_callers("setDocument|read|setScene", 20)

        # Exit app
        QTimer.singleShot(0, app.quit)

    # Wait for mainwindow to be fully initialized before loading
    QTimer.singleShot(500, start_load)

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
