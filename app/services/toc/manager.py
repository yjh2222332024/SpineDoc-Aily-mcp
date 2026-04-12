from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from .base import SpineNode
from .aligner import LogicAligner
import logging

logger = logging.getLogger(__name__)

class TOCManager:
    """
    🚀 SpineDoc 逻辑脊梁管理器 (V46.5 结构化重构版)
    职责：
    1. 物理/逻辑页码自动校准。
    2. 真·栈式算法构建嵌套脊梁树。
    3. 维护物理区间闭合性 (Physical Interval Closure)。
    """
    
    def process_raw_toc(self, raw_items: List[SpineNode], total_pages: int) -> List[SpineNode]:
        """
        全流程处理：校准 -> 栈式闭合 -> 排序 (强类型契约版)
        职责：接收强类型的 SpineNode 列表，执行物理对齐与区间闭合。
        """
        if not raw_items:
            # 兜底：主内容节点
            return [SpineNode(
                title="Main Content", 
                level=1, 
                logical_page=1, 
                physical_start=1, 
                physical_end=total_pages
            )]

        # 1. 自动计算对齐偏移量
        raw_dicts = [n.model_dump() for n in raw_items]
        offset = LogicAligner.calculate_offset(raw_dicts)
        
        # 2. 注入物理起点并确保索引稳定性
        nodes = []
        for i, n in enumerate(raw_items):
            n.index = i
            n.physical_start = max(1, n.logical_page + offset)
            nodes.append(n)
            
        # 3. 核心栈式算法：确保物理区间绝对闭合 (Interval Closure)
        sorted_nodes = sorted(nodes, key=lambda x: (x.logical_page, x.index))
        stack: List[SpineNode] = []
        
        for current in sorted_nodes:
            while stack and stack[-1].level >= current.level:
                closed = stack.pop()
                closed.physical_end = max(closed.physical_start, current.physical_start - 1)
            
            stack.append(current)
            
        # 4. 收尾：延伸至文档末尾
        while stack:
            remaining = stack.pop()
            remaining.physical_end = total_pages
            
        return sorted_nodes

    def build_tree(self, nodes: List[SpineNode]) -> List[SpineNode]:
        """
        将扁平列表转换为嵌套树形结构 (Spine Tree)
        """
        if not nodes: return []
        
        root_nodes = []
        stack: List[SpineNode] = []
        
        for node in nodes:
            # 清空子节点（以防重用）
            node.children = []
            
            # 寻找父节点
            while stack and stack[-1].level >= node.level:
                stack.pop()
                
            if not stack:
                root_nodes.append(node)
            else:
                stack[-1].children.append(node)
                
            stack.append(node)
            
        return root_nodes

toc_manager = TOCManager()
