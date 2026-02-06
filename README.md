# imrank

A PyQt5-based GUI application for ranking astronomical images. Simple, intuitive, and cross-platform (macOS and Windows).

## Features

- Browse and display `.jpg` images from a directory
- Rank images on a scale of 0-3
- Interactive list panel with real-time updates
- Keyboard shortcuts for efficient workflow
- Resume previous sessions with the `-c` or `--continue` flag
- Save rankings to a `.txt` file for future reference

## Installation

### Prerequisites

- Python 3.8 or higher
- conda (Miniconda or Anaconda)

### Quick Start

1. **Create a conda environment:**
   ```bash
   conda create -n imrank python=3.10
   conda activate imrank
   ```

2. **Clone the repository:**
   ```bash
   cd ~/Research/Tools
   git clone https://github.com/eriksolhaug/imrank.git
   cd imrank
   ```

3. **Install imrank:**
   ```bash
   pip install -e .
   ```

4. **Run imrank:**
   ```bash
   imrank /path/to/images/directory -o output.txt
   ```

## Usage

### Basic Usage

```bash
imrank /path/to/images/directory
```

This will start the imrank GUI and look for all `.jpg` files in the specified directory. Rankings will be saved to `rankings.txt` by default.

### With Custom Output File

```bash
imrank /path/to/images/directory -o my_rankings.txt
```

### Resume Previous Session

```bash
imrank /path/to/images/directory -o my_rankings.txt -c
```

This will start with the first unranked image from your previous session.

## Keyboard Shortcuts

- **0-3**: Rank the current image (0=worst, 3=best)
- **Enter/Return**: Confirm ranking
- **Left Arrow or Up Arrow**: Go to previous image
- **Right Arrow or Down Arrow**: Go to next image
- **Shift + Right Arrow**: Skip to next unranked image

## GUI Elements

- **Image Viewer**: Large display area for the current image
- **Ranking Input**: Text field for entering ranks (0-3 only)
- **Navigation Buttons**: Previous, Next, and Skip to Next Unranked
- **Image List Panel**: Shows all images with their filenames, ranks, and ranking status
- **Current Image Highlight**: Blue highlight indicates the currently viewed image

## Output Format

The output `.txt` file has the following format:

```
image_001.jpg 3
image_002.jpg 1
image_003.jpg 2
...
```

Each line contains the filename and the rank (0-3).

## Development

To contribute or modify the code:

```bash
git clone https://github.com/eriksolhaug/imrank.git
cd imrank
conda create -n imrank-dev python=3.10
conda activate imrank-dev
pip install -e .
pip install PyQt5 Pillow
```

## License

MIT License - see LICENSE file for details

## Author

Erik Solhaug
