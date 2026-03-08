@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "CONTROLL_DIR=%SCRIPT_DIR%"
set "AI_SERVICE_DIR=%SCRIPT_DIR%..\ai_service"
set "VENV_DIR=%CONTROLL_DIR%.venv"
set "REQ_FILE=%CONTROLL_DIR%requirements-chat.txt"
set "CONTROLL_PY=%VENV_DIR%\Scripts\python.exe"
if not defined AIPA_OLLAMA_MODEL set "AIPA_OLLAMA_MODEL=qwen2.5:7b"
if not defined AIPA_OLLAMA_URL set "AIPA_OLLAMA_URL=http://127.0.0.1:11434"
if not defined AIPA_ENABLE_HF_FALLBACK set "AIPA_ENABLE_HF_FALLBACK=1"
if not defined AIPA_TEXT_MODEL set "AIPA_TEXT_MODEL=google/flan-t5-base"
if not defined HF_HUB_OFFLINE set "HF_HUB_OFFLINE=1"
if not defined TRANSFORMERS_OFFLINE set "TRANSFORMERS_OFFLINE=1"
if not defined AIPA_WEB_SEARCH_MODE set "AIPA_WEB_SEARCH_MODE=smart"
if not defined SERPER_API_KEY set "SERPER_API_KEY="
if not defined SERPAPI_API_KEY set "SERPAPI_API_KEY=c629e7a7a90a45a8c084a2663bcd9ccf5837bb88ea711d9a1fa5bf22f4c11abb"
if not defined OPENAI_API_KEY set "OPENAI_API_KEY="
if not defined GEMINI_API_KEY set "GEMINI_API_KEY="

if not defined AIPA_OLLAMA_EXE set "AIPA_OLLAMA_EXE="
if not defined AIPA_OLLAMA_MODELS_DIR set "AIPA_OLLAMA_MODELS_DIR=%AI_SERVICE_DIR%\ollama\models"
set "SERVICE_OLLAMA_MODELS_DIR=%AI_SERVICE_DIR%\ollama\models"
set "RUNTIME_OLLAMA_MODELS_DIR=%CONTROLL_DIR%runtime\ollama\models"
set "BUNDLED_OLLAMA_EXE_1=%AI_SERVICE_DIR%\ollama\ollama.exe"
set "BUNDLED_OLLAMA_EXE_2=%CONTROLL_DIR%ollama\ollama.exe"
set "BUNDLED_OLLAMA_EXE_3=%CONTROLL_DIR%runtime\ollama\ollama.exe"
set "SYSTEM_OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
set "LEGACY_OLLAMA_MODELS_DIR=%SCRIPT_DIR%..\ai_models"
set "OLLAMA_MODELS_DIR=%AIPA_OLLAMA_MODELS_DIR%"
set "OLLAMA_EXE="

if not exist "%OLLAMA_MODELS_DIR%\manifests" if exist "%SERVICE_OLLAMA_MODELS_DIR%\manifests" set "OLLAMA_MODELS_DIR=%SERVICE_OLLAMA_MODELS_DIR%"
if not exist "%OLLAMA_MODELS_DIR%\manifests" if exist "%RUNTIME_OLLAMA_MODELS_DIR%\manifests" set "OLLAMA_MODELS_DIR=%RUNTIME_OLLAMA_MODELS_DIR%"
if not exist "%OLLAMA_MODELS_DIR%\manifests" if exist "%LEGACY_OLLAMA_MODELS_DIR%\manifests" set "OLLAMA_MODELS_DIR=%LEGACY_OLLAMA_MODELS_DIR%"

if defined AIPA_OLLAMA_EXE if exist "%AIPA_OLLAMA_EXE%" set "OLLAMA_EXE=%AIPA_OLLAMA_EXE%"
if not defined OLLAMA_EXE if exist "%BUNDLED_OLLAMA_EXE_1%" set "OLLAMA_EXE=%BUNDLED_OLLAMA_EXE_1%"
if not defined OLLAMA_EXE if exist "%BUNDLED_OLLAMA_EXE_2%" set "OLLAMA_EXE=%BUNDLED_OLLAMA_EXE_2%"
if not defined OLLAMA_EXE if exist "%BUNDLED_OLLAMA_EXE_3%" set "OLLAMA_EXE=%BUNDLED_OLLAMA_EXE_3%"
if not defined OLLAMA_EXE if exist "%SYSTEM_OLLAMA_EXE%" set "OLLAMA_EXE=%SYSTEM_OLLAMA_EXE%"
if not defined OLLAMA_EXE (
  set "AIPA_OLLAMA_MODEL="
  set "AIPA_OLLAMA_URL="
)

if not exist "%CONTROLL_DIR%chat_server.py" (
  echo [ERROR] Khong tim thay chat_server.py trong: %CONTROLL_DIR%
  pause
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
    echo [ERROR] Khong tim thay Python he thong de tao .venv tren may nay.
    echo Cai Python 3 roi chay lai file bat.
    pause
    exit /b 1
  )

  echo [INFO] Dang tao lai Python venv cho may hien tai...
  if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%"
  call !HOST_PY_CMD! -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [ERROR] Tao .venv that bai.
    pause
    exit /b 1
  )

  if not exist "%REQ_FILE%" (
    echo [ERROR] Khong tim thay file requirements: %REQ_FILE%
    pause
    exit /b 1
  )
  call "%CONTROLL_PY%" -m pip install -r "%REQ_FILE%"
  if errorlevel 1 (
    echo [ERROR] Cai dependencies that bai.
    pause
    exit /b 1
  )
)

if /i "%~1"=="--dry-run" (
  echo [DRY-RUN] Se chay lenh:
  echo set OLLAMA_EXE=%OLLAMA_EXE%
  echo set OLLAMA_MODELS=%OLLAMA_MODELS_DIR%
  echo set AIPA_OLLAMA_MODEL=%AIPA_OLLAMA_MODEL%
  echo set AIPA_OLLAMA_URL=%AIPA_OLLAMA_URL%
  echo set AIPA_TEXT_MODEL=%AIPA_TEXT_MODEL%
  echo set HF_HUB_OFFLINE=%HF_HUB_OFFLINE%
  echo set TRANSFORMERS_OFFLINE=%TRANSFORMERS_OFFLINE%
  echo set AIPA_WEB_SEARCH_MODE=%AIPA_WEB_SEARCH_MODE%
  echo set SERPER_API_KEY=***hidden***
  echo set SERPAPI_API_KEY=***hidden***
  echo set OPENAI_API_KEY=%OPENAI_API_KEY%
  echo set GEMINI_API_KEY=%GEMINI_API_KEY%
  echo set AIPA_ENABLE_HF_FALLBACK=%AIPA_ENABLE_HF_FALLBACK%
  echo cd /d "%CONTROLL_DIR%" ^&^& "%CONTROLL_PY%" -m uvicorn chat_server:app --host 0.0.0.0 --port 8001
  exit /b 0
)

cd /d "%CONTROLL_DIR%"
if not exist "%OLLAMA_MODELS_DIR%" mkdir "%OLLAMA_MODELS_DIR%"
set "OLLAMA_MODELS=%OLLAMA_MODELS_DIR%"
set "AIPA_OLLAMA_MODEL=%AIPA_OLLAMA_MODEL%"
set "AIPA_OLLAMA_URL=%AIPA_OLLAMA_URL%"
set "AIPA_TEXT_MODEL=%AIPA_TEXT_MODEL%"
set "HF_HUB_OFFLINE=%HF_HUB_OFFLINE%"
set "TRANSFORMERS_OFFLINE=%TRANSFORMERS_OFFLINE%"
set "AIPA_ENABLE_HF_FALLBACK=%AIPA_ENABLE_HF_FALLBACK%"
set "AIPA_WEB_SEARCH_MODE=%AIPA_WEB_SEARCH_MODE%"
set "SERPER_API_KEY=%SERPER_API_KEY%"
set "SERPAPI_API_KEY=%SERPAPI_API_KEY%"
set "OPENAI_API_KEY=%OPENAI_API_KEY%"
set "GEMINI_API_KEY=%GEMINI_API_KEY%"
set "OLLAMA_OK=0"

if "%SERPER_API_KEY%%SERPAPI_API_KEY%"=="" (
  echo [WARN] Chua co SERPAPI_API_KEY/SERPER_API_KEY. Cau hoi can tra cuu/tai lieu se khong tim tren Google.
)

if defined OLLAMA_EXE (
  for %%D in ("%OLLAMA_EXE%") do set "OLLAMA_BIN_DIR=%%~dpD"
  set "PATH=%OLLAMA_BIN_DIR%;%PATH%"

  powershell -NoProfile -Command "try { Invoke-RestMethod -Uri '%AIPA_OLLAMA_URL%/api/tags' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
  if not errorlevel 1 set "OLLAMA_OK=1"
  if errorlevel 1 (
    echo Khoi dong Ollama serve ^(hidden^) tu: %OLLAMA_EXE%
    powershell -NoProfile -Command "$env:OLLAMA_MODELS='%OLLAMA_MODELS_DIR%'; Start-Process -FilePath '%OLLAMA_EXE%' -ArgumentList 'serve' -WindowStyle Hidden"
    for /l %%I in (1,1,30) do (
      powershell -NoProfile -Command "try { Invoke-RestMethod -Uri '%AIPA_OLLAMA_URL%/api/tags' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
      if not errorlevel 1 (
        set "OLLAMA_OK=1"
        goto :ollama_ready
      )
      timeout /t 1 >nul
    )
  )
) else (
  echo [WARN] Khong tim thay Ollama executable.
  echo [WARN] Hay dat file vao mot trong cac duong dan sau:
  echo        1^) %BUNDLED_OLLAMA_EXE_1%
  echo        2^) %BUNDLED_OLLAMA_EXE_2%
  echo        3^) %BUNDLED_OLLAMA_EXE_3%
  echo [WARN] Hoac set bien moi truong AIPA_OLLAMA_EXE truoc khi chay.
)

:ollama_ready
if defined OLLAMA_EXE if "%OLLAMA_OK%"=="1" (
  echo Ollama API san sang: %AIPA_OLLAMA_URL%
) else (
  if defined OLLAMA_EXE (
    echo [WARN] Khong ket noi duoc Ollama API: %AIPA_OLLAMA_URL%
    echo [WARN] Kiem tra runtime/ollama/ollama.exe va model trong: %OLLAMA_MODELS_DIR%
  ) else (
    echo [INFO] Khong co ollama.exe, se chay bang local HF model: %AIPA_TEXT_MODEL%
  )
)

if defined AIPA_OLLAMA_MODEL (
  echo Dang chay backend voi local model: %AIPA_OLLAMA_MODEL%
) else (
  echo Dang chay backend voi local HF model: %AIPA_TEXT_MODEL%
)
echo [INFO] Dang don backend cu tren cong 8001...
powershell -NoProfile -Command "$toStop = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'uvicorn\\s+chat_server:app' -and $_.CommandLine -match '--port\\s+8001' }; foreach ($p in $toStop) { try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch {} }"
timeout /t 1 >nul
"%CONTROLL_PY%" -m uvicorn chat_server:app --host 0.0.0.0 --port 8001

endlocal



