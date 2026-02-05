# File Organizer - PowerShell Launcher
# Automatically sets up environment and launches GUI

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "🗂️  File Organizer - Setup & Launch" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check Python
Write-Host "`n[1/4] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw }
    Write-Host "✓ Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found!" -ForegroundColor Red
    Write-Host "  Install Python 3.8+ from https://www.python.org/downloads/" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check/Create Virtual Environment
Write-Host "`n[2/4] Checking virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "✓ Virtual environment exists" -ForegroundColor Green
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    try {
        python -m venv .venv
        Write-Host "✓ Virtual environment created" -ForegroundColor Green
    } catch {
        Write-Host "✗ Failed to create virtual environment" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Activate Virtual Environment
Write-Host "`n[3/4] Activating virtual environment..." -ForegroundColor Yellow
$activateScript = Join-Path $ScriptDir ".venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    . $activateScript
    Write-Host "✓ Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "✗ Activation script not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Install/Update Dependencies
Write-Host "`n[4/4] Checking dependencies..." -ForegroundColor Yellow
try {
    $installed = pip list --format=freeze 2>&1 | Select-String "PySide6"
    if ($installed) {
        Write-Host "✓ Dependencies already installed" -ForegroundColor Green
    } else {
        Write-Host "Installing dependencies..." -ForegroundColor Yellow
        pip install -r requirements.txt --quiet
        Write-Host "✓ Dependencies installed" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠ Dependency check failed, attempting install..." -ForegroundColor Yellow
    try {
        pip install -r requirements.txt
        Write-Host "✓ Dependencies installed" -ForegroundColor Green
    } catch {
        Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Launch GUI
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "🚀 Launching File Organizer GUI..." -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

try {
    python org_docs_gui.py
} catch {
    Write-Host "`n✗ Failed to launch GUI" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
