@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "SCRIPT_DIR=%~dp0"
set "CONTROLL_DIR=%SCRIPT_DIR%"
set "LOG_FILE=%CONTROLL_DIR%run_aipa_all.log"
set "LOCK_DIR=%CONTROLL_DIR%.startup.lock"
set "VENV_DIR=%CONTROLL_DIR%.venv"
set "REQ_FILE=%CONTROLL_DIR%requirements-chat.txt"
set "CONTROLL_PY=%VENV_DIR%\Scripts\python.exe"
set "UVICORN_STDOUT=%CONTROLL_DIR%uvicorn.out.log"
set "UVICORN_STDERR=%CONTROLL_DIR%uvicorn.err.log"

>>"%LOG_FILE%" echo.
>>"%LOG_FILE%" echo [START] %date% %time% cwd=%cd% script_dir=%SCRIPT_DIR%

if not exist "%CONTROLL_DIR%chat_server.py" (
  >>"%LOG_FILE%" echo [ERROR] Missing chat_server.py in %CONTROLL_DIR%
  exit /b 1
)

set "HOST_PY_CMD="
set "NEED_BOOTSTRAP_VENV=0"
if not exist "%CONTROLL_PY%" set "NEED_BOOTSTRAP_VENV=1"
if "%NEED_BOOTSTRAP_VENV%"=="0" (
  "%CONTROLL_PY%" -c "import sys" >nul 2>nul
  if errorlevel 1 set "NEED_BOOTSTRAP_VENV=1"
)

if "%NEED_BOOTSTRAP_VENV%"=="1" (
  where py >nul 2>nul
  if not errorlevel 1 set "HOST_PY_CMD=py -3"
  if not defined HOST_PY_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "HOST_PY_CMD=python"
  )
  if not defined HOST_PY_CMD (
    >>"%LOG_FILE%" echo [ERROR] No host python found to bootstrap venv.
    exit /b 1
  )

  >>"%LOG_FILE%" echo [INFO] Rebuilding .venv with !HOST_PY_CMD!
  if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%"
  call !HOST_PY_CMD! -m venv "%VENV_DIR%"
  if errorlevel 1 (
    >>"%LOG_FILE%" echo [ERROR] venv creation failed.
    exit /b 1
  )
  if not exist "%REQ_FILE%" (
    >>"%LOG_FILE%" echo [ERROR] Missing requirements file %REQ_FILE%
    exit /b 1
  )
  call "%CONTROLL_PY%" -m pip install -r "%REQ_FILE%"
  if errorlevel 1 (
    >>"%LOG_FILE%" echo [ERROR] pip install failed.
    exit /b 1
  )
)

>>"%LOG_FILE%" echo [INFO] Using python=%CONTROLL_PY%

call :check_port
if not errorlevel 1 (
  >>"%LOG_FILE%" echo [INFO] Backend 8001 already available. Exit startup script.
  exit /b 0
)

if exist "%LOCK_DIR%" (
  >>"%LOG_FILE%" echo [WARN] Found existing startup lock. Waiting briefly before reclaiming...
  for /l %%I in (1,1,8) do (
    call :check_port
    if not errorlevel 1 (
      >>"%LOG_FILE%" echo [INFO] Backend became available while waiting on stale lock.
      exit /b 0
    )
    ping 127.0.0.1 -n 2 >nul
  )
  rmdir "%LOCK_DIR%" >nul 2>nul
  >>"%LOG_FILE%" echo [WARN] Removed stale startup lock.
)

mkdir "%LOCK_DIR%" >nul 2>nul
if errorlevel 1 (
  >>"%LOG_FILE%" echo [ERROR] Could not acquire startup lock.
  exit /b 1
)
>>"%LOG_FILE%" echo [INFO] Startup lock acquired.

if not defined AIPA_ENABLE_HF_FALLBACK set "AIPA_ENABLE_HF_FALLBACK=1"
if not defined AIPA_TEXT_MODEL set "AIPA_TEXT_MODEL=google/flan-t5-base"
if not defined AIPA_WEB_SEARCH_MODE set "AIPA_WEB_SEARCH_MODE=smart"

>>"%LOG_FILE%" echo [INFO] Spawning detached uvicorn process...
powershell -NoProfile -Command "Start-Process -FilePath '%CONTROLL_PY%' -WorkingDirectory '%CONTROLL_DIR%' -ArgumentList '-m','uvicorn','chat_server:app','--host','0.0.0.0','--port','8001' -WindowStyle Hidden -RedirectStandardOutput '%UVICORN_STDOUT%' -RedirectStandardError '%UVICORN_STDERR%'"
if errorlevel 1 (
  >>"%LOG_FILE%" echo [ERROR] Failed to spawn detached uvicorn process.
  rmdir "%LOCK_DIR%" >nul 2>nul
  exit /b 1
)

for /l %%I in (1,1,20) do (
  call :check_port
  if not errorlevel 1 (
    >>"%LOG_FILE%" echo [INFO] Backend 8001 is available after detached launch.
    rmdir "%LOCK_DIR%" >nul 2>nul
    exit /b 0
  )
  ping 127.0.0.1 -n 2 >nul
)

>>"%LOG_FILE%" echo [ERROR] Backend 8001 did not become available in time.
if exist "%UVICORN_STDERR%" (
  for /f "usebackq delims=" %%L in ("%UVICORN_STDERR%") do >>"%LOG_FILE%" echo [UVICORN-ERR] %%L
)
rmdir "%LOCK_DIR%" >nul 2>nul
exit /b 1

:check_port
"%CONTROLL_PY%" -c "import socket,sys; s=socket.socket(); s.settimeout(1.5); rc=s.connect_ex(('127.0.0.1',8001)); s.close(); sys.exit(0 if rc==0 else 1)" >nul 2>nul
exit /b %ERRORLEVEL%
