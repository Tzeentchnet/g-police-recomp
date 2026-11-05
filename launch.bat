@echo off
setlocal

set "ROOT=%~dp0"

rem Prefer a build that has completed launcher setup.
set "EXE=%ROOT%G_Police_Recompiled.exe"
if exist "%EXE%" if exist "%ROOT%bios.cfg" goto launch

call :try_build "%ROOT%build-release"
if not errorlevel 1 if exist "%ROOT%build-release\bios.cfg" goto launch

call :try_build "%ROOT%build-latest"
if not errorlevel 1 if exist "%ROOT%build-latest\bios.cfg" goto launch

call :try_build "%ROOT%build"
if not errorlevel 1 if exist "%ROOT%build\bios.cfg" goto launch

call :try_build "%ROOT%build-full"
if not errorlevel 1 if exist "%ROOT%build-full\bios.cfg" goto launch

call :try_build "%ROOT%build-verify"
if not errorlevel 1 if exist "%ROOT%build-verify\bios.cfg" goto launch

set "EXE=%ROOT%G_Police_Recompiled.exe"
if exist "%EXE%" goto launch

call :try_build "%ROOT%build-release"
if not errorlevel 1 goto launch

call :try_build "%ROOT%build-latest"
if not errorlevel 1 goto launch

call :try_build "%ROOT%build"
if not errorlevel 1 goto launch

call :try_build "%ROOT%build-full"
if not errorlevel 1 goto launch

call :try_build "%ROOT%build-verify"
if not errorlevel 1 goto launch

echo Playable launcher executable not found.
echo Setup-host-only build directories were ignored.
echo Build the psx-runtime target first:
echo   cmake --build build --target psx-runtime
pause
exit /b 1

:launch
if /I "%G_POLICE_LAUNCH_DRY_RUN%"=="1" goto print_selection
start "" /D "%ROOT%" "%EXE%" --launcher
if errorlevel 1 goto launch_failed

exit /b 0

:print_selection
echo %EXE%
exit /b 0

:launch_failed
echo Failed to start the launcher:
echo   %EXE%
pause
exit /b 1

:try_build
set "EXE=%~1\G_Police_Recompiled.exe"
if not exist "%EXE%" exit /b 1
if not exist "%~1\CMakeCache.txt" exit /b 0
findstr /B /C:"PSXRECOMP_FORCE_SETUP_HOST:BOOL=ON" "%~1\CMakeCache.txt" >nul 2>nul
if not errorlevel 1 exit /b 1
if not exist "%~1\psx-runtime_generated_sources.txt" exit /b 1
exit /b 0
