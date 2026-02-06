# <img src="logo/astrorank_logo.png" alt="astrorank Logo" width="140">&nbsp;&nbsp;AstroRank

*An Image Ranking Tool for Astronomical Images*

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-blue)
![Pillow](https://img.shields.io/badge/Pillow-8.0%2B-green)
![numpy](https://img.shields.io/badge/numpy-1.20%2B-yellow)
![astropy](https://img.shields.io/badge/astropy-5.0%2B-red)
![requests](https://img.shields.io/badge/requests-2.20%2B-orange)

`astrorank` is a PyQt5-based GUI application for efficiently ranking astronomical images. It was inspired by Aidan Cloonan's original `lensranker` tool developed for the COOL-LAMPS collaboration and allows the user to provide an interface for browsing and ranking `.jpg` images on a scale of 0-3, with keyboard shortcuts optimized for a fast workflow.

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

## Configuration

AstroRank uses a `config.json` file to customize keyboard shortcuts, ranking scales, and the survey URL for the dual-panel view. The configuration file is automatically created in the working directory on first run with default values.

### Configuring the Survey URL

To use a different astronomical survey for the dual-panel view (press **G** to toggle), edit the `url_template` and `name` in the `secondary_download` section:

```json
"secondary_download": {
  "enabled": true,
  "name": "WISE",
  "url_template": "https://www.legacysurvey.org/viewer/decals-unwise-neo11/{ra}/{dec}?layer=unwise-neo1&zoom=15"
}
```

**Parameters:**
- `{ra}` and `{dec}` in the `url_template` are automatically replaced with coordinates parsed from your image filenames
- `zoom=15` in the `url_template` controls the zoom level in the viewer (adjust as needed; higher values = more zoom)
- `name` is used for UI labels and output directory naming
- Works on Windows, macOS, and Linux

**Configuring FITS Extensions for Different Surveys:**
Different surveys provide FITS files with different band/extension structures. The current implementation assumes a 3D FITS array where:
- Layer 0 → Blue channel
- Layer 1 → Green and Red channels

For a custom survey, you need to:
1. Check the survey's documentation for FITS file structure (number of extensions, which bands they contain)
2. Update `astrorank/utils.py` in the `download_secondary_image()` function to extract the correct layers for your survey's FITS format
3. Map the extracted data to RGB channels appropriately

Example: If your survey has a single 2D FITS extension instead of a 3D array, you'd modify the layer extraction logic accordingly.

### Custom Ranking Scale

By default, AstroRank uses ranks 0-3 with keys 0, 1, 2, 3, and backtick (`) which map to rank 0. To use a different scale or custom keys, **edit the `config.json` file** in the astrorank package directory and modify the `ranks` section:

```json
"ranks": {
  "0": 0,
  "1": 1,
  "2": 2,
  "3": 3,
  "backtick": 0
}
```

Example for 1-5 scale:
```json
"ranks": {
  "1": 1,
  "2": 2,
  "3": 3,
  "4": 4,
  "5": 5
}
```

You can also assign any key to a rank value. The rank value doesn't have to be the same as the key:
```json
"ranks": {
  "p": 1,
  "e": 2,
  "f": 3,
  "g": 4,
  "b": 5
}
```

Or use the keys as the rank values themselves:
```json
"ranks": {
  "a": "a",
  "b": "b",
  "c": "c",
  "d": "d"
}
```

**Important:** 
- Ensure rank keys do not overlap with any other key functionalities defined in the `keys` section (e.g., don't use 'q' as a rank if 'q' is your quit key). It is the user's responsibility to avoid these conflicts.
- After editing `config.json`, restart astrorank for changes to take effect
- Use `-c` flag to load a custom config: `astrorank /path/to/images -c /path/to/custom_config.json`

The UI will automatically update to show "Rank (min-max):" based on your configured values.

### Custom Keyboard Shortcuts

Customize any keyboard shortcut by editing the `keys` section (all keys are case-insensitive):

```json
"keys": {
  "quit": "q",
  "clear_rank": "c",
  "fit_image": "f",
  "reset_container": "r",
  "toggle_list": "l",
  "toggle_dark_mode": "d",
  "comment": "k",
  "wise_toggle": "g",
  "legacy_survey": "b",
  "zoom_in": "plus,equal",
  "zoom_out": "minus",
  "submit_and_next": "return,enter",
  "previous": "left,up",
  "next": "right,down",
  "first_image": "shift+left",
  "skip_to_next_unranked": "shift+right"
}
```

Multiple keys can be assigned to the same action using commas (e.g., `"quit": "q,escape"`). Works on Windows, macOS, and Linux.

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
| **R** | Reset image container to original size |
| **L** | Toggle list panel visibility |
| **D** | Toggle dark/light mode |
| **K** | Open comment dialog for current image |
| **G** | Download WISE unwise neo7 image (press again to toggle dual view) |
| **B** | Open Legacy Survey viewer for current coordinates |
| **+** / **−** | Zoom image in/out |
| **?** | Show/hide keyboard shortcuts helper |
| **Q** | Quit the application |

---

## Some Notes about the Interface

- **Image Viewer**: Display of current active image with filename and previous ranking (if any) shown above in parentheses
- **Zoom Controls**: Click the + and − buttons to adjust image size and expand container; "Fit" button to reset zoom to default; "Reset" button to return container to original size
- **Rank Input**: Text field for entering ranks (0-3)
- **Navigation Buttons**: Previous, Next, Skip to Next Unranked, and Hide/Show List - can use these instead of keys
- **Image List Panel**: Shows all images with filenames, ranks, ranking status, and WISE download status (toggle visibility with `L` key)

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
