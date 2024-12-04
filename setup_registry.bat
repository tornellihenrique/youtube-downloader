@echo off
REM Get the directory of the batch file
SET "SCRIPT_DIR=%~dp0"

REM Define paths
SET "SCRIPT_PATH=%SCRIPT_DIR%youtube_downloader.pyw"
SET "ICON_PATH=%SCRIPT_DIR%youtube_icon.ico"

REM Detect the full path of pythonw.exe
FOR /F "delims=" %%I IN ('where pythonw.exe') DO SET "PYTHONW_PATH=%%I"

REM If pythonw.exe is not found, show an error and exit
IF NOT DEFINED PYTHONW_PATH (
    echo pythonw.exe not found in PATH. Ensure Python is installed and added to PATH.
    pause
    exit /b
)

REM Add registry entry for "Download from YouTube" in the context menu
REM For context menu inside folders
REG ADD "HKEY_CLASSES_ROOT\Directory\Background\shell\Download from YouTube" /ve /d "Download from YouTube" /f
REG ADD "HKEY_CLASSES_ROOT\Directory\Background\shell\Download from YouTube" /v "Icon" /d "\"%ICON_PATH%\"" /f
REG ADD "HKEY_CLASSES_ROOT\Directory\Background\shell\Download from YouTube\command" /ve /t REG_EXPAND_SZ /d "\"%PYTHONW_PATH%\" \"%SCRIPT_PATH%\" \"%%V\"" /f

REM For context menu on folders
REG ADD "HKEY_CLASSES_ROOT\Directory\shell\Download from YouTube" /ve /d "Download from YouTube" /f
REG ADD "HKEY_CLASSES_ROOT\Directory\shell\Download from YouTube" /v "Icon" /d "\"%ICON_PATH%\"" /f
REG ADD "HKEY_CLASSES_ROOT\Directory\shell\Download from YouTube\command" /ve /t REG_EXPAND_SZ /d "\"%PYTHONW_PATH%\" \"%SCRIPT_PATH%\" \"%%V\"" /f

echo Registry entries have been added successfully.
pause
