#!/usr/bin/env python3
"""Profile diagram loading performance."""

import cProfile
import pstats
import sys
import os
from io import StringIO

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pkdiagram.pyqt import QApplication
from pkdiagram.scene import Scene
from pkdiagram import util

def load_diagram(filepath):
    """Load a diagram file and return the scene."""
    scene = Scene()

    # Handle .fd bundle directories
    if os.path.isdir(filepath):
        filepath = os.path.join(filepath, 'diagram.pickle')

    # Read the file
    with open(filepath, 'rb') as f:
        import pickle
        data = pickle.load(f)

    # Load into scene
    error = scene.read(data)
    if error:
        print(f"Error loading: {error}")
        return None

    return scene

def main():
    filepath = "/Users/patrick/Library/Mobile Documents/iCloud~com~vedanamedia~familydiagram/Documents/FD Presentations/Guiterrez.fd"

    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return 1

    # Need QApplication for Qt
    app = QApplication(sys.argv)

    print(f"Profiling load of: {filepath}")
    print("=" * 80)

    # Profile the load
    profiler = cProfile.Profile()
    profiler.enable()

    scene = load_diagram(filepath)

    profiler.disable()

    if scene:
        print(f"Loaded {len(scene.people())} people, {len(scene.events())} events, {len(scene.emotions())} emotions")

    # Print stats
    s = StringIO()
    stats = pstats.Stats(profiler, stream=s)
    stats.strip_dirs()
    stats.sort_stats('cumulative')

    print("\n" + "=" * 80)
    print("Top 50 functions by cumulative time:")
    print("=" * 80)
    stats.print_stats(50)
    print(s.getvalue())

    # Print callers for slow functions
    print("\n" + "=" * 80)
    print("Callers for Scene.read and related methods:")
    print("=" * 80)
    stats.print_callers('read', 20)

    return 0

if __name__ == '__main__':
    sys.exit(main())
