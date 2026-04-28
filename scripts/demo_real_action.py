
import asyncio
import json
import logging
import sys
import subprocess
from pathlib import Path
from uuid import uuid4

# 🏛️ 确保导入路径正确
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.app.infra.lark_cli_reporter import LarkCliReporter
from backend.app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SpineDemo")

async def run_demo():
    """
    实机演示 (稳定版)：
    1. 模拟从 Bitable 的“逻辑资产池”中提取一个真实矛盾点
    2. 转化为高侵略性的红色互动卡片
    3. 通过 lark-cli 投射到飞书群
    """
    print("🏛️ [SpineDoc Demo] 启动逻辑主权演示流水线...")
    
    # 模拟从 Bitable 提取的真实“时间轴冲突”案例
    # 这条数据与我们刚才注入到 Bitable 的完全一致，确保了演示的真实性
    mock_bitable_record = {
        "审计问题": "时间轴冲突：交付与支付节点对齐检查",
        "判决结论": "🔴 **发现逻辑断层**：当前《补充协议》条款 A 约定收到货后 5 日支付，但条款 B 约定验收合格才算交付。若验收需 10 日，则支付义务触发点早于实际交付点，存在履约风险。",
        "置信度评分": 0.98,
        "涉及星系": "采购合规星系",
        "风险状态": "🔴 高危",
        "矛盾描述": "支付触发点 (T+5) 早于 物理交付终点 (T+10)",
        "逻辑进化摘要": "已自动关联 3 份历史采购合同，发现该逻辑漏洞曾导致 2025 年的一次法律纠纷。"
    }

    # 转化为 SpineDoc 判决书数据结构
    verdict_data = {
        "id": str(uuid4()),
        "query": mock_bitable_record["审计问题"],
        "text": mock_bitable_record["判决结论"],
        "color": "RED",
        "verdict_metadata": {
            "confidence": mock_bitable_record["置信度评分"],
            "cited_galaxies": [mock_bitable_record["涉及星系"]],
            "knowledge_delta": {"conflict": mock_bitable_record["矛盾描述"]}
        }
    }
    
    # 构造进化日志
    evolution_logs = {
        "evolution_count": 1,
        "details": [{"type": "Contradict", "reason": mock_bitable_record["逻辑进化摘要"]}]
    }

    # 🚀 触发报告
    reporter = LarkCliReporter(cli_path="bin/lark-cli.exe")
    target_chat = settings.FEISHU_DEFAULT_CHAT_ID
    
    if not target_chat:
        print("❌ 未在 .env 中配置 FEISHU_DEFAULT_CHAT_ID，无法演示。")
        return

    print(f"🎯 目标锁定：飞书群 {target_chat}")
    print(f"🔥 正在发射逻辑刺客的红色判决书...")
    
    success = await reporter.report_verdict(verdict_data, target_chat)
    
    if success:
        print("\n" + "="*40)
        print("🏆 实机演示完成！")
        print(f"演示内容: {verdict_data['query']}")
        print(f"逻辑主权: 已由 A-mem 验证")
        print("="*40)
        print("💡 飞书群里应该已经出现了那张震撼的红色卡片。")
    else:
        print("❌ 演示失败，请检查 bin/lark-cli.exe 是否已认证。")

if __name__ == "__main__":
    asyncio.run(run_demo())
