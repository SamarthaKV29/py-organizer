# CRITICAL BUG FIXES - February 5, 2026

## Problem Summary
When NO folders were selected in the GUI, the script was moving ENTIRE DIRECTORIES into year-based folders instead of only processing FILES. This was a critical bug that caused unintended directory moves.

## What Went Wrong
The bash script's `is_excluded()` function had a logic flaw:
- When `INCLUDED_DIRS` was empty (no folders selected), it fell through to checking `EXCLUDED_DIRS`
- If `EXCLUDED_DIRS` was also empty (or didn't match), ALL directories were processed
- This caused directories like "AlienFX/", "Alienware TactX/", etc. to be moved

## Fixes Applied

### 1. Revert Script Created
**Files:** `revert_moves.sh`, `run_revert.bat`

Created a one-time script to undo the incorrect directory moves. This will move back:
- AlienFX (2023 → Drive-Documents)
- Alienware TactX (2023 → Drive-Documents)
- American Truck Simulator (2025 → Drive-Documents)
- Audacity (2022 → Drive-Documents)
- AutoHotkey (2023 → Drive-Documents)
- Battlefield 3 (2025 → Drive-Documents)
- cache (2021 → Drive-Documents)
- Call of Duty Modern Warfare (2021 → Drive-Documents)
- Cline (2025 → Drive-Documents)
- Criterion Games (2021 → Drive-Documents)

**To run:**
- Windows: Double-click `run_revert.bat`
- Linux/Mac: `bash revert_moves.sh`

### 2. Added --files-only Flag to Bash Script
**File:** `org_docs.sh`

Changes:
- Added `FILES_ONLY=false` variable (line 25)
- Added `--files-only` help text
- Added `--files-only` argument parsing
- Modified `process_directory()` to skip ALL directories when `FILES_ONLY=true`

When this flag is set, the script ONLY processes files and completely ignores subdirectories.

### 3. GUI Automatically Uses --files-only
**File:** `org_docs_gui.py`

Changes in `build_command_args()`:
```python
if selected_folders:
    for folder in selected_folders:
        args.extend(["--include", folder])
else:
    # No folders selected: only process files, not directories
    args.append("--files-only")
```

Now when NO folders are selected, GUI sends `--files-only` to ensure only FILES are processed.

### 4. Updated Confirmation Message
**File:** `org_docs_gui.py`

Changed the "No Folders Selected" dialog from:
> "This will process ALL top-level items."

To:
> "This will process ONLY FILES (directories will be skipped)."

This clearly communicates the new behavior to users.

### 5. Dry Run Always ON by Default
**File:** `org_docs_gui.py`

**CRITICAL SAFETY IMPROVEMENT:**
- `dry_run` checkbox is NO LONGER saved to JSON
- `dry_run` checkbox is NO LONGER loaded from JSON
- Checkbox ALWAYS defaults to CHECKED when GUI opens
- User must manually uncheck it each session to make changes

This prevents accidental data loss by ensuring dry-run mode is always on when starting the GUI.

Changes:
- Removed `'dry_run': self.dry_run_cb.isChecked()` from `save_settings()`
- Removed loading of `dry_run` from `load_settings()`
- Added comments explaining this is intentional for safety

## How to Use Going Forward

### Recommended Workflow:
1. **Always start with Dry Run ON** (it's now the default)
2. **Select specific folders** if you want to process directories
3. **Select NO folders** if you only want to organize loose files
4. **Review the dry-run output** before unchecking dry-run
5. **Run again without dry-run** to apply changes

### Important Notes:
- ✅ **Selecting folders**: Processes ONLY those folders (moves entire directories)
- ✅ **Selecting NO folders**: Processes ONLY files, skips all directories
- ✅ **Dry Run**: ALWAYS ON by default for safety
- ✅ **Duplicates**: Automatically renamed with timestamp (no blocking)

## Testing
Both scripts validated:
```bash
bash -n org_docs.sh         # Syntax OK
python -m py_compile org_docs_gui.py  # Syntax OK
```

## Next Steps
1. **RUN THE REVERT SCRIPT FIRST** to undo incorrect moves
2. Delete or backup old `org_docs_gui.json` settings file (optional, but recommended)
3. Test the new behavior with dry-run mode
4. Verify files-only mode works as expected

---
**Author:** GitHub Copilot
**Date:** February 5, 2026
**Severity:** CRITICAL - Data safety fix
