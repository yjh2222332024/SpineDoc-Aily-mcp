"""
SpineDoc 证人节点集合 (Intelligence Layer / Witness Nodes)
=========================================================
职责：实现单文档质证流的核心节点逻辑。
"""

import json
import logging
import asyncio
from typing import List, Dict, Any
from openai import AsyncOpenAI
from backend.app.core.config import settings
from .state import WitnessState

logger = logging.getLogger(__name__)

async def scout_node(state: WitnessState):
    """
    🕵️ Node 1: 侦察员 (The Scout)
    职责：执行意图拆解，将主问题转化为 3 个精准的子探测任务。
    """
    client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
    
    prompt = f"""你是一个顶级的法医审计侦察员。你的任务是将一个复杂的审计问题拆解为 3 个具体的子任务。
    
    【主问题】：{state['query']}
    
    要求：
    1. 子任务必须是具体的、可检索的短句（例如：“番茄炒蛋的原材料”而不是“准备工作”）。
    2. 子任务之间应保持逻辑互补，力求覆盖该文档中所有可能相关的角落。
    3. 如果主问题已经非常具体，可以提供相关的侧面印证任务。
    4. 严格输出 JSON 对象格式：{{"sub_queries": ["q1", "q2", "q3"]}}
    """
    
    print(f"🕵️ [Scout] 正在拆解意图: {state['query'][:30]}...")
    
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        data = json.loads(response.choices[0].message.content)
        sub_queries = data.get("sub_queries", [state['query']])
        
        print(f"  ↳ 任务拆解完成: {sub_queries}")
        return {"sub_queries": sub_queries}
    except Exception as e:
        logger.error(f"Scout 节点崩溃: {e}")
        return {"sub_queries": [state['query']]}

async def witness_collector_node(state: WitnessState):
    """
    📡 Node 2: 采集员 (The Witness Collector)
    职责：纯代码逻辑。针对子问题并行调用金字塔检索器，搜集指纹。
    """
    from backend.app.services.rag.pyramid_harvester import PyramidHarvester
    from backend.app.services.rag.vector_store import PostgresStore
    
    print(f"📡 [Witness] 启动物理收割，覆盖 {len(state['sub_queries'])} 个探测任务...")
    
    store = PostgresStore()
    harvester = PyramidHarvester(store)
    
    # 并行执行子任务收割
    tasks = [harvester.harvest(q, doc_id=state['doc_id'], limit=10) for q in state['sub_queries']]
    results_list = await asyncio.gather(*tasks)
    
    # 指纹池化与去重 (仅保留 ID, Path, Tags, Page)
    fingerprint_pool = []
    seen_ids = set()
    
    for results in results_list:
        for res in results:
            if res['id'] not in seen_ids:
                fingerprint_pool.append({
                    "id": str(res['id']),
                    "p": res['page_number'],
                    "path": res['breadcrumb'],
                    "tags": res['logic_tags'][:10]
                })
                seen_ids.add(res['id'])
                
    print(f"  ↳ 收割完成：指纹库沉淀 {len(fingerprint_pool)} 个嫌疑分片。")
    return {"fingerprint_pool": fingerprint_pool}

async def examiner_node(state: WitnessState):
    """
    ⚖️ Node 3: 质证员 (The Examiner)
    职责：基于 TOC 逻辑树、指纹库与原始问题，执行逻辑重排序。
    目标：剔除向量漂移点，锁定 3-5 个最具“事实主权”的证据 ID。
    """
    client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
    
    # 构造极简质证上下文
    prompt = f"""你是一个严谨的法医审计质证员。你需要通过审视【指纹库】和【逻辑脊梁】，选出最能回答问题的证据分片。
    
    【目标文档逻辑脊梁 (TOC)】:
    {json.dumps(state['toc'][:50], ensure_ascii=False)} 
    
    【待选证据指纹库】:
    {json.dumps(state['fingerprint_pool'], ensure_ascii=False)}
    
    【原始审计问题】:
    {state['query']}
    
    你的任务：
    1. 交叉比对问题、TOC 路径与指纹关键词。
    2. 剔除那些“语义漂移”项（如：出现在参考文献或无关章节的分片）。
    3. 选出 3-5 个最具代表性的 Chunk ID。
    4. 严格输出 JSON 数组格式：{{"selected_ids": ["uuid1", "uuid2"]}}
    """
    
    print(f"⚖️ [Examiner] 正在对 {len(state['fingerprint_pool'])} 个指纹进行逻辑质证...")
    
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        data = json.loads(response.choices[0].message.content)
        selected_ids = data.get("selected_ids", [])[:5]
        
        print(f"  ↳ 质证完毕：锁定 {len(selected_ids)} 个核心证据 ID。")
        return {"selected_ids": selected_ids}
    except Exception as e:
        logger.error(f"Examiner 节点崩溃: {e}")
        # 兜底：取指纹池前 3 个
        return {"selected_ids": [f["id"] for f in state['fingerprint_pool'][:3]]}

async def integrator_node(state: WitnessState):
    """
    👨‍⚖️ Node 4: 记录员/审判长 (The Integrator)
    职责：根据选定的 ID 读回全文，产出 100% 忠于原文的单文档证词。
    """
    from backend.app.core.db import get_async_sessionmaker
    from backend.app.core.models import Chunk
    from sqlmodel import select
    from uuid import UUID
    
    print(f"👨‍⚖️ [Integrator] 正在读取原文并撰写证词...")
    
    session_maker = get_async_sessionmaker()
    pro_evidence = []
    
    async with session_maker() as session:
        for c_id in state['selected_ids']:
            # 兼容处理
            stmt = select(Chunk).where(Chunk.id == UUID(c_id))
            res = (await session.execute(stmt)).scalar_one_or_none()
            if res:
                pro_evidence.append({
                    "id": str(res.id),
                    "content": res.content,
                    "page": res.page_number,
                    "path": res.breadcrumb
                })

    # 构造最终合成 Prompt
    context = "\n---\n".join([f"[Source: P{e['page']} | {e['path']}]\n{e['content']}" for e in pro_evidence])
    
    client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
    system_msg = """你是一个诚实的单文档证人。
    1. 你的回答必须完全基于提供的【Source】片段。
    2. 严禁使用任何外部先验知识。
    3. 如果证据不足以回答，请直说“本文件未提供相关信息”。
    4. 在回答的关键句后，必须标注 (Pxx)。
    """
    
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"问题: {state['query']}\n\n上下文:\n{context}"}
            ],
            temperature=0.1
        )
        answer = response.choices[0].message.content
        return {
            "final_answer": answer,
            "pro_evidence": pro_evidence,
            "citation_ids": state['selected_ids'],
            "is_sufficient": "本文件未提供相关信息" not in answer
        }
    except Exception as e:
        logger.error(f"Integrator 节点崩溃: {e}")
        return {"final_answer": "证词合成阶段发生逻辑溃缩。"}
