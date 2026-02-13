"""
Utility functions for astrorank
"""

import os
import re
import json
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def get_jpg_files(directory: str) -> List[str]:
    """
    Get all .jpg files from a directory, sorted alphabetically.
    
    Args:
        directory: Path to the directory containing images
        
    Returns:
        List of .jpg filenames (not full paths)
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    jpg_files = sorted([f.name for f in dir_path.glob("*.jpg")])
    return jpg_files


def load_rankings(output_file: str) -> Dict[str, int]:
    """
    Load rankings from a previous session.
    
    Args:
        output_file: Path to the rankings file
        
    Returns:
        Dictionary with filename as key and rank as value
    """
    rankings = {}
    
    if not os.path.exists(output_file):
        return rankings
    
    try:
        with open(output_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 1:
                        filename = parts[0]
                        try:
                            rank = int(parts[1])
                            rankings[filename] = rank
                        except (ValueError, IndexError):
                            continue
    except Exception as e:
        print(f"Error loading rankings: {e}")
    
    return rankings


def save_rankings(output_file: str, rankings: Dict[str, int], jpg_files: List[str], comments: Dict[str, str] = None):
    """
    Save rankings to a file and comments to a separate file.
    
    Args:
        output_file: Path to save rankings to (e.g., rankings.txt)
        rankings: Dictionary with filename as key and rank as value
        jpg_files: List of all jpg files in order
        comments: Optional dictionary with filename as key and comment as value
    """
    if comments is None:
        comments = {}
    
    try:
        # Save all files to rankings.txt, with unranked files marked as empty or with placeholder
        with open(output_file, 'w') as f:
            for filename in jpg_files:
                if filename in rankings:
                    rank = rankings[filename]
                    f.write(f"{filename}\t{rank}\n")
                else:
                    # Write unranked files with empty rank field (or use a placeholder like "UNRANKED")
                    f.write(f"{filename}\t\n")
    except Exception as e:
        print(f"Error saving rankings: {e}")
    
    # Save all files with comments to a separate file
    try:
        comments_file = output_file.replace('.txt', '_comments.txt')
        with open(comments_file, 'w') as f:
            for filename in jpg_files:
                if filename in rankings:
                    rank = rankings[filename]
                else:
                    rank = ""
                comment = comments.get(filename, "")
                f.write(f"{filename}\t{rank}\t{comment}\n")
    except Exception as e:
        print(f"Error saving comments: {e}")


def find_next_unranked(jpg_files: List[str], rankings: Dict[str, int], current_index: int) -> int:
    """
    Find the next unranked image starting from current_index.
    
    Args:
        jpg_files: List of all jpg files
        rankings: Dictionary with filename as key and rank as value
        current_index: Starting index to search from
        
    Returns:
        Index of next unranked image, or -1 if all are ranked
    """
    for i in range(current_index, len(jpg_files)):
        if jpg_files[i] not in rankings:
            return i
    
    return -1


def find_first_unranked(jpg_files: List[str], rankings: Dict[str, int]) -> int:
    """
    Find the first unranked image.
    
    Args:
        jpg_files: List of all jpg files
        rankings: Dictionary with filename as key and rank as value
        
    Returns:
        Index of first unranked image, or 0 if all are ranked
    """
    for i, filename in enumerate(jpg_files):
        if filename not in rankings:
            return i
    
    return 0


def is_valid_rank(rank_str: str, min_rank=0, max_rank=3, rank_map=None) -> Tuple[bool]:
    """
    Validate that the input is a valid rank from configured ranks.
    
    Args:
        rank_str: String input from user
        min_rank: Minimum valid rank value (used for numeric ranges)
        max_rank: Maximum valid rank value (used for numeric ranges)
        rank_map: Dictionary mapping rank keys to rank values (preferred if provided)
        
    Returns:
        Tuple of (is_valid, rank_value)
    """
    rank_str = rank_str.strip()
    
    # If rank_map provided, check if input is a valid key
    if rank_map:
        if rank_str in rank_map:
            return True, rank_map[rank_str]
        return False, None
    
    # Fall back to numeric validation
    try:
        rank = int(rank_str)
        if min_rank <= rank <= max_rank:
            return True, rank
    except ValueError:
        pass
    
    return False, None


def sexagesimal_to_decimal(ra_str: str, dec_str: str) -> Optional[Tuple[float, float]]:
    """
    Convert sexagesimal coordinates to decimal degrees.
    
    Sexagesimal format: HHMMSS.SS+DDMMSS.SS or HHMMSS.SS-DDMMSS.SS
    Where + or - separates RA and Dec
    
    Args:
        ra_str: RA in sexagesimal format (HHMMSS.SS)
        dec_str: Dec in sexagesimal format (DDMMSS.SS with +/- sign)
        
    Returns:
        Tuple of (ra_decimal, dec_decimal), or None if parsing fails
    """
    try:
        # Parse RA (hours, minutes, seconds)
        # Format: HHMMSS.SS (at least 6 digits before decimal, then optional fractional seconds)
        ra_str = ra_str.strip()
        if len(ra_str) < 6:
            return None
            
        ra_hh = int(ra_str[0:2])
        ra_mm = int(ra_str[2:4])
        ra_ss = float(ra_str[4:])
        
        # RA in decimal degrees (convert from hours to degrees: multiply by 15)
        ra_decimal = (ra_hh + ra_mm/60.0 + ra_ss/3600.0) * 15.0
        
        # Parse Dec (degrees, arcminutes, arcseconds)
        # Format: ±DDMMSS.SS (sign, then at least 6 digits, optional fractional seconds)
        dec_str = dec_str.strip()
        if len(dec_str) < 7:  # At least 1 sign char + 6 digits
            return None
        
        # Extract sign
        sign = 1.0
        if dec_str[0] == '-':
            sign = -1.0
            dec_str = dec_str[1:]
        elif dec_str[0] == '+':
            dec_str = dec_str[1:]
        
        if len(dec_str) < 6:
            return None
            
        dec_dd = int(dec_str[0:2])
        dec_mm = int(dec_str[2:4])
        dec_ss = float(dec_str[4:])
        
        # Dec in decimal degrees
        dec_decimal = sign * (dec_dd + dec_mm/60.0 + dec_ss/3600.0)
        
        return (ra_decimal, dec_decimal)
    except (ValueError, IndexError):
        return None


def detect_coordinate_format(ra_str: str, dec_str: str) -> str:
    """
    Detect coordinate format: 'decimal' or 'sexagesimal'
    
    Args:
        ra_str: RA string from filename
        dec_str: Dec string from filename
        
    Returns:
        'decimal', 'sexagesimal', or 'unknown'
    """
    ra_str = ra_str.strip()
    dec_str = dec_str.strip()
    
    # Check for sexagesimal: contains + or - at the junction, and RA/Dec are mostly digits
    # Sexagesimal format example: 085925.43+074849.05 or 085925.43-074849.05
    if any(c in dec_str[:1] for c in ['+', '-']):
        # Try to detect if it looks like sexagesimal
        if len(ra_str) >= 6 and len(dec_str) >= 7:
            # Check if characters are mostly digits/dots
            ra_valid = all(c.isdigit() or c == '.' for c in ra_str)
            dec_valid = all(c.isdigit() or c == '.' or c in ['+', '-'] for c in dec_str)
            if ra_valid and dec_valid:
                return 'sexagesimal'
    
    # Check for decimal: should be parseable as float
    try:
        float(ra_str)
        float(dec_str)
        # Both are valid floats, check if they look like coordinates
        # RA should be 0-360 (or 0-24 in hours, but we'll accept wider range)
        # Dec should be -90 to +90
        ra_float = float(ra_str)
        dec_float = float(dec_str)
        if 0 <= ra_float <= 360 and -90 <= dec_float <= 90:
            return 'decimal'
    except ValueError:
        pass
    
    return 'unknown'


def parse_radec_from_filename(filename: str) -> Optional[Tuple[float, float]]:
    """
    Parse RA and Dec from filename. Supports two formats:
    1. Decimal degrees: <name>_<ra>_<dec>.jpg (e.g., qso_100.00371_-69.056759.jpg)
    2. Sexagesimal: <prefix>HHMMSS.SS±DDMMSS.SS.jpg (e.g., COOLJ085925.43+074849.05.jpg)
    
    Auto-detects format and converts both to decimal degrees.
    
    Args:
        filename: Filename to parse
        
    Returns:
        Tuple of (ra_decimal, dec_decimal) as floats, or None if parsing fails
    """
    name_without_ext = filename.rsplit('.', 1)[0]
    
    # Try sexagesimal format first (format with + or - sign)
    # Look for pattern: ...+... or ...-... 
    for sep_idx, char in enumerate(name_without_ext):
        if char in ['+', '-']:
            # Found a separator, try to extract coordinates
            ra_part = name_without_ext[:sep_idx]
            dec_part = name_without_ext[sep_idx:]
            
            # Extract the trailing digits/dots from ra_part (RA coordinates)
            ra_match_start = len(ra_part) - 1
            while ra_match_start >= 0 and (ra_part[ra_match_start].isdigit() or ra_part[ra_match_start] == '.'):
                ra_match_start -= 1
            ra_match_start += 1
            
            if ra_match_start < len(ra_part):
                ra_str = ra_part[ra_match_start:]
                dec_str = dec_part
                
                # Try sexagesimal parsing
                result = sexagesimal_to_decimal(ra_str, dec_str)
                if result:
                    return result
    
    # Try decimal degrees format: split by underscores and get last two parts
    parts = name_without_ext.split('_')
    
    if len(parts) >= 3:
        try:
            ra = float(parts[-2])
            dec = float(parts[-1])
            
            # Validate ranges
            if 0 <= ra <= 360 and -90 <= dec <= 90:
                return (ra, dec)
        except (ValueError, IndexError):
            pass
    
    return None


def load_config(config_file: str = "config.json") -> Dict:
    """
    Load configuration from config.json
    
    Args:
        config_file: Path to config.json file. If relative, searches in current dir, then in package directory
        
    Returns:
        Dictionary with configuration, or defaults if file not found
    """
    default_config = {
        "browser": {
            "enabled": True,
            "url_template": "https://www.legacysurvey.org/viewer/?ra={ra}&dec={dec}&layer=ls-dr10&zoom=16"
        },
        "secondary_download": {
            "enabled": True,
            "name": "WISE",
            "url_template": "https://www.legacysurvey.org/viewer/decals-unwise-neo11/{ra}/{dec}?layer=unwise-neo1&zoom=15",
            "url_template_download": "https://www.legacysurvey.org/viewer/fits-cutout?ra={ra}&dec={dec}&layer=unwise-neo7&size=512&pixscale=0.263672&bands=w1",
            "extensions": {
                "0": ["R", "G"],
                "1": ["B"]
            }
        },
        "secondary_dir": {
            "enabled": False,
            "path": ""
        },
        "ranks": {
            "0": 0,
            "1": 1,
            "2": 2,
            "3": 3,
            "backtick": 0
        }
    }
    
    # Try current working directory first
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"Error loading config from {config_file}: {e}")
            return default_config
    
    # Try package directory if relative path
    if not os.path.isabs(config_file):
        package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        package_config = os.path.join(package_dir, config_file)
        if os.path.exists(package_config):
            try:
                with open(package_config, 'r') as f:
                    config = json.load(f)
                    return config
            except Exception as e:
                print(f"Error loading config from {package_config}: {e}")
                return default_config
    
    return default_config


def download_secondary_image(ra: float, dec: float, output_dir: str, config: Dict) -> Optional[str]:
    """
    Download secondary image FITS file and create RGB composite JPG based on config
    
    Args:
        ra: Right ascension
        dec: Declination
        output_dir: Directory to save image to
        config: Configuration dictionary with secondary_download section
        
    Returns:
        Path to generated RGB JPG image, or None if download failed
    """
    import numpy as np
    from PIL import Image
    
    try:
        from astropy.io import fits
    except ImportError:
        print("Error: astropy required for FITS processing. Install with: pip install astropy")
        return None
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get configuration
    secondary_config = config.get("secondary_download", {})
    survey_name = secondary_config.get("name", "secondary")
    url_template_download = secondary_config.get("url_template_download")
    extensions_mapping = secondary_config.get("extensions", {})
    
    if not url_template_download:
        print(f"Error: url_template_download not found in secondary_download config")
        return None
    
    # Substitute placeholders in download URL
    fits_url = url_template_download.replace("{ra}", str(ra)).replace("{dec}", str(dec))
    
    try:
        # Download FITS file
        response = requests.get(fits_url, timeout=30)
        response.raise_for_status()
        
        # Save temporary FITS file
        fits_path = Path(output_dir) / f"temp_{survey_name}_{ra}_{dec}.fits"
        
        with open(fits_path, 'wb') as f:
            f.write(response.content)
        
        # Load FITS data
        hdul = fits.open(fits_path)
        data = hdul[0].data.astype(float)
        hdul.close()
        
        # Get image dimensions (assume last two dims are spatial)
        if len(data.shape) == 3:
            n_layers = data.shape[0]
            height, width = data.shape[1], data.shape[2]
        elif len(data.shape) == 2:
            n_layers = 1
            height, width = data.shape
            data = np.expand_dims(data, axis=0)  # Add layer dimension
        else:
            print(f"Error: Unexpected FITS shape {data.shape}")
            fits_path.unlink()
            return None
        
        # Apply asinh (inverse hyperbolic sine) scaling - better for astronomy
        def apply_asinh_scaling(data, Q=8.0):
            """
            Apply asinh scaling for better visualization of astronomical images.
            This handles both bright and faint sources well.
            
            Args:
                data: Input image data
                Q: Softening parameter (default 8.0). Higher Q = more contrast
            """
            if data.size == 0:
                return np.zeros_like(data)
            
            # Remove NaNs
            data_clean = np.where(np.isnan(data), 0, data)
            
            # Normalize to [0, 1] using percentiles for better handling of outliers
            flat = np.ravel(data_clean)
            flat_sorted = np.sort(flat[flat > 0])  # Only look at positive values
            
            if len(flat_sorted) == 0:
                return np.zeros_like(data_clean)
            
            # Use percentiles to set min/max
            vmin = np.percentile(flat_sorted, 1)
            vmax = np.percentile(flat_sorted, 99)
            
            if vmin == vmax:
                vmin = flat_sorted.min()
                vmax = flat_sorted.max()
            
            # Normalize to [0, 1]
            normalized = (data_clean - vmin) / (vmax - vmin)
            normalized = np.clip(normalized, 0, 1)
            
            # Apply asinh scaling: this compresses bright sources while preserving faint detail
            # asinh(Q * x) / asinh(Q) maps [0, 1] -> [0, 1] with non-linear stretching
            scaled = np.arcsinh(Q * normalized) / np.arcsinh(Q)
            scaled = np.clip(scaled, 0, 1)
            
            return (scaled * 255).astype(np.uint8)
        
        # Create RGB image based on extension mapping
        rgb = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Map each layer to RGB channels according to config
        for layer_idx_str, channels in extensions_mapping.items():
            layer_idx = int(layer_idx_str)
            if layer_idx < n_layers:
                scaled = apply_asinh_scaling(data[layer_idx])
                # Handle both single channel (string) and multiple channels (list)
                if isinstance(channels, str):
                    channels = [channels]
                for channel in channels:
                    if channel == "R":
                        rgb[:, :, 0] = scaled
                    elif channel == "G":
                        rgb[:, :, 1] = scaled
                    elif channel == "B":
                        rgb[:, :, 2] = scaled
        
        # Flip image vertically (across y-axis) for correct orientation
        rgb = np.flipud(rgb)
        
        # Convert to PIL Image and save as JPG
        image = Image.fromarray(rgb, mode='RGB')
        output_path = Path(output_dir) / f"{survey_name}_{ra}_{dec}.jpg"
        image.save(output_path, quality=90)
        
        # Clean up temporary FITS file
        fits_path.unlink()
        
        return str(output_path)
    
    except Exception as e:
        print(f"Error downloading/processing secondary image: {e}")
        return None


def parse_key_string(key_string: str) -> List[str]:
    """
    Parse a key string from config into a list of key names.
    Examples: "q" -> ["q"], "plus,equal" -> ["plus", "equal"], "shift+left" -> ["shift+left"]
    
    Args:
        key_string: String representation of key(s)
        
    Returns:
        List of key name strings
    """
    return [k.strip() for k in key_string.split(',')]


def string_to_qt_key(key_string: str) -> List:
    """
    Convert string representation of keys to Qt key enums.
    Examples: "q" -> Qt.Key_Q, "delete" -> Qt.Key_Delete, "backtick" -> Qt.Key_QuoteLeft
    
    Args:
        key_string: String representation of key (e.g., "q", "delete", "shift+left")
        
    Returns:
        List of (key_enum, has_shift) tuples
    """
    from PyQt5.QtCore import Qt
    
    # Key mappings from string names to Qt enums
    key_map = {
        "delete": Qt.Key_Delete,
        "backspace": Qt.Key_Backspace,
        "q": Qt.Key_Q,
        "c": Qt.Key_C,
        "f": Qt.Key_F,
        "r": Qt.Key_R,
        "?": Qt.Key_Question,
        "l": Qt.Key_L,
        "d": Qt.Key_D,
        "k": Qt.Key_K,
        "g": Qt.Key_G,
        "b": Qt.Key_B,
        "plus": Qt.Key_Plus,
        "equal": Qt.Key_Equal,
        "minus": Qt.Key_Minus,
        "0": Qt.Key_0,
        "1": Qt.Key_1,
        "2": Qt.Key_2,
        "3": Qt.Key_3,
        "4": Qt.Key_4,
        "5": Qt.Key_5,
        "6": Qt.Key_6,
        "7": Qt.Key_7,
        "8": Qt.Key_8,
        "9": Qt.Key_9,
        "a": Qt.Key_A,
        "b": Qt.Key_B,
        "c": Qt.Key_C,
        "d": Qt.Key_D,
        "e": Qt.Key_E,
        "f": Qt.Key_F,
        "g": Qt.Key_G,
        "h": Qt.Key_H,
        "i": Qt.Key_I,
        "j": Qt.Key_J,
        "k": Qt.Key_K,
        "l": Qt.Key_L,
        "m": Qt.Key_M,
        "n": Qt.Key_N,
        "o": Qt.Key_O,
        "p": Qt.Key_P,
        "q": Qt.Key_Q,
        "r": Qt.Key_R,
        "s": Qt.Key_S,
        "t": Qt.Key_T,
        "u": Qt.Key_U,
        "v": Qt.Key_V,
        "w": Qt.Key_W,
        "x": Qt.Key_X,
        "y": Qt.Key_Y,
        "z": Qt.Key_Z,
        "backtick": Qt.Key_QuoteLeft,
        "space": Qt.Key_Space,
        "return": Qt.Key_Return,
        "enter": Qt.Key_Enter,
        "left": Qt.Key_Left,
        "up": Qt.Key_Up,
        "right": Qt.Key_Right,
        "down": Qt.Key_Down,
    }
    
    # Handle shift modifier
    has_shift = "shift+" in key_string.lower()
    clean_key = key_string.lower().replace("shift+", "")
    
    if clean_key in key_map:
        return [(key_map[clean_key], has_shift)]
    
    return []


def parse_rank_config(rank_config: Dict) -> Dict[int, List]:
    """
    Parse rank configuration from config.json into a mapping of Qt key enums to rank values.
    
    Args:
        rank_config: Dictionary mapping key strings to rank values (e.g., {"0": 0, "p": 1, "backtick": 0})
        
    Returns:
        Dictionary mapping Qt key enums to rank values {Qt.Key_0: 0, Qt.Key_P: 1, ...}
    """
    from PyQt5.QtCore import Qt
    
    rank_map = {}
    
    for key_str, rank_value in rank_config.items():
        qt_keys = string_to_qt_key(key_str)
        for qt_key, _ in qt_keys:
            rank_map[qt_key] = rank_value
    
    return rank_map


def get_rank_range(rank_config: Dict) -> Tuple[int, int]:
    """
    Get the min and max rank values from rank configuration.
    
    Args:
        rank_config: Dictionary mapping key strings to rank values
        
    Returns:
        Tuple of (min_rank, max_rank)
    """
    if not rank_config:
        return (0, 3)  # Default fallback
    
    values = list(rank_config.values())
    return (min(values), max(values))
