"""
Harvest Subagents - Concurrent Evidence Gathering
=================================================
Three independent subagents for parallel evidence harvesting:
1. A-MEM memory queries
2. Local galaxy retrieval (SovereignSentry)
3. Online web search (WitnessExpert)
"""
import asyncio
import logging
from uuid import uuid4
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .schema import EvidenceSchema
from ..local_retriever import LocalRetriever
from ..experts.online_retriever import OnlineRetriever
from backend.app.core.interfaces import IAgenticMemory

logger = logging.getLogger(__name__)


@dataclass
class HarvestSubagentResult:
    """Typed result from a single harvest subagent."""
    source: str  # "A_MEMORY" | "LOCAL_GALAXY" | "INTERNET_WITNESS"
    evidence: List[Dict] = field(default_factory=list)
    error: Optional[Exception] = None
    duration_s: float = 0.0


async def harvest_memory_subagent(
    memory: IAgenticMemory,
    missions: List[str],
    limit_per_mission: int = 3,
) -> HarvestSubagentResult:
    """Subagent 1: Query A-MEM memory for each mission."""
    import time
    start = time.time()

    if not memory or not missions:
        return HarvestSubagentResult(source="A_MEMORY")

    evidence = []
    try:
        mem_coros = [memory.query_memory(m, limit=limit_per_mission) for m in missions]
        mem_results_list = await asyncio.gather(*mem_coros, return_exceptions=True)

        for mem_results in mem_results_list:
            if isinstance(mem_results, Exception):
                logger.warning(f" [MemorySubagent] 查询异常: {mem_results}")
                continue
            for r in (mem_results or []):
                normalized = {
                    "id": r.get("id", str(uuid4())),
                    "content": r.get("content", ""),
                    "claims": r.get("logic_tags") or r.get("claims", []),
                    "origin": "A-MEMORY",
                    "confidence": r.get("confidence", 0.75),
                    "color": "BLUE",
                    "stability": 0.9,
                    "doc_id": r.get("document_id"),
                }
                try:
                    valid_e = EvidenceSchema(**normalized)
                    evidence.append(valid_e.dict())
                except Exception as ve:
                    logger.warning(f" [MemorySubagent] 校验失败: {ve}")
    except Exception as e:
        logger.error(f" [MemorySubagent] 收割故障: {e}")
        return HarvestSubagentResult(source="A_MEMORY", error=e)

    return HarvestSubagentResult(
        source="A_MEMORY",
        evidence=evidence,
        duration_s=round(time.time() - start, 2),
    )


async def harvest_local_subagent(
    sentry: LocalRetriever,
    missions: List[str],
    doc_id: str = "all",
    pre_located_galaxies: Optional[List[str]] = None,
) -> HarvestSubagentResult:
    """Subagent 2: Local galaxy retrieval via SovereignSentry."""
    import time
    start = time.time()

    evidence = []
    try:
        tasks = []
        for m in missions:
            if doc_id != "all":
                tasks.append(sentry.route_query_by_document(doc_id, m, limit=5))
            else:
                tasks.append(sentry.route_query(m, limit=5, pre_located_galaxies=pre_located_galaxies))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, list):
                for e in res:
                    try:
                        valid_e = EvidenceSchema(**e)
                        evidence.append(valid_e.dict())
                    except Exception as ve:
                        logger.warning(f" [LocalSubagent] 校验失败: {ve}")
            elif isinstance(res, Exception):
                logger.error(f" [LocalSubagent] 取证失败: {res}")
    except Exception as e:
        logger.error(f" [LocalSubagent] 收割故障: {e}")
        return HarvestSubagentResult(source="LOCAL_GALAXY", error=e)

    return HarvestSubagentResult(
        source="LOCAL_GALAXY",
        evidence=evidence,
        duration_s=round(time.time() - start, 2),
    )


async def harvest_online_subagent(
    witness: OnlineRetriever,
    missions: List[str],
) -> HarvestSubagentResult:
    """Subagent 3: Online web search via WitnessExpert."""
    import time
    start = time.time()

    evidence = []
    try:
        tasks = [witness.retrieve([m]) for m in missions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, dict):
                chunks = res.get("evidence_chunks", [])
                for e in chunks:
                    e["origin"] = "INTERNET_WITNESS"
                    e["is_sovereign"] = False
                    try:
                        valid_e = EvidenceSchema(**e)
                        evidence.append(valid_e.dict())
                    except Exception as ve:
                        logger.warning(f" [OnlineSubagent] 校验失败: {ve}")
            elif isinstance(res, Exception):
                logger.error(f" [OnlineSubagent] 联网取证失败: {res}")
    except Exception as e:
        logger.error(f" [OnlineSubagent] 收割故障: {e}")
        return HarvestSubagentResult(source="INTERNET_WITNESS", error=e)

    return HarvestSubagentResult(
        source="INTERNET_WITNESS",
        evidence=evidence,
        duration_s=round(time.time() - start, 2),
    )
