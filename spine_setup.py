#!/usr/bin/env python3
"""
SpineDoc (阅脊) - 配置工具

用法:
  python spine_setup.py --check  检查配置状态
  python spine_setup.py --setup  运行配置向导
  python spine_setup.py --help   显示帮助

启动 MCP 服务请使用:
  start_mcp.bat
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List

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
║{Colors.BOLD}  🛡️  SpineDoc (阅脊) - 配置工具{Colors.CYAN}                               ║
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
        checks = {
            "llm": {"name": "LLM 配置", "status": "missing", "required": True},
            "database": {"name": "数据库配置 (可选)", "status": "missing", "required": False},
            "embedding": {"name": "向量模型配置 (可选)", "status": "missing", "required": False},
            "vlm": {"name": "VLM 配置 (可选)", "status": "missing", "required": False},
        }

        if self.config.get("LLM_API_KEY"):
            checks["llm"]["status"] = "configured"
        if self.config.get("DATABASE_URL"):
            checks["database"]["status"] = "configured"
        if self.config.get("EMBEDDING_API_KEY"):
            checks["embedding"]["status"] = "configured"
        if self.config.get("VLM_API_KEY"):
            checks["vlm"]["status"] = "configured"

        return checks

    def check_required_config(self) -> tuple:
        checks = self.check_status()
        missing_required = [
            info["name"] for key, info in checks.items()
            if info.get("required", False) and info["status"] != "configured"
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
            import sys
            print(f"{display_prompt}: ", end="", flush=True)
            value = ""
            while True:
                if sys.platform == "win32":
                    import msvcrt
                    char = msvcrt.getwch()
                else:
                    import termios, tty
                    fd = sys.stdin.fileno()
                    old_settings = termios.tcgetattr(fd)
                    try:
                        tty.setraw(fd)
                        char = sys.stdin.read(1)
                    finally:
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

                if char in ('\r', '\n'):
                    break
                elif char == '\b':
                    if value:
                        value = value[:-1]
                        print('\b \b', end='', flush=True)
                elif len(char) == 1 and char.isprintable():
                    value += char
                    print('*', end='', flush=True)
            print()
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
        return True

    def quick_setup(self):
        print_info("快速配置模式 (仅需 LLM Key)")

        print_section("🤖 LLM 配置")
        self.config["LLM_API_KEY"] = self.quick_input("  LLM API Key", hide=True)
        self.config["LLM_BASE_URL"] = self.quick_input("  API Base URL", "https://api.deepseek.com/v1")
        self.config["LLM_MODEL_NAME"] = self.quick_input("  Model Name", "deepseek-chat")

        if input("是否配置本地数据库 (用于本地审计存储)? [y/N]: ").lower() == 'y':
            self.config["DATABASE_URL"] = self.quick_input(
                "PostgreSQL 连接字符串",
                "postgresql+asyncpg://spinedoc:spinedoc123@localhost:5432/spinedoc"
            )

        if input("是否配置 SiliconFlow (用于向量/VLM能力)? [y/N]: ").lower() == 'y':
            sf_key = self.quick_input("  SiliconFlow API Key", hide=True)
            self.config["EMBEDDING_API_KEY"] = sf_key
            self.config["EMBEDDING_BASE_URL"] = "https://api.siliconflow.cn/v1"
            self.config["EMBEDDING_MODEL_NAME"] = "BAAI/bge-m3"
            self.config["VLM_API_KEY"] = sf_key
            self.config["VLM_BASE_URL"] = "https://api.siliconflow.cn/v1"
            self.config["VLM_MODEL_NAME"] = "Qwen/Qwen2.5-VL-72B-Instruct"

        print_success("快速配置完成!")

    def interactive_setup(self):
        print_info("进入交互式配置")

        print_section("🗄️ 数据库配置")
        self.config["DATABASE_URL"] = self.quick_input(
            "PostgreSQL 连接字符串",
            "postgresql+asyncpg://spinedoc:spinedoc123@localhost:5432/spinedoc",
            comment="默认值适用于 Docker 安装的 PostgreSQL"
        )

        print_section("🤖 LLM 配置")
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

        print_section("📐 向量模型配置")
        self.config["EMBEDDING_BASE_URL"] = self.quick_input("  API Base URL", "https://api.siliconflow.cn/v1")
        self.config["EMBEDDING_API_KEY"] = self.quick_input("  API Key", hide=True)
        self.config["EMBEDDING_MODEL_NAME"] = self.quick_input("  Model", "BAAI/bge-m3")
        self.config["EMBEDDING_DIMENSION"] = "1024"

        print_section("👁️ VLM 配置")
        self.config["VLM_BASE_URL"] = self.quick_input("  API Base URL", "https://api.siliconflow.cn/v1")
        self.config["VLM_API_KEY"] = self.quick_input("  API Key", hide=True)
        self.config["VLM_MODEL_NAME"] = self.quick_input("  Model", "Qwen/Qwen2.5-VL-72B-Instruct")

        print_section("🌐 联网搜索 (可选)")
        if input("是否配置 Tavily? [Y/n]: ").strip().lower() in ["", "y", "yes"]:
            self.config["TAVILY_API_KEY"] = self.quick_input("  Tavily API Key", hide=True)
            self.config["TAVILY_MAX_RESULTS"] = "3"

        self.config["CACHE_DIR"] = str(self.project_root / "ai_models")
        self.config["COURT_SCOUT_QUERY_LIMIT"] = "5"
        self.config["COURT_CONTEXT_TOC_LIMIT"] = "30"
        self.config["COURT_AUTHORITY_PEER_REVIEW_BONUS"] = "1.15"
        self.config["COURT_AUTHORITY_USER_GENERATED_PENALTY"] = "0.85"
        self.config["COURT_AUTHORITY_CROSS_SOURCE_BONUS"] = "1.20"
        self.config["TOC_MAX_PAGES_LIMIT"] = "5000"
        self.config["TOC_MAX_DEPTH_LIMIT"] = "8"
        self.config["TOC_MAX_ITEMS_LIMIT"] = "1000"
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

        if self.env_file.exists():
            import shutil
            shutil.copy(self.env_file, self.env_file.with_suffix(".env.bak"))
            print_info(f"已备份到 {self.env_file.with_suffix('.env.bak').name}")

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
        elif arg in ["--help", "-h"]:
            print(f"""
{Colors.BOLD}SpineDoc 配置工具{Colors.RESET}

用法:
  {Colors.CYAN}python spine_setup.py --check{Colors.RESET}  检查配置状态
  {Colors.CYAN}python spine_setup.py --setup{Colors.RESET}  运行配置向导

启动 MCP 服务:
  {Colors.CYAN}start_mcp.bat{Colors.RESET}                  双击运行或命令行启动

MCP 服务地址 (Aily 后台配置):
  {Colors.CYAN}https://spinedoc.xiangyinben.xyz/sse{Colors.RESET}
""")
        else:
            print(f"{Colors.RED}✗ 未知参数：{arg}{Colors.RESET}")
            print("使用 --help 查看帮助")
    else:
        print_banner()
        print_info("无参数模式已移除，请使用以下命令：")
        print(f"  {Colors.CYAN}python spine_setup.py --check{Colors.RESET}  检查配置")
        print(f"  {Colors.CYAN}python spine_setup.py --setup{Colors.RESET}  配置向导")
        print(f"  {Colors.CYAN}start_mcp.bat{Colors.RESET}            启动 MCP 服务")


if __name__ == "__main__":
    main()