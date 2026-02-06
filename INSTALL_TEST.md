# imrank Installation & Testing Guide

This guide walks you through installing and testing the `imrank` package.

## Installation Steps

### Step 1: Create a Conda Environment

```bash
conda create -n imrank python=3.10
conda activate imrank
```

### Step 2: Clone the Repository

```bash
cd ~/Research/Tools
git clone https://github.com/eriksolhaug/imrank.git
cd imrank
```

### Step 3: Install Dependencies (if not already in environment)

The `setup.py` will handle dependencies, but you can also install them manually:

```bash
conda activate imrank
pip install PyQt5 Pillow
```

### Step 4: Install imrank in Editable Mode

```bash
pip install -e .
```

This allows you to run `imrank` from anywhere in your terminal.

## Testing the Installation

### Quick Test

```bash
imrank /Users/eriksolhaug/Research/Searches/decals_august2025/wslq/aug21_2025A/
```

This will:
1. Load all `.jpg` files from the directory
2. Create a `rankings.txt` file in your current directory
3. Open the imrank GUI window

### Test with Custom Output File

```bash
imrank /Users/eriksolhaug/Research/Searches/decals_august2025/wslq/aug21_2025A/ -o my_test_rankings.txt
```

### Test Resume Functionality

1. Rank a few images (0-3)
2. Close the window
3. Run with the `-c` flag:

```bash
imrank /Users/eriksolhaug/Research/Searches/decals_august2025/wslq/aug21_2025A/ -o my_test_rankings.txt -c
```

You should start at the first unranked image.

## Using the GUI

### Navigation
- **Number Keys (0-3)**: Enter a rank
- **Enter/Return**: Submit the rank and move to next image
- **Left/Up Arrow**: Previous image
- **Right/Down Arrow**: Next image
- **Shift + Right Arrow**: Skip to next unranked image
- **Mouse Click on Table**: Click any row to jump to that image

### Output File Format

The rankings file is a simple text file:

```
image_001.jpg 2
image_002.jpg 3
image_003.jpg 1
```

Each line contains the filename and rank separated by a space.

## Troubleshooting

### Module Not Found Error
Make sure you've activated the conda environment:
```bash
conda activate imrank
```

### PyQt5 Issues on macOS
If PyQt5 fails to install, try:
```bash
conda install -c conda-forge pyqt5
```

### No Images Found
Make sure:
1. The directory path is correct
2. The directory contains `.jpg` files (not `.JPG` or other formats)
3. You have read permissions for the directory

## Development

To modify the code:

```bash
cd ~/Research/Tools/imrank
conda activate imrank
# Edit files as needed
# Changes are automatically reflected since we used `pip install -e .`
```

## Uninstallation

```bash
pip uninstall imrank
conda deactivate
conda remove -n imrank --all
```
