@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
REM xMobu Installation Script - VERBOSE MODE
REM Automatically configures MotionBuilder to load xMobu on startup

echo.
echo ========================================
echo  xMobu Installation [VERBOSE MODE]
echo ========================================
echo.
echo [INFO] Starting installation process...
echo [INFO] Time: %TIME%
echo [INFO] Date: %DATE%
echo.

REM Check for admin rights
echo [CHECK] Checking administrator privileges...
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARN] Not running as Administrator!
    echo [WARN] Installation may fail if write permissions are denied.
    echo [WARN] If installation fails, right-click and "Run as administrator"
    echo.
) else (
    echo [OK] Running with Administrator privileges
    echo.
)

REM Get the directory where this script is located
echo [STEP 1/5] Determining xMobu installation directory...
set "XMOBU_ROOT=%~dp0"
set "XMOBU_ROOT=%XMOBU_ROOT:~0,-1%"
echo [INFO] Script location: %~dp0
echo [INFO] xMobu Root: %XMOBU_ROOT%
echo.

REM Verify xMobu structure
echo [STEP 2/5] Verifying xMobu directory structure...
set "STRUCTURE_OK=1"

if exist "%XMOBU_ROOT%\core" (
    echo [OK] Found: core\
) else (
    echo [ERROR] Missing: core\
    set "STRUCTURE_OK=0"
)

if exist "%XMOBU_ROOT%\mobu" (
    echo [OK] Found: mobu\
) else (
    echo [ERROR] Missing: mobu\
    set "STRUCTURE_OK=0"
)

if exist "%XMOBU_ROOT%\config\config.json" (
    echo [OK] Found: config\config.json
) else (
    echo [ERROR] Missing: config\config.json
    set "STRUCTURE_OK=0"
)

if "!STRUCTURE_OK!"=="0" (
    echo.
    echo [FATAL] xMobu directory structure is incomplete!
    echo [FATAL] Please ensure all files are present.
    echo.
    pause
    exit /b 1
)
echo.

REM Detect MotionBuilder installations
echo [STEP 3/5] Detecting MotionBuilder installations...
set "MOBU_FOUND=0"
set "MOBU_VERSIONS="

REM Check common installation paths for MotionBuilder 2020-2025
for %%v in (2025 2024 2023 2022 2021 2020) do (
    echo [SCAN] Checking for MotionBuilder %%v...
    if exist "C:\Program Files\Autodesk\MotionBuilder %%v" (
        echo [FOUND] MotionBuilder %%v at: C:\Program Files\Autodesk\MotionBuilder %%v

        REM Check if PythonStartup directory exists
        if exist "C:\Program Files\Autodesk\MotionBuilder %%v\bin\config\PythonStartup" (
            echo [OK] PythonStartup directory exists
        ) else (
            echo [WARN] PythonStartup directory not found, will attempt to create
        )

        set "MOBU_FOUND=1"
        set "MOBU_VERSIONS=!MOBU_VERSIONS! %%v"
    ) else (
        echo [SKIP] MotionBuilder %%v not found
    )
)

echo.
if "%MOBU_FOUND%"=="0" (
    echo [ERROR] No MotionBuilder installation detected in default location
    echo [INFO] Default search location: C:\Program Files\Autodesk\MotionBuilder [VERSION]
    echo.
    echo Manual Installation Required:
    echo 1. Locate your MotionBuilder installation folder
    echo 2. Navigate to: bin\config\PythonStartup
    echo 3. Create a file called xmobu_init.py with the following content:
    echo.
    echo ---- BEGIN FILE CONTENT ----
    echo import sys
    echo sys.path.insert(0, r'%XMOBU_ROOT%'^)
    echo import mobu.startup
    echo ---- END FILE CONTENT ----
    echo.
    echo Terminal will remain open for review...
    pause
    exit /b 1
)

echo [STEP 4/5] Selecting MotionBuilder version(s) to configure...
echo.
echo Found MotionBuilder installations:
echo.

REM List available versions
set /a count=0
for %%v in (%MOBU_VERSIONS%) do (
    set /a count+=1
    echo [!count!] MotionBuilder %%v
    set "VERSION_!count!=%%v"
)

echo.
echo [AUTO-INSTALL] Installing for ALL detected versions...
echo [INFO] To manually select versions, edit install.bat
echo.

echo [STEP 5/5] Installing xMobu...
echo.

REM Automatically install for all versions
for %%v in (%MOBU_VERSIONS%) do (
    call :InstallForVersion %%v
)
goto :Done

:InstallForVersion
set "VERSION=%~1"
set "MOBU_PATH=C:\Program Files\Autodesk\MotionBuilder %VERSION%"
set "STARTUP_PATH=%MOBU_PATH%\bin\config\PythonStartup"

echo.
echo ----------------------------------------
echo [VERSION] MotionBuilder %VERSION%
echo ----------------------------------------
echo [INFO] MotionBuilder path: %MOBU_PATH%
echo [INFO] Startup path: %STARTUP_PATH%
echo.

REM Check if MotionBuilder directory exists
if not exist "%MOBU_PATH%" (
    echo [ERROR] MotionBuilder directory does not exist!
    echo [ERROR] Path: %MOBU_PATH%
    goto :eof
)

REM Create PythonStartup directory if it doesn't exist
if not exist "%STARTUP_PATH%" (
    echo [WARN] PythonStartup directory does not exist
    echo [ACTION] Creating directory: %STARTUP_PATH%
    mkdir "%STARTUP_PATH%" 2>nul

    if exist "%STARTUP_PATH%" (
        echo [OK] Directory created successfully
    ) else (
        echo [ERROR] Failed to create directory (permission denied?)
        echo [ERROR] You may need to run this installer as Administrator
        goto :eof
    )
) else (
    echo [OK] PythonStartup directory exists
)

REM Create the startup script
set "STARTUP_FILE=%STARTUP_PATH%\xmobu_init.py"
echo.
echo [ACTION] Creating startup script...
echo [FILE] %STARTUP_FILE%
echo.
echo [CONTENT] Writing Python startup script:
echo ----------------------------------------

echo # xMobu Startup Script > "%STARTUP_FILE%"
echo # Auto-generated by xMobu installer >> "%STARTUP_FILE%"
echo # This file is executed when MotionBuilder starts >> "%STARTUP_FILE%"
echo # Generated: %DATE% %TIME% >> "%STARTUP_FILE%"
echo. >> "%STARTUP_FILE%"
echo import sys >> "%STARTUP_FILE%"
echo from pathlib import Path >> "%STARTUP_FILE%"
echo. >> "%STARTUP_FILE%"
echo # Add xMobu to Python path >> "%STARTUP_FILE%"
echo xmobu_root = r'%XMOBU_ROOT%' >> "%STARTUP_FILE%"
echo if xmobu_root not in sys.path: >> "%STARTUP_FILE%"
echo     sys.path.insert(0, xmobu_root) >> "%STARTUP_FILE%"
echo     print(f"[xMobu] Added {xmobu_root} to Python path") >> "%STARTUP_FILE%"
echo else: >> "%STARTUP_FILE%"
echo     print(f"[xMobu] {xmobu_root} already in Python path") >> "%STARTUP_FILE%"
echo. >> "%STARTUP_FILE%"
echo # Initialize xMobu >> "%STARTUP_FILE%"
echo print("[xMobu] Initializing xMobu menu system...") >> "%STARTUP_FILE%"
echo try: >> "%STARTUP_FILE%"
echo     import mobu.startup >> "%STARTUP_FILE%"
echo     print("[xMobu] Initialization completed successfully!") >> "%STARTUP_FILE%"
echo     print("[xMobu] Menu should appear in: xMobu ^> [categories]") >> "%STARTUP_FILE%"
echo except ImportError as e: >> "%STARTUP_FILE%"
echo     print(f"[xMobu ERROR] Import failed - {str(e)}") >> "%STARTUP_FILE%"
echo     print("[xMobu ERROR] Check that all xMobu files are present") >> "%STARTUP_FILE%"
echo     import traceback >> "%STARTUP_FILE%"
echo     traceback.print_exc() >> "%STARTUP_FILE%"
echo except Exception as e: >> "%STARTUP_FILE%"
echo     print(f"[xMobu ERROR] Initialization failed - {str(e)}") >> "%STARTUP_FILE%"
echo     import traceback >> "%STARTUP_FILE%"
echo     traceback.print_exc() >> "%STARTUP_FILE%"

echo ----------------------------------------
echo.

REM Verify file was created
if exist "%STARTUP_FILE%" (
    echo [OK] Startup script created successfully!

    REM Show file size
    for %%A in ("%STARTUP_FILE%") do (
        echo [INFO] File size: %%~zA bytes
        echo [INFO] File location: %%~fA
    )

    REM Try to read first few lines to verify content
    echo.
    echo [VERIFY] Reading back file content (first 5 lines^):
    echo ----------------------------------------
    type "%STARTUP_FILE%" | more +0 | findstr /N "^" | findstr "^[1-5]:"
    echo ----------------------------------------
    echo.
    echo [SUCCESS] MotionBuilder %VERSION% configured successfully!
) else (
    echo [ERROR] Failed to create startup script!
    echo [ERROR] Target path: %STARTUP_FILE%
    echo [ERROR] Possible causes:
    echo [ERROR] - Permission denied (try running as Administrator^)
    echo [ERROR] - Disk full
    echo [ERROR] - Antivirus blocking file creation
    echo.
    echo [WORKAROUND] Manual installation:
    echo 1. Create file: %STARTUP_FILE%
    echo 2. Copy the content shown above into the file
    echo 3. Save and restart MotionBuilder
)
echo.

goto :eof

:Done
echo.
echo ========================================
echo  Installation Complete!
echo ========================================
echo [INFO] Installation finished at: %TIME%
echo.

if exist "%STARTUP_FILE%" (
    echo [STATUS] xMobu has been installed successfully!
    echo.
    echo [NEXT STEPS]
    echo 1. Start/Restart MotionBuilder %VERSION%
    echo 2. Open Python Console: View ^> Python Console
    echo 3. Look for xMobu initialization messages in console
    echo 4. Check menu bar for "xMobu" menu
    echo 5. If menu appears - SUCCESS! Browse tools in submenus
    echo.
    echo [TROUBLESHOOTING]
    echo - If menu doesn't appear, check Python Console for errors
    echo - All xMobu messages are prefixed with [xMobu]
    echo - Report any errors you see
    echo.
) else (
    echo [WARNING] Installation may have failed!
    echo [ACTION] Review error messages above
    echo [ACTION] Try running this installer as Administrator
    echo.
)

echo [CONFIGURATION]
echo - Config file: %XMOBU_ROOT%\config\config.json
echo - Add tools to: %XMOBU_ROOT%\mobu\tools\
echo - Documentation: %XMOBU_ROOT%\README.md
echo.
echo [UNINSTALL]
echo - Run: %XMOBU_ROOT%\uninstall.bat
echo - Or delete: %STARTUP_FILE%
echo.
echo Terminal will remain open for review...
echo Press any key to close...
pause >nul
