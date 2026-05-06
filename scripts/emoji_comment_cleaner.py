#!/usr/bin/env python3
"""
emoji_comment_cleaner.py - 批量移除代码注释中的表情符号

用法:
    python emoji_comment_cleaner.py --dry-run    # 预览模式
    python emoji_comment_cleaner.py --execute     # 执行模式
    python emoji_comment_cleaner.py --target backend  # 指定目录
"""

import re
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# 装饰性注释表情符号集合
DECORATIVE_EMOJIS = [
    '🏛️', '🏗️', '🚀', '🛰️', '🚑', '🛡️', '🕸️', '🔥', '⚖️', '🎯',
    '📂', '📄', '🕵️', '💾', '📦', '🎭', '🤖', '🛠️', '🔧', '🪛',
    '🏃', '📡', '🔑', '⚙️', '🐦', '💡', '✅', '☑️', '❌', '❎',
    '⚠️', '⚡', '🔴', '🟢', '🟡', '🔵', '🔍', '📝', '🔄', '🎪',
    '🎨', '🎬', '🏆', '🥇', '🥈', '🥉', '🏅', '🎖️', '🎗️', '🎁',
    '🎊', '🎉', '🎈', '🎋', '🎍', '🎎', '🎏', '🎐', '🎑', '👁️',
    '🖐️', '✂️', '🖋️', '❄️', '🖥️', '💻', '🪶', '⭐', '🌟', '✨',
]

# 日志状态表情替换映射
LOG_EMOJI_MAP = {
    '[OK]': '[OK]',
    '[OK]': '[OK]',
    '[ERROR]': '[ERROR]',
    '[FAIL]': '[FAIL]',
    '[WARNING]': '[WARNING]',
    '[WARN]': '[WARN]',
    '[CircuitBreaker]': '[CircuitBreaker]',
}

# 需要跳过的文件模式
SKIP_PATTERNS = [
    '.git',
    'node_modules',
    '__pycache__',
    '.venv',
    'venv',
    '.egg-info',
]

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {'.py', '.go', '.sh', '.yaml', '.yml'}


class EmojiCleaner:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.stats = {
            'files_scanned': 0,
            'files_modified': 0,
            'changes_made': 0,
            'emojis_removed': 0,
        }

    def should_skip_file(self, path: Path) -> bool:
        """检查是否应该跳过该文件"""
        path_str = str(path)
        for pattern in SKIP_PATTERNS:
            if pattern in path_str:
                return True
        return False

    def clean_comment_part(self, comment_text: str) -> Tuple[str, int]:
        """清理注释部分中的表情符号"""
        emoji_count = 0
        for emoji in DECORATIVE_EMOJIS:
            if emoji in comment_text:
                count = comment_text.count(emoji)
                emoji_count += count
                comment_text = comment_text.replace(emoji, '')

        # 版本标注清理 - 移除版本号前的表情符号
        emoji_chars = ''.join(DECORATIVE_EMOJIS)
        comment_text = re.sub(
            rf'(#\s*)[{re.escape(emoji_chars)}]+(\s*\[V\d+(?:\.\d+)*\])',
            r'\1\2',
            comment_text
        )
        comment_text = re.sub(
            rf'(#\s*)[{re.escape(emoji_chars)}]+(\s*VERSION)',
            r'\1\2',
            comment_text
        )

        return comment_text, emoji_count

    def clean_line(self, line: str, file_ext: str) -> Tuple[str, int]:
        """
        清理单行中的表情符号
        返回: (清理后的行, 移除的表情符号数量)
        """
        original = line
        emoji_count = 0

        # Python 行内注释处理
        if file_ext == '.py':
            # 检查是否有行内注释
            in_string = False
            comment_start = -1
            i = 0
            while i < len(line):
                char = line[i]
                if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                    in_string = not in_string
                elif char == '#' and not in_string:
                    comment_start = i
                    break
                i += 1

            if comment_start >= 0:
                # 行内有注释，分段处理
                code_part = line[:comment_start]
                comment_part = line[comment_start:]

                cleaned_comment, count = self.clean_comment_part(comment_part)
                emoji_count += count

                # 处理代码部分中的日志状态表情
                for emoji_text, replacement in LOG_EMOJI_MAP.items():
                    if emoji_text in code_part:
                        code_part = code_part.replace(emoji_text, replacement)
                        emoji_count += 1

                line = code_part + cleaned_comment

            else:
                # 没有注释，只处理代码部分中的日志状态表情
                code_part = line
                for emoji_text, replacement in LOG_EMOJI_MAP.items():
                    if emoji_text in code_part:
                        code_part = code_part.replace(emoji_text, replacement)
                        emoji_count += 1
                line = code_part

        elif file_ext in ('.go', '.sh'):
            # 处理 // 和 # 注释
            in_string = False
            comment_start = -1
            i = 0
            while i < len(line):
                char = line[i]
                if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                    in_string = not in_string
                elif (line[i:i+2] == '//' or line[i] == '#') and not in_string:
                    comment_start = i
                    break
                i += 1

            if comment_start >= 0:
                code_part = line[:comment_start]
                comment_part = line[comment_start:]
                cleaned_comment, count = self.clean_comment_part(comment_part)
                emoji_count += count
                line = code_part + cleaned_comment

        elif file_ext in ('.yaml', '.yml'):
            # YAML 行内注释
            in_string = False
            comment_start = -1
            i = 0
            while i < len(line):
                char = line[i]
                if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                    in_string = not in_string
                elif char == '#' and not in_string:
                    comment_start = i
                    break
                i += 1

            if comment_start >= 0:
                code_part = line[:comment_start]
                comment_part = line[comment_start:]
                cleaned_comment, count = self.clean_comment_part(comment_part)
                emoji_count += count
                line = code_part + cleaned_comment

        return line, emoji_count

    def process_file(self, file_path: Path, dry_run: bool = True) -> Dict:
        """处理单个文件"""
        file_ext = file_path.suffix.lower()

        if file_ext not in SUPPORTED_EXTENSIONS:
            return {'status': 'skipped', 'reason': 'unsupported_ext'}

        if self.should_skip_file(file_path):
            return {'status': 'skipped', 'reason': 'skip_pattern'}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except UnicodeDecodeError:
            return {'status': 'skipped', 'reason': 'encoding_error'}
        except Exception as e:
            return {'status': 'error', 'reason': str(e)}

        self.stats['files_scanned'] += 1

        # 对于 Python 文件，处理 docstring
        if file_ext == '.py':
            new_content, count = self._clean_python_content(original_content)
        else:
            new_content, count = self._clean_generic_content(original_content, file_ext)

        if count > 0:
            self.stats['files_modified'] += 1
            self.stats['changes_made'] += 1  # 按文件计数
            self.stats['emojis_removed'] += count

            if not dry_run:
                # 创建备份
                backup_path = file_path.with_suffix(file_path.suffix + '.emoji.bak')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)

                # 写入新内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                if self.verbose:
                    print(f"  Modified: {file_path} ({count} emojis removed)")

            return {
                'status': 'modified',
                'changes': 1,
                'emojis_removed': count,
                'details': []
            }

        return {'status': 'clean', 'changes': 0, 'emojis_removed': 0}

    def _clean_python_content(self, content: str) -> Tuple[str, int]:
        """清理 Python 文件内容"""
        emoji_count = 0
        new_content = content

        # 1. 清理行内注释中的表情符号
        lines = new_content.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_line, count = self.clean_line(line, '.py')
            emoji_count += count
            cleaned_lines.append(cleaned_line)
        new_content = '\n'.join(cleaned_lines)

        # 2. 清理 docstring 中的表情符号
        # 匹配三引号 docstring
        for emoji in DECORATIVE_EMOJIS:
            if emoji in new_content:
                count = new_content.count(emoji)
                emoji_count += count
                new_content = new_content.replace(emoji, '')

        return new_content, emoji_count

    def _clean_generic_content(self, content: str, file_ext: str) -> Tuple[str, int]:
        """清理通用文件内容"""
        emoji_count = 0
        new_content = content

        lines = new_content.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_line, count = self.clean_line(line, file_ext)
            emoji_count += count
            cleaned_lines.append(cleaned_line)
        new_content = '\n'.join(cleaned_lines)

        return new_content, emoji_count

        return {'status': 'clean', 'changes': 0, 'emojis_removed': 0}

    def process_directory(self, root_path: Path, dry_run: bool = True) -> Dict:
        """处理目录"""
        results = {
            'files': [],
            'summary': {}
        }

        for file_path in sorted(root_path.rglob('*')):
            if file_path.is_file():
                result = self.process_file(file_path, dry_run)
                results['files'].append({
                    'path': str(file_path.relative_to(root_path)),
                    'result': result
                })

        results['summary'] = self.stats.copy()
        return results


def print_results(results: Dict, dry_run: bool):
    """打印结果"""
    mode = "[DRY-RUN]" if dry_run else "[EXECUTE]"
    print(f"\n{'='*60}")
    print(f"emoji_comment_cleaner {mode}")
    print(f"{'='*60}")

    stats = results['summary']
    print(f"\n统计:")
    print(f"  扫描文件: {stats['files_scanned']}")
    print(f"  修改文件: {stats['files_modified']}")
    print(f"  总变更数: {stats['changes_made']}")
    print(f"  删除emoji: {stats['emojis_removed']}")

    if dry_run:
        print(f"\n这是预览模式，未实际修改任何文件。")
        print(f"使用 --execute 参数执行实际修改。")

    # 列出被修改的文件
    modified_files = [f for f in results['files'] if f['result']['status'] == 'modified']
    if modified_files:
        print(f"\n修改的文件列表 (共 {len(modified_files)} 个):")
        for f in modified_files[:20]:  # 只显示前20个
            result = f['result']
            print(f"  - {f['path']}: {result['changes']} changes, {result['emojis_removed']} emojis")

        if len(modified_files) > 20:
            print(f"  ... 还有 {len(modified_files) - 20} 个文件")


def main():
    parser = argparse.ArgumentParser(
        description='批量移除代码注释中的表情符号',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python emoji_comment_cleaner.py --dry-run
  python emoji_comment_cleaner.py --execute
  python emoji_comment_cleaner.py --target backend/app/services
  python emoji_comment_cleaner.py --verbose --execute
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式，不实际修改文件'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='执行模式，实际修改文件'
    )
    parser.add_argument(
        '--target',
        type=str,
        default='.',
        help='目标目录 (默认: 当前目录)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("请指定 --dry-run 或 --execute")
        print("使用 --help 查看帮助")
        sys.exit(1)

    if args.dry_run and args.execute:
        print("不能同时指定 --dry-run 和 --execute")
        sys.exit(1)

    root_path = Path(args.target).resolve()

    if not root_path.exists():
        print(f"错误: 目录不存在: {root_path}")
        sys.exit(1)

    dry_run = args.dry_run

    print(f"处理目录: {root_path}")
    print(f"模式: {'预览' if dry_run else '执行'}")

    cleaner = EmojiCleaner(verbose=args.verbose)
    results = cleaner.process_directory(root_path, dry_run=dry_run)
    print_results(results, dry_run)


if __name__ == '__main__':
    main()
