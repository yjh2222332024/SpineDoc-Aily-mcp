import fitz
from typing import List, Dict, Any, Optional, Tuple
import os
import uuid
import asyncio
from .ocr.integration.architect_parser import ArchitectVisualParser
from .toc.manager import toc_manager
from .toc.base import SpineNode
from .toc.aligner import LogicAligner

class HybridParser:
    def __init__(self, mode: str = "auto"):
        self.visual_parser = ArchitectVisualParser(mode=mode)
        self.logic_aligner = LogicAligner()

    async def extract_toc_async(self, file_path: str,
                                 limit_pages: int = 0,
                                 manual_range: Optional[List[int]] = None,
                                 force_ocr: bool = False) -> List[SpineNode]:
        """
         脊梁提取入口 - V46.0 深度耦合版
        职责：根据文档类型分流提取，最终通过 TOCManager 统一逻辑架构。
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF 文件未找到：{file_path}")

        raw_toc = []
        with fitz.open(file_path) as doc:
            total_pages = len(doc)

        # 1.  [分支一] 物理/视觉强制模式 (OCR 优先)
        if manual_range:
            #  只有显式指定目录范围时，才动用昂贵的云端 VLM
            if len(manual_range) == 2:
                actual_range = list(range(manual_range[0], manual_range[1] + 1))
            else:
                actual_range = manual_range

            print(f"📸 [Parser] 目录闭区间 {min(actual_range)}-{max(actual_range)}：启用高精度 VLM...")
            #  [V46.6] 修正：显式调用针对 TOC 优化的接口
            try:
                raw_toc = await self.visual_parser.extract_toc_async(file_path, manual_range=actual_range)
                if raw_toc and len(raw_toc) > 0:
                    print(f" [Parser] VLM 成功识别 {len(raw_toc)} 个目录项")
                else:
                    print(f" [Parser] VLM 返回空结果，后续将进入 Emergent 模式")
                    raw_toc = []
            except Exception as e:
                print(f" [Parser] VLM 不可用：{e}")
                print(f"📚 [Parser] 降级为正文语义涌现模式（Emergent）")
                raw_toc = []

        # 2.  [分支二] 数字原生模式 (Metadata 优先)
        if not raw_toc:
            print(" [Parser] 扫描数字元数据...")
            with fitz.open(file_path) as doc:
                meta_toc = doc.get_toc(simple=True)
                if meta_toc and len(meta_toc) > 3:
                    print(f" [Metadata] 发现 {len(meta_toc)} 个有效目录项")
                    raw_toc = [SpineNode(
                        id=uuid.uuid4(), 
                        level=it[0], 
                        title=it[1].strip(), 
                        logical_page=it[2], 
                        source="metadata"
                    ) for it in meta_toc]

        # 3.  [分支三] 自动判定与最后兜底（字体特征提取已废弃）
        # 无 Outline 时，直接判断是否为扫描件
        is_scanned = True
        with fitz.open(file_path) as doc:
            text_sample = ""
            for i in range(min(5, len(doc))):
                text_sample += doc[i].get_text("text").strip()
                if len(text_sample) > 100:
                    is_scanned = False; break

        if is_scanned:
            print("📸 [Parser] 最终确认：该文档为扫描件，启动全量视觉引擎...")
            raw_toc = await self.visual_parser.rebuild_spine_concurrently(file_path)
        else:
            print("📚 [Parser] 无法提取有效脊梁，作为【无序文本流】处理。")
            raw_toc = [SpineNode(title="[Full Document]", logical_page=1, level=1, source="text_stream")]
        #  [统一耦合点] 使用 TOCManager 进行最后的逻辑对齐与区间闭合
        print(f"🧬 [Parser] 正在通过 TOCManager 进行逻辑脊梁重构 (V46.5)...")
        return toc_manager.process_raw_toc(raw_toc, total_pages)

    def extract_toc(self, file_path: str, limit_pages: int = 0) -> List[SpineNode]:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.extract_toc_async(file_path, limit_pages))

hybrid_parser = HybridParser()
