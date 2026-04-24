"""
🧪 [V53.5] Git Dream Sandbox (梦境沙盒)
=====================================
职责：
为系统的逻辑推演提供隔离的 Git 环境。

设计哲学：
- 隔离性 (Isolation)：梦境中的逻辑不应污染主分支。
- 原子性 (Atomicity)：要么全部合并，要么全部回滚。
- 依据：Andrej Karpathy (2025) Compiled Knowledge Bases。
"""

import logging
from uuid import uuid4
from contextlib import contextmanager
from backend.app.services.knowledge.git_manager import GitManager, get_git_manager

logger = logging.getLogger(__name__)

class DreamSandbox:
    """
    梦境沙盒：封装 Git 分支隔离逻辑。
    """
    
    def __init__(self, manager: GitManager = None):
        self.manager = manager or get_git_manager()
        self.original_branch = "main" # 默认假设为主分支
        self.temp_branch = f"dream/{uuid4().hex[:8]}"

    def _git(self, *args):
        """执行 git 命令并检查错误"""
        return self.manager._git(*args)

    def enter(self):
        """开启沙盒：创建并切换到临时分支"""
        # 1. 记录当前分支
        self.original_branch = self._git("rev-parse", "--abbrev-ref", "HEAD")
        
        # 2. 创建临时分支
        logger.info(f"🚧 [Sandbox] 正在开启隔离区: {self.temp_branch}")
        self._git("checkout", "-b", self.temp_branch)
        return self

    def exit(self, success: bool):
        """关闭沙盒：合并或销毁"""
        if success:
            logger.info(f"✅ [Sandbox] 审计通过，正在合并梦境分支: {self.temp_branch}")
            # 切换回原分支并合并
            self._git("checkout", self.original_branch)
            self._git("merge", self.temp_branch)
        else:
            logger.info(f"🗑️ [Sandbox] 审计失败或逻辑平平，正在销毁隔离区: {self.temp_branch}")
            self._git("checkout", self.original_branch)
            self._git("branch", "-D", self.temp_branch)

@contextmanager
def dream_sandbox(manager: GitManager = None):
    """
    使用 Python contextmanager 语法的整洁封装。
    用法：
        with dream_sandbox() as sandbox:
            # 在这里进行逻辑推演和 Git Commit
            ...
            if logic_is_valid:
                sandbox_success = True
    """
    sandbox = DreamSandbox(manager)
    sandbox.enter()
    success = False
    try:
        # yield 返回给调用者，外部需要设置一个 success 标志
        # 这里我们使用一个简单的闭包或对象属性来传递结果
        yield sandbox
        # 默认情况下，如果代码块没抛异常且逻辑自洽，则认为成功
        # 但实际应用中，我们需要外部显式确认
    except Exception as e:
        logger.error(f"🚨 [Sandbox] 梦境发生崩溃: {e}")
        success = False
        raise e
    finally:
        # 注意：这里需要外部逻辑来通过某种方式告知 success 状态
        # 为了简洁，我们让调用者在 sandbox 对象上设置属性
        pass

# 修正：为了更符合 Uncle Bob 的整洁风格，我们定义一个显式的 commit 方法
class MetabolicSandbox(DreamSandbox):
    def __init__(self, manager: GitManager = None):
        super().__init__(manager)
        self.is_finalized = False
        self.success_state = False

    def finalize(self, success: bool):
        self.success_state = success
        self.is_finalized = True

@contextmanager
def metabolic_sandbox(manager: GitManager = None):
    sandbox = MetabolicSandbox(manager)
    sandbox.enter()
    try:
        yield sandbox
    finally:
        # 强制要求外部调用者显式 finalize，否则默认回滚（防御性编程）
        sandbox.exit(sandbox.success_state)
