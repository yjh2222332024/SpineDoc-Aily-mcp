from typing import List
from backend.app.core.interfaces.loader import IDocumentLoader
from .docx_loader import DocxLoader
from .lark_doc_loader import LarkDocLoader

class UniversalLoader:
    def __init__(self):
        self.loaders: List[IDocumentLoader] = [
            DocxLoader(),
            LarkDocLoader()
            # PDFLoader 将在集成时作为默认兜底或显式加载
        ]

    async def load_to_markdown(self, path_or_url: str) -> str:
        for loader in self.loaders:
            if loader.can_handle(path_or_url):
                return await loader.load(path_or_url)
        
        # 默认处理（假设是 Markdown 或 纯文本）
        with open(path_or_url, "r", encoding="utf-8") as f:
            return f.read()

# 单例
universal_loader = UniversalLoader()
