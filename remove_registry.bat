@echo off

echo Deleting registry entries for YouTube Downloader...

reg delete "HKEY_CLASSES_ROOT\Directory\Background\shell\Download from YouTube" /f
reg delete "HKEY_CLASSES_ROOT\Directory\shell\Download from YouTube" /f

echo All registry entries have been removed!
pause
