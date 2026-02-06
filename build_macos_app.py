#!/usr/bin/env python
"""
build_macos_app.py - Create a simple macOS app bundle for astrorank

This creates a minimal .app bundle that can be launched from the Finder
and will show the proper icon in the dock.

Run with: python build_macos_app.py
"""

import os
import shutil
from pathlib import Path

def create_app_bundle():
    """Create a simple macOS app bundle"""
    
    app_name = "astrorank"
    app_path = Path(f"{app_name}.app")
    
    # Remove existing app bundle if it exists
    if app_path.exists():
        shutil.rmtree(app_path)
    
    # Create directory structure
    (app_path / "Contents" / "MacOS").mkdir(parents=True, exist_ok=True)
    (app_path / "Contents" / "Resources").mkdir(parents=True, exist_ok=True)
    
    # Create the launcher script
    launcher_script = app_path / "Contents" / "MacOS" / app_name
    launcher_script.write_text("""#!/bin/bash
# Find the app's Resources directory
APP_DIR="$(cd "$(dirname "$0")" && pwd)/.."

# Set up Python path to find our modules
export PYTHONPATH="${APP_DIR}/Resources:${PYTHONPATH}"

# Run the application
python3 "${APP_DIR}/Resources/astrorank.py" "$@"
""")
    launcher_script.chmod(0o755)
    
    # Copy the Python module
    shutil.copy("astrorank/astrorank.py", app_path / "Contents" / "Resources")
    shutil.copy("astrorank/utils.py", app_path / "Contents" / "Resources")
    
    # Copy the logo/icon
    resources_logo_dir = app_path / "Contents" / "Resources" / "logo"
    resources_logo_dir.mkdir(exist_ok=True)
    shutil.copy("astrorank/logo/astrorank_logo.png", resources_logo_dir)
    
    # Create Info.plist
    plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>astrorank</string>
    <key>CFBundleIdentifier</key>
    <string>com.eriksolhaug.astrorank</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>astrorank</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>NSMainNibFile</key>
    <string>MainMenu</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>CFBundleIconFile</key>
    <string>logo/astrorank_logo.png</string>
    <key>CFBundleDisplayName</key>
    <string>astrorank - Image Ranking Tool</string>
</dict>
</plist>
"""
    
    plist_path = app_path / "Contents" / "Info.plist"
    plist_path.write_text(plist_content)
    
    print(f"✓ Created {app_name}.app bundle")
    print(f"✓ To run: open {app_name}.app")
    print(f"✓ Or: {app_name}.app/Contents/MacOS/{app_name} /path/to/images")

if __name__ == "__main__":
    create_app_bundle()
