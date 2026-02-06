"""
Utility functions for imrank
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple


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
