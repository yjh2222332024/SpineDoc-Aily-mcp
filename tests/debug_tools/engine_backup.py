
import os
import json
import fitz
import asyncio
import re
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.services.parser import hybrid_parser
from app.services.rag.splitter import context_splitter
from app.core.config import settings

from sqlmodel import select
from app.core.db import get_async_sessionmaker
from app.core.models import Document, TocItem, ProcessingStatus
from spine_cli.indexer.postgres_store import PostgresStore
from spine_cli.core.agents.graph import create_spine_graph
from spine_cli.core.kg.adapter import KGAdapter
from spine_cli.core.router import SemanticRouter
from spine_cli.llm.summarizer import SpineSummarizer

class SpineEngine:
    def __init__(self, storage_dir: str = ".spine"):
        self.storage_dir = Path(storage_dir)
        self._ensure_storage()

        self.vector_store = PostgresStore()
        self._session_maker = get_async_sessionmaker()
        self.agent_graph = create_spine_graph()
        self.kg_adapter = KGAdapter(self.storage_dir / "kg_cache")
        self.router = SemanticRouter()
        self.summarizer = SpineSummarizer()

    def _ensure_storage(self):
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def ingest_document(self, file_path: str, progress_callback=None) -> str:
        p = Path(file_path)
        if progress_callback: progress_callback("🚀 正在重建脊梁...")
        initial_state = {"file_path": str(p.absolute()), "structured_toc": [], "metadata": {}, "retry_count": 0, "max_retries": 2}
        final_state = await self.agent_graph.ainvoke(initial_state)
        toc_items = final_state.get("structured_toc", [])
        
        async with self._session_maker() as session:
            db_doc = Document(
                filename=p.name,
                file_path=str(p.absolute()),
                status=ProcessingStatus.COMPLETED,
                total_pages=final_state.get("total_pages", 0)
            )
            session.add(db_doc)
            await session.commit()
            await session.refresh(db_doc)
            doc_id = str(db_doc.id)

        if progress_callback: progress_callback("🧩 正在切片...")
        with fitz.open(file_path) as pdf:
            chunks = context_splitter.split_by_toc(pdf, toc_items)
            
        if self.vector_store.is_available:
            try:
                await self.vector_store.add_documents(doc_id, chunks)
            except: pass
            
        return doc_id

    async def list_documents(self) -> List[Dict]:
        async with self._session_maker() as session:
            stmt = select(Document)
            result = await session.execute(stmt)
            docs = result.scalars().all()
            return [{"id": str(d.id), "filename": d.filename} for d in docs]
