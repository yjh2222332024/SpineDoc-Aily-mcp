"""
SpineDoc Prompt 模板管理系统
==========================

提供统一的 Prompt 模板定义、注册、渲染和评估功能。

核心组件:
- PromptTemplate: Prompt 模板数据类
- PromptRegistry: Prompt 注册中心
- PromptSecurityGuard: Prompt 安全检查器
"""

from spine_cli.prompts.templates import (
    PromptTemplate,
    PromptRegistry,
    PromptCategory,
    RAG_ANSWER_PROMPT,
    HMAC_DEBATE_PROMPT,
    TOC_STRUCTURE_PROMPT,
    NAVIGATOR_CARTOGRAPHER_PROMPT,
    NAVIGATOR_EDITOR_PROMPT,
    CHAPTER_SUMMARY_PROMPT,
    KG_ENTITY_LINKING_PROMPT,
)

from spine_cli.prompts.security import PromptSecurityGuard

__all__ = [
    "PromptTemplate",
    "PromptRegistry",
    "PromptCategory",
    "RAG_ANSWER_PROMPT",
    "HMAC_DEBATE_PROMPT",
    "TOC_STRUCTURE_PROMPT",
    "NAVIGATOR_CARTOGRAPHER_PROMPT",
    "NAVIGATOR_EDITOR_PROMPT",
    "CHAPTER_SUMMARY_PROMPT",
    "KG_ENTITY_LINKING_PROMPT",
    "PromptSecurityGuard",
]
