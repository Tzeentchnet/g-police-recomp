@echo off
setlocal

set "ROOT=%~dp0"

rem Prefer a build that has completed launcher setup.
set "EXE=%ROOT%G_Police_Recompiled.exe"
if exist "%EXE%" if exist "%ROOT%bios.cfg" goto launch

set "EXE=%ROOT%build-release\G_Police_Recompiled.exe"
if exist "%EXE%" if exist "%ROOT%build-release\bios.cfg" goto launch

set "EXE=%ROOT%build-latest\G_Police_Recompiled.exe"
if exist "%EXE%" if exist "%ROOT%build-latest\bios.cfg" goto launch

set "EXE=%ROOT%build\G_Police_Recompiled.exe"
if exist "%EXE%" if exist "%ROOT%build\bios.cfg" goto launch

set "EXE=%ROOT%build-full\G_Police_Recompiled.exe"
if exist "%EXE%" if exist "%ROOT%build-full\bios.cfg" goto launch

set "EXE=%ROOT%build-verify\G_Police_Recompiled.exe"
if exist "%EXE%" if exist "%ROOT%build-verify\bios.cfg" goto launch

set "EXE=%ROOT%G_Police_Recompiled.exe"
if exist "%EXE%" goto launch

set "EXE=%ROOT%build-release\G_Police_Recompiled.exe"
if exist "%EXE%" goto launch

set "EXE=%ROOT%build-latest\G_Police_Recompiled.exe"
if exist "%EXE%" goto launch

set "EXE=%ROOT%build\G_Police_Recompiled.exe"
if exist "%EXE%" goto launch

set "EXE=%ROOT%build-full\G_Police_Recompiled.exe"
if exist "%EXE%" goto launch

set "EXE=%ROOT%build-verify\G_Police_Recompiled.exe"
if exist "%EXE%" goto launch

echo Launcher executable not found.
echo Build the psx-runtime target first:
echo   cmake --build build --target psx-runtime
pause
exit /b 1

:launch
start "" /D "%ROOT%" "%EXE%" --launcher
if errorlevel 1 (
    echo Failed to start the launcher:
    echo   %EXE%
    pause
    exit /b 1
)

exit /b 0
