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
    职责：执行意图拆解，将主问题转化为 3 个精准的子探测任务，并推荐需要的证据数量。
    """
    client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

    prompt = f"""你是一个顶级的法医审计侦察员。你的任务是将一个复杂的审计问题拆解为 3 个具体的子探测任务。

    【主问题】：{state['query']}

    要求：
    1. 子任务必须是具体的、可检索的短句。
    2. 子任务之间应保持逻辑互补，力求覆盖所有可能相关的角落。
    3. 根据问题类型，推荐需要检索的证据分片数量：
       - 入门教程/怎么做 (How-to)：推荐 8-12 个
       - 原理分析/为什么 (Why)：推荐 5-8 个
       - 事实查询/是什么 (What)：推荐 3-5 个
    4. 严格输出 JSON 对象格式：{{"sub_queries": ["q1", "q2", "q3"], "recommended_chunks": 8}}
    """

    print(f"🕵️ [Scout] 正在拆解意图：{state['query'][:settings.CONTEXT_COMMIT_QUERY_PREFIX]}...")

    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        data = json.loads(response.choices[0].message.content)
        sub_queries = data.get("sub_queries", [state['query']])
        recommended_chunks = data.get("recommended_chunks", 5)  # 默认 5 个

        print(f"  ↳ 任务拆解完成：{sub_queries}")
        print(f"  ↳ 推荐证据数量：{recommended_chunks} 个")
        return {"sub_queries": sub_queries, "recommended_chunks": recommended_chunks}
    except Exception as e:
        logger.error(f"Scout 节点崩溃：{e}")
        return {"sub_queries": [state['query']], "recommended_chunks": 5}

async def witness_collector_node(state: WitnessState):
    """
    📡 Node 2: 采集员 (The Witness Collector)
    职责：纯代码逻辑。针对子问题并行调用金字塔检索器，搜集指纹。
    """
    from backend.app.services.rag.pyramid_harvester import PyramidHarvester
    from backend.app.services.rag.vector_store import PostgresStore
    from backend.app.core.db import get_async_sessionmaker
    from backend.app.core.models import TocItem
    from sqlmodel import select

    print(f"📡 [Witness] 启动物理收割，覆盖 {len(state['sub_queries'])} 个探测任务...")

    # 🚀 加载 TOC（如果还没有加载）
    if not state.get('toc') or len(state['toc']) == 0:
        print(f"  ↳ 正在加载文档 TOC...")
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = select(TocItem).where(TocItem.document_id == state['doc_id']).order_by(TocItem.page)
            result = await session.execute(stmt)
            toc_items = result.scalars().all()
            state['toc'] = [{"title": t.title, "page": t.page, "level": t.level, "physical_start": t.physical_start} for t in toc_items]
        print(f"  ↳ TOC 加载完成：{len(state['toc'])} 个章节")

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
                    "tags": res['logic_tags'][:settings.CONTEXT_LOGIC_TAGS_LIMIT]
                })
                seen_ids.add(res['id'])

    print(f"  ↳ 收割完成：指纹库沉淀 {len(fingerprint_pool)} 个嫌疑分片。")
    return {"fingerprint_pool": fingerprint_pool}

async def examiner_node(state: WitnessState):
    """
    ⚖️ Node 3: 质证员 (The Examiner)
    职责：基于 TOC 逻辑树、指纹库与原始问题，执行逻辑重排序。
    动态：根据 Scout 推荐的数量，选择证据分片。
    """
    client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

    # 🚀 [V51.0] 动态证据数量：从 Scout 的推荐读取，默认 5 个
    recommended_chunks = state.get('recommended_chunks', 5)

    # 构造极简质证上下文
    prompt = f"""你是一个严谨的法医审计质证员。你需要通过审视【指纹库】和【逻辑脊梁】，选出最能回答问题的证据分片。

    【目标文档逻辑脊梁 (TOC)】:
    {json.dumps(state['toc'][:settings.COURT_CONTEXT_TOC_LIMIT], ensure_ascii=False)}

    【待选证据指纹库】:
    {json.dumps(state['fingerprint_pool'], ensure_ascii=False)}

    【原始审计问题】:
    {state['query']}

    你的任务：
    1. 交叉比对问题、TOC 路径与指纹关键词。
    2. 剔除那些"语义漂移"项（如：出现在参考文献或无关章节的分片）。
    3. 根据问题类型选择合适的证据数量（简单事实 3-5 个，教程类 8-12 个），最多不超过 {recommended_chunks} 个。
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
        selected_ids = data.get("selected_ids", [])[:recommended_chunks]

        # 🚀 兜底逻辑：如果 LLM 没有选出证据，取指纹池 RRF 分数最高的前 recommended_chunks 个
        if not selected_ids and state['fingerprint_pool']:
            print(f"  ↳ LLM 未选出证据，使用 RRF 兜底：取前 {recommended_chunks} 个分片")
            sorted_pool = sorted(state['fingerprint_pool'], key=lambda x: x.get('rrf_score', 0), reverse=True)
            selected_ids = [f["id"] for f in sorted_pool[:recommended_chunks]]

        print(f"  ↳ 质证完毕：锁定 {len(selected_ids)} 个核心证据 ID。")
        return {"selected_ids": selected_ids}
    except Exception as e:
        logger.error(f"Examiner 节点崩溃：{e}")
        # 兜底：取指纹池前 recommended_chunks 个
        return {"selected_ids": [f["id"] for f in state['fingerprint_pool'][:recommended_chunks]]}

async def integrator_node(state: WitnessState):
    """
    👨‍⚖️ Node 4: 记录员/外交官 (The Integrator/Synthesizer)
    职责：根据选定的证据，创造性整合成一份连贯的学习指南。
    """
    from backend.app.core.db import get_async_sessionmaker
    from backend.app.core.models import Chunk
    from sqlmodel import select
    from uuid import UUID
    from backend.app.services.intelligence.court.synthesizer import Synthesizer

    print(f"👨‍⚖️ [Integrator] 正在整合证据并撰写答案...")

    session_maker = get_async_sessionmaker()
    pro_evidence = []

    async with session_maker() as session:
        for c_id in state['selected_ids']:
            stmt = select(Chunk).where(Chunk.id == UUID(c_id))
            res = (await session.execute(stmt)).scalar_one_or_none()
            if res:
                pro_evidence.append({
                    "id": str(res.id),
                    "content": res.content,
                    "page": res.page_number,
                    "path": res.breadcrumb
                })

    # 🚀 [V51.0] 调用 Synthesizer 进行创造性整合
    synthesizer = Synthesizer()

    # 构造简易 verdict 结构（兼容 Synthesizer 接口）
    fake_verdict = {
        "reasoning": "单文档模式，无冲突检测。基于 TOC 逻辑脊梁与证据指纹库，Examiner 已锁定最具代表性的证据分片。"
    }

    # 构造证据包结构（兼容 Synthesizer 接口）
    evidence_package = [{
        "source": "单文档检索",
        "evidence": [
            {"p": e["page"], "path": e["path"], "content": e["content"]}
            for e in pro_evidence
        ]
    }]

    try:
        answer = await synthesizer.weave_answer(
            query=state['query'],
            verdict=fake_verdict,
            evidence_packages=evidence_package,
            temperature=0.6  # 🚀 [V51.0] 抽象问题需要整合能力
        )

        return {
            "final_answer": answer,
            "pro_evidence": pro_evidence,
            "citation_ids": state['selected_ids'],
            "is_sufficient": "未找到相关信息" not in answer
        }
    except Exception as e:
        logger.error(f"Integrator 节点崩溃：{e}")
        return {"final_answer": "证词合成阶段发生逻辑溃缩。"}
