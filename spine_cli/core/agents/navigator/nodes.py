import re
import asyncio
import json
from collections import defaultdict
from typing import List, Dict, Any
from openai import AsyncOpenAI
from app.core.config import settings
from .state import NavigatorState
from sqlalchemy import select
from app.core.db import get_async_sessionmaker
from backend.app.core.models import Chunk, Document
from uuid import UUID

async def cartographer_node(state: NavigatorState):
    """ Agent A: 联邦逻辑制图师 (V37.0 铁锚版) """
    hop = state.get("hop_count", 0) + 1
    id_to_alias = {d_id: f"DOC_{i+1}" for i, d_id in enumerate(state['doc_ids'])}
    doc_alias_map = {f"DOC_{i+1}": d_id for i, d_id in enumerate(state['doc_ids'])}

    # 1. 智能锚点提取 (优先选择正文深度锚点)
    anchors = []
    seen = set()
    for h in state.get('initial_hits', []):
        d_id = str(h.get('document_id'))
        p = h.get('page_number')
        # 🚀 [Iron Anchor]：除非明确问目录，否则排除 25 页以内的干扰项
        if d_id and p and p > 0 and (d_id, p) not in seen:
            is_toc_zone = p < 25
            if is_toc_zone and any(a['page'] >= 25 for a in anchors):
                continue
            anchors.append({"alias": id_to_alias.get(d_id, "UNK"), "page": p, "is_toc": is_toc_zone})
            seen.add((d_id, p))
            if len(anchors) >= 6: break

    # 2. 启发式推理
    client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
    prompt = f"""你是一个高精度的物理导航专家。
【检索锚点列表】：{json.dumps(anchors)}
用户问题：{state['query']}

任务：
1. 从锚点中选出 3 个最有潜力的物理坐标。
2. ⚠️ 铁锚警告：优先选择 page > 25 的锚点。如果所有锚点都在 25 页以内，说明命中目录，请基于目录页码外推正文开始的物理页（如目录提到第一章在 P10，物理 Offset 为 45，则正文在 P55）。
3. 输出 JSON: {{"coordinates": [{{"alias": "DOC_1", "page": 55, "reason": "Chapter 1 start"}}]}}
"""
    try:
        res = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" },
            temperature=0
        )
        data = json.loads(res.choices[0].message.content)
        final_coords = []
        for c in (data.get("coordinates") or []):
            real_id = doc_alias_map.get(c.get('alias'))
            p = int(c.get('page', 0))
            if real_id and p > 0: final_coords.append({"doc_id": real_id, "page": p})
        
        return {"target_coordinates": final_coords, "hop_count": hop}
    except:
        return {"target_coordinates": [{"doc_id": doc_alias_map[a['alias']], "page": a['page']} for a in anchors[:3]], "hop_count": hop}

async def field_investigator_node(state: NavigatorState):
    """ Agent B: 联邦取证员 (V37.0 物理收割) """
    coords = state.get("target_coordinates", [])
    if not coords: return {"is_complex": False}

    doc_groups = defaultdict(list)
    for c in coords: doc_groups[str(c['doc_id'])].append(int(c['page']))

    from app.services.ocr.body_alchemist import BodyAlchemist
    alchemist = BodyAlchemist(concurrent_limit=4)
    session_maker = get_async_sessionmaker()
    
    current_evidence = state.get("pro_evidence") or []
    seen_keys = {(e['doc_name'], e['page_number']) for e in current_evidence}
    new_evidence = []

    async def process_doc(d_id, pages):
        d_path = state['doc_paths'].get(d_id)
        if not d_path: return []
        async with session_maker() as session:
            # 兼容 UUID 或字符串 ID
            try: d_uuid = UUID(d_id)
            except: d_uuid = d_id
            doc_obj = await session.get(Document, d_uuid)
            fname = doc_obj.filename if doc_obj else "Unknown"
        
        # 扩展抓取范围 (±1页)，形成上下文块
        expanded_pages = set()
        for p in pages:
            expanded_pages.update([p-1, p, p+1])
        
        target_pages = [p for p in expanded_pages if p > 0 and (fname, p) not in seen_keys]
        if not target_pages: return []
        
        # harvest_pages 使用 0-indexed
        results_map = await alchemist.harvest_pages(d_path, target_pages=[p-1 for p in target_pages])
        return [{"content": results_map.get(p-1, ""), "doc_name": fname, "page_number": p, "document_id": d_id} 
                for p in target_pages if len(results_map.get(p-1, "")) > 50]

    all_results = await asyncio.gather(*[process_doc(d_id, pages) for d_id, pages in doc_groups.items()])
    for dr in all_results: new_evidence.extend(dr)
    
    return {"pro_evidence": new_evidence + current_evidence, "is_complex": True}

async def grader_critic_node(state: NavigatorState):
    evidence = state.get("pro_evidence") or []
    # 只要有实质性正文（> 25页）的证据，就视为足够
    if any(e['page_number'] >= 25 for e in evidence): 
        return {"is_sufficient": True}
    return {"is_sufficient": False, "gaps": "仅发现目录线索，缺乏正文细节。"}

async def rewriter_node(state: NavigatorState):
    # 如果进入重写，通常是因为第一跳只抓到了目录，要求 Agent 尝试搜索更高页码
    new_q = f"{state['query']} (请深入文档正文，避开目录页)"
    return {"rewrite_query": new_q}

async def editor_node(state: NavigatorState):
    """ Agent C: 铁锚终审法庭 """
    evidence = state.get("pro_evidence") or []
    if not evidence: return {"final_answer": "未能发现有效物理证据，检索航道可能受阻。"}
    
    # 证据清洗与排序
    evidence.sort(key=lambda x: x['page_number'])
    context = "\n".join([f"【Source: {e['doc_name']} | Physical P{e['page_number']}】\n{e['content']}" for e in evidence[:8]])
    
    client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
    system_msg = """你是一个严谨的学术审稿人。
1. 你的回答必须完全基于提供的【Source】片段。
2. 严禁使用你自身的先验知识来扩充答案。
3. 如果证据中没有提到某个细节，请直接说“证据不足”。
4. 必须在每个关键结论后括号标注 (Pxx)，页码必须与 Source 中的 Physical Pxx 一致。
"""
    try:
        res = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": f"问题: {state['query']}\n\n证据库:\n{context}"}],
            temperature=0.1
        )
        return {"final_answer": res.choices[0].message.content}
    except: return {"final_answer": "合成阶段发生逻辑溃缩。"}
