#!/usr/bin/env python3
"""
🚀 SpineDoc (阅脊) - 一键配置与启动脚本

用法:
    python spine_setup.py          # 交互式配置
    python spine_setup.py --check  # 检查配置状态
    python spine_setup.py --launch # 启动并显示帮助
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

# ============== 颜色输出 ==============
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

def print_banner():
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗
║{Colors.BOLD}  🛡️  SpineDoc (阅脊) - 配置与启动{Colors.CYAN}                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
""")

def print_section(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}═══ {title} {Colors.RESET}")

def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")

def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")

def print_info(msg: str):
    print(f"{Colors.CYAN}ℹ {msg}{Colors.RESET}")

# ============== 依赖安装 ==============
class DependencyInstaller:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.venv_path = project_root / ".venv"
        if sys.platform == "win32":
            self.python_path = self.venv_path / "Scripts" / "python.exe"
            self.pip_path = self.venv_path / "Scripts" / "pip.exe"
        else:
            self.python_path = self.venv_path / "bin" / "python"
            self.pip_path = self.venv_path / "bin" / "pip"

    def check_python_version(self) -> bool:
        if sys.version_info < (3, 10):
            print_error(f"Python 版本过低：{sys.version} (需要 3.10+)")
            return False
        print_success(f"Python 版本：{sys.version.split()[0]}")
        return True

    def create_venv(self) -> bool:
        print_info("创建虚拟环境...")
        result = subprocess.run([sys.executable, "-m", "venv", str(self.venv_path)])
        return result.returncode == 0

    def install_dependencies(self) -> bool:
        print_section("📦 安装依赖")

        # 升级 pip
        subprocess.run([str(self.python_path), "-m", "pip", "install", "--upgrade", "pip"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 安装 requirements.txt
        req_file = self.project_root / "backend" / "requirements.txt"
        if req_file.exists():
            print_info("安装 backend/requirements.txt...")
            subprocess.run([str(self.python_path), "-m", "pip", "install", "-r", str(req_file)])

        # 安装 spine-cli
        print_info("安装 spine-cli...")
        subprocess.run([str(self.python_path), "-m", "pip", "install", "-e", str(self.project_root)],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print_success("依赖安装完成")
        return True

# ============== 配置向导 ==============
class ConfigWizard:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.env_file = project_root / ".env"
        self.config: Dict[str, str] = {}
        self.load_current_config()

    def load_current_config(self):
        if self.env_file.exists():
            with open(self.env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        self.config[key.strip()] = value.strip()

    def check_status(self) -> Dict[str, dict]:
        """检查配置状态，返回每个配置项的状态（必需/可选）"""
        checks = {
            "database": {"name": "数据库配置", "status": "missing", "required": True},
            "llm": {"name": "LLM 配置", "status": "missing", "required": True},
            "embedding": {"name": "向量模型配置", "status": "missing", "required": True},
            "vlm": {"name": "VLM 配置", "status": "missing", "required": True},
            "tavily": {"name": "联网搜索配置 (可选)", "status": "missing", "required": False},
        }

        if self.config.get("DATABASE_URL"):
            checks["database"]["status"] = "configured"
        if self.config.get("LLM_API_KEY") and self.config.get("LLM_BASE_URL"):
            checks["llm"]["status"] = "configured"
        if self.config.get("EMBEDDING_API_KEY") and self.config.get("EMBEDDING_BASE_URL"):
            checks["embedding"]["status"] = "configured"
        if self.config.get("VLM_API_KEY") and self.config.get("VLM_BASE_URL"):
            checks["vlm"]["status"] = "configured"
        if self.config.get("TAVILY_API_KEY"):
            checks["tavily"]["status"] = "configured"

        return checks

    def check_required_config(self) -> tuple:
        """检查必需配置是否完整，返回 (是否完整, 缺失的必需配置列表)"""
        checks = self.check_status()
        missing_required = [
            info["name"] for key, info in checks.items()
            if info["required"] and info["status"] != "configured"
        ]
        return len(missing_required) == 0, missing_required

    def quick_input(self, prompt: str, default: str = None, hide: bool = False, comment: str = None) -> str:
        if default:
            display_prompt = f"{prompt} [默认：{Colors.YELLOW}{default}{Colors.RESET}]"
        else:
            display_prompt = prompt

        if comment:
            print(f"  {Colors.DIM}{comment}{Colors.RESET}")

        if hide:
            # 自定义密码输入，显示 * 号
            import sys
            print(f"{display_prompt}: ", end="", flush=True)
            value = ""
            while True:
                if sys.platform == "win32":
                    import msvcrt
                    char = msvcrt.getwch()
                else:
                    import termios
                    import tty
                    fd = sys.stdin.fileno()
                    old_settings = termios.tcgetattr(fd)
                    try:
                        tty.setraw(fd)
                        char = sys.stdin.read(1)
                    finally:
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

                if char in ('\r', '\n'):  # 回车结束
                    break
                elif char == '\b':  # 退格
                    if value:
                        value = value[:-1]
                        print('\b \b', end='', flush=True)
                elif len(char) == 1 and char.isprintable():
                    value += char
                    print('*', end='', flush=True)
            print()  # 换行
        else:
            value = input(f"{display_prompt} (直接回车使用默认): ")

        return value.strip() if value.strip() else (default or "")

    def select_option(self, prompt: str, options: List[str], default_idx: int = 0) -> int:
        print(f"\n{prompt}")
        for i, opt in enumerate(options):
            marker = "→" if i == default_idx else " "
            print(f"  {Colors.YELLOW}[{i}]{Colors.RESET} {marker} {opt}")

        while True:
            choice = input(f"\n请选择 [{default_idx}]: ").strip()
            if not choice:
                return default_idx
            try:
                idx = int(choice)
                if 0 <= idx < len(options):
                    return idx
                print_error(f"请输入 0-{len(options)-1} 之间的数字")
            except ValueError:
                print_error("请输入有效数字")

    def run_wizard(self) -> bool:
        print_banner()
        print_section("⚡ 配置模式")

        # 首次配置提示 Docker 安装
        if not self.env_file.exists() or not self.config.get("DATABASE_URL"):
            print_info("🐳 首次使用需要先安装 PostgreSQL 数据库")
            print("""
  使用 Docker 一键安装（推荐）:

  {cyan}docker run -d --name spinedoc-postgres \\
    -e POSTGRES_PASSWORD=spinedoc123 \\
    -p 5432:5432 postgres:15{reset}

  或使用 Docker Compose:

  {cyan}docker-compose up -d postgres{reset}

  数据库安装完成后继续配置。
""".format(cyan=Colors.CYAN, reset=Colors.RESET))

        modes = ["快速配置 (推荐)", "交互式配置", "仅检查配置", "退出"]
        mode = self.select_option("请选择配置模式:", modes)

        if mode == 0:
            self.quick_setup()
        elif mode == 1:
            self.interactive_setup()
        elif mode == 2:
            self.show_status()
            return False
        elif mode == 3:
            print_info("已退出")
            return False

        print_section("💾 保存配置")
        self.save_config()

        # 提示下载模型
        print_section("📦 模型下载")
        print_info("""
SpineDoc 需要以下 AI 模型：

  {bold}必需模型:{reset}
  - BAAI/bge-m3 (向量嵌入，~2.2GB)
  - PaddleOCR (中文 OCR，~500MB)

  {bold}可选模型:{reset}
  - GOT-OCR2_0 (通用 OCR，~2GB)
  - KeyBERT (关键词提取，~500MB)

运行以下命令下载模型：
  {cyan}python scripts/download_models.py --required{reset}  - 下载必需模型
  {cyan}python scripts/download_models.py --all{reset}       - 下载所有模型
  {cyan}python scripts/download_models.py --mirror{reset}    - 使用国内镜像加速
""".format(bold=Colors.BOLD, reset=Colors.RESET, cyan=Colors.CYAN))

        return True

    def quick_setup(self):
        print_info("快速配置模式")
        print("""
  LLM:        DeepSeek (deepseek-chat)
  向量模型：   BAAI/bge-m3 (SiliconFlow)
  VLM:       Qwen2.5-VL-72B-Instruct
  数据库：    PostgreSQL (localhost:5432)
""")

        if input("确认使用推荐配置？[Y/n]: ").strip().lower() not in ["", "y", "yes"]:
            print_info("已取消")
            return

        # 数据库
        print_section("🗄️ 数据库配置")
        print("  用于本地 PostgreSQL 存储（Docker 安装）")
        self.config["DATABASE_URL"] = self.quick_input(
            "PostgreSQL 连接字符串",
            "postgresql+asyncpg://spinedoc:spinedoc123@localhost:5432/spinedoc",
            comment="默认值适用于 Docker 安装的 PostgreSQL"
        )

        # DeepSeek
        print_section("🤖 LLM 配置")
        print("  注册地址：https://platform.deepseek.com/")
        self.config["LLM_API_KEY"] = self.quick_input("  DeepSeek API Key", hide=True)
        self.config["LLM_BASE_URL"] = "https://api.deepseek.com/v1"
        self.config["LLM_MODEL_NAME"] = "deepseek-chat"

        # SiliconFlow
        print_section("📐 向量模型 & VLM 配置")
        print("  注册地址：https://cloud.siliconflow.cn/")
        sf_key = self.quick_input("  SiliconFlow API Key", hide=True)
        self.config["EMBEDDING_API_KEY"] = sf_key
        self.config["EMBEDDING_BASE_URL"] = "https://api.siliconflow.cn/v1"
        self.config["EMBEDDING_MODEL_NAME"] = "BAAI/bge-m3"
        self.config["EMBEDDING_DIMENSION"] = "1024"
        self.config["VLM_API_KEY"] = sf_key
        self.config["VLM_BASE_URL"] = "https://api.siliconflow.cn/v1"
        self.config["VLM_MODEL_NAME"] = "Qwen/Qwen2.5-VL-72B-Instruct"

        # Tavily
        print_section("🌐 联网搜索 (可选)")
        tavily_key = self.quick_input("  Tavily API Key (可跳过)", hide=True)
        if tavily_key:
            self.config["TAVILY_API_KEY"] = tavily_key
            self.config["TAVILY_MAX_RESULTS"] = "3"

        # 其他配置
        self.config["CACHE_DIR"] = str(self.project_root / "ai_models")

        # 联邦法庭配置（默认值）
        self.config["COURT_SCOUT_QUERY_LIMIT"] = "5"
        self.config["COURT_CONTEXT_TOC_LIMIT"] = "30"
        self.config["COURT_AUTHORITY_PEER_REVIEW_BONUS"] = "1.15"
        self.config["COURT_AUTHORITY_USER_GENERATED_PENALTY"] = "0.85"
        self.config["COURT_AUTHORITY_CROSS_SOURCE_BONUS"] = "1.20"

        # TOC 验证约束（默认值）
        self.config["TOC_MAX_PAGES_LIMIT"] = "5000"
        self.config["TOC_MAX_DEPTH_LIMIT"] = "8"
        self.config["TOC_MAX_ITEMS_LIMIT"] = "1000"

        # 上下文截断配置（默认值）
        self.config["CONTEXT_LOGIC_TAGS_LIMIT"] = "10"
        self.config["CONTEXT_SELECTED_IDS_LIMIT"] = "5"
        self.config["CONTEXT_FALLBACK_CHUNKS"] = "3"
        self.config["CONTEXT_COMMIT_QUERY_PREFIX"] = "30"
        self.config["CONTEXT_COMMIT_DOC_ID_PREFIX"] = "8"
        self.config["CONTEXT_EVIDENCE_CONTENT_PREFIX"] = "150"
        self.config["CONTEXT_EVIDENCE_REASON_PREFIX"] = "50"
        self.config["CONTEXT_CHUNK_PREVIEW_KEYWORDS"] = "5"
        self.config["CONTEXT_CHUNK_PREVIEW_CONTENT"] = "200"
        self.config["CONTEXT_VECTOR_BATCH_TEXT_PREFIX"] = "1500"

        print_success("快速配置完成!")

    def interactive_setup(self):
        print_info("进入交互式配置")

        # 数据库
        print_section("🗄️ 数据库配置")
        print("  用于本地 PostgreSQL 存储（Docker 安装）")
        self.config["DATABASE_URL"] = self.quick_input(
            "PostgreSQL 连接字符串",
            "postgresql+asyncpg://spinedoc:spinedoc123@localhost:5432/spinedoc",
            comment="默认值适用于 Docker 安装的 PostgreSQL"
        )

        # LLM
        print_section("🤖 LLM 配置")
        # 🏛️ 架构师：所有服务商都兼容 OpenAI API 格式
        providers = ["DeepSeek (推荐)", "OpenAI", "Moonshot (月之暗面)", "硅基流动", "自定义"]
        idx = self.select_option("选择 LLM 提供商:", providers)
        urls = [
            "https://api.deepseek.com/v1",
            "https://api.openai.com/v1",
            "https://api.moonshot.cn/v1",
            "https://api.siliconflow.cn/v1",
            "custom"
        ]
        default_models = ["deepseek-chat", "gpt-4o", "moonshot-v1-128k", "deepseek-ai/DeepSeek-V3", ""]
        self.config["LLM_BASE_URL"] = self.quick_input("  API Base URL", urls[idx])
        self.config["LLM_API_KEY"] = self.quick_input("  API Key", hide=True)
        self.config["LLM_MODEL_NAME"] = self.quick_input("  Model", default_models[idx] if idx < len(default_models) else "")

        # 向量模型
        print_section("📐 向量模型配置")
        self.config["EMBEDDING_BASE_URL"] = self.quick_input("  API Base URL", "https://api.siliconflow.cn/v1")
        self.config["EMBEDDING_API_KEY"] = self.quick_input("  API Key", hide=True)
        self.config["EMBEDDING_MODEL_NAME"] = self.quick_input("  Model", "BAAI/bge-m3")
        self.config["EMBEDDING_DIMENSION"] = "1024"

        # VLM
        print_section("👁️ VLM 配置")
        self.config["VLM_BASE_URL"] = self.quick_input("  API Base URL", "https://api.siliconflow.cn/v1")
        self.config["VLM_API_KEY"] = self.quick_input("  API Key", hide=True)
        self.config["VLM_MODEL_NAME"] = self.quick_input("  Model", "Qwen/Qwen2.5-VL-72B-Instruct")

        # Tavily
        print_section("🌐 联网搜索 (可选)")
        if input("是否配置 Tavily? [Y/n]: ").strip().lower() in ["", "y", "yes"]:
            self.config["TAVILY_API_KEY"] = self.quick_input("  Tavily API Key", hide=True)
            self.config["TAVILY_MAX_RESULTS"] = "3"

        # 其他配置
        self.config["CACHE_DIR"] = str(self.project_root / "ai_models")

        # 联邦法庭配置（默认值）
        self.config["COURT_SCOUT_QUERY_LIMIT"] = "5"
        self.config["COURT_CONTEXT_TOC_LIMIT"] = "30"
        self.config["COURT_AUTHORITY_PEER_REVIEW_BONUS"] = "1.15"
        self.config["COURT_AUTHORITY_USER_GENERATED_PENALTY"] = "0.85"
        self.config["COURT_AUTHORITY_CROSS_SOURCE_BONUS"] = "1.20"

        # TOC 验证约束（默认值）
        self.config["TOC_MAX_PAGES_LIMIT"] = "5000"
        self.config["TOC_MAX_DEPTH_LIMIT"] = "8"
        self.config["TOC_MAX_ITEMS_LIMIT"] = "1000"

        # 上下文截断配置（默认值）
        self.config["CONTEXT_LOGIC_TAGS_LIMIT"] = "10"
        self.config["CONTEXT_SELECTED_IDS_LIMIT"] = "5"
        self.config["CONTEXT_FALLBACK_CHUNKS"] = "3"
        self.config["CONTEXT_COMMIT_QUERY_PREFIX"] = "30"
        self.config["CONTEXT_COMMIT_DOC_ID_PREFIX"] = "8"
        self.config["CONTEXT_EVIDENCE_CONTENT_PREFIX"] = "150"
        self.config["CONTEXT_EVIDENCE_REASON_PREFIX"] = "50"
        self.config["CONTEXT_CHUNK_PREVIEW_KEYWORDS"] = "5"
        self.config["CONTEXT_CHUNK_PREVIEW_CONTENT"] = "200"
        self.config["CONTEXT_VECTOR_BATCH_TEXT_PREFIX"] = "1500"

        print_success("交互式配置完成!")

    def show_status(self):
        print_section("📋 配置检查")
        checks = self.check_status()

        # 统计必需配置和可选配置
        required_checks = {k: v for k, v in checks.items() if v.get("required", True)}
        optional_checks = {k: v for k, v in checks.items() if not v.get("required", True)}

        required_configured = sum(1 for c in required_checks.values() if c["status"] == "configured")
        optional_configured = sum(1 for c in optional_checks.values() if c["status"] == "configured")

        print(f"\n必需配置：{Colors.GREEN}{required_configured}/{len(required_checks)}{Colors.RESET}")
        print(f"可选配置：{Colors.GREEN}{optional_configured}/{len(optional_checks)}{Colors.RESET}\n")

        for info in checks.values():
            icon = "✓" if info["status"] == "configured" else "⚠"
            color = Colors.GREEN if info["status"] == "configured" else Colors.YELLOW
            required_tag = " [必需]" if info.get("required", True) else " [可选]"
            print(f"  {color}{icon} {info['name']}{required_tag}{Colors.RESET}")

    def save_config(self):
        if not self.config:
            print_warning("没有要保存的配置")
            return

        # 备份
        if self.env_file.exists():
            import shutil
            shutil.copy(self.env_file, self.env_file.with_suffix(".env.bak"))
            print_info(f"已备份到 {self.env_file.with_suffix('.env.bak').name}")

        # 写入
        with open(self.env_file, "w", encoding="utf-8") as f:
            f.write(f"# SpineDoc Configuration\n")
            f.write(f"# Generated: {__import__('datetime').datetime.now().isoformat()}\n\n")

            categories = [
                ("DATABASE_URL", "数据库配置"),
                ("LLM_", "LLM 配置"),
                ("EMBEDDING_", "向量模型配置"),
                ("VLM_", "VLM 配置"),
                ("OCR_", "OCR 配置"),
                ("TAVILY_", "联网搜索配置"),
                ("CACHE_DIR", "缓存配置"),
                ("COURT_", "联邦法庭配置"),
                ("TOC_", "TOC 配置"),
                ("CONTEXT_", "上下文配置"),
            ]

            written = set()
            for prefix, comment in categories:
                f.write(f"# ========== {comment} ==========\n")
                for key, value in sorted(self.config.items()):
                    if key.startswith(prefix) and key not in written:
                        f.write(f"{key}={value}\n")
                        written.add(key)
                f.write("\n")

            for key, value in sorted(self.config.items()):
                if key not in written:
                    f.write(f"{key}={value}\n")

        print_success(f"配置已保存到 {self.env_file}")

# ============== 启动器 ==============
class SpineLauncher:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.env_file = project_root / ".env"

    def show_help(self):
        print_section("📖 快速开始")
        print(f"""
  {Colors.BOLD}常用命令:{Colors.RESET}

  {Colors.CYAN}spine ingest <pdf 文件>{Colors.RESET}         - 导入 PDF 文档
  {Colors.CYAN}spine ask "<问题>"{Colors.RESET}             - 提问 (多文档)
  {Colors.CYAN}spine ask "<问题>" -d <文档 ID>{Colors.RESET} - 提问 (单文档)
  {Colors.CYAN}spine ask "<问题>" --online{Colors.RESET}    - 提问 (联网搜索)
  {Colors.CYAN}spine list{Colors.RESET}                     - 列出所有文档
  {Colors.CYAN}spine tree <文档 ID>{Colors.RESET}           - 查看文档脊梁
  {Colors.CYAN}spine git history <ChunkID>{Colors.RESET}    - 查看 Git 历史
  {Colors.CYAN}spine git revert <ChunkID> --to <commit>{Colors.RESET} - 回滚

  {Colors.BOLD}更多帮助:{Colors.RESET}
  {Colors.CYAN}spine --help{Colors.RESET}  查看完整帮助

  {Colors.BOLD}示例:{Colors.RESET}
  {Colors.CYAN}spine ingest SM4.pdf{Colors.RESET}              - 导入 SM4.pdf
  {Colors.CYAN}spine ask "SM4 的主要贡献是什么"{Colors.RESET}       - 提问
  {Colors.CYAN}spine ask "SM4 的密钥长度" -d 9b1d1195{Colors.RESET} - 单文档提问
""")

    def launch(self):
        print_banner()

        # 检查配置
        wizard = ConfigWizard(self.project_root)
        checks = wizard.check_status()

        # 只检查必需配置
        all_required_configured, missing_required = wizard.check_required_config()

        if not all_required_configured:
            print_warning(f"必需配置缺失：{', '.join(missing_required)}")
            print_info(f"运行 {Colors.CYAN}python spine_setup.py --setup{Colors.RESET} 进行配置\n")
            print(f"{Colors.RED}{'=' * 60}")
            print("⚠️  配置不完整，无法启动!")
            print(f"{'=' * 60}{Colors.RESET}\n")
            return

        # 显示配置状态（包括可选配置）
        configured_count = sum(1 for c in checks.values() if c["status"] == "configured")
        total_count = len(checks)
        print_success(f"配置已完整 ({configured_count}/{total_count})")

        self.show_help()
        print(f"\n{Colors.GREEN}{'=' * 60}")
        print("🚀 SpineDoc 已就绪!")
        print(f"{'=' * 60}{Colors.RESET}\n")

# ============== 主入口 ==============
def main():
    project_root = Path(__file__).parent

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        wizard = ConfigWizard(project_root)

        if arg == "--check":
            print_banner()
            wizard.show_status()
        elif arg == "--setup":
            wizard.run_wizard()
        elif arg == "--launch":
            SpineLauncher(project_root).launch()
        elif arg in ["--help", "-h"]:
            print(f"""
{Colors.BOLD}SpineDoc 配置与启动工具{Colors.RESET}

用法:
  {Colors.CYAN}python spine_setup.py{Colors.RESET}          交互式配置
  {Colors.CYAN}python spine_setup.py --check{Colors.RESET}  检查配置
  {Colors.CYAN}python spine_setup.py --setup{Colors.RESET}  运行配置向导
  {Colors.CYAN}python spine_setup.py --launch{Colors.RESET} 启动并显示帮助

配置完成后使用:
  {Colors.CYAN}spine --help{Colors.RESET}  查看 spine-cli 帮助
  {Colors.CYAN}spine ingest <file.pdf>{Colors.RESET}  导入文档
  {Colors.CYAN}spine ask "问题"{Colors.RESET}  提问
""")
        else:
            print_error(f"未知参数：{arg}")
            print("使用 --help 查看帮助")
    else:
        # 无参数：完整设置流程
        print_banner()

        # 检查 Python
        print_section("🐍 Python 检查")
        if sys.version_info < (3, 10):
            print_error(f"Python 版本过低：{sys.version} (需要 3.10+)")
            sys.exit(1)
        print_success(f"Python 版本：{sys.version.split()[0]}")

        # 检查/创建虚拟环境
        installer = DependencyInstaller(project_root)
        venv_path = project_root / ".venv"

        if not venv_path.exists():
            print_section("📦 创建虚拟环境")
            if not installer.create_venv():
                print_error("虚拟环境创建失败")
                sys.exit(1)
            print_success("虚拟环境创建完成")
            installer.python_path = venv_path / "Scripts" / "python.exe" if sys.platform == "win32" else venv_path / "bin" / "python"

        # 检查依赖
        print_section("📦 依赖检查")
        try:
            subprocess.run([str(installer.python_path), "-c", "import sqlmodel, typer, rich"],
                          capture_output=True, check=True)
            print_success("依赖已安装")
        except (subprocess.CalledProcessError, FileNotFoundError):
            installer.install_dependencies()

        # 配置检查
        wizard = ConfigWizard(project_root)
        all_required_configured, missing_required = wizard.check_required_config()
        checks = wizard.check_status()
        configured = sum(1 for c in checks.values() if c["status"] == "configured")

        if not all_required_configured:
            print_warning(f"必需配置缺失：{', '.join(missing_required)}")
            print_info("首次使用必须先配置 API Key\n")
            if not wizard.run_wizard():
                print_info("已退出")
                sys.exit(0)
        else:
            print_success(f"配置已完整 ({configured}/{len(checks)})")

        # 启动
        print_section("🚀 启动")
        SpineLauncher(project_root).launch()

if __name__ == "__main__":
    main()
