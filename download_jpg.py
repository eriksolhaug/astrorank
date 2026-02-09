#!/usr/bin/env python3
"""
Download DECaLS g, r, z images for sources in a CSV file and create RGB JPGs.

By default reads RA and DEC from CSV file (columns 0 and 1), downloads DECaLS imaging,
applies asinh scaling, and creates RGB JPEGs.

Usage:
    python download_jpg.py <csv_file> [output_dir] [--prefix PREFIX] [--skip-first-column]

Arguments:
    csv_file: Path to CSV file with source data
    output_dir: Directory to save RGB JPEGs (default: examples/)
    --prefix: Prefix for output filenames (default: download_)
    --skip-first-column: If set, uses columns 1 and 2 as RA and DEC (skips column 0 which may be the object ID)

Examples:
    python download_jpg.py data.csv examples/ --prefix decals_
    python download_jpg.py wslq_redshifts.csv examples/ --prefix decals_ --skip-first-column
"""

import sys
import csv
from pathlib import Path
import numpy as np
from astropy.io import fits
from PIL import Image
import urllib.request
import urllib.error


def apply_asinh_scaling(data, Q=8.0):
    """
    Apply asinh scaling for better visualization of astronomical images.
    This handles both bright and faint sources well.
    
    Args:
        data: Input image data
        Q: Softening parameter (default 8.0). Higher Q = more contrast
        
    Returns:
        Scaled image data as uint8 (0-255)
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
    
    # Apply asinh scaling: meant to remove make bright sources matter less while preserving faint detail
    # asinh(Q * x) / asinh(Q) maps [0, 1] -> [0, 1] with non-linear stretching
    scaled = np.arcsinh(Q * normalized) / np.arcsinh(Q)
    scaled = np.clip(scaled, 0, 1)
    
    return (scaled * 255).astype(np.uint8)


def download_decals_image(ra, dec, band, size=512):
    """
    Download a single DECaLS image from the web API.
    
    Args:
        ra: Right ascension in degrees
        dec: Declination in degrees
        band: Filter band ('g', 'r', or 'z')
        size: Image size in pixels (default 512)
        
    Returns:
        FITS data as numpy array, or None if download failed
    """
    url = f"http://legacysurvey.org/viewer/fits-cutout?ra={ra}&dec={dec}&layer=ls-dr10&size={size}&pixscale=0.263672&bands={band}"
    
    try:
        print(f"  Downloading {band}-band")
        with urllib.request.urlopen(url, timeout=30) as response:
            fits_data = fits.open(response)
            data = fits_data[0].data.astype(np.float32)
            fits_data.close()
            return data
    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        print(f"  ERROR: Failed to download {band}-band at RA={ra}, DEC={dec}: {e}")
        return None


def create_rgb_image(g_data, r_data, z_data):
    """
    Create an RGB image from g, r, z bands with asinh scaling.
    
    Mapping: g=blue, r=green, z=red (standard for optical observations)
    Images are vertically flipped so bottom-left becomes top-left.
    
    Args:
        g_data: g-band image data
        r_data: r-band image data
        z_data: z-band image data
        
    Returns:
        RGB image as uint8 numpy array (height, width, 3)
    """
    # Get dimensions
    height, width = g_data.shape
    
    # Create RGB image
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Apply asinh scaling and assign to channels
    # z -> Red, r -> Green, g -> Blue
    rgb[:, :, 0] = apply_asinh_scaling(z_data)  # Red channel
    rgb[:, :, 1] = apply_asinh_scaling(r_data)  # Green channel
    rgb[:, :, 2] = apply_asinh_scaling(g_data)  # Blue channel
    
    # Flip vertically so bottom-left becomes top-left
    rgb = np.flipud(rgb)
    
    return rgb


def process_sources(csv_file, output_dir="examples/", prefix="download_", skip_first_column=False):
    """
    Read CSV file and download/process DECaLS images for each source.
    
    Args:
        csv_file: Path to CSV file with source data
        output_dir: Directory to save RGB JPEGs
        prefix: Prefix for output filenames (default: download_)
        skip_first_column: If True, use columns 1,2 as RA,DEC instead of 0,1
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    csv_path = Path(csv_file)
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_file}")
        return False
    
    print(f"Reading sources from {csv_file}")
    
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header
        print(f"Header: {header}")
        
        # Determine column indices
        if skip_first_column:
            # Skip first column (ID), use columns 1 and 2
            ra_col, dec_col, name_col = 1, 2, 0
        else:
            # Default: use columns 0 and 1 as RA and DEC
            ra_col, dec_col, name_col = 0, 1, None
        
        for row_idx, row in enumerate(reader):
            try:
                # Generate source name
                if name_col is not None and name_col < len(row):
                    source_name = row[name_col].strip()
                else:
                    # Use RA and DEC to generate a generic name
                    source_name = f"source_{row_idx}"
                
                ra = float(row[ra_col])
                dec = float(row[dec_col])
                
                print(f"\nProcessing: {source_name} (RA={ra}, DEC={dec})")
                
                # Download images
                g_data = download_decals_image(ra, dec, 'g')
                r_data = download_decals_image(ra, dec, 'r')
                z_data = download_decals_image(ra, dec, 'z')
                
                if g_data is None or r_data is None or z_data is None:
                    print(f"  WARNING: Could not download all bands for {source_name}")
                    continue
                
                # Create RGB image
                rgb_image = create_rgb_image(g_data, r_data, z_data)
                
                # Save as JPEG
                output_file = output_path / f"{prefix}{source_name}_{ra:.4f}_{dec:.4f}.jpg"
                pil_image = Image.fromarray(rgb_image, mode='RGB')
                pil_image.save(output_file, 'JPEG', quality=95)
                print(f"  Saved: {output_file}")
                
            except (ValueError, IndexError) as e:
                print(f"  ERROR: Could not parse row {row_idx}: {e}")
                continue
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python download_jpg.py <csv_file> [output_dir] [--prefix PREFIX] [--skip-first-column]")
        print("\nExamples:")
        print("  python download_jpg.py data.csv")
        print("  python download_jpg.py data.csv examples/ --prefix decals_")
        print("  python download_jpg.py wslq_redshifts.csv examples/ --prefix decals_ --skip-first-column")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    output_dir = "examples/"
    prefix = "download_"
    skip_first_column = False
    
    # Parse optional arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--prefix":
            if i + 1 < len(sys.argv):
                prefix = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        elif sys.argv[i] == "--skip-first-column":
            skip_first_column = True
            i += 1
        elif not sys.argv[i].startswith("--"):
            # Non-flag argument is output_dir
            output_dir = sys.argv[i]
            i += 1
        else:
            i += 1
    
    success = process_sources(csv_file, output_dir, prefix, skip_first_column)
    sys.exit(0 if success else 1)
