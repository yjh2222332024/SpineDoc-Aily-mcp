from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

class SpineNode(BaseModel):
    """
    🚀 SpineDoc 统一脊梁节点契约
    职责：消除全系统字段歧义，确保物理与语义坐标统一。
    """
    id: UUID = Field(default_factory=uuid4)
    parent_id: Optional[UUID] = None # 🏛️ 顶级架构师：必须显式定义字段
    index: int = 0             # 原始提取顺序
    title: str
    level: int
    logical_page: int          # 书本上印的页码
    physical_start: int = 0    # 对齐后的起始物理页
    physical_end: int = 0      # 对齐后的结束物理页
    confidence: float = 1.0
    source: str = "ocr"        # ocr, vlm, metadata
    
    # 树形结构
    children: List["SpineNode"] = []
    
    class Config:
        arbitrary_types_allowed = True

class TOCStrategy:
    """TOC 提取策略基类"""
    async def extract(self, file_path: str, **kwargs) -> List[SpineNode]:
        raise NotImplementedError
