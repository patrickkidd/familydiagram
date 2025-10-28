#!/usr/bin/env python3
"""Install .pth file to enable vendored packages from familydiagram/lib/site-packages"""
import os
import sys
from pathlib import Path


def install_pth():
    # Find site-packages in .venv
    site_packages = None
    for path in sys.path:
        if 'site-packages' in path and '.venv' in path:
            site_packages = Path(path)
            break

    if not site_packages:
        print("ERROR: Could not find .venv site-packages directory")
        sys.exit(1)

    # Get absolute path to vendored packages
    vendored_dir = Path(__file__).parent / "lib" / "site-packages"
    if not vendored_dir.exists():
        print(f"ERROR: Vendored directory does not exist: {vendored_dir}")
        sys.exit(1)

    # Create .pth file
    pth_file = site_packages / "familydiagram-vendored.pth"
    with open(pth_file, 'w') as f:
        f.write(str(vendored_dir.resolve()) + '\n')

    print(f"✓ Created: {pth_file}")
    print(f"  Points to: {vendored_dir.resolve()}")
    print("\nVendored packages will now be used instead of PyPI versions.")


if __name__ == '__main__':
    install_pth()
