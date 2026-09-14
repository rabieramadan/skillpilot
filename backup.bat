@echo off
REM ===========================================================================
REM  SkillPilot - back up everything that cannot be reinstalled
REM
REM  Run this before upgrading, and on a schedule.
REM  Usage:  backup.bat [destination-directory]     default: backups
REM ===========================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set DEST=%1
if "%DEST%"=="" set DEST=backups

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set DT=%%I
set STAMP=%DT:~0,8%-%DT:~8,6%
set OUT=%DEST%\skillpilot-%STAMP%
mkdir "%OUT%" 2>nul

echo.
echo Backing up to %OUT%
echo.

REM --- 1. Database -----------------------------------------------------------
set DB_URL=
for /f "tokens=1,* delims==" %%A in ('findstr /b "DATABASE_URL=" .env 2^>nul') do set DB_URL=%%B
if defined DB_URL (
    where pg_dump >nul 2>nul
    if errorlevel 1 (
        echo   database ... SKIPPED ^(pg_dump not on PATH^)
        echo       Add PostgreSQL's bin folder to PATH, or back up by hand.
    ) else (
        echo   database ...
        pg_dump "%DB_URL%" > "%OUT%\database.sql"
        if errorlevel 1 (
            echo       FAILED - back the database up by hand before upgrading.
        ) else (
            echo       written
        )
    )
) else (
    echo   database ... SKIPPED ^(DATABASE_URL not found in .env^)
)

REM --- 2. Files the application wrote ---------------------------------------
for %%D in (uploads certificates certificates_issued course_files exam_data exports) do (
    if exist "%%D" (
        echo   %%D\ ...
        xcopy "%%D" "%OUT%\%%D\" /E /I /Q /Y >nul
    )
)

mkdir "%OUT%\json" 2>nul
for %%F in (*.json) do (
    if /i not "%%F"=="package.json" if /i not "%%F"=="package-lock.json" (
        copy /y "%%F" "%OUT%\json\" >nul
    )
)

REM --- 3. Configuration ------------------------------------------------------
echo   configuration ...
if exist config.yaml copy /y config.yaml "%OUT%\" >nul
if exist .env copy /y .env "%OUT%\" >nul
if exist .env.server copy /y .env.server "%OUT%\" >nul

(
echo SkillPilot backup taken %STAMP%
echo.
echo To restore:
echo   1. Database:  psql "%%DATABASE_URL%%" ^< database.sql   ^(into an empty database^)
echo   2. Files:     copy uploads\, certificates\, course_files\, exam_data\
echo                 and the contents of json\ back into the project folder.
echo   3. Config:    copy config.yaml and .env back into the project folder.
echo.
echo SESSION_SECRET in .env must match the value in use when this backup was
echo taken, or API keys stored through Admin ^> AI Settings will not decrypt.
echo.
echo This backup contains live credentials. Keep it private.
) > "%OUT%\RESTORE.txt"

echo.
echo Done: %OUT%
echo It contains live credentials - keep it private.
echo.
pause
