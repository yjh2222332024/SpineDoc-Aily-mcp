@echo off
setlocal enabledelayedexpansion
title SpineDoc Setup Wizard
cd /d %~dp0

set ENV_FILE=.env

echo ============================================
echo   SpineDoc Setup Wizard
echo ============================================
echo.

:: -- Check existing .env --
if exist "%ENV_FILE%" (
    set "OVERWRITE="
    set /p "OVERWRITE=.env exists, overwrite? (y/N): "
    if /i not "!OVERWRITE!"=="y" (
        if /i not "!OVERWRITE!"=="Y" (
            echo Cancelled, using existing .env.
            goto :end
        )
    )
)

:: -- [1/4] LLM --
echo -- [1/4] LLM (required) -------------------

set "TEMP_VAR="
set /p "TEMP_VAR=LLM API Key [no default]: "
set "LLM_API_KEY=%TEMP_VAR%"

set "TEMP_VAR="
set /p "TEMP_VAR=LLM Base URL [https://ark.cn-beijing.volces.com/api/v3]: "
if not defined TEMP_VAR set "TEMP_VAR=https://ark.cn-beijing.volces.com/api/v3"
set "LLM_BASE_URL=%TEMP_VAR%"

set "TEMP_VAR="
set /p "TEMP_VAR=LLM Endpoint ID [no default]: "
set "LLM_ENDPOINT=%TEMP_VAR%"

echo.

:: -- [2/4] Embedding & Search --
echo -- [2/4] Embedding & Search (required) ------

set "TEMP_VAR="
set /p "TEMP_VAR=SiliconFlow API Key [no default]: "
set "EMBEDDING_API_KEY=%TEMP_VAR%"

set "TEMP_VAR="
set /p "TEMP_VAR=Zhipu API Key (web search) [no default]: "
set "ZHIPU_API_KEY=%TEMP_VAR%"

echo.

:: -- [3/4] Feishu --
echo -- [3/4] Feishu Integration (required) -----

set "TEMP_VAR="
set /p "TEMP_VAR=App ID [no default]: "
set "FEISHU_APP_ID=%TEMP_VAR%"

set "TEMP_VAR="
set /p "TEMP_VAR=App Secret [no default]: "
set "FEISHU_APP_SECRET=%TEMP_VAR%"

echo.
set "TEMP_VAR="
set /p "TEMP_VAR=Auto-create Feishu tables? (y/N): "
if /i "!TEMP_VAR!"=="y" (
    echo -- Auto-creating Feishu Bitable...
    .venv\Scripts\python.exe scripts/provision_feishu.py --yes
    if !ERRORLEVEL! equ 0 (
        echo [OK] Auto-config success
        echo -- Reading back from .env...
        for /f "tokens=1,* delims==" %%a in ('findstr /R "^[A-Z].*=." .env') do (
            if /i "%%a"=="FEISHU_BITABLE_TOKEN" set "FEISHU_BITABLE_TOKEN=%%b"
            if /i "%%a"=="FEISHU_BITABLE_TABLE_ID" set "FEISHU_BITABLE_TABLE_ID=%%b"
            if /i "%%a"=="FEISHU_BITABLE_CHUNK_TABLE_ID" set "FEISHU_BITABLE_CHUNK_TABLE_ID=%%b"
            if /i "%%a"=="FEISHU_BITABLE_TOC_TABLE_ID" set "FEISHU_BITABLE_TOC_TABLE_ID=%%b"
            if /i "%%a"=="FEISHU_BITABLE_MEMORY_TABLE_ID" set "FEISHU_BITABLE_MEMORY_TABLE_ID=%%b"
            if /i "%%a"=="FEISHU_BITABLE_GALAXY_TABLE_ID" set "FEISHU_BITABLE_GALAXY_TABLE_ID=%%b"
        )
        goto :feishu_done
    ) else (
        echo [WARN] Auto-config failed, please enter manually
    )
)

set "TEMP_VAR="
set /p "TEMP_VAR=Bitable Token [no default]: "
set "FEISHU_BITABLE_TOKEN=%TEMP_VAR%"

set "TEMP_VAR="
set /p "TEMP_VAR=Docs Table ID [no default]: "
set "FEISHU_BITABLE_TABLE_ID=%TEMP_VAR%"

set "TEMP_VAR="
set /p "TEMP_VAR=Chunks Table ID [no default]: "
set "FEISHU_BITABLE_CHUNK_TABLE_ID=%TEMP_VAR%"

set "TEMP_VAR="
set /p "TEMP_VAR=Memory Table ID [no default]: "
set "FEISHU_BITABLE_MEMORY_TABLE_ID=%TEMP_VAR%"

set "TEMP_VAR="
set /p "TEMP_VAR=TOC Table ID (optional, create if empty): "
set "FEISHU_BITABLE_TOC_TABLE_ID=%TEMP_VAR%"

set "TEMP_VAR="
set /p "TEMP_VAR=Galaxy Table ID (optional, create if empty): "
set "FEISHU_BITABLE_GALAXY_TABLE_ID=%TEMP_VAR%"

:feishu_done

set "TEMP_VAR="
set /p "TEMP_VAR=Notify Chat ID (oc_xxx, optional): "
if defined TEMP_VAR set "FEISHU_DEFAULT_CHAT_ID=%TEMP_VAR%"

echo.

:: -- [4/4] Optional --
echo -- [4/4] Optional -------------------------

set "TEMP_VAR="
set /p "TEMP_VAR=ARK API Key (OCR, optional): "
set "ARK_API_KEY=%TEMP_VAR%"

set "TEMP_VAR="
set /p "TEMP_VAR=ARK Endpoint (optional): "
set "ARK_ENDPOINT=%TEMP_VAR%"

set "TEMP_VAR="
set /p "TEMP_VAR=Aily Token (optional): "
set "FEISHU_AILY_TOKEN=%TEMP_VAR%"

echo.

:: -- Write .env --
echo ============================================
echo Generating %ENV_FILE%...
echo ============================================

(
    echo # SpineDoc auto-generated config
    echo.
    echo # --- LLM ---
    echo LLM_API_KEY=%LLM_API_KEY%
    echo LLM_BASE_URL=%LLM_BASE_URL%
    echo LLM_ENDPOINT=%LLM_ENDPOINT%
    echo.
    echo # --- Embedding ---
    echo EMBEDDING_API_KEY=%EMBEDDING_API_KEY%
    echo.
    echo # --- Web Search ---
    echo ZHIPU_API_KEY=%ZHIPU_API_KEY%
    echo.
    echo # --- Feishu ---
    echo FEISHU_APP_ID=%FEISHU_APP_ID%
    echo FEISHU_APP_SECRET=%FEISHU_APP_SECRET%
    echo FEISHU_BITABLE_TOKEN=%FEISHU_BITABLE_TOKEN%
    echo FEISHU_BITABLE_TABLE_ID=%FEISHU_BITABLE_TABLE_ID%
    echo FEISHU_BITABLE_CHUNK_TABLE_ID=%FEISHU_BITABLE_CHUNK_TABLE_ID%
    echo FEISHU_BITABLE_TOC_TABLE_ID=%FEISHU_BITABLE_TOC_TABLE_ID%
    echo FEISHU_BITABLE_MEMORY_TABLE_ID=%FEISHU_BITABLE_MEMORY_TABLE_ID%
    echo FEISHU_BITABLE_GALAXY_TABLE_ID=%FEISHU_BITABLE_GALAXY_TABLE_ID%
    echo FEISHU_DEFAULT_CHAT_ID=%FEISHU_DEFAULT_CHAT_ID%
    echo.
    echo # --- OCR (optional) ---
    echo ARK_API_KEY=%ARK_API_KEY%
    echo ARK_ENDPOINT=%ARK_ENDPOINT%
    echo.
    echo # --- Aily (optional) ---
    echo FEISHU_AILY_TOKEN=%FEISHU_AILY_TOKEN%
) > %ENV_FILE%

echo [OK] .env generated: %CD%\%ENV_FILE%
echo.

:: -- Validate required fields --
echo ============================================
echo Validating...

set MISSING=

if not defined LLM_API_KEY            set "MISSING=%MISSING% LLM_API_KEY"
if not defined EMBEDDING_API_KEY       set "MISSING=%MISSING% EMBEDDING_API_KEY"
if not defined ZHIPU_API_KEY           set "MISSING=%MISSING% ZHIPU_API_KEY"
if not defined FEISHU_APP_ID           set "MISSING=%MISSING% FEISHU_APP_ID"
if not defined FEISHU_APP_SECRET       set "MISSING=%MISSING% FEISHU_APP_SECRET"
if not defined FEISHU_BITABLE_TOKEN    set "MISSING=%MISSING% FEISHU_BITABLE_TOKEN"
if not defined FEISHU_BITABLE_TABLE_ID set "MISSING=%MISSING% FEISHU_BITABLE_TABLE_ID"
if not defined FEISHU_BITABLE_CHUNK_TABLE_ID   set "MISSING=%MISSING% FEISHU_BITABLE_CHUNK_TABLE_ID"
if not defined FEISHU_BITABLE_MEMORY_TABLE_ID  set "MISSING=%MISSING% FEISHU_BITABLE_MEMORY_TABLE_ID"
if not defined FEISHU_DEFAULT_CHAT_ID  set "MISSING=%MISSING% FEISHU_DEFAULT_CHAT_ID"

if defined MISSING (
    echo [WARN] Missing required fields:
    for %%v in (%MISSING%) do echo   - %%v
) else (
    echo [OK] All required fields set.
)

echo.
echo ============================================
echo Setup complete. Run start_mcp.bat to start.
echo ============================================

:end
pause