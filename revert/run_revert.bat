@echo off
REM One-time batch script to run the revert script on Windows
REM This will move the incorrectly moved directories back to Drive-Documents

echo ============================================
echo DIRECTORY REVERT SCRIPT
echo ============================================
echo.
echo This will move the following directories back to Drive-Documents:
echo   - AlienFX (from 2023)
echo   - Alienware TactX (from 2023)
echo   - American Truck Simulator (from 2025)
echo   - Audacity (from 2022)
echo   - AutoHotkey (from 2023)
echo   - Battlefield 3 (from 2025)
echo   - cache (from 2021)
echo   - Call of Duty Modern Warfare (from 2021)
echo   - Cline (from 2025)
echo   - Criterion Games (from 2021)
echo.
echo.

pause

REM Run the revert script using Git Bash
"C:\Program Files\Git\bin\bash.exe" revert_moves.sh

echo.
echo ============================================
echo REVERT PROCESS COMPLETE
echo ============================================
echo.
pause
