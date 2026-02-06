# astrorank — Image Ranking Tool

![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-blue)

`astrorank` is a PyQt5-based GUI application for efficiently ranking astronomical images. It provides an intuitive interface for browsing and ranking `.jpg` images on a scale of 0-3, with keyboard shortcuts optimized for fast workflow.

---

## Installation & Running

### Prerequisites

- Python 3.8 or higher
- conda (Miniconda or Anaconda)

---

### Quick Start

1. **Create a conda environment:**

   ```bash
   conda create -n astrorank python=3.10
   conda activate astrorank
   ```

2. **Clone the repository:**

   ```bash
   cd ~/Research/Tools
   git clone https://github.com/eriksolhaug/astrorank.git
   cd astrorank
   ```

3. **Install astrorank:**

   ```bash
   pip install -e .
   ```

4. **Run astrorank:**

   ```bash
   imrank </path/to/images/directory>
   ```

---

## How to Use ImRank?

### Basic Usage

```bash
imrank </path/to/images/directory> #This starts the GUI and looks for all `.jpg` files in the directory. Rankings are saved to `rankings.txt` by default.
imrank /path/to/images/directory -o my_rankings.txt # Specifies custom output file

### Resume Previous Session

```bash
imrank /path/to/images/directory -o my_rankings.txt -c # Resume previous session
```

This starts with the first unranked image from your previous session and keeps all rankings.

---

## Keyboard Shortcuts

**Fast Workflow:** Press a number (0-3), then press Enter or arrow keys to submit and move.

| Key | Action |
|-----|--------|
| **0-3** | Fill the rank input field (0=worst, 3=best) |
| **Enter/Return** | Submit current rank and move to next image |
| **Delete/Backspace** | Clear the rank input field |
| **Left/Up Arrow** | Go to previous image. Submit rank if entered |
| **Right/Down Arrow** | Go to next image. Submit rank if entered |
| **Shift + Left Arrow** | Jump to the first image |
| **Shift + Right Arrow** | Skip to next unranked image (or submit rank first) |
| **C** | Clear the rank for current image |
| **F** | Fit image to container (reset zoom) |
| **L** | Toggle list panel visibility |
| **+** / **−** | Zoom image in/out |
| **?** | Show/hide keyboard shortcuts helper |
| **Q** | Quit the application |

---

## Some Notes about the Interface

- **Image Viewer**: Display of current active image with filename and previous ranking (if any) shown above in parentheses
- **Zoom Controls**: Click the + and − buttons to adjust image size; "Fit" button to reset to default size
- **Rank Input**: Text field for entering ranks (0-3)
- **Navigation Buttons**: Previous, Next, Skip to Next Unranked, and Hide/Show List - can use these instead of keys
- **Image List Panel**: Shows all images with filenames, ranks, and ranking status (toggle visibility with `L` key)

---

## Output Format

The output `.txt` file has the following format:

```
image_001.jpg 0
image_002.jpg 0
image_003.jpg 1
image_001.jpg 0
image_002.jpg 3
image_003.jpg 0
```

Each line contains a filename and its rank (0-3).

---

## Development

To modify or extend the code:

```bash
cd ~/Research/Tools/astrorank
conda create -n astrorank-dev python=3.10
conda activate astrorank-dev
pip install -e .
```

---

## License

MIT License - see LICENSE file for details

## Author

Erik Solhaug
