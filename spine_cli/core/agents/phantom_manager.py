from typing import List, Dict, Any
import sys
from pathlib import Path

# 🚀 [V1.3.1] 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app.services.ocr.visual_sniffer import VisualSaliencySniffer
from backend.app.services.toc.base import SpineNode
from .structure_agent import StructureAgent

class PhantomSpineManager:
    """
    PhantomSpineManager V34.5: 强类型拓荒总控
    职责：视觉重建逻辑，输出标准 SpineNode 脊梁。
    """
    def __init__(self):
        self.sniffer = VisualSaliencySniffer()
        self.agent = StructureAgent()

    async def rebuild_spine(self, pdf_path: str) -> List[SpineNode]:
        print(f"⚠️  未检测到物理目录，启动『幻影脊梁』视觉重建程序...")

        # 1. 物理探测
        candidates = self.sniffer.sniff(pdf_path)
        if not candidates:
            return []

        # 2. 逻辑合成
        virtual_raw = await self.agent.synthesize_toc(candidates)
        
        # 3. 强类型转化
        spine_nodes = []
        for i, it in enumerate(virtual_raw):
            n = SpineNode(
                index=i,
                title=it.get("title", "Untitled"),
                level=int(it.get("level", 1)),
                logical_page=int(it.get("page", 1)),
                confidence=0.7,  # Inferred 默认置信度
                source="phantom"
            )
            spine_nodes.append(n)

        if spine_nodes:
            print(f"✅  幻影脊梁重建成功：生成 {len(spine_nodes)} 个逻辑节点。")

        return spine_nodes
