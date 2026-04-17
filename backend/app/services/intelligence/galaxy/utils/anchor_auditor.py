"""
⚖️ AdvancedAnchorAuditor - 语义锚点高级审计员
=============================================
职责：通过“物理过滤+语义质证”双重关卡，确保星系锚点的纯净度。
架构：Layer 1 (Regex/Blacklist) + Layer 2 (CPU-based Cross-Encoder)
"""

import re
import logging
from typing import List, Optional
from sentence_transformers import CrossEncoder
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class AdvancedAnchorAuditor:
    def __init__(self, use_cross_encoder: bool = True):
        # 🏛️ 硬件纪律：强行指定 CPU，为 4060 留出显存
        self.device = "cpu"
        self.model = None
        
        # 🛡️ Layer 1: 物理黑名单 (包含章节脚手架与网页通用噪音)
        self.blacklist = {
            "introduction", "background", "appendix", "references", "bibliography",
            "results", "analysis", "experimental", "table", "figure", "index",
            "macos", "linux", "windows", "implementation", "details", "summary",
            "overview", "conclusions", "conclusion", "methodology", "methods",
            "next page", "previous page", "log in", "sign up", "contact us",
            "privacy policy", "terms of service", "copyright", "all rights reserved"
        }
        
        if use_cross_encoder:
            try:
                # 🚀 顶配：CPU 优化版 Cross-Encoder
                # 注意：ms-marco-MiniLM 是极轻量且高效的语义相关性判定模型
                model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
                print(f"📡 [Auditor] 正在加载 CPU 级语义审计引擎: {model_name}...")
                self.model = CrossEncoder(model_name, device=self.device)
                print("✅ [Auditor] 语义审计引擎已就绪 (CPU)")
            except Exception as e:
                logger.error(f"无法加载 Cross-Encoder: {e}，将降级为纯物理过滤。")

    def audit_keywords(self, keywords: List[str], context_text: str, top_n: int = 3) -> List[str]:
        """
        双层审计工作流
        """
        if not keywords:
            return []

        # --- Layer 1: 物理过滤 ---
        physically_clean = [
            kw for kw in keywords 
            if self._is_physically_valid(kw)
        ]
        
        if not physically_clean:
            # 如果全军覆没，返回空，让调用者去 Misc 星系
            return []

        # --- Layer 2: 语义质证 (顶配逻辑) ---
        if self.model and context_text:
            # 问 Cross-Encoder：这些词和文档上下文真的相关吗？
            # 我们取上下文的前 1500 字符，通常是 Abstract 或 Introduction
            cleaned_context = context_text[:1500]
            pairs = [[cleaned_context, kw] for kw in physically_clean]
            
            try:
                scores = self.model.predict(pairs)
                
                # 过滤并排序：相关性分数 > 0.1 (ms-marco 负分代表不相关，正分越高越相关)
                # 注意：ms-marco 分数范围通常在 -10 到 10 之间
                scored_kws = sorted(
                    [(kw, score) for kw, score in zip(physically_clean, scores) if score > 0.0],
                    key=lambda x: x[1], reverse=True
                )
                
                if not scored_kws:
                    # 如果语义上都没有通过，返回物理过滤的前 N 个
                    return physically_clean[:top_n]
                
                return [kw for kw, score in scored_kws[:top_n]]
            except Exception as e:
                logger.error(f"Cross-Encoder 预测异常: {e}")
                return physically_clean[:top_n]
        
        # 降级：仅返回物理干净的前 N 个
        return physically_clean[:top_n]

    def _is_physically_valid(self, kw: str) -> bool:
        """物理级“一票否决”逻辑"""
        kw_clean = kw.lower().strip()
        
        # 1. 长度校验 (过于短小的词通常无主权)
        if len(kw_clean) <= 2: return False
        
        # 2. 数字噪音校验 (如 "10", "3.1", "2024")
        if re.match(r'^[\d\.\-\/]+$', kw_clean): return False
        
        # 3. 纯特殊字符
        if not any(c.isalpha() or '\u4e00' <= c <= '\u9fff' for c in kw_clean):
            return False

        # 4. 黑名单校验
        if kw_clean in self.blacklist: return False
        
        return True
