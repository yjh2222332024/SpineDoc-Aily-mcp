"""
DocumentIngestionService - Responsibility: Handle document loading, hashing, and orchestration.
"""
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from backend.app.services.ocr.body_alchemist import PdfTextExtractor
from backend.app.services.orchestrators.base import IngestContext
from backend.app.infra.loaders.universal_loader import universal_loader
from backend.app.services.orchestrators.pdf_standard import StandardPdfOrchestrator
from backend.app.services.orchestrators.pdf_emergent import EmergentPdfOrchestrator
from backend.app.services.orchestrators.structured_text import StructuredTextOrchestrator

class DocumentIngestionService:
    def __init__(self, alchemist: PdfTextExtractor, store=None):
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        self.alchemist = alchemist
        self.store = store or bitable_ledger

    async def ingest(self,
                    file_path: str,
                    limit_pages: Optional[int] = None,
                    manual_toc_range: Optional[List[int]] = None,
                    manual_offset: Optional[int] = None,
                    force: bool = False,
                    force_ocr: bool = False,
                    force_emergent: bool = False,
                    engine_ref: Any = None
                    ) -> Dict[str, Any]:
        """
        Handle document ingestion from local or cloud sources.
        """
        is_url = file_path.startswith("http")
        
        if is_url:
            print(f"[Ingestion] Detecting cloud document link, capturing content...")
            doc_content_md = await universal_loader.load_to_markdown(file_path)
            file_hash = hashlib.md5(doc_content_md.encode()).hexdigest()
        else:
            p = Path(file_path)
            is_pdf = p.suffix.lower() == ".pdf"
            
            if not is_pdf:
                print(f"[Ingestion] Detecting non-PDF local file, executing generic conversion...")
                doc_content_md = await universal_loader.load_to_markdown(file_path)
                file_hash = hashlib.md5(doc_content_md.encode()).hexdigest()
            else:
                with open(str(p), "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                doc_content_md = None

        ctx = IngestContext(
            force=force, force_ocr=force_ocr,
            limit_pages=limit_pages,
            manual_toc_range=manual_toc_range,
            manual_offset=manual_offset,
            content_md=doc_content_md
        )

        if not is_url and Path(file_path).suffix.lower() == ".pdf":
            if force_emergent:
                orch = EmergentPdfOrchestrator(self.alchemist, self.store)
            else:
                orch = StandardPdfOrchestrator(self.alchemist, self.store)
            return await orch.ingest(file_path, file_hash, engine=engine_ref, ctx=ctx)

        orch = StructuredTextOrchestrator(self.store)
        return await orch.ingest(file_path, file_hash, engine=engine_ref, ctx=ctx)
