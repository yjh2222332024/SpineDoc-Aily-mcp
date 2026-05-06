from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from .base import SpineNode
from .aligner import LogicAligner
from .sanitizer import title_sanitizer
import logging

logger = logging.getLogger(__name__)

class TOCManager:
    """
     SpineDoc 逻辑脊梁管理器 (V48.0 并列守护者版)
    职责：
    1. 标题向量化去重 (Vectorized De-duplication)。
    2. 物理/逻辑页码自动校准 (支持用户确权 Offset)。
    3. 注入 [Introductory Material] 等 Level 1 节点，确保 100% 物理覆盖。
    4. 真·栈式算法构建嵌套脊梁树。
    """
    
    def process_raw_toc(self, 
                        raw_items: List[SpineNode], 
                        total_pages: int, 
                        forced_offset: Optional[int] = None,
                        toc_physical_range: Optional[List[int]] = None) -> List[SpineNode]:
        """
         [V48.0] 并列守护者重构版
        职责：通过注入 [Introductory Material] 等 Level 1 节点，确保 100% 物理覆盖，
             同时保持与正文一级标题的并列地位，不产生层级下沉。
        """
        # 0.  [V46.6] 向量化清洗
        clean_items = title_sanitizer.sanitize(raw_items)
        
        # 1.  确定偏移量
        if forced_offset is not None:
            offset = forced_offset
            print(f" [Manager] 应用强制偏移 Offset = {offset}")
        else:
            raw_dicts = [n.model_dump() for n in clean_items]
            offset = LogicAligner.calculate_offset(raw_dicts)
            print(f" [Manager] 自动计算偏移 Offset = {offset}")
        
        # 2. 注入核心正文物理起点
        nodes = []
        for i, n in enumerate(clean_items):
            n.index = i
            n.physical_start = max(1, n.logical_page + offset)
            nodes.append(n)
            
        #  [V48.0] 并列守护者补全逻辑
        guardian_nodes = []
        toc_start = toc_physical_range[0] if (toc_physical_range and len(toc_physical_range) >= 1) else (nodes[0].physical_start if nodes else total_pages)
        toc_end = toc_physical_range[1] if (toc_physical_range and len(toc_physical_range) >= 2) else toc_start
        logic_1_phys = 1 + offset
        
        # A. 合并补全：采用 Level 1 确保与后续章节并列
        if toc_start > 1:
            guardian_nodes.append(SpineNode(
                id=uuid4(), title="[Introductory Material]", level=1, logical_page=0,
                physical_start=1, physical_end=toc_start - 1, source="implicit_guardian"
            ))

        if logic_1_phys > toc_end + 1:
            guardian_nodes.append(SpineNode(
                id=uuid4(), title="[Introductory Material]", level=1, logical_page=0,
                physical_start=toc_end + 1, physical_end=logic_1_phys - 1, 
                source="implicit_guardian"
            ))

        all_nodes = guardian_nodes + nodes
        # 重新排序：物理起点优先
        sorted_nodes = sorted(all_nodes, key=lambda x: (x.physical_start, x.index))

        # 3. 核心栈式算法：确保物理区间绝对闭合
        stack: List[SpineNode] = []
        for current in sorted_nodes:
            while stack and stack[-1].level >= current.level:
                closed = stack.pop()
                #  [V48.8] 只有当 current 在 closed 之后开始时，才划定界限
                # 如果 current 和 closed 同页开始（父子关系），closed 保持 open
                if current.physical_start > closed.physical_start:
                    closed.physical_end = current.physical_start - 1
                else:
                    # 如果同页开始，closed 的终点暂时跟随 current，直到被更高层级闭合
                    closed.physical_end = current.physical_start 
            
            stack.append(current)
            
        # 4. 收尾：延伸至文档末尾
        while stack:
            remaining = stack.pop()
            remaining.physical_end = total_pages
            
        # 重新分配 index 确保有序
        for i, n in enumerate(sorted_nodes):
            n.index = i
            
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
                # 建立父子链接 (DIP)
                stack[-1].children.append(node)
                node.parent_id = stack[-1].id
                
            stack.append(node)
            
        return root_nodes

    def get_leaf_nodes(self, flat_nodes: List[SpineNode]) -> List[SpineNode]:
        """
         [V47.0] 核心逻辑：提取所有叶子节点（真正承载正文的单元）
        """
        # 首先确保树形结构已建立（如果没建立，先跑一遍简单的层级判定）
        self.build_tree(flat_nodes)
        
        # 筛选出没有子节点的节点
        leaves = [n for n in flat_nodes if not n.children]
        
        # 按照物理起始页排序，确保流式收割的单调性
        return sorted(leaves, key=lambda x: (x.physical_start, x.index))

toc_manager = TOCManager()
