@setlocal DisableDelayedExpansion
@set "CHAMELEON_ACTION_DIR=%~dp0..\runtime\actions"
@set "CHAMELEON_CORE=%~dp0..\core\ChameleonCore.exe"
@set "CHAMELEON_RESPONSE=%CHAMELEON_ACTION_DIR%\%RANDOM%%RANDOM%%RANDOM%%RANDOM%.response"
@"%CHAMELEON_CORE%" --emit cmd --response "%CHAMELEON_RESPONSE%" %*
@if errorlevel 1 (endlocal & exit /b 1)
@if not exist "%CHAMELEON_RESPONSE%" (endlocal & exit /b 0)
@for /f "usebackq delims=" %%T in ("%CHAMELEON_RESPONSE%") do @set "CHAMELEON_TOKEN=%%T"
@del "%CHAMELEON_RESPONSE%" >nul 2>&1
@endlocal & set "_CHAMELEON_ACTION_FILE=%CHAMELEON_ACTION_DIR%\%CHAMELEON_TOKEN%.cmd"
@call "%%_CHAMELEON_ACTION_FILE%%"
@set "_CHAMELEON_EXIT=%errorlevel%"
@del "%_CHAMELEON_ACTION_FILE%" >nul 2>&1
@set "_CHAMELEON_ACTION_FILE="
@set "_CHAMELEON_EXIT=" & exit /b %_CHAMELEON_EXIT%
