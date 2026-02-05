#!/bin/bash
# File Organizer - Bash Launcher
# Automatically sets up environment and launches GUI

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🗂️  File Organizer - Setup & Launch${NC}"
echo -e "${CYAN}========================================${NC}"

# Check Python
echo -e "\n${YELLOW}[1/4] Checking Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ Found: $PYTHON_VERSION${NC}"
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
    PYTHON_VERSION=$(python --version)
    echo -e "${GREEN}✓ Found: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python not found!${NC}"
    echo -e "${RED}  Install Python 3.8+ from https://www.python.org/downloads/${NC}"
    exit 1
fi

# Check/Create Virtual Environment
echo -e "\n${YELLOW}[2/4] Checking virtual environment...${NC}"
if [ -d ".venv" ]; then
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
else
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    if $PYTHON_CMD -m venv .venv; then
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    else
        echo -e "${RED}✗ Failed to create virtual environment${NC}"
        exit 1
    fi
fi

# Activate Virtual Environment
echo -e "\n${YELLOW}[3/4] Activating virtual environment...${NC}"
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${RED}✗ Activation script not found${NC}"
    exit 1
fi

# Install/Update Dependencies
echo -e "\n${YELLOW}[4/4] Checking dependencies...${NC}"
if pip list 2>/dev/null | grep -q "PySide6"; then
    echo -e "${GREEN}✓ Dependencies already installed${NC}"
else
    echo -e "${YELLOW}Installing dependencies...${NC}"
    if pip install -r requirements.txt --quiet; then
        echo -e "${GREEN}✓ Dependencies installed${NC}"
    else
        echo -e "${RED}✗ Failed to install dependencies${NC}"
        exit 1
    fi
fi

# Launch GUI
echo -e "\n${CYAN}========================================${NC}"
echo -e "${CYAN}🚀 Launching File Organizer GUI...${NC}"
echo -e "${CYAN}========================================${NC}\n"

if ! python org_docs_gui.py; then
    echo -e "\n${RED}✗ Failed to launch GUI${NC}"
    exit 1
fi
