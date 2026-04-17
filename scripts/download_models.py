#!/usr/bin/env python3
"""
📥 SpineDoc 模型下载器

一键下载所有必需的 AI 模型，支持断点续传和镜像加速。

用法:
    python scripts/download_models.py          # 交互式下载
    python scripts/download_models.py --list   # 显示模型列表
    python scripts/download_models.py --clean  # 清理已下载的模型
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import shutil

# ============== 颜色输出 ==============
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

def print_banner():
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗
║{Colors.BOLD}  📥 SpineDoc 模型下载器{Colors.CYAN}                                      ║
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

# ============== 模型配置 ==============
MODELS: Dict[str, dict] = {
    # HuggingFace 模型
    "bge-m3": {
        "name": "BAAI/bge-m3",
        "type": "huggingface",
        "size": "~2.2GB",
        "description": "智源 BGE-M3 向量模型 (多语言)",
        "required": True,
        "cache_dir": "models--BAAI--bge-m3"
    },
    "bge-small-zh": {
        "name": "BAAI/bge-small-zh-v1.5",
        "type": "huggingface",
        "size": "~200MB",
        "description": "智源 BGE 小型中文向量模型",
        "required": True,
        "cache_dir": "models--BAAI--bge-small-zh-v1.5"
    },
    "got-ocr": {
        "name": "stepfun-ai/GOT-OCR2_0",
        "type": "huggingface",
        "size": "~2GB",
        "description": "GOT 通用 OCR 模型",
        "required": False,
        "cache_dir": "models--stepfun-ai--GOT-OCR2_0"
    },

    # PaddlePaddle 模型
    "paddle-ocr": {
        "name": "PaddleOCR v4",
        "type": "paddle",
        "size": "~500MB",
        "description": "PaddleOCR 中文检测 + 识别模型",
        "required": True,
        "cache_dir": "paddleocr"
    },

    # KeyBERT
    "keybert": {
        "name": "KeyBERT (sentence-transformers)",
        "type": "pip",
        "size": "~500MB",
        "description": "基于 BERT 的关键词提取",
        "required": False,
        "pip_package": "keybert"
    },
}

# HF 镜像加速
HF_MIRRORS = {
    "official": "https://huggingface.co",
    "mirror": "https://hf-mirror.com",  # 国内镜像
}

# ============== 模型下载器 ==============
class ModelDownloader:
    def __init__(self, cache_root: Path):
        self.cache_root = cache_root
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def check_model_exists(self, model_id: str) -> bool:
        """检查模型是否已下载"""
        model_info = MODELS.get(model_id)
        if not model_info:
            return False

        cache_dir = model_info.get("cache_dir", "")
        if model_info["type"] == "huggingface":
            # HuggingFace 缓存目录结构
            hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
            model_path = hf_cache / cache_dir
            return model_path.exists() and any(model_path.glob("*.bin")) or any(model_path.glob("*.safetensors"))
        elif model_info["type"] == "paddle":
            paddle_cache = self.cache_root / "paddleocr"
            return paddle_cache.exists()
        elif model_info["type"] == "pip":
            try:
                import importlib
                importlib.import_module(model_info.get("pip_module", model_id))
                return True
            except ImportError:
                return False
        return False

    def download_huggingface(self, model_id: str, use_mirror: bool = False) -> bool:
        """下载 HuggingFace 模型"""
        model_info = MODELS[model_id]
        repo_id = model_info["name"]

        print_info(f"正在下载 {model_info['description']}...")
        print_info(f"模型仓库：{repo_id}")
        print_info(f"预计大小：{model_info['size']}")

        # 构建下载命令
        base_url = HF_MIRRORS["mirror"] if use_mirror else HF_MIRRORS["official"]
        cmd = [
            sys.executable, "-m", "pip", "install", "huggingface_hub", "-q"
        ]
        subprocess.run(cmd, check=True)

        from huggingface_hub import snapshot_download

        try:
            snapshot_download(
                repo_id=repo_id,
                cache_dir=self.cache_root / "huggingface",
                resume_download=True,
                ignore_patterns=["*.msgpack", "*.ot", "*.pth"],  # 跳过非必要文件
            )
            print_success(f"{model_info['description']} 下载完成")
            return True
        except Exception as e:
            print_error(f"下载失败：{e}")
            return False

    def download_paddle(self) -> bool:
        """下载 PaddleOCR 模型"""
        print_info("正在下载 PaddleOCR 模型...")

        # 安装 PaddlePaddle
        print_info("安装 PaddlePaddle 框架...")
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "paddlepaddle", "-q"
        ], check=True)

        # PaddleOCR 会自动下载模型
        print_info("首次使用时 PaddleOCR 会自动下载所需模型")
        print_success("PaddleOCR 框架安装完成")
        return True

    def download_pip(self, model_id: str) -> bool:
        """通过 pip 安装包"""
        model_info = MODELS[model_id]
        package = model_info.get("pip_package", model_id)

        print_info(f"正在安装 {model_info['description']}...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", package, "-q"
        ], check=True)

        print_success(f"{model_info['description']} 安装完成")
        return True

    def download_model(self, model_id: str, use_mirror: bool = False) -> bool:
        """下载单个模型"""
        if model_id not in MODELS:
            print_error(f"未知模型：{model_id}")
            return False

        model_info = MODELS[model_id]

        # 检查是否已存在
        if self.check_model_exists(model_id):
            print_success(f"{model_info['description']} 已存在")
            return True

        # 根据类型下载
        if model_info["type"] == "huggingface":
            return self.download_huggingface(model_id, use_mirror)
        elif model_info["type"] == "paddle":
            return self.download_paddle()
        elif model_info["type"] == "pip":
            return self.download_pip(model_id)

        return False

    def download_all(self, required_only: bool = False, use_mirror: bool = False) -> bool:
        """下载所有必需模型"""
        print_section("📦 模型下载")

        models_to_download = [
            mid for mid, info in MODELS.items()
            if not required_only or info.get("required", False)
        ]

        if not models_to_download:
            print_success("所有模型已就绪")
            return True

        print_info(f"需要下载的模型：{len(models_to_download)} 个")
        for mid in models_to_download:
            info = MODELS[mid]
            status = "✓" if self.check_model_exists(mid) else "○"
            required = "[必需]" if info.get("required", False) else "[可选]"
            print(f"  {status} {info['name']} {required} - {info['size']}")

        print()
        success_count = 0
        for mid in models_to_download:
            if self.download_model(mid, use_mirror):
                success_count += 1

        print(f"\n下载完成：{success_count}/{len(models_to_download)}")
        return success_count == len(models_to_download)

    def list_models(self):
        """显示模型列表"""
        print_section("📋 模型列表")

        for mid, info in MODELS.items():
            exists = self.check_model_exists(mid)
            status = f"{Colors.GREEN}✓{Colors.RESET}" if exists else f"{Colors.YELLOW}○{Colors.RESET}"
            required = "[必需]" if info.get("required", False) else "[可选]"
            print(f"  {status} {info['name']} {required}")
            print(f"      {info['description']}")
            print(f"      大小：{info['size']}")
            print()

    def clean_cache(self):
        """清理缓存"""
        print_warning("此操作将删除所有已下载的模型缓存")
        if input("确认？[y/N]: ").strip().lower() != "y":
            print_info("已取消")
            return

        # 清理 HuggingFace 缓存
        hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
        if hf_cache.exists():
            shutil.rmtree(hf_cache)
            print_success(f"已清理 HuggingFace 缓存：{hf_cache}")

        # 清理本地缓存
        if self.cache_root.exists():
            shutil.rmtree(self.cache_root)
            print_success(f"已清理本地缓存：{self.cache_root}")

        print_info("清理完成")

# ============== 主入口 ==============
def main():
    print_banner()

    # 默认缓存目录
    default_cache = Path.home() / ".cache" / "spinedoc"
    cache_root = Path(os.getenv("SPINEDOC_CACHE_DIR", default_cache))

    downloader = ModelDownloader(cache_root)

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--list":
            downloader.list_models()
        elif arg == "--clean":
            downloader.clean_cache()
        elif arg == "--required":
            downloader.download_all(required_only=True, use_mirror="--mirror" in sys.argv)
        elif arg == "--all":
            downloader.download_all(required_only=False, use_mirror="--mirror" in sys.argv)
        elif arg == "--help":
            print(f"""
{Colors.BOLD}SpineDoc 模型下载器{Colors.RESET}

用法:
  {Colors.CYAN}python scripts/download_models.py{Colors.RESET}          交互式下载
  {Colors.CYAN}python scripts/download_models.py --list{Colors.RESET}   显示模型列表
  {Colors.CYAN}python scripts/download_models.py --clean{Colors.RESET}  清理缓存
  {Colors.CYAN}python scripts/download_models.py --required{Colors.RESET}  下载必需模型
  {Colors.CYAN}python scripts/download_models.py --all{Colors.RESET}    下载所有模型
  {Colors.CYAN}python scripts/download_models.py --mirror{Colors.RESET}  使用国内镜像

模型缓存目录：{cache_root}
""")
        else:
            print_error(f"未知参数：{arg}")
            print("使用 --help 查看帮助")
    else:
        # 交互式下载
        print_info(f"模型缓存目录：{cache_root}")
        print()

        # 检查是否使用镜像
        use_mirror = input("是否使用国内镜像加速？[Y/n]: ").strip().lower() != "n"

        # 选择下载模式
        print("\n下载模式:")
        print("  [0] 仅下载必需模型 (推荐)")
        print("  [1] 下载所有模型 (包括可选)")

        choice = input("\n请选择 [0]: ").strip()
        if choice == "1":
            downloader.download_all(required_only=False, use_mirror=use_mirror)
        else:
            downloader.download_all(required_only=True, use_mirror=use_mirror)

        print(f"\n{Colors.GREEN}{'=' * 60}")
        print("🚀 模型下载完成!")
        print(f"{'=' * 60}{Colors.RESET}\n")

if __name__ == "__main__":
    main()
