import asyncio
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# Make sure env vars are loaded for LLM_API_KEY
from app.core.config import settings

from spine_cli.core.agents.federation.state import create_initial_state
from spine_cli.core.agents.federation.witness_node import witness_node
from spine_cli.core.agents.federation.moderator_node import moderator_node
from spine_cli.core.agents.federation.cross_examination_node import cross_examination_node
from spine_cli.core.agents.federation.integrator_node import integrator_node

console = Console()

async def test_logic_assassin():
    console.print(Panel("[bold red]🥷 SpineDoc V40.3 - 逻辑刺客 (Logic Assassin) 实验田[/bold red]\n[dim]目标：验证蒙眼取证、冲突嗅探与终审判决全链路。[/dim]"))
    
    # 模拟输入 (创造一个逻辑冲突场景)
    query = "请问 SM4 算法的分组长度是多少？"
    doc_1_context = "【Source: DOC_1 | Physical P102】\n根据早期草案，SM4 算法（原名 SMS4）的分组长度为 64 位，使用 8 个 S 盒进行替换。"
    doc_2_context = "【Source: DOC_2 | Physical P45】\n第四章 SM4算法：SM4 算法是我国自主设计的商用密码标准，它采用 128 位的分组长度，密钥长度也是 128 位。"

    # 1. 初始化状态
    state = create_initial_state(query=query, doc_ids=["DOC_1", "DOC_2"], doc_paths={})
    # 🆕 V40.2: 存入原始 context 以便回溯
    state["witness_contexts"] = {
        "DOC_1": doc_1_context,
        "DOC_2": doc_2_context
    }
    
    # 2. 蒙眼取证 (并发执行)
    console.print("\n[bold yellow]Step 1: 证人蒙眼取证 (Witness Node)[/bold yellow]")
    
    async def run_witness(agent_id, context):
        console.print(f"  [dim]正在唤醒证人 {agent_id}...[/dim]")
        claims = await witness_node(query, context, agent_id)
        return agent_id, claims
        
    results = await asyncio.gather(
        run_witness("DOC_1", doc_1_context),
        run_witness("DOC_2", doc_2_context)
    )
    
    witness_opinions = {}
    for agent_id, claims in results:
        witness_opinions[agent_id] = claims
        console.print(f"\n[green]证人 {agent_id} 提取的原子论点：[/green]")
        for c in claims:
            console.print(f"  - {c.raw_text}")
            
    state["witness_opinions"] = witness_opinions
    
    # 3. 冷酷主理人审查
    console.print("\n[bold yellow]Step 2: 主理人审查与冲突嗅探 (Moderator Node)[/bold yellow]")
    mod_result = await moderator_node(state)
    state.update(mod_result) # 将状态合并回主状态
    
    status = mod_result.get("last_status")
    collisions = mod_result.get("collision_points", [])
    
    if status == "CONFLICT":
        console.print(f"[bold red]🚨 发现 {len(collisions)} 处逻辑冲突！[/bold red]")
        for c in collisions:
            console.print(f"  [red]描述:[/red] {c.get('description', c.get('point'))}")
            console.print(f"  [red]涉事证人:[/red] {', '.join(c.get('involved_witnesses', c.get('witnesses', [])))}")
    else:
        console.print("[bold green]✅ 未发现冲突，证词一致。[/bold green]")
        
    # 4. 交叉盘问 (如果有冲突)
    if status == "CONFLICT":
        console.print("\n[bold yellow]Step 3: 触发交叉盘问 (Cross-Examination Node)[/bold yellow]")
        cross_result = await cross_examination_node(state)
        state["witness_opinions"] = cross_result["witness_opinions"]
        console.print(f"🔄 盘问结果：{cross_result.get('last_status')}")
        
        console.print("\n[green]⚖️ 交叉盘问后的证词更新 (回溯对线结果)：[/green]")
        for agent_id, claims in state["witness_opinions"].items():
            console.print(f"  证人 {agent_id}:")
            for c in claims:
                console.print(f"    - {c.raw_text}")

    # 5. 最终判决
    console.print("\n[bold yellow]Step 4: 最终知识判决 (Integrator Node)[/bold yellow]")
    final_result = await integrator_node(state)
    
    console.print(Panel(final_result.get("final_answer", "判决书合成失败"), title="🏛️ SpineDoc 联邦判决书", border_style="cyan"))

if __name__ == "__main__":
    asyncio.run(test_logic_assassin())
