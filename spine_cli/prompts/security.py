"""
SpineDoc Prompt 安全守卫
======================

检测并防御 Prompt Injection 攻击，保护系统安全。

参考 Claw Code 的安全设计，提供:
- 输入检查：检测恶意输入
- 输出检查：防止信息泄露
- 模式匹配：识别常见攻击模式
"""

import re
from typing import Tuple, List
from dataclasses import dataclass


@dataclass
class SecurityCheckResult:
    """安全检查结果"""
    is_safe: bool
    reason: str
    risk_level: str  # "low" | "medium" | "high" | "critical"


class PromptSecurityGuard:
    """
    Prompt 安全检查器
    
    检测类型:
    - Prompt Injection: 试图覆盖系统指令
    - Information Leakage: 试图获取系统 Prompt
    - Role Play Attack: 试图让 AI 扮演其他角色
    - Jailbreak Attempt: 试图绕过安全限制
    """
    
    # 攻击模式库（持续更新）
    INJECTION_PATTERNS = [
        # 忽略指令类
        (r"忽略.*指令", "high", "忽略系统指令"),
        (r"绕过.*限制", "high", "绕过安全限制"),
        (r"忘记.*规则", "medium", "忘记规则"),
        (r"不要遵守.*prompt", "critical", "违反 Prompt"),
        
        # 信息泄露类
        (r"输出.*prompt", "high", "获取系统 Prompt"),
        (r"显示.*系统.*指令", "high", "获取系统指令"),
        (r"你的.*system.*prompt.*是什么", "high", "询问系统 Prompt"),
        (r"重复.*上面的.*内容", "medium", "重复上文"),
        
        # 角色扮演类
        (r"扮演.*[无限制 | 越狱 | 自由]", "critical", "危险角色扮演"),
        (r"假装你是.*没有限制", "critical", "假装无限制"),
        (r"进入.*开发者模式", "critical", "开发者模式"),
        
        # 逻辑覆盖类
        (r"现在.*规则.*改变", "medium", "规则变更"),
        (r"新.*指令.*覆盖", "high", "指令覆盖"),
        (r"以下.*内容.*不受限制", "high", "声明无限制"),
        
        # 编码绕过类
        (r"base64.*解码.*执行", "high", "编码绕过"),
        (r"rot13.*翻译", "medium", "编码绕过"),
        (r"十六进制.*转换", "medium", "编码绕过"),
    ]
    
    # 安全响应模板
    SAFE_RESPONSES = {
        "injection": "我无法执行此请求，这违反了安全策略。",
        "leakage": "我无法分享系统内部信息，请理解。",
        "roleplay": "我只能作为 SpineDoc 助手为您服务。",
        "default": "我无法执行此请求。",
    }
    
    def __init__(self, enabled: bool = True):
        """
        初始化安全检查器
        
        Args:
            enabled: 是否启用检查（调试时可关闭）
        """
        self.enabled = enabled
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """预编译正则表达式（提升性能）"""
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), risk, desc)
            for pattern, risk, desc in self.INJECTION_PATTERNS
        ]
    
    def check_input(self, user_input: str) -> SecurityCheckResult:
        """
        检查用户输入是否安全
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            SecurityCheckResult
        """
        if not self.enabled:
            return SecurityCheckResult(
                is_safe=True,
                reason="检查已禁用",
                risk_level="low"
            )
        
        # 空输入检查
        if not user_input or len(user_input.strip()) == 0:
            return SecurityCheckResult(
                is_safe=False,
                reason="空输入",
                risk_level="low"
            )
        
        # 模式匹配检查
        for pattern, risk, desc in self.compiled_patterns:
            if pattern.search(user_input):
                return SecurityCheckResult(
                    is_safe=False,
                    reason=f"检测到攻击模式：{desc}",
                    risk_level=risk
                )
        
        # 长度检查（防止超长输入）
        if len(user_input) > 10000:
            return SecurityCheckResult(
                is_safe=False,
                reason=f"输入过长 ({len(user_input)} 字符)",
                risk_level="medium"
            )
        
        return SecurityCheckResult(
            is_safe=True,
            reason="通过检查",
            risk_level="low"
        )
    
    def check_output(self, output: str, context: str = "") -> SecurityCheckResult:
        """
        检查 LLM 输出是否安全
        
        Args:
            output: LLM 输出文本
            context: 上下文（可选）
            
        Returns:
            SecurityCheckResult
        """
        if not self.enabled:
            return SecurityCheckResult(
                is_safe=True,
                reason="检查已禁用",
                risk_level="low"
            )
        
        # 检查是否泄露系统 Prompt
        system_keywords = [
            "system prompt", "系统指令", "system instruction",
            "你是 SpineDoc", "你的职责是", "你的角色是",
        ]
        
        for keyword in system_keywords:
            if keyword.lower() in output.lower():
                # 进一步检查是否真的在泄露
                if len(output) < 500:  # 短文本可能是误报
                    continue
                if re.search(rf"{keyword}.*[:：].{{50,}}", output):
                    return SecurityCheckResult(
                        is_safe=False,
                        reason="可能泄露系统信息",
                        risk_level="high"
                    )
        
        return SecurityCheckResult(
            is_safe=True,
            reason="输出检查通过",
            risk_level="low"
        )
    
    def get_safe_response(self, check_result: SecurityCheckResult) -> str:
        """
        根据检查结果获取安全响应
        
        Args:
            check_result: 安全检查结果
            
        Returns:
            安全响应文本
        """
        if "泄露" in check_result.reason or "泄漏" in check_result.reason:
            return self.SAFE_RESPONSES["leakage"]
        elif "扮演" in check_result.reason or "角色" in check_result.reason:
            return self.SAFE_RESPONSES["roleplay"]
        elif "指令" in check_result.reason or "限制" in check_result.reason:
            return self.SAFE_RESPONSES["injection"]
        else:
            return self.SAFE_RESPONSES["default"]
    
    def log_attempt(self, user_input: str, result: SecurityCheckResult) -> None:
        """
        记录安全检查日志（用于审计和分析）
        
        Args:
            user_input: 用户输入
            result: 检查结果
        """
        import logging
        from datetime import datetime
        
        if not result.is_safe:
            logging.warning(
                f"[Security] {datetime.now().isoformat()} | "
                f"Risk: {result.risk_level} | "
                f"Reason: {result.reason} | "
                f"Input: {user_input[:100]}..."
            )
    
    def check_and_raise(self, user_input: str) -> None:
        """
        检查输入，如果不安全则抛出异常
        
        Args:
            user_input: 用户输入
            
        Raises:
            SecurityError: 检测到不安全请求
        """
        result = self.check_input(user_input)
        if not result.is_safe:
            self.log_attempt(user_input, result)
            raise SecurityError(
                message=result.reason,
                risk_level=result.risk_level,
                safe_response=self.get_safe_response(result)
            )


class SecurityError(Exception):
    """安全异常"""
    
    def __init__(
        self,
        message: str,
        risk_level: str = "medium",
        safe_response: str = ""
    ):
        self.message = message
        self.risk_level = risk_level
        self.safe_response = safe_response
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """转换为字典（用于 API 响应）"""
        return {
            "error": "security_violation",
            "message": self.message,
            "risk_level": self.risk_level,
            "safe_response": self.safe_response,
        }


# 全局单例
security_guard = PromptSecurityGuard(enabled=True)


def check_prompt_safety(user_input: str) -> Tuple[bool, str]:
    """
    便捷函数：检查 Prompt 安全性
    
    Args:
        user_input: 用户输入
        
    Returns:
        (是否安全，原因/响应)
    """
    result = security_guard.check_input(user_input)
    if result.is_safe:
        return True, result.reason
    else:
        return False, security_guard.get_safe_response(result)
