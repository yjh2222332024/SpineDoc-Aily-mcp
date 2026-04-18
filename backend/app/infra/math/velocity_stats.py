"""
⏱️ LogicalMetabolismStats - 逻辑代谢统计员
==========================================
职责：扫描 Git Ledger (ChunkRevision)，统计各领域的“逻辑半衰期” (τ)。
理论：自适应时间衰减模型。
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.models import ChunkRevision, DocumentGalaxyLink, Chunk

logger = logging.getLogger(__name__)

class LogicalMetabolismStats:
    """
    负责计算不同星系领域的“知识迭代速度”。
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        # 🏛️ 物理常数：默认代谢周期（1年），作为冷启动的基准
        self.DEFAULT_TAU_SECONDS = 365 * 24 * 3600 

    async def get_sector_velocity(self, galaxy_id: str) -> float:
        """
        🚀 核心逻辑：从 Git 历史中统计 tau (τ)
        算法：计算该星系下所有文档修正的平均时间间隔。
        """
        try:
            # 1. 查询该星系关联的所有 Revision 的创建时间
            # 我们需要通过 Chunk 链条追溯到 Galaxy
            from uuid import UUID
            g_uuid = UUID(galaxy_id) if isinstance(galaxy_id, str) else galaxy_id
            
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
                # 冷启动：没有足够的演进数据，使用默认高主权周期
                return self.DEFAULT_TAU_SECONDS

            # 2. 计算平均时间跨度
            intervals = []
            for i in range(1, len(timestamps)):
                diff = (timestamps[i] - timestamps[i-1]).total_seconds()
                if diff > 60: # 物理过滤：忽略 1 分钟内的批量操作噪音
                    intervals.append(diff)

            if not intervals:
                return self.DEFAULT_TAU_SECONDS

            # 3. 统计学产出：这就是该领域的“逻辑代谢率”
            tau = sum(intervals) / len(intervals)
            
            # 🛡️ 边界防御：tau 不能过小（防止过度焦虑）
            # 最快不允许超过 1 天
            return max(tau, 24 * 3600)

        except Exception as e:
            logger.error(f"无法统计星系 {galaxy_id} 的代谢率: {e}")
            return self.DEFAULT_TAU_SECONDS

    def calculate_decay_weight(self, time_diff_seconds: float, tau: float) -> float:
        """
        指数衰减公式实现：W = e^(-Δt / τ)
        """
        import math
        # W 最小不低于 0.1，保留最微弱的逻辑主权
        return max(0.1, math.exp(-time_diff_seconds / tau))
