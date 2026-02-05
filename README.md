# 🗂️ File Organizer

**Automatically organize files and folders into year-based directories.**

Transform this mess:
```
Documents/
├─ report.pdf (2023)
├─ photo.jpg (2024)
├─ OldProject/ (2022)
└─ invoice.pdf (2025)
```

Into this:
```
Documents/
├─ 2022/OldProject/
├─ 2023/report.pdf
├─ 2024/photo.jpg
└─ 2025/invoice.pdf
```

---

## ✨ Features

🎯 **Smart Date Detection** - Uses creation/modification date
🖥️ **Modern GUI + CLI** - Choose your preferred interface
🛡️ **Safe Mode** - Preview changes before applying
📦 **Folder Support** - Moves entire directories as units
💾 **Settings Memory** - Remembers your last preferences
🪟 **Windows Integration** - Configure Git Bash vs WSL path

---

## 🚀 Quick Start

### ⚡ One-Click Launch (Recommended)

**Windows:**
```cmd
launch.bat
```
Or double-click `launch.bat`

**Linux/macOS:**
```bash
./launch.sh
```

The launcher automatically:
- ✅ Checks Python installation
- ✅ Creates virtual environment (if needed)
- ✅ Installs dependencies
- ✅ Launches the GUI
- ❌ Fails fast with clear error messages

### 🔧 Manual Setup

If you prefer manual control:

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows Git Bash
source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt
python org_docs_gui.py
```

---

## 📖 How to Use

1. Launch GUI (see Quick Start above)
2. Select source folder
3. Check folders to organize
4. Enable **Dry Run** (preview mode)
5. Click **▶ Run**
6. Review output, then uncheck Dry Run and run again

---

## 📟 Command Line (Advanced)

```bash
# Preview changes
./org_docs.sh --dry-run

# Interactive selection
./org_docs.sh --choose-includes --dry-run

# Process specific folders
./org_docs.sh --include "Documents" --include "Photos"

# Filter by year or type
./org_docs.sh --year 2023 --type pdf,gdoc
```

**Common Options:**
- `--source-dir PATH` - Source folder
- `--target-dir PATH` - Where to create year folders
- `--dry-run` - Preview only (safe mode)
- `--interactive` - Confirm each move
- `--verbose` - Detailed output

---

## 💡 How It Works

1️⃣ Scans source directory
2️⃣ Reads creation/modification dates
3️⃣ Groups items by year
4️⃣ Moves to year folders (e.g., `2023/`, `2024/`)
5️⃣ Handles duplicates intelligently

---

## 🛡️ Safety

✅ **Dry Run Default** - GUI starts in preview mode
✅ **Settings Saved** - Remembers paths and preferences
✅ **Duplicate Handling** - Rename, merge, or skip conflicts
✅ **Non-Destructive** - Files preserved during moves

---

## 📦 Requirements

- **Python 3.8+**
- **Git Bash** (Windows) or Bash (Linux/macOS)
- **PySide6** (auto-installed via requirements.txt)

---

## 🐛 Troubleshooting

**GUI won't launch?**
```bash
python --version  # Check 3.8+
pip install --upgrade -r requirements.txt
```

**"bash command not found" (Windows)?**
Install [Git Bash](https://git-scm.com/downloads)

**Using Windows and script fails?**
By default, `bash` command launches WSL bash. To use Git Bash:
1. In the GUI, find "Bash Configuration (Windows)" section
2. Set path to: `C:\Program Files\Git\bin\bash.exe`
3. Or click Browse to locate it
4. Path is saved automatically

**Made with ❤️ for organizing chaos**
