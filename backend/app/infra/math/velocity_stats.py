"""
⚠️ DEPRECATED - LogicalMetabolismStats
==========================================
This module is deprecated. Local database persistence has been phased out.
Logical velocity and decay should now be tracked via Git Ledger or cloud history.
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.models import ChunkRevision, DocumentGalaxyLink, Chunk

logger = logging.getLogger(__name__)

class LogicalMetabolismStats:
    “””
    Responsible for calculating knowledge iteration velocity per cluster domain.
    “””

    def __init__(self, session: AsyncSession):
        self.session = session
        self.DEFAULT_TAU_SECONDS = 365 * 24 * 3600

    async def get_sector_velocity(self, cluster_id: str) -> float:
        “””
        Core logic: Calculate tau (τ) from Git history.
        Algorithm: Average time interval of all document revisions within the cluster.
        “””
        try:
            from uuid import UUID
            g_uuid = UUID(cluster_id) if isinstance(cluster_id, str) else cluster_id

            stmt = (
                select(ChunkRevision.created_at)
                .join(Chunk, Chunk.id == ChunkRevision.chunk_id)
                .join(DocumentGalaxyLink, DocumentGalaxyLink.document_id == Chunk.document_id)
                .where(DocumentGalaxyLink.galaxy_id == g_uuid)
                .order_by(ChunkRevision.created_at)
            )
            result = await self.session.execute(stmt)
            timestamps = result.scalars().all()

            if len(timestamps) < 2:
                return self.DEFAULT_TAU_SECONDS

            intervals = []
            for i in range(1, len(timestamps)):
                diff = (timestamps[i] - timestamps[i-1]).total_seconds()
                if diff > 60:
                    intervals.append(diff)

            if not intervals:
                return self.DEFAULT_TAU_SECONDS

            tau = sum(intervals) / len(intervals)
            return max(tau, 24 * 3600)

        except Exception as e:
            logger.error(f”Failed to calculate velocity for cluster {cluster_id}: {e}”)
            return self.DEFAULT_TAU_SECONDS

    def calculate_decay_weight(self, time_diff_seconds: float, tau: float) -> float:
        """
        指数衰减公式实现：W = e^(-Δt / τ)
        """
        import math
        # W 最小不低于 0.1，保留最微弱的逻辑主权
        return max(0.1, math.exp(-time_diff_seconds / tau))
