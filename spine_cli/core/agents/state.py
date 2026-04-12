from typing import List, Dict, Any, Optional, TypedDict
from app.schemas.document import DocumentType

class PageInfo(TypedDict):
    page_num: int
    text_content: Optional[str]
    has_text_layer: bool
    ocr_result: Optional[Dict[str, Any]]

class TocItem(TypedDict):
    id: str
    level: int
    title: str
    page: int
    parent_id: Optional[str]
    confidence: float

class DocumentState(TypedDict):
    file_path: str
    document_type: Optional[DocumentType]
    total_pages: int
    pages: List[PageInfo]
    raw_toc: Optional[List[Dict[str, Any]]]
    structured_toc: List[TocItem]
    processing_errors: List[str]
    confidence_score: float
    current_node: Optional[str]
    instructions: List[Dict[str, Any]]
    retry_count: int
    max_retries: int
    manual_toc_range: Optional[List[int]] # 🆕 核心支持
    metadata: Dict[str, Any]
