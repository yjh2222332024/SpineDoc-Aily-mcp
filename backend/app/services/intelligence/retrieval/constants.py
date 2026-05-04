"""
检索系统常量配置
将魔法数字提取为命名常量，提高可维护性
"""
from enum import Enum


# ==================== 检索阈值 ====================

# 向量相似度阈值
SIMILARITY_THRESHOLD = 0.65

# 金字塔回退阈值（当分数低于此值时触发降级）
PYRAMID_FALLBACK_THRESHOLD = 0.35

# 向量相似度门槛
VECTOR_SIMILARITY_THRESHOLD = 0.5

# 直接名称匹配得分
DIRECT_NAME_MATCH_SCORE = 0.6

# 关键词匹配得分
KEYWORD_MATCH_SCORE = 0.5

# 精准采样限制
PRECISION_SAMPLE_LIMIT = 15

# 单文档检索稳定性和置信度
SINGLE_DOC_STABILITY = 0.85
SINGLE_DOC_CONFIDENCE = 0.85


# ==================== 审计辩论 ====================

# 证据归档权重阈值
ARCHIVE_WEIGHT_THRESHOLD = 0.2

# 权重差异判断阈值（无法确定胜负时触发）
UNCERTAINTY_WEIGHT_DIFF = 0.3

# 最低权重门槛
MIN_WEIGHT_THRESHOLD = 0.2

# 默认权重值
DEFAULT_WEIGHT = 0.5

# 补充侦查次数上限
MAX_SUPPLEMENTARY_SEARCHES = 1


# ==================== 状态机阶段（枚举） ====================

class RetrievalPhase(str, Enum):
    """检索流程阶段枚举（替代字符串字面量）"""
    QUERY_DECOMPOSITION = "PLAN"           # 查询分解
    EVIDENCE_GATHERING = "HARVEST"        # 并行取证
    EVIDENCE_VALIDATION = "AUDIT"          # 冲突检测
    VERDICT_SYNTHESIS = "SYNTHESIZE"       # 判决综合
    KNOWLEDGE_BACKFILL = "EVOLVE"         # 知识回填
    FINALIZED = "END"                      # 结束

    # 向后兼容的别名
    PLAN = "PLAN"
    HARVEST = "HARVEST"
    AUDIT = "AUDIT"
    SYNTHESIZE = "SYNTHESIZE"
    EVOLVE = "EVOLVE"
    END = "END"

    @classmethod
    def all_steps(cls) -> list:
        """返回有序的阶段列表"""
        return [cls.PLAN, cls.HARVEST, cls.AUDIT, cls.SYNTHESIZE, cls.EVOLVE]


# ==================== 证据源类型 ====================

class EvidenceSource(str, Enum):
    """证据源类型"""
    LOCAL_GALAXY = "LOCAL_GALAXY"
    INTERNET_WITNESS = "INTERNET_WITNESS"


# ==================== 旧字符串常量（已废弃，使用枚举） ====================

# 兼容旧代码，逐步迁移
LEGACY_PLAN = "PLAN"
LEGACY_HARVEST = "HARVEST"
LEGACY_AUDIT = "AUDIT"
LEGACY_SYNTHESIZE = "SYNTHESIZE"
LEGACY_EVOLVE = "EVOLVE"
LEGACY_END = "END"