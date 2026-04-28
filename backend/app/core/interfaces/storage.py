from typing import Protocol, List, Dict, Any, Optional

class IDocumentStore(Protocol):
    """
    🏗️ Document Persistence Contract
    业务编排器只与此契约对话，不关心数据最后去了哪里。
    """
    async def get_or_create_document(self, filename: str, file_hash: str, total_pages: int, force: bool = False) -> str:
        """创建文档主记录，返回唯一标识符"""
        ...

    async def save_chunks_batch(self, doc_id: str, chunks: List[Dict[str, Any]]):
        """批量保存文档分片"""
        ...

    async def save_toc_items_batch(self, doc_id: str, toc_items: List[Dict[str, Any]]):
        """批量保存目录条目"""
        ...
