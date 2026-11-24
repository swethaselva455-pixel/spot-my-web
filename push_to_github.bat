@echo off
title Push SpotMyShoot to GitHub
cd /d "C:\Users\sweth\.gemini\antigravity\scratch\spotmyshoot"

set "GIT=C:\Users\sweth\AppData\Local\Programs\Git\cmd\git.exe"

echo ===============================================================
echo     Pushing SpotMyShoot to https://github.com/swethaselva455-pixel/spot-my-web
echo ===============================================================
echo.

"%GIT%" remote remove origin 2>nul
"%GIT%" remote add origin https://github.com/swethaselva455-pixel/spot-my-web.git
"%GIT%" branch -M main

echo Staging any recent changes...
"%GIT%" add .
"%GIT%" commit -m "feat: complete SpotMyShoot creative studio booking platform" 2>nul

echo.
echo Pushing to GitHub (A browser window may open to authorize GitHub)...
"%GIT%" push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===============================================================
    echo [SUCCESS] All files and folders pushed successfully to GitHub!
    echo Check your repository: https://github.com/swethaselva455-pixel/spot-my-web
    echo ===============================================================
) else (
    echo.
    echo [NOTE] If it asks for credentials, you can enter your GitHub Username
    echo and a GitHub Personal Access Token (PAT) as the password.
)

echo.
pause
