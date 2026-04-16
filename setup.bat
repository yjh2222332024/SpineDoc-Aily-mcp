@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 颜色定义
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do (
  set "DEL=%%a"
  set "CLR=%%b"
)
set "GREEN=[32m"
set "RED=[31m"
set "YELLOW=[33m"
set "BLUE=[34m"
set "CYAN=[36m"
set "RESET=[0m"
set "BOLD=[1m"

:: 标题
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║  🛡️  SpineDoc (阅脊) - 一键配置与启动                        ║
echo ║      Logic Assassin Document Audit Engine                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: 检查 Python
echo %BOLD%%BLUE%═══ 🐍 Python 环境检查 %RESET%
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%✗ Python 未安装或未添加到 PATH%RESET%
    echo.
    echo 请前往 https://www.python.org/downloads/ 安装 Python 3.10+
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1 ^| find "Python"') do set PYVER=%%i
echo %GREEN%✓ Python %PYVER%%RESET%

:: 检查虚拟环境
if not exist ".venv" (
    echo %YELLOW%⚠ 虚拟环境不存在，正在创建...%RESET%
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo %RED%✗ 虚拟环境创建失败%RESET%
        pause
        exit /b 1
    )
    echo %GREEN%✓ 虚拟环境创建完成%RESET%
) else (
    echo %GREEN%✓ 虚拟环境已存在%RESET%
)

:: 激活虚拟环境
call .venv\Scripts\activate.bat

:: 检查依赖
echo %BOLD%%BLUE%═══ 📦 依赖检查 %RESET%
python -c "import sqlmodel, typer, rich" >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%⚠ 依赖缺失，正在安装...%RESET%

    :: 升级 pip
    python -m pip install --upgrade pip -q

    :: 安装 requirements.txt
    if exist "requirements.txt" (
        echo 安装 requirements.txt...
        pip install -r requirements.txt -q
    ) else if exist "backend\requirements.txt" (
        echo 安装 backend/requirements.txt...
        pip install -r backend\requirements.txt -q
    )

    :: 安装 spine-cli
    echo 安装 spine-cli...
    pip install -e . -q

    echo %GREEN%✓ 依赖安装完成%RESET%
) else (
    echo %GREEN%✓ 依赖已安装%RESET%
)

:: 检查 .env 配置
echo %BOLD%%BLUE%═══ ⚙️ 配置检查 %RESET%
if not exist ".env" (
    echo %YELLOW%⚠ .env 配置文件不存在%RESET%
    echo.
    echo 将启动配置向导...
    echo.
    goto :wizard
) else (
    echo %GREEN%✓ .env 配置文件存在%RESET%

    :: 简单检查关键配置
    findstr /C:"LLM_API_KEY=" .env >nul 2>&1
    if %errorlevel% neq 0 (
        echo %YELLOW%⚠ LLM_API_KEY 未配置%RESET%
        goto :wizard
    )

    findstr /C:"EMBEDDING_API_KEY=" .env >nul 2>&1
    if %errorlevel% neq 0 (
        echo %YELLOW%⚠ EMBEDDING_API_KEY 未配置%RESET%
        goto :wizard
    )

    echo %GREEN%✓ 关键配置已设置%RESET%
)

goto :launch

:wizard
echo.
echo %BOLD%%CYAN%═══ 快速配置向导 %RESET%
echo.

:: 数据库
set /p DB_URL="PostgreSQL 连接字符串 [postgresql+asyncpg://spinedoc:spinedoc123@localhost:5432/spinedoc]: "
if "!DB_URL!"=="" set "DB_URL=postgresql+asyncpg://spinedoc:spinedoc123@localhost:5432/spinedoc"

:: DeepSeek
echo.
echo %BOLD%DeepSeek API Key%RESET%
echo  - 注册地址：https://platform.deepseek.com/
set /p LLM_KEY="请输入 DeepSeek API Key: "

:: SiliconFlow
echo.
echo %BOLD%SiliconFlow API Key%RESET%
echo  - 注册地址：https://cloud.siliconflow.cn/
echo  - 用于向量模型和 VLM
set /p SF_KEY="请输入 SiliconFlow API Key: "

:: Tavily (可选)
echo.
echo %BOLD%Tavily API Key (可选，联网搜索)%RESET%
echo  - 注册地址：https://tavily.com/
set /p TAVILY_KEY="请输入 Tavily API Key (直接回车跳过): "

:: 保存配置
echo.
echo %BOLD%%GREEN%正在保存配置...%RESET%

(
    echo # SpineDoc Configuration
    echo # Generated at: %date% %time%
    echo.
    echo # ========== 数据库配置 ==========
    echo DATABASE_URL=!DB_URL!
    echo.
    echo # ========== LLM 配置 ==========
    echo LLM_API_KEY=!LLM_KEY!
    echo LLM_BASE_URL=https://api.deepseek.com/v1
    echo LLM_MODEL_NAME=deepseek-chat
    echo.
    echo # ========== 向量模型配置 ==========
    echo EMBEDDING_API_KEY=!SF_KEY!
    echo EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
    echo EMBEDDING_MODEL_NAME=BAAI/bge-m3
    echo EMBEDDING_DIMENSION=1024
    echo.
    echo # ========== VLM 配置 ==========
    echo VLM_API_KEY=!SF_KEY!
    echo VLM_BASE_URL=https://api.siliconflow.cn/v1
    echo VLM_MODEL_NAME=Qwen/Qwen2.5-VL-72B-Instruct
    echo.
    echo # ========== OCR 配置 ==========
   
    echo.
    echo # ========== 联网搜索配置 ==========
    if "!TAVILY_KEY!"=="" (
        echo # TAVILY_API_KEY=未配置
    ) else (
        echo TAVILY_API_KEY=!TAVILY_KEY!
        echo TAVILY_MAX_RESULTS=3
        echo TAVILY_SEARCH_DEPTH=advanced
    )
    echo.
    echo # ========== 缓存配置 ==========
    echo CACHE_DIR=%CD%/ai_models
) > .env

echo %GREEN%✓ 配置已保存到 .env%RESET%

:launch
echo.
echo %BOLD%%BLUE%═══ 📖 快速开始 %RESET%
echo.
echo   %BOLD%常用命令:%RESET%
echo.
echo   %CYAN%spine ingest ^<pdf 文件^>%RESET%         - 导入 PDF 文档
echo   %CYAN%spine ask "^<问题^>"%RESET%             - 提问 (多文档)
echo   %CYAN%spine ask "^<问题^>" -d ^<文档 ID^>%RESET% - 提问 (单文档)
echo   %CYAN%spine ask "^<问题^>" --online%RESET%    - 提问 (联网搜索)
echo   %CYAN%spine list%RESET%                     - 列出所有文档
echo   %CYAN%spine tree ^<文档 ID^>%RESET%           - 查看文档脊梁
echo   %CYAN%spine git history ^<ChunkID^>%RESET%    - 查看 Git 历史
echo   %CYAN%spine git revert ^<ChunkID^> --to ^<commit^>%RESET% - 回滚
echo.
echo   %BOLD%更多帮助:%RESET%
echo   %CYAN%spine --help%RESET%  查看完整帮助
echo.
echo   %BOLD%示例:%RESET%
echo   %CYAN%spine ingest SM4.pdf%RESET%              - 导入 SM4.pdf
echo   %CYAN%spine ask "SM4 的主要贡献是什么"%RESET%       - 提问
echo   %CYAN%spine ask "SM4 的密钥长度" -d 9b1d1195%RESET% - 单文档提问
echo.
echo.
echo ═══════════════════════════════════════════════════════════════
echo %GREEN%🚀 SpineDoc 已就绪！%RESET%
echo ═══════════════════════════════════════════════════════════════
echo.

:: 检测 spine 命令
where spine >nul 2>&1
if %errorlevel% equ 0 (
    echo 输入 %CYAN%spine --help%RESET% 开始使用
) else (
    echo 提示：使用 %CYAN%python -m spine_cli.main --help%RESET% 查看帮助
)
echo.
