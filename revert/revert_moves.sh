#!/bin/bash
# One-time revert script to undo incorrect directory moves
# This script moves directories back to Drive-Documents from their year-based locations

set -e

SOURCE_BASE="G:/My Drive"
TARGET_DIR="G:/My Drive/Drive-Documents"

echo "========================================="
echo "REVERT SCRIPT - Moving directories back"
echo "========================================="
echo "Target: $TARGET_DIR"
echo ""

# Array of directories to move back with their year locations
declare -a dirs_to_revert=(
    "2023/AlienFX"
    "2023/Alienware TactX"
    "2025/American Truck Simulator"
    "2022/Audacity"
    "2023/AutoHotkey"
    "2025/Battlefield 3"
    "2021/cache"
    "2021/Call of Duty Modern Warfare"
    "2025/Cline"
    "2021/Criterion Games"
)

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

echo "Starting revert process..."
echo ""

success_count=0
error_count=0

for dir_path in "${dirs_to_revert[@]}"; do
    src="${SOURCE_BASE}/${dir_path}"
    dir_name=$(basename "$dir_path")
    dest="${TARGET_DIR}/${dir_name}"

    echo "Reverting: $dir_name"

    if [ -d "$src" ]; then
        if [ -d "$dest" ]; then
            echo "  ⚠️  WARNING: $dest already exists, skipping..."
            ((error_count++))
        else
            mv "$src" "$dest"
            echo "  ✓ Moved back: $src -> $dest"
            ((success_count++))
        fi
    else
        echo "  ⚠️  WARNING: Source not found: $src"
        ((error_count++))
    fi
    echo ""
done

echo "========================================="
echo "REVERT COMPLETE"
echo "========================================="
echo "Successfully reverted: $success_count directories"
echo "Errors/Skipped: $error_count directories"
echo ""
echo "All directories have been moved back to:"
echo "$TARGET_DIR"
