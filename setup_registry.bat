@echo off
REM Get the current directory where the script is located
SET "SCRIPT_DIR=%~dp0"

REM Define the paths
SET "PYTHONW_PATH=pythonw.exe"
SET "SCRIPT_PATH=%SCRIPT_DIR%youtube_downloader.pyw"
SET "ICON_PATH=%SCRIPT_DIR%youtube_icon.ico"

REM Add registry entry for Download from YouTube
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
