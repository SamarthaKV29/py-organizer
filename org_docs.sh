#!/bin/bash

# org_docs.sh - Organize files into year-based folders
# Usage: ./org_docs.sh [OPTIONS]
#
# Options:
#   --year YYYY           Process only files from specific year
#   --type EXT            Process only files with extension (e.g., pdf, gdoc)
#   --source-dir PATH     Directory to process files from (default: current dir)
#   --target-dir PATH     Where to create year folders (default: source dir)
#   --dry-run             Show what would be done without making changes
#   --exclude DIR         Exclude directory from processing (can be used multiple times)
#   --include DIR         Include directory for processing (can be used multiple times)
#   --choose-excludes     Interactively select subdirectories to exclude
#   --choose-includes     Interactively select ONLY subdirectories to process
#   --interactive         Prompt for each file move (default for duplicates only)
#   --help                Show this help message

set -euo pipefail

# Default configuration
SOURCE_DIR="$(pwd)"  # Default to current directory
TARGET_BASE_DIR=""  # Will default to SOURCE_DIR if not set
DRY_RUN=false
FILES_ONLY=false  # Skip all directories, process only files
TARGET_YEAR=""
FILE_TYPE=""
INTERACTIVE=false
CHOOSE_EXCLUDES=false
CHOOSE_INCLUDES=false
EXCLUDED_DIRS=("2020" "2021" "2022" "2023" "2024" "2025" "2026")
INCLUDED_DIRS=()
VERBOSE=false
DUPLICATE_MODE="interactive"  # interactive, skip, or rename

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Statistics
declare -i FILES_MOVED=0
declare -i FILES_SKIPPED=0
declare -i FILES_RENAMED=0
declare -i ERRORS=0

# Function to display help
show_help() {
    cat << EOF
Usage: ./org_docs.sh [OPTIONS]

Organize files into year-based folders based on modification date.

Options:
    --year YYYY          Process only files from specific year
    --type EXT           Process only files with extension (comma-separated: pdf,gdoc)
    --source-dir PATH    Directory to process files from (default: current directory)
    --target-dir PATH    Where to create year folders (default: source directory)
    --dry-run            Show what would be done without making changes
    --files-only         Process only files, skip all subdirectories
    --exclude DIR        Exclude directory (can be used multiple times)
    --include DIR        Include directory (can be used multiple times, overrides excludes)
    --choose-excludes    Interactively select subdirectories to exclude before processing
    --choose-includes    Interactively select ONLY subdirectories to process (overrides excludes)
    --interactive        Prompt for confirmation before each move
    --skip-duplicates    Automatically skip duplicate files (non-interactive)
    --rename-duplicates  Automatically rename duplicate files with timestamp
    --verbose            Show detailed output
    --help               Show this help message

Examples:
    ./org_docs.sh --dry-run                              # Preview changes in current dir
    ./org_docs.sh --choose-excludes --dry-run            # Interactively exclude folders
    ./org_docs.sh --choose-includes --dry-run            # Interactively select ONLY folders to process
    ./org_docs.sh --year 2023                            # Organize only 2023 files
    ./org_docs.sh --type gdoc,gsheet                     # Organize only Google Docs/Sheets
    ./org_docs.sh --target-dir ..                        # Create year folders in parent dir

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --year)
            TARGET_YEAR="$2"
            shift 2
            ;;
        --type)
            FILE_TYPE="$2"
            shift 2
            ;;
        --source-dir)
            SOURCE_DIR="$(cd "$2" && pwd)"
            shift 2
            ;;
        --target-dir)
            TARGET_BASE_DIR="$(cd "$2" && pwd)"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --exclude)
            EXCLUDED_DIRS+=("$2")
            shift 2
            ;;
        --include)
            INCLUDED_DIRS+=("$2")
            shift 2
            ;;
        --choose-excludes)
            CHOOSE_EXCLUDES=true
            shift
            ;;
        --choose-includes)
            CHOOSE_INCLUDES=true
            shift
            ;;
        --interactive)
            INTERACTIVE=true
            shift
            ;;
        --skip-duplicates)
            DUPLICATE_MODE="skip"
            shift
            ;;
        --rename-duplicates)
            DUPLICATE_MODE="rename"
            shift
            ;;
        --files-only)
            FILES_ONLY=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            ;;
    esac
done

# Set TARGET_BASE_DIR to SOURCE_DIR if not specified
if [[ -z "$TARGET_BASE_DIR" ]]; then
    TARGET_BASE_DIR="$SOURCE_DIR"
fi

# Function to check if directory should be excluded
is_excluded() {
    local dir_name="$1"

    # If INCLUDED_DIRS is populated, only process directories in that list
    if [[ ${#INCLUDED_DIRS[@]} -gt 0 ]]; then
        for included in "${INCLUDED_DIRS[@]}"; do
            if [[ "$dir_name" == "$included" || "$dir_name" == *"/$included" || "$dir_name" == "$included/"* ]]; then
                return 1  # Not excluded (is included)
            fi
        done
        return 0  # Excluded (not in include list)
    fi

    # Otherwise, check exclusion list
    for excluded in "${EXCLUDED_DIRS[@]}"; do
        if [[ "$dir_name" == "$excluded" || "$dir_name" == *"/$excluded" || "$dir_name" == "$excluded/"* ]]; then
            return 0
        fi
    done
    return 1
}

# Function to interactively choose which subdirectories to exclude/include
choose_exclusions() {
    local mode="$1"  # "exclude" or "include"
    local title

    if [[ "$mode" == "include" ]]; then
        title="Select Subdirectories to PROCESS"
    else
        title="Select Subdirectories to EXCLUDE"
    fi

    echo -e "${BLUE}Scanning for subdirectories in: ${GREEN}$SOURCE_DIR${NC}"

    # Collect all subdirectories (not files)
    local -a dirs=()
    local -a dir_info=()

    cd "$SOURCE_DIR"
    for item in */; do
        if [[ -d "$item" ]]; then
            local dir_name="${item%/}"
            dirs+=("$dir_name")

            # Get directory info (top-level only, non-recursive)
            local mod_date
            local file_count
            mod_date=$(stat -c "%y" "$item" 2>/dev/null | cut -d' ' -f1 || stat -f "%Sm" -t "%F" "$item" 2>/dev/null || echo "unknown")
            # Count only immediate files in directory, not recursive
            file_count=$(find "$item" -maxdepth 1 -type f 2>/dev/null | wc -l | tr -d ' ')
            dir_info+=("$mod_date|$file_count")
        fi
    done

    if [[ ${#dirs[@]} -eq 0 ]]; then
        echo -e "${YELLOW}No subdirectories found.${NC}"
        return
    fi

    # Build selection state (1 = selected, 0 = not selected)
    local -a selected=()
    for dir_name in "${dirs[@]}"; do
        if [[ "$mode" == "include" ]]; then
            # For include mode, nothing selected by default
            selected+=(0)
        else
            # For exclude mode, check if already in exclude list
            if is_excluded "$dir_name"; then
                selected+=(1)
            else
                selected+=(0)
            fi
        fi
    done

    local page=0
    local page_size=20
    local total_pages=$(( (${#dirs[@]} + page_size - 1) / page_size ))

    while true; do
        clear
        echo -e "${BLUE}========================================"
        echo -e "$title"
        echo -e "========================================${NC}"
        echo -e "Directory: ${GREEN}$SOURCE_DIR${NC}"
        echo -e "Page $((page + 1)) of $total_pages (${#dirs[@]} total subdirectories)\n"

        local start=$((page * page_size))
        local end=$((start + page_size))
        [[ $end -gt ${#dirs[@]} ]] && end=${#dirs[@]}

        for ((i=start; i<end; i++)); do
            local idx=$((i + 1))
            local dir_name="${dirs[$i]}"
            local info="${dir_info[$i]}"
            local mod_date="${info%%|*}"
            local file_count="${info##*|}"
            local check=" "

            [[ ${selected[$i]} -eq 1 ]] && check="✓"

            printf "  [%s%2d] %-30s (Date: %s, Files: %s)\n" "$check" "$idx" "$dir_name/" "$mod_date" "$file_count"
        done

        echo -e "\n${BLUE}Commands:${NC}"
        echo "  Numbers: Toggle selections (e.g., 1,3,5-8)"
        echo "  [a]ll    Select all on this page"
        echo "  [c]lear  Deselect all on this page"
        echo "  [n]ext   Next page"
        echo "  [p]rev   Previous page"
        echo "  [d]one   Finish and continue"
        echo "  [q]uit   Cancel and exit script"

        read -p "Your choice: " -r choice

        case "$choice" in
            n|N)
                [[ $((page + 1)) -lt $total_pages ]] && page=$((page + 1))
                ;;
            p|P)
                [[ $page -gt 0 ]] && page=$((page - 1))
                ;;
            a|A)
                for ((i=start; i<end; i++)); do
                    selected[$i]=1
                done
                ;;
            c|C)
                for ((i=start; i<end; i++)); do
                    selected[$i]=0
                done
                ;;
            d|D)
                break
                ;;
            q|Q)
                echo -e "${RED}Cancelled by user${NC}"
                exit 0
                ;;
            *)
                # Parse number selections (e.g., "1,3,5-8")
                IFS=',' read -ra selections <<< "$choice"
                for sel in "${selections[@]}"; do
                    if [[ "$sel" =~ ^([0-9]+)-([0-9]+)$ ]]; then
                        # Range
                        local range_start="${BASH_REMATCH[1]}"
                        local range_end="${BASH_REMATCH[2]}"
                        for ((j=range_start; j<=range_end; j++)); do
                            local idx=$((j - 1))
                            if [[ $idx -ge 0 && $idx -lt ${#dirs[@]} ]]; then
                                selected[$idx]=$((1 - selected[$idx]))
                            fi
                        done
                    elif [[ "$sel" =~ ^[0-9]+$ ]]; then
                        # Single number
                        local idx=$((sel - 1))
                        if [[ $idx -ge 0 && $idx -lt ${#dirs[@]} ]]; then
                            selected[$idx]=$((1 - selected[$idx]))
                        fi
                    fi
                done
                ;;
        esac
    done

    # Update EXCLUDED_DIRS or INCLUDED_DIRS based on selections
    if [[ "$mode" == "include" ]]; then
        INCLUDED_DIRS=()
        for ((i=0; i<${#dirs[@]}; i++)); do
            if [[ ${selected[$i]} -eq 1 ]]; then
                INCLUDED_DIRS+=("${dirs[$i]}")
            fi
        done
        echo -e "\n${GREEN}Selection complete. ${#INCLUDED_DIRS[@]} directories will be processed.${NC}"
        [[ "${#INCLUDED_DIRS[@]}" -gt 0 ]] && echo -e "${BLUE}Processing: ${INCLUDED_DIRS[*]}${NC}"
    else
        EXCLUDED_DIRS=()
        for ((i=0; i<${#dirs[@]}; i++)); do
            if [[ ${selected[$i]} -eq 1 ]]; then
                EXCLUDED_DIRS+=("${dirs[$i]}")
            fi
        done
        echo -e "\n${GREEN}Exclusion list updated. ${#EXCLUDED_DIRS[@]} directories will be excluded.${NC}"
        [[ "${#EXCLUDED_DIRS[@]}" -gt 0 ]] && echo -e "${YELLOW}Excluded: ${EXCLUDED_DIRS[*]}${NC}"
    fi
    sleep 2
}

# Function to get item year from creation date (with fallback to modification date)
get_item_year() {
    local item="$1"
    local birth_time
    local year

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS: try birth time first, fallback to modification time
        year=$(stat -f "%SB" -t "%Y" "$item" 2>/dev/null)
        if [[ -z "$year" || "$year" == "" ]]; then
            year=$(stat -f "%Sm" -t "%Y" "$item" 2>/dev/null)
        fi
    else
        # Linux/Windows: try birth time first
        birth_time=$(stat -c %W "$item" 2>/dev/null)
        if [[ -n "$birth_time" && "$birth_time" != "0" && "$birth_time" != "-" ]]; then
            year=$(date -d "@$birth_time" +%Y 2>/dev/null)
        fi
        # Fallback to modification time
        if [[ -z "$year" || "$year" == "" ]]; then
            year=$(stat -c "%y" "$item" 2>/dev/null | cut -d'-' -f1)
        fi
    fi

    # Return year or "unknown"
    if [[ -n "$year" && "$year" =~ ^[0-9]{4}$ ]]; then
        echo "$year"
    else
        echo "unknown"
    fi
}

# Function to extract extension
get_extension() {
    local filename="$1"
    local ext="${filename##*.}"
    if [[ "$filename" == "$ext" ]]; then
        echo ""
    else
        echo "$ext"
    fi
}

# Function to handle duplicate files
handle_duplicate() {
    local src="$1"
    local dest="$2"
    local filename
    filename=$(basename "$src")

    echo -e "\n${YELLOW}Duplicate found:${NC}"
    echo -e "  Source: $src"
    echo -e "  Exists: $dest"

    # Compare file sizes
    local src_size
    local dest_size
    src_size=$(stat -c%s "$src" 2>/dev/null || stat -f%z "$src" 2>/dev/null)
    dest_size=$(stat -c%s "$dest" 2>/dev/null || stat -f%z "$dest" 2>/dev/null)

    echo -e "  Source size: ${src_size} bytes"
    echo -e "  Existing size: ${dest_size} bytes"

    # Handle based on duplicate mode
    if [[ "$DUPLICATE_MODE" == "skip" ]]; then
        echo -e "${YELLOW}Skipping duplicate file (auto-skip mode)${NC}"
        FILES_SKIPPED=$((FILES_SKIPPED + 1))
        return 1
    elif [[ "$DUPLICATE_MODE" == "rename" ]]; then
        local timestamp
        local base
        local ext
        local new_name
        local new_dest
        timestamp=$(date -r "$src" +"%Y%m%d_%H%M%S" 2>/dev/null || stat -f "%Sm" -t "%Y%m%d_%H%M%S" "$src" 2>/dev/null)
        base="${filename%.*}"
        ext=$(get_extension "$filename")
        new_name="${base}_${timestamp}"
        [[ -n "$ext" ]] && new_name="${new_name}.${ext}"
        new_dest="$(dirname "$dest")/$new_name"

        echo -e "${GREEN}Auto-renaming to: $new_name${NC}"
        if [[ "$DRY_RUN" == false ]]; then
            mv "$src" "$new_dest"
            echo -e "${GREEN}Moved (renamed): $src -> $new_dest${NC}"
            FILES_RENAMED=$((FILES_RENAMED + 1))
        fi
        return 0
    fi

    # Interactive mode
    while true; do
        echo -e "\n${BLUE}Options:${NC}"
        echo "  [r] Rename and move (append timestamp)"
        echo "  [o] Overwrite existing file"
        echo "  [s] Skip this file"
        echo "  [d] Show diff (if text file)"
        echo "  [q] Quit script"
        read -p "Choose [r/o/s/d/q]: " -n 1 -r choice
        echo

        case $choice in
            r|R)
                local timestamp
                local base
                local ext
                local new_name
                local new_dest
                timestamp=$(date -r "$src" +"%Y%m%d_%H%M%S" 2>/dev/null || stat -f "%Sm" -t "%Y%m%d_%H%M%S" "$src" 2>/dev/null)
                base="${filename%.*}"
                ext=$(get_extension "$filename")
                new_name="${base}_${timestamp}"
                [[ -n "$ext" ]] && new_name="${new_name}.${ext}"
                new_dest="$(dirname "$dest")/$new_name"

                echo -e "${GREEN}Renaming to: $new_name${NC}"
                if [[ "$DRY_RUN" == false ]]; then
                    mv "$src" "$new_dest"
                    FILES_RENAMED=$((FILES_RENAMED + 1))
                fi
                return 0
                ;;
            o|O)
                echo -e "${YELLOW}Overwriting existing file${NC}"
                if [[ "$DRY_RUN" == false ]]; then
                    mv -f "$src" "$dest"
                    FILES_MOVED=$((FILES_MOVED + 1))
                fi
                return 0
                ;;
            s|S)
                echo -e "${YELLOW}Skipping file${NC}"
                FILES_SKIPPED=$((FILES_SKIPPED + 1))
                return 1
                ;;
            d|D)
                if command -v diff &> /dev/null; then
                    diff "$src" "$dest" || true
                else
                    echo -e "${RED}diff command not available${NC}"
                fi
                ;;
            q|Q)
                echo -e "${RED}Quitting...${NC}"
                print_summary
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid choice. Please try again.${NC}"
                ;;
        esac
    done
}

# Function to move file to year folder
move_file() {
    local file="$1"
    local year
    year=$(get_item_year "$file")

    if [[ "$year" == "unknown" ]]; then
        [[ "$VERBOSE" == true ]] && echo -e "${RED}Skipping (no date): $file${NC}"
        FILES_SKIPPED=$((FILES_SKIPPED + 1))
        return 0
    fi

    # Filter by year if specified
    if [[ -n "$TARGET_YEAR" && "$year" != "$TARGET_YEAR" ]]; then
        [[ "$VERBOSE" == true ]] && echo -e "Skipping (wrong year): $file"
        return 0
    fi

    # Filter by file type if specified
    if [[ -n "$FILE_TYPE" ]]; then
        local ext
        ext=$(get_extension "$file")
        if [[ ",$FILE_TYPE," != *",$ext,"* ]]; then
            [[ "$VERBOSE" == true ]] && echo -e "Skipping (wrong type): $file"
            return 0
        fi
    fi

    local target_dir="$TARGET_BASE_DIR/$year"
    local filename
    local dest_file
    filename=$(basename "$file")
    dest_file="$target_dir/$filename"

    # Interactive confirmation
    if [[ "$INTERACTIVE" == true ]]; then
        echo -e "\n${BLUE}Move file?${NC}"
        echo -e "  From: $file"
        echo -e "  To:   $dest_file"
        read -p "Proceed? [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            FILES_SKIPPED=$((FILES_SKIPPED + 1))
            return 0
        fi
    fi

    # Create year directory if it doesn't exist
    if [[ "$DRY_RUN" == true ]]; then
        echo -e "${GREEN}[DRY-RUN] Would move: $file -> $dest_file${NC}"
    else
        mkdir -p "$target_dir"

        # Check for duplicates
        if [[ -e "$dest_file" ]]; then
            handle_duplicate "$file" "$dest_file"
        else
            echo -e "${GREEN}Moving: $file -> $dest_file${NC}"
            mv "$file" "$dest_file"
            FILES_MOVED=$((FILES_MOVED + 1))
        fi
    fi
}

# Function to move entire directory to year folder
move_directory() {
    local dir="$1"
    local year
    year=$(get_item_year "$dir")

    if [[ "$year" == "unknown" ]]; then
        [[ "$VERBOSE" == true ]] && echo -e "${RED}Skipping directory (no date): $dir${NC}"
        FILES_SKIPPED=$((FILES_SKIPPED + 1))
        return 0
    fi

    # Filter by year if specified
    if [[ -n "$TARGET_YEAR" && "$year" != "$TARGET_YEAR" ]]; then
        [[ "$VERBOSE" == true ]] && echo -e "Skipping directory (wrong year): $dir"
        return 0
    fi

    local target_dir="$TARGET_BASE_DIR/$year"
    local dirname
    local dest_dir
    dirname=$(basename "$dir")
    dest_dir="$target_dir/$dirname"

    # Interactive confirmation
    if [[ "$INTERACTIVE" == true ]]; then
        echo -e "\n${BLUE}Move entire directory?${NC}"
        echo -e "  From: $dir/"
        echo -e "  To:   $dest_dir/"
        read -p "Proceed? [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            FILES_SKIPPED=$((FILES_SKIPPED + 1))
            return 0
        fi
    fi

    # Create year directory if it doesn't exist
    if [[ "$DRY_RUN" == true ]]; then
        echo -e "${GREEN}[DRY-RUN] Would move directory: $dir/ -> $dest_dir/${NC}"
    else
        mkdir -p "$target_dir"

        # Check for duplicates (directory already exists)
        if [[ -e "$dest_dir" ]]; then
            echo -e "\n${YELLOW}Duplicate directory found:${NC}"
            echo -e "  Source: $dir/"
            echo -e "  Exists: $dest_dir/"

            while true; do
                echo -e "\n${BLUE}Options:${NC}"
                echo "  [r] Rename and move (append timestamp)"
                echo "  [m] Merge contents (move files into existing directory)"
                echo "  [s] Skip this directory"
                echo "  [q] Quit script"
                read -p "Choose [r/m/s/q]: " -n 1 -r choice
                echo

                case $choice in
                    r|R)
                        local timestamp
                        local new_name
                        local new_dest
                        timestamp=$(date +"%Y%m%d_%H%M%S")
                        new_name="${dirname}_${timestamp}"
                        new_dest="$target_dir/$new_name"

                        echo -e "${GREEN}Renaming to: $new_name${NC}"
                        mv "$dir" "$new_dest"
                        FILES_RENAMED=$((FILES_RENAMED + 1))
                        return 0
                        ;;
                    m|M)
                        echo -e "${YELLOW}Merging contents into existing directory${NC}"
                        # Move contents, not the directory itself
                        shopt -s dotglob
                        mv "$dir"/* "$dest_dir/" 2>/dev/null || true
                        shopt -u dotglob
                        rmdir "$dir" 2>/dev/null || echo -e "${YELLOW}Note: Source directory not empty or has hidden files${NC}"
                        FILES_MOVED=$((FILES_MOVED + 1))
                        return 0
                        ;;
                    s|S)
                        echo -e "${YELLOW}Skipping directory${NC}"
                        FILES_SKIPPED=$((FILES_SKIPPED + 1))
                        return 1
                        ;;
                    q|Q)
                        echo -e "${RED}Quitting...${NC}"
                        print_summary
                        exit 0
                        ;;
                    *)
                        echo -e "${RED}Invalid choice. Please try again.${NC}"
                        ;;
                esac
            done
        else
            echo -e "${GREEN}Moving directory: $dir/ -> $dest_dir/${NC}"
            mv "$dir" "$dest_dir"
            FILES_MOVED=$((FILES_MOVED + 1))
        fi
    fi
}

# Function to process files in a directory
process_directory() {
    local dir="$1"
    local current_dir
    current_dir=$(pwd)

    cd "$dir"

    for file in *; do
        # Skip if doesn't exist (empty directory)
        [[ -e "$file" ]] || continue

        # Handle subdirectories
        if [[ -d "$file" ]]; then
            # Skip all directories if --files-only is set
            if [[ "$FILES_ONLY" == true ]]; then
                [[ "$VERBOSE" == true ]] && echo -e "${YELLOW}Skipping directory (files-only mode): $file${NC}"
                continue
            fi

            # Check if directory is excluded
            if is_excluded "$file"; then
                [[ "$VERBOSE" == true ]] && echo -e "${YELLOW}Excluding directory: $file${NC}"
                continue
            fi

            # Move the entire directory to year folder
            move_directory "$file" 2>&1 || {
                echo -e "${RED}Error processing directory: $file${NC}"
                ERRORS=$((ERRORS + 1))
            }
            continue
        fi

        # Skip the script itself
        if [[ "$file" == "org_docs.sh" ]]; then
            continue
        fi

        # Process the file
        move_file "$file" 2>&1 || {
            echo -e "${RED}Error processing: $file${NC}"
            ERRORS=$((ERRORS + 1))
        }
    done

    cd "$current_dir"
}

# Function to print summary
print_summary() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "Files moved:   ${GREEN}${FILES_MOVED}${NC}"
    echo -e "Files renamed: ${YELLOW}${FILES_RENAMED}${NC}"
    echo -e "Files skipped: ${YELLOW}${FILES_SKIPPED}${NC}"
    [[ $ERRORS -gt 0 ]] && echo -e "Errors:        ${RED}${ERRORS}${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Main processing
echo -e "${BLUE}Starting file organization...${NC}"
echo -e "Source directory: ${GREEN}$SOURCE_DIR${NC}"
echo -e "Target base directory: ${GREEN}$TARGET_BASE_DIR${NC}"
[[ "$DRY_RUN" == true ]] && echo -e "${YELLOW}DRY RUN MODE - No changes will be made${NC}"
echo

# Interactive exclusion/inclusion selection if requested
if [[ "$CHOOSE_INCLUDES" == true ]]; then
    choose_exclusions "include"
elif [[ "$CHOOSE_EXCLUDES" == true ]]; then
    choose_exclusions "exclude"
fi

# Process files in source directory
shopt -s nullglob
process_directory "$SOURCE_DIR"

# Print final summary
print_summary

if [[ "$DRY_RUN" == true ]]; then
    echo -e "\n${YELLOW}This was a dry run. Run without --dry-run to apply changes.${NC}"
fi

exit 0
