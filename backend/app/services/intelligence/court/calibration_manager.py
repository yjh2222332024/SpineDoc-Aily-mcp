"""
⚖️ CalibrationManager - 置信度自校准经理
=============================================
职责：对比 AI 判决与物理真理，动态修正置信度量化参数。
理论：误差反馈控制 (Error Feedback Control)。
"""

import json
import logging
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.models import CourtVerdict

logger = logging.getLogger(__name__)

class CalibrationManager:
    """
    SpineDoc 的“元认知控制中心”。它负责监控系统的表现，
    并自动修正 backend/storage/confidence_config.json 中的参数。
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        # 物理路径锁定
        self.config_path = Path("backend/storage/confidence_config.json")

    async def optimize_thresholds(self):
        """
        🚀 执行参数优化：从失败中学习，修正魔法数字。
        """
        try:
            # 1. 查询所有判例
            stmt = select(CourtVerdict)
            result = await self.session.execute(stmt)
            verdicts = result.scalars().all()

            # 🚀 物理过滤：从 reasoning_thought 中寻找 ground_truth 标签
            valid_verdicts = []
            for v in verdicts:
                # 兼容 SQLAlchemy 加载 JSONB 为字典或字符串的情况
                thought = v.reasoning_thought or {}
                if isinstance(thought, str):
                    thought = json.loads(thought)

                if thought.get("has_ground_truth") in [True, "true"]:
                    valid_verdicts.append(v)

            if len(valid_verdicts) < 5: 
                return {"status": "skipped", "reason": f"Insufficient samples ({len(valid_verdicts)})"}

            # 2. 误差统计
            overconfidence_count = 0 
            underconfidence_count = 0 
            
            for v in valid_verdicts:
                ai_score = v.confidence_score
                thought = v.reasoning_thought or {}
                if isinstance(thought, str):
                    thought = json.loads(thought)

                truth = thought.get("ground_truth_verdict") # 'SAFE' or 'ATTACK'
                
                if ai_score > 0.7 and truth == 'ATTACK':
                    overconfidence_count += 1
                elif ai_score < 0.3 and truth == 'SAFE':
                    underconfidence_count += 1

            # 3. 动态调整逻辑
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            updated = False
            # 🛡️ 惩罚过度自信 (降低 Belief 上限，抬高 SNR 门槛)
            if overconfidence_count / len(verdicts) > 0.03:
                config["snr_gate"]["min_confidence_threshold"] = round(config["snr_gate"]["min_confidence_threshold"] + 0.02, 3)
                config["sovereignty"]["max_belief_cap"] = round(config["sovereignty"]["max_belief_cap"] - 0.01, 3)
                updated = True
                logger.warning(f"🚨 系统探测到过度自信误差 ({overconfidence_count})，已物理性抬高审判门槛。")

            # 🌟 修正过于保守
            if underconfidence_count / len(verdicts) > 0.1:
                config["snr_gate"]["min_confidence_threshold"] = round(config["snr_gate"]["min_confidence_threshold"] - 0.01, 3)
                updated = True
                logger.info("⚖️ 系统表现过于保守，已自动释放逻辑灵活性。")

            # 4. 持久化
            if updated:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                return {"status": "updated", "overconfident": overconfidence_count, "underconfident": underconfidence_count}

            return {"status": "stable"}

        except Exception as e:
            logger.error(f"校准过程发生故障: {e}")
            return {"status": "error", "message": str(e)}
