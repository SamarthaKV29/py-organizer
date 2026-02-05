# File Organizer - Year-based Folders

A simple and elegant tool to organize files and folders into year-based directories using creation/modification dates.

## Features

- 🗂️ **Automatic Organization**: Moves files and folders into year-based directories (e.g., 2023/, 2024/)
- 🎯 **Smart Date Detection**: Uses file/folder creation time with modification time fallback
- 🖥️ **Dual Interface**: Command-line script + modern GUI
- 🔍 **Selective Processing**: Choose specific folders to process
- 🛡️ **Safe Mode**: Dry-run preview before making changes
- 📦 **Directory Support**: Moves entire folders as units (non-recursive)
- ⚠️ **Duplicate Handling**: Interactive resolution for conflicts

## Installation

### Prerequisites

- **Git Bash** (Windows) or **Bash** (Linux/macOS)
- **Python 3.8+**

### Setup

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment**:
   - Windows (Git Bash): `source venv/Scripts/activate`
   - Linux/macOS: `source venv/bin/activate`

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### GUI (Recommended)

Launch the graphical interface:

```bash
python org_docs_gui.py
```

**Features**:
- Browse and select source/target directories
- Tree view with folder preview (only top-level folders selectable)
- Year display next to each folder name with modification date tooltip
- Toggle options (Dry Run, Interactive, Verbose)
- Real-time log output with color coding
- Select/Deselect all folders
- Automatic settings persistence (paths, options, splitter position)

### Command Line

Run the bash script directly:

```bash
# Preview changes (dry run)
./org_docs.sh --dry-run

# Interactive folder selection
./org_docs.sh --choose-includes --dry-run

# Process specific folders
./org_docs.sh --include "Drive-Documents" --include "FlashDMS" --dry-run

# Run for real (remove --dry-run when ready)
./org_docs.sh --include "Drive-Documents"
```

### Options

```
--source-dir PATH     Directory to process files from (default: current dir)
--target-dir PATH     Where to create year folders (default: source dir)
--dry-run             Preview changes without moving files
--include DIR         Include specific directory (repeatable)
--exclude DIR         Exclude specific directory (repeatable)
--choose-includes     Interactively select folders to process
--choose-excludes     Interactively select folders to exclude
--interactive         Prompt before each move
--verbose             Show detailed output
--year YYYY           Process only files from specific year
--type EXT            Process only specific file types (comma-separated)
--help                Show help message
```

## How It Works

1. **Scans** the source directory for files and top-level subdirectories
2. **Detects** creation date (falls back to modification date)
3. **Creates** year-based folders (e.g., `2023/`, `2024/`)
4. **Moves** files and entire subdirectories to appropriate year folders
5. **Handles** duplicates interactively (rename/merge/skip)

## Examples

### GUI Workflow

1. Launch GUI: `python org_docs_gui.py`
2. Click **Browse** to select source directory
3. Check **Dry Run** to preview
4. Select folders in tree view (only top-level)
5. Click **▶ Run** and monitor log output
6. Review results, uncheck **Dry Run** when ready
7. Run again to apply changes

### Command Line Examples

```bash
# Preview all changes
./org_docs.sh --dry-run

# Interactively choose folders
./org_docs.sh --choose-includes --dry-run

# Process only Google Docs
./org_docs.sh --type gdoc,gsheet --dry-run

# Process only 2023 files
./org_docs.sh --year 2023

# Organize to parent directory
./org_docs.sh --target-dir ..
```

## Project Structure

```
py-reorganizer/
├── org_docs.sh           # Bash script (core logic)
├── org_docs_gui.py       # PySide6 GUI wrapper
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Safety Features

- **Dry Run Default**: GUI starts with dry-run enabled
- **Interactive Duplicates**: Always prompts for duplicate handling
- **Non-Destructive**: Original files preserved during moves
- **Rollback**: Use `--interactive` mode for per-file confirmation

## Troubleshooting

### "Script Not Found" Error
Ensure `org_docs.sh` is in the same directory as `org_docs_gui.py`

### "bash: command not found" (Windows)
Install Git Bash from https://git-scm.com/downloads

### GUI Not Launching
```bash
# Check Python version (3.8+ required)
python --version

# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

## License

Free to use and modify.

## Contributing

Suggestions and improvements welcome!
