@echo off
echo ========================================
echo    Git Commit Helper
echo ========================================
echo.

echo Current status:
git status --short
echo.

set /p commit_type="Type (feat/fix/style/refactor): "
set /p commit_msg="Message: "

echo.
echo Creating commit...
git add .
git commit -m "%commit_type%: %commit_msg%"

echo.
echo Commit created successfully!
echo.
pause
