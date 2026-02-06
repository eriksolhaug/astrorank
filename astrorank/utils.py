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
        # Save rankings without comments to rankings.txt
        with open(output_file, 'w') as f:
            for filename in jpg_files:
                if filename in rankings:
                    rank = rankings[filename]
                    f.write(f"{filename}\t{rank}\n")
    except Exception as e:
        print(f"Error saving rankings: {e}")
    
    # Save rankings with comments to a separate file
    if comments:
        try:
            comments_file = output_file.replace('.txt', '_comments.txt')
            with open(comments_file, 'w') as f:
                for filename in jpg_files:
                    if filename in rankings:
                        rank = rankings[filename]
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


def is_valid_rank(rank_str: str) -> Tuple[bool, int]:
    """
    Validate that the input is a valid rank (0-3).
    
    Args:
        rank_str: String input from user
        
    Returns:
        Tuple of (is_valid, rank_value)
    """
    try:
        rank = int(rank_str.strip())
        if 0 <= rank <= 3:
            return True, rank
    except ValueError:
        pass
    
    return False, -1


def parse_radec_from_filename(filename: str) -> Optional[Tuple[float, float]]:
    """
    Parse RA and Dec from filename of format: <name>_<ra>_<dec>.jpg
    
    Args:
        filename: Filename to parse
        
    Returns:
        Tuple of (ra, dec) as floats, or None if parsing fails
    """
    # Remove .jpg extension and split by underscores
    name_without_ext = filename.rsplit('.', 1)[0]
    parts = name_without_ext.split('_')
    
    # Need at least 3 parts: name, ra, dec
    if len(parts) < 3:
        return None
    
    try:
        ra = float(parts[-2])
        dec = float(parts[-1])
        return (ra, dec)
    except (ValueError, IndexError):
        return None


def load_config(config_file: str = "config.json") -> Dict:
    """
    Load configuration from config.json
    
    Args:
        config_file: Path to config.json file
        
    Returns:
        Dictionary with configuration, or defaults if file not found
    """
    default_config = {
        "wise_download": {
            "enabled": True,
            "output_directory": "wise",
            "url_template": "https://www.legacysurvey.org/viewer/decals-unwise-neo11/{ra}/{dec}?layer=unwise-neo1&zoom=15",
            "image_url_template": "https://www.legacysurvey.org/data/unwise/neo11/unwise-{ra}-{dec}-{band}.jpg"
        }
    }
    
    if not os.path.exists(config_file):
        return default_config
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return default_config


def download_wise_image(ra: float, dec: float, output_dir: str, config: Dict) -> Optional[str]:
    """
    Download WISE unwise neo7 FITS file and create RGB composite JPG
    
    Args:
        ra: Right ascension
        dec: Declination
        output_dir: Directory to save image to
        config: Configuration dictionary
        
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
    
    # FITS cutout parameters
    size = 512
    pixscale = 0.263672
    
    # Download FITS with W1 (contains both W1 and W2 as separate layers)
    fits_url = f"https://www.legacysurvey.org/viewer/fits-cutout?ra={ra}&dec={dec}&layer=unwise-neo7&size={size}&pixscale={pixscale}&bands=w1"
    
    try:
        # Download FITS file
        response = requests.get(fits_url, timeout=30)
        response.raise_for_status()
        
        # Save temporary FITS file
        fits_path = Path(output_dir) / f"temp_wise_{ra}_{dec}.fits"
        
        with open(fits_path, 'wb') as f:
            f.write(response.content)
        
        # Load FITS data
        hdul = fits.open(fits_path)
        data = hdul[0].data.astype(float)
        hdul.close()
        
        # Extract W1 and W2 from the 3D array (2, H, W)
        # Layer 0 = W1, Layer 1 = W2
        if len(data.shape) == 3 and data.shape[0] == 2:
            data_w1 = data[0]
            data_w2 = data[1]
        else:
            print(f"Error: Expected shape (2, H, W), got {data.shape}")
            fits_path.unlink()
            return None
        
        # Apply asinh (inverse hyperbolic sine) scaling - better for astronomy
        # This preserves faint features while suppressing bright sources
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
        
        # Apply asinh scaling to both bands
        w1_scaled = apply_asinh_scaling(data_w1)
        w2_scaled = apply_asinh_scaling(data_w2)
        
        # Create RGB image
        # W1 = Blue channel
        # W2 = Green and Red channels
        rgb = np.zeros((size, size, 3), dtype=np.uint8)
        rgb[:, :, 0] = w2_scaled  # Red = W2
        rgb[:, :, 1] = w2_scaled  # Green = W2
        rgb[:, :, 2] = w1_scaled  # Blue = W1
        
        # Flip image vertically (across y-axis) for correct orientation
        rgb = np.flipud(rgb)
        
        # Convert to PIL Image and save as JPG
        image = Image.fromarray(rgb, mode='RGB')
        output_path = Path(output_dir) / f"wise_{ra}_{dec}.jpg"
        image.save(output_path, quality=90)
        
        # Clean up temporary FITS file
        fits_path.unlink()
        
        return str(output_path)
    
    except Exception as e:
        print(f"Error downloading/processing WISE image: {e}")
        return None
