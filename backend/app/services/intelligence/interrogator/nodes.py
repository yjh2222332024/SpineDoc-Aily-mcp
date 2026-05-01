"""
SpineDoc Interrogator Nodes (Intelligence Layer)
=================================================
Core node logic for single-document interrogation flow.
"""

import json
import logging
import asyncio
from typing import List, Dict, Any
from openai import AsyncOpenAI
from backend.app.core.config import settings
from .state import InterrogatorState

logger = logging.getLogger(__name__)

async def decomposer_node(state: InterrogatorState):
    """
    Node 1: Query Decomposer
    Responsibility: Decompose the main query into precise sub-probes.
    """
    client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

    prompt = f"""你是一个顶级的问题拆解专家。你的任务是将一个复杂问题拆解为 3 个具体的子探测任务。

【主问题】：{state['query']}

要求：
1. 子任务必须是具体的、可检索的短句。
2. 子任务之间应保持逻辑互补，覆盖所有相关角落。
3. 根据问题类型，推荐需要检索的证据分片数量：
   - 入门教程/怎么做 (How-to)：推荐 8-12 个
   - 原理分析/为什么 (Why)：推荐 5-8 个
   - 事实查询/是什么 (What)：推荐 3-5 个
4. 严格输出 JSON 对象格式：{{"sub_queries": ["q1", "q2", "q3"], "recommended_chunks": 8}}
"""

    print(f"[Decomposer] 正在拆解意图：{state['query'][:settings.CONTEXT_COMMIT_QUERY_PREFIX]}...")

    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        data = json.loads(response.choices[0].message.content)
        sub_queries = data.get("sub_queries", [state['query']])
        recommended_chunks = data.get("recommended_chunks", 5)

        print(f"  ↳ 任务拆解完成：{sub_queries}")
        print(f"  ↳ 推荐证据数量：{recommended_chunks} 个")
        return {"sub_queries": sub_queries, "recommended_chunks": recommended_chunks}
    except Exception as e:
        logger.error(f"Decomposer 节点异常：{e}")
        return {"sub_queries": [state['query']], "recommended_chunks": 5}

async def harvester_node(state: InterrogatorState):
    """
    Node 2: Evidence Harvester
    Responsibility: Parallel harvest from Bitable for each sub-query.
    """
    from backend.app.services.rag.aily_harvester import aily_harvester
    from backend.app.services.feishu.bitable_ledger import bitable_ledger

    print(f"[Harvester] 启动云端物理收割，覆盖 {len(state['sub_queries'])} 个探测任务...")

    if not state.get('toc') or len(state['toc']) == 0:
        print(f"  ↳ 正在从 Bitable 加载文档 TOC...")
        try:
            items = await bitable_ledger.search_chunks(query="", doc_record_id=state['doc_id'], limit=100)
            tocs = []
            seen_titles = set()
            for it in items:
                title = it.get("breadcrumb")
                if title and title not in seen_titles:
                    tocs.append({"title": title, "page": it.get("page_number", 0), "level": 1})
                    seen_titles.add(title)
            state['toc'] = tocs
            print(f"  ↳ TOC 加载完成：{len(state['toc'])} 个章节")
        except Exception as e:
            print(f"⚠️ [Harvester] 加载云端 TOC 失败: {e}")
            state['toc'] = []

    tasks = [aily_harvester.harvest(q, doc_record_id=state['doc_id'], limit=10) for q in state['sub_queries']]
    results_list = await asyncio.gather(*tasks)

    fingerprint_pool = []
    seen_ids = set()

    for results in results_list:
        for res in results:
            if res['id'] not in seen_ids:
                fingerprint_pool.append({
                    "id": str(res['id']),
                    "p": res.get('page_number', 0),
                    "path": res.get('breadcrumb', 'Unknown'),
                    "tags": res.get('logic_tags', [])[:settings.CONTEXT_LOGIC_TAGS_LIMIT]
                })
                seen_ids.add(res['id'])

    print(f"  ↳ 收割完成：指纹库沉淀 {len(fingerprint_pool)} 个候选分片。")
    return {"fingerprint_pool": fingerprint_pool}

async def selector_node(state: InterrogatorState):
    """
    Node 3: Evidence Selector
    Responsibility: Cross-reference TOC, fingerprint pool, and query to select top evidence chunks.
    """
    client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

    recommended_chunks = state.get('recommended_chunks', 5)

    prompt = f"""你是一个严谨的证据筛选专家。你需要通过审视指纹库和逻辑树，选出最能回答问题的证据分片。

【目标文档逻辑树 (TOC)】:
{json.dumps(state['toc'][:settings.COURT_CONTEXT_TOC_LIMIT], ensure_ascii=False)}

【待选证据指纹库】:
{json.dumps(state['fingerprint_pool'], ensure_ascii=False)}

【原始问题】:
{state['query']}

你的任务：
1. 交叉比对问题、TOC 路径与指纹关键词。
2. 剔除"语义漂移"项（如：出现在参考文献或无关章节的分片）。
3. 根据问题类型选择合适的证据数量（简单事实 3-5 个，教程类 8-12 个），最多不超过 {recommended_chunks} 个。
4. 严格输出 JSON 数组格式：{{"selected_ids": ["uuid1", "uuid2"]}}
"""

    print(f"[Selector] 正在对 {len(state['fingerprint_pool'])} 个指纹进行筛选...")

    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        data = json.loads(response.choices[0].message.content)
        selected_ids = data.get("selected_ids", [])[:recommended_chunks]

        if not selected_ids and state['fingerprint_pool']:
            print(f"  ↳ LLM 未选出证据，使用 RRF 兜底：取前 {recommended_chunks} 个分片")
            sorted_pool = sorted(state['fingerprint_pool'], key=lambda x: x.get('rrf_score', 0), reverse=True)
            selected_ids = [f["id"] for f in sorted_pool[:recommended_chunks]]

        print(f"  ↳ 筛选完毕：锁定 {len(selected_ids)} 个核心证据 ID。")
        return {"selected_ids": selected_ids}
    except Exception as e:
        logger.error(f"Selector 节点异常：{e}")
        return {"selected_ids": [f["id"] for f in state['fingerprint_pool'][:recommended_chunks]]}

async def synthesizer_node(state: InterrogatorState):
    """
    Node 4: Answer Synthesizer
    Responsibility: Synthesize selected evidence into a coherent answer.
    """
    from backend.app.services.feishu.bitable_ledger import bitable_ledger
    from backend.app.services.intelligence.retrieval.answer_builder import AnswerBuilder

    print(f"[Synthesizer] 正在从 Bitable 整合证据并撰写答案...")

    pro_evidence = []

    for c_id in state['selected_ids']:
        hit = next((f for f in state['fingerprint_pool'] if f['id'] == c_id), None)
        if hit:
            chunks = await bitable_ledger.search_chunks(query="", doc_record_id=state['doc_id'], limit=100)
            res = next((c for c in chunks if c['id'] == c_id), None)
            if res:
                pro_evidence.append({
                    "id": res['id'],
                    "content": res['content'],
                    "page": res['page_number'],
                    "path": res['breadcrumb']
                })

    builder = AnswerBuilder()

    fake_result = {
        "reasoning": "单文档模式，无冲突检测。基于 TOC 逻辑树与证据指纹库，Selector 已锁定最具代表性的证据分片。"
    }

    source_result = [{
        "source_name": "单文档检索",
        "evidence_chunks": [
            {"page_number": e["page"], "breadcrumb": e["path"], "content": e["content"]}
            for e in pro_evidence
        ]
    }]

    try:
        answer = await builder.build_answer(
            query=state['query'],
            final_result=fake_result,
            source_results=source_result,
            temperature=0.6
        )

        return {
            "final_answer": answer,
            "pro_evidence": pro_evidence,
            "citation_ids": state['selected_ids'],
            "is_sufficient": "未找到相关信息" not in answer
        }
    except Exception as e:
        logger.error(f"Synthesizer 节点异常：{e}")
        return {"final_answer": "答案合成阶段发生异常。"}
