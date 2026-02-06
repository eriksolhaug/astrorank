"""
UI utilities for astrorank
"""

from pathlib import Path
from PyQt5.QtGui import QIcon


def get_astrorank_icon():
    """Load and return the astrorank logo as a QIcon for use in all windows."""
    # Try multiple possible paths to find the logo
    possible_paths = [
        # When running from development
        Path(__file__).parent.parent / 'logo' / 'astrorank_logo.png',
        # When installed in package
        Path(__file__).parent / 'logo' / 'astrorank_logo.png',
        # Alternative path
        Path(__file__).parent / '..' / 'logo' / 'astrorank_logo.png',
    ]
    
    for logo_path in possible_paths:
        resolved_path = logo_path.resolve()
        if resolved_path.exists():
            return QIcon(str(resolved_path))
    
    # If logo not found, return empty icon
    return QIcon()
