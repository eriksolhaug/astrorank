# <img src="logo/astrorank_logo.png" alt="astrorank Logo" width="140">&nbsp;&nbsp;AstroRank

*An Image Ranking Tool for Astronomical Images*

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-blue)
![Pillow](https://img.shields.io/badge/Pillow-8.0%2B-green)
![numpy](https://img.shields.io/badge/numpy-1.20%2B-yellow)
![astropy](https://img.shields.io/badge/astropy-5.0%2B-red)
![requests](https://img.shields.io/badge/requests-2.20%2B-orange)

`astrorank` is a PyQt5-based GUI application for efficiently ranking astronomical images. This software provides an interface for browsing and ranking `.jpg` images based on a custom scale, with keyboard shortcuts that can be optimized by the user for a fast workflow.

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

   First, enter (`cd` into) a directory you want to place the astrorank code, e.g. `~/Research/Tools/`.

   ```bash
   git clone https://github.com/eriksolhaug/astrorank.git
   cd astrorank
   ```

3. **Install astrorank:**

   ```bash
   pip install -e .
   ```

4. **Run astrorank:**

   ```bash
   astrorank YOUR_IMAGE_DIRECTORY
   ```

---

## How to Use AstroRank?

### Basic Usage

```bash
astrorank YOUR_IMAGE_DIRECTORY # This starts the GUI and looks for all `.jpg` files in the directory. Rankings are saved to `rankings.txt` by default.
astrorank YOUR_IMAGE_DIRECTORY -o my_rankings.txt # Specifies custom output file

Example: astrorank ~/Research/Tools/astrorank/examples
```

### Image Filename Format

`astrorank` can read any .jpg files, and the file name does not need a specific format for the software to work. However, for `astrorank` to work with the browser (press `b`) and secondary image download (press `g`) features enabled, your image filenames must follow this format:

```
<any_name>_<ra>_<dec>.jpg
```

Where `<ra>` and `<dec>` are the right ascension and declination in **decimal degrees**. This is so that `astrorank` can obtain the RA and DEC of the image and use this to query the field online.

**Example:** `qso_aug_aug21_2025A_run1_100.00371_-69.056759.jpg`

### Output Files

`astrorank` produces a `rankings.txt` file containing the file name and rank for the given file. If any comments are created, these will be included as a third column in a separate file `rankings_comments.txt`. You can change the output name using the `-o` flag (see above). E.g. running `astrorank PATH_TO_IMAGES -o my_rankings.txt` will produce both a `my_rankings.txt` and a `my_rankings_comments.txt` file.

When downloading secondary images (press `g`), they are saved as:

```
<survey_name>_<ra>_<dec>.jpg
```

**Example:** `wise_100.00371_-69.056759.jpg` or `galex_100.00371_-69.056759.jpg`

### Resume Previous Session

Running the code specifying an already existing rank file will allow you to resume that previous session.

```bash
astrorank YOUR_IMAGE_DIRECTORY # Resumes the session for rankings.txt (default output file name) if previously run
astrorank YOUR_IMAGE_DIRECTORY -o my_rankings.txt # Resumes the session for my_rankings.txt if previously run
```

---

## Configuration

AstroRank uses a `config.json` file to customize keyboard shortcuts, ranking scales, browser URLs, and the survey for the dual-panel view. The configuration file is automatically created in the working directory on first run with default values.

### Survey and Browser Configuration

The configuration supports two main sections for URL-based features:

**Browser Section** - for opening survey viewers (press `b`):
```json
"browser": {
  "url_template": "https://www.legacysurvey.org/viewer/?ra={ra}&dec={dec}&layer=ls-dr10&zoom=16"
}
```

**Secondary Download Section** - for downloading and compositing FITS images (press `g`):
```json
"secondary_download": {
  "enabled": true,
  "name": "WISE",
  "url_template_download": "https://www.legacysurvey.org/viewer/fits-cutout?ra={ra}&dec={dec}&layer=unwise-neo11&size=512&pixscale=0.263672&bands=w1",
  "extensions": {
    "0": ["B"],
    "1": ["R", "G"]
  }
}
```

**Parameters:**
- `{ra}` and `{dec}` placeholders are automatically replaced with coordinates parsed from your image filenames
- `url_template_download`: The URL template for downloading FITS files. Supports `{ra}` and `{dec}` substitution
- `extensions`: Maps FITS layer indices to RGB channels. Each layer can map to one or more channels:
  - `"0": ["R", "G"]` → Layer 0 goes to both Red and Green channels
  - `"1": ["B"]` → Layer 1 goes to Blue channel
  - Layers and channels are configured by index
- `name`: Used for UI labels and output file naming
- `enabled`: Set to `false` to disable secondary image downloads
- Works on Windows, macOS, and Linux

**Example: GALEX Configuration**
```json
"secondary_download": {
  "enabled": true,
  "name": "GALEX",
  "url_template_download": "https://www.legacysurvey.org/viewer/fits-cutout?ra={ra}&dec={dec}&layer=galex&size=512&pixscale=0.263672&bands=fuv,nuv",
  "extensions": {
    "0": ["R", "G"],
    "1": ["B"]
  }
}
```

This approach makes the system fully configurable - different surveys can be used by simply changing the configuration, no code modification needed.

## Displaying Images with the Same Name from Two Separate Directories

The config has its own section to specify a secondary directory to look for images of the same file name as in the primary directory (the one specified in the command-line). When enabled, you can toggle back and forth between images from the two directories.

**Secondary Directory Section** - for toggling between images from primary and secondary directories (press `e`):
```json
"secondary_dir": {
  "enabled": false,
  "path": "PATH_TO_SECONDARY_DIRECTORY"
}
```

When enabled, the secondary directory should contain images with the same filenames as the primary directory. Press `e` to toggle between displaying images from the primary and secondary directories.



### Loading a Custom Configuration File

By default, AstroRank loads `config.json` from the current working directory, or falls back to the package installation directory. To use a custom configuration file, use the `-c` or `--config` flag:

```bash
astrorank YOUR_IMAGE_DIRECTORY -c custom_config.json
astrorank YOUR_IMAGE_DIRECTORY --config custom_config.json

Example: astrorank ~/Research/Tools/astrorank/examples -c ~/Research/Tools/astrorank/config_galex.json
```

This is useful for maintaining different configurations for different projects or surveys.

### Custom Ranking Scale

By default, AstroRank uses ranks 0-3 with keys 0, 1, 2, 3, and backtick (\`) which map to rank 0. To use a different scale or custom keys, **edit the `config.json` file or (preferably) copy/create a new .json file and load with the `-c` flag** in the astrorank package directory and modify the `ranks` section:

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
  "toggle_secondary_dir": "e",
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
| `0-3` | Fill the rank input field (e.g. 0=least likely/worst, 3=most likely/best) |
| `` ` `` (backtick) | Also works as rank 0 (added as an option to shorten the distance from the 0-3 keys) |
| `Enter/Return` | Submit current rank and move to next image |
| `Delete/Backspace` | Clear the rank input field |
| `Left/Up Arrow` | Go to previous image. Submit rank if entered |
| `Right/Down Arrow` | Go to next image. Submit rank if entered |
| `Shift + Left Arrow` | Jump to the first image |
| `Shift + Right Arrow` | Skip to next unranked image (or submit rank first) |
| `c` | Clear the rank for current image |
| `f` | Fit image to container (reset zoom) |
| `r` | Reset image container to original size |
| `l` | Toggle list panel visibility |
| `d` | Toggle dark/light mode |
| `k` | Open comment dialog for current image |
| `e` | Toggle images from the secondary directory that are already downloaded (when enabled in the config) |
| `g` | Download secondary images (when enabled in the config). E.g. WISE unwise neo11 image (press again to toggle dual view) |
| `b` | Open Legacy Survey viewer for current coordinates (when enabled in the config) |
| `+` / `−` | Zoom image in/out |
| `?` | Show/hide keyboard shortcuts helper |
| `q` | Quit the application |

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
cd YOUR_ASTRORANK_DIRECTORY
conda create -n astrorank-dev python=3.10
conda activate astrorank-dev
pip install -e .
```

---

## Acknowledgments

`astrorank` was inspired by Aidan Cloonan's `lensranker` tool (an earlier version may have existed) developed for the COOL-LAMPS collaboration.

---

## License

MIT License - see LICENSE file for details

## Author

Erik Solhaug
