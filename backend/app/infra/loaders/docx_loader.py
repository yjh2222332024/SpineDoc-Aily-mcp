import docx
from pathlib import Path
from backend.app.core.interfaces.loader import IDocumentLoader

class DocxLoader(IDocumentLoader):
    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith(".docx")

    async def load(self, file_path: str) -> str:
        """将 Word 文档转化为带标题层级的 Markdown"""
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            # 根据 Word 样式自动转 Markdown 标题
            if para.style.name.startswith('Heading 1'):
                full_text.append(f"# {para.text}")
            elif para.style.name.startswith('Heading 2'):
                full_text.append(f"## {para.text}")
            else:
                full_text.append(para.text)
        return "\n\n".join(full_text)
