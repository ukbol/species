@echo off
echo ========================================
echo UKBOL Gap Analysis Website Updater
echo ========================================
echo.

REM Copy TSV files from mind-the-gap
echo Step 1: Copying TSV files...
copy /Y "C:\GitHub\mind-the-gap\final_result\*.tsv" "C:\GitHub\species\data\"
echo.

REM Build the website
echo Step 2: Building website...
cd /d C:\GitHub\species
python scripts\build.py
echo.

REM Ask about deployment
echo.
set /p deploy="Deploy to GitHub? (y/n): "
if /i "%deploy%"=="y" (
    echo Step 3: Deploying to GitHub...
    git add .
    git commit -m "Update gap analysis data - %date%"
    git push
    echo.
    echo Deployment complete!
) else (
    echo Skipping deployment.
)

echo.
echo Done! Press any key to exit.
pause >nul
