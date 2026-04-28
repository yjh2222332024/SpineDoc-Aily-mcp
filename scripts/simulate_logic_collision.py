
import asyncio
import json
import logging
import sys
from pathlib import Path
from uuid import uuid4

# 🏛️ 确保导入路径正确
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.app.infra.lark_cli_reporter import LarkCliReporter
from backend.app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Simulation")

async def simulate_logic_collision():
    """模拟一次逻辑冲突的判决推送"""
    print("🛰️ [Simulation] 启动逻辑冲突演习...")
    
    # 1. 模拟 A-mem 发现的逻辑矛盾
    verdict_data = {
        "id": str(uuid4()),
        "query": "检查合同违约金条款一致性",
        "text": "🔴 **发现逻辑断层**：当前《补充协议》约定的 20% 违约金，与基准知识库中的《主合同》第 4.2 条（10%）存在物理冲突。建议立即通过 Git Diff 查看版本演变。",
        "color": "RED",
        "verdict_metadata": {
            "confidence": 0.95,
            "cited_galaxies": ["合同基准星系", "风险预警星系"],
            "knowledge_delta": {"conflict_point": "penalty_rate"}
        }
    }
    
    # 2. 模拟进化日志
    evolution_logs = {
        "evolution_count": 2,
        "details": [
            {"type": "Contradict", "reason": "违约金比例从 10% 剧增至 20%，未发现调解说明。"},
            {"type": "Support", "reason": "签署主体与主合同保持一致。"}
        ]
    }

    # 3. 触发报告
    reporter = LarkCliReporter(cli_path="bin/lark-cli.exe")
    
    # 获取测试 Chat ID (从设置中读取)
    target_chat = settings.FEISHU_DEFAULT_CHAT_ID or "oc_xxxxxxxxxxxx" # 请确保你的 settings 里配置了测试群
    
    print(f"📡 [Simulation] 正在通过 lark-cli 发送红色判决书到群: {target_chat}...")
    
    # 发送判决卡片
    success = await reporter.report_verdict(verdict_data, target_chat)
    
    if success:
        print("✅ [Simulation] 判决书卡片投递成功！")
        # 同步 Bitable 和发送进化卡片
        await reporter.sync_asset(verdict_data, evolution_logs)
        print("✅ [Simulation] Bitable 资产同步与进化提醒发送成功！")
    else:
        print("❌ [Simulation] 投递失败。请检查 bin/lark-cli.exe 是否已登录并配置了正确的权限。")

if __name__ == "__main__":
    asyncio.run(simulate_logic_collision())
