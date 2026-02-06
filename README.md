# <img src="logo/astrorank_logo.png" alt="astrorank Logo" width="120">&nbsp;&nbsp;astrorank — Image Ranking Tool

![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-blue)

`astrorank` is a PyQt5-based GUI application for efficiently ranking astronomical images. It provides an interface for browsing and ranking `.jpg` images on a scale of 0-3, with keyboard shortcuts optimized for a fast workflow.

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
   astrorank </path/to/images/directory>
   ```

### macOS App Bundle (Optional)

To create a proper macOS app bundle with the app icon showing in the dock:

1. **Install py2app:**

   ```bash
   conda activate astrorank
   pip install py2app
   ```

2. **Build the app bundle:**

   ```bash
   cd ~/Research/Tools/astrorank
   python setup_mac.py py2app
   ```

3. **Run the app:**

   ```bash
   open dist/astrorank.app
   ```

The app bundle will be created in `dist/astrorank.app` with the custom icon showing in the macOS dock.

---

## How to Use AstroRank?

### Basic Usage

```bash
astrorank /path/to/images/directory # This starts the GUI and looks for all `.jpg` files in the directory. Rankings are saved to `rankings.txt` by default.
astrorank /path/to/images/directory -o my_rankings.txt # Specifies custom output file
```

### Resume Previous Session

Running the code specifying an already existing rank file will allow you to resume that previous session.

```bash
astrorank /path/to/images/directory # Resumes the session for rankings.txt (default output file name) if previously run
astrorank /path/to/images/directory -o my_rankings.txt # Resumes the session for my_rankings.txt if previously run
```

---

## Keyboard Shortcuts

**Fast Workflow:** Press a number (0-3), then press Enter or arrow keys to submit and move.

| Key | Action |
|-----|--------|
| **0-3** | Fill the rank input field (0=worst, 3=best) |
| **` (backtick)** | Also works as rank 0 (added as an option to shorten the distance from the 0-3 keys) |
| **Enter/Return** | Submit current rank and move to next image |
| **Delete/Backspace** | Clear the rank input field |
| **Left/Up Arrow** | Go to previous image. Submit rank if entered |
| **Right/Down Arrow** | Go to next image. Submit rank if entered |
| **Shift + Left Arrow** | Jump to the first image |
| **Shift + Right Arrow** | Skip to next unranked image (or submit rank first) |
| **C** | Clear the rank for current image |
| **F** | Fit image to container (reset zoom) |
| **L** | Toggle list panel visibility |
| **D** | Toggle dark/light mode |
| **K** | Open comment dialog for current image |
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
