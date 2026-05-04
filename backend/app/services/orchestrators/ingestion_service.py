"""
DocumentIngestionService - Thin shim that delegates to SpineEngine.

Kept for backwards compatibility with scripts/ that import it.
All routing logic lives in SpineEngine.ingest_document().
"""
from backend.app.services.spine_engine import SpineEngine


class DocumentIngestionService:
    def __init__(self, alchemist, store=None):
        self.alchemist = alchemist
        self.store = store

    async def ingest(self,
                     file_path: str,
                     limit_pages=None,
                     manual_toc_range=None,
                     manual_offset=None,
                     force=False,
                     force_ocr=False,
                     force_emergent=False,
                     engine_ref=None
                     ):
        engine = engine_ref or SpineEngine(
            alchemist=self.alchemist,
            store=self.store,
        )
        return await engine.ingest_document(
            file_path=file_path,
            limit_pages=limit_pages,
            manual_toc_range=manual_toc_range,
            manual_offset=manual_offset,
            force=force,
            force_ocr=force_ocr,
            force_emergent=force_emergent,
        )
