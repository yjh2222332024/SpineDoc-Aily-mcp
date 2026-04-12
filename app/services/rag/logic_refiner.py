"""
SpineDoc 逻辑精炼引擎 (V43.4 三级跳兜底版)
========================================
职责：承接分块，利用 SLM 和 Embedding 进行语义增强。
     实现 [GPU -> RAM -> Pure Logic] 三级跳优雅降级。
"""
import os
import json
import logging
import asyncio
import jieba.analyse
import numpy as np
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from .embedding import embedding_service
from backend.app.infra.gpu_orchestrator import gpu_orchestrator

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class LogicRefiner:
    def __init__(self, stop_words_path: Optional[str] = None, api_key: Optional[str] = None):
        # 🚀 [V43.5] 统一配置中心：从 settings 读取推理地址
        self.slm_url = settings.SLM_API_URL
        self.slm_model = settings.SLM_MODEL_NAME
        self.client = AsyncOpenAI(api_key=api_key or settings.LLM_API_KEY or "none", base_url=self.slm_url)
        
        self.stop_words = {"普通", "高等教育", "规划", "教材", "项目", "方面", "内容", "介绍", "但是", "具有", "重要", "规划教材"}
        if stop_words_path and os.path.exists(stop_words_path):
            try:
                with open(stop_words_path, "r", encoding="utf-8") as f:
                    self.stop_words.update({line.strip() for line in f if line.strip()})
            except Exception as e:
                logger.error(f"📂 加载停用词库失败: {e}")

    async def _extract_spine_terms(self, toc_items: List[SpineNode]) -> set:
        """用 SLM 批量从目录标题提取领域术语 (SpineNode 强契约版)"""
        if not toc_items: return set()
        
        # 🚀 绝对契约：直接从 SpineNode 对象提取
        titles = [n.title for n in toc_items[:30]]
        
        prompt = f"你是一个文档结构分析专家。提取领域术语。返回 JSON 数组格式：[\"术语 1\", ...]\n目录：{json.dumps(titles, ensure_ascii=False)}"
        
        try:
            async def _call():
                res = await self.client.chat.completions.create(
                    model=self.slm_model, messages=[{"role": "user", "content": prompt}],
                    temperature=0.1, response_format={"type": "json_object"}, timeout=15.0
                )
                return json.loads(res.choices[0].message.content)
            
            data = await gpu_orchestrator.execute("SLM_SpineTerms", _call)
            
            if isinstance(data, list):
                terms = data
            elif isinstance(data, dict):
                terms = next((v for v in data.values() if isinstance(v, list)), [])
            else:
                terms = []
                
            return {str(t).strip() for t in terms if len(str(t).strip()) >= 2 and str(t).strip() not in self.stop_words}
        except:
            return set()

    async def refine_batch(self, doc_title: str, toc_items: List[SpineNode], segments: List[Dict[str, Any]], batch_size: int = 1) -> List[Dict[str, Any]]:
        """🚀 串行精炼模式 (SpineNode 强契约版)"""
        spine_terms = await self._extract_spine_terms(toc_items)
        system_prompt = f"任务：提取 5个硬核实体(entities)、逻辑角色(role)和总结(summary)。仅返回标准 JSON。"

        refined_results = []
        for seg in segments:
            # 串行执行，确保 GPUOrchestrator 的 Semaphore(1) 生效
            texts = [seg['content'][:800]]
            try:
                embeddings = await embedding_service.get_embeddings(texts)
                emb = embeddings[0]
            except:
                emb = [0.0]*768

            info = await self._slm_analyze(system_prompt, seg['content'], seg.get('breadcrumb', ''))

            # 注入逻辑
            seg['embedding'] = emb
            seg['logic_tags'] = await self._merge_and_filter(seg['content'], emb, info.get('entities', []) if info else [], spine_terms)
            seg['metadata_json'].update({
                "logic_role": info.get('role', 'unknown') if info else "unknown",
                "summary": info.get('summary', '') if info else "",
                "slm_refined": True if info and not info.get("is_fallback") else False
            })
            refined_results.append(seg)

            # 🚀 [V45.1] 强制喘息：给显存回收留出宝贵的一秒
            await asyncio.sleep(1.0)

        return refined_results


    async def _slm_analyze(self, system_prompt: str, content: str, breadcrumb: str) -> Optional[Dict]:
        """🚀 三级跳降级核心：GPU -> SLM -> Pure Logic"""
        try:
            return await gpu_orchestrator.execute("SLM_Distill", self._call_slm_raw, system_prompt, content, breadcrumb)
        except Exception as e:
            logger.error(f"🚨 [Distiller] SLM 崩溃: {e}. 退守纯逻辑提取 (jieba)")
            return self._fallback_analyze(content)

    async def _call_slm_raw(self, system_prompt: str, content: str, breadcrumb: str) -> Optional[Dict]:
        # 🚀 [V44.5] 绝对契约：强制限制长度，自动定位边界
        prompt = f"{system_prompt}\n\nContext: {breadcrumb}\nText: {content[:500]}\n\nRespond ONLY with JSON object {{...}}"

        res = await self.client.chat.completions.create(
            model=self.slm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0, 
            max_tokens=300, # 🚀 强力限制长度，防止模型长篇大论
            timeout=20.0
        )
        raw_text = res.choices[0].message.content.strip()

        # 🚀 [V44.5] 边界定位：在垃圾堆中寻找 JSON
        start = raw_text.find('{')
        end = raw_text.rfind('}')
        if start == -1 or end == -1:
            logger.error(f"🚨 [Distiller] 无法识别 JSON 边界: {raw_text[:200]}")
            raise ValueError("No JSON found")

        clean_text = raw_text[start:end+1]
        return json.loads(clean_text)


    def _fallback_analyze(self, content: str) -> Dict:
        """[Level 3] 纯物理分词兜底逻辑"""
        tags = jieba.analyse.extract_tags(content, topK=5)
        return {"entities": tags, "role": "data_fragment", "summary": content[:150] + "...", "is_fallback": True}

    async def _merge_and_filter(self, text: str, chunk_vec: List[float], slm_entities: List[Any], spine_terms: set) -> List[str]:
        # 类型清洗
        clean_entities = []
        for e in slm_entities:
            if isinstance(e, dict): clean_entities.append(str(e.get("entity") or e.get("name") or e))
            else: clean_entities.append(str(e))

        candidates = list(set(jieba.analyse.extract_tags(text, topK=20) + clean_entities))
        candidates = [c for c in candidates if c not in self.stop_words and len(c) > 1]
        if not candidates: return clean_entities[:5]
        
        try:
            cand_embs = await embedding_service.get_embeddings(candidates)
            chunk_vec = np.array(chunk_vec)
            scored = []
            for i, word in enumerate(candidates):
                word_vec = np.array(cand_embs[i])
                sim = np.dot(chunk_vec, word_vec) / (np.linalg.norm(chunk_vec) * np.linalg.norm(word_vec) + 1e-9)
                score = float(sim)
                if word in spine_terms: score *= 5.0
                scored.append((word, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [w for w, s in scored if s > 0.25 or w in spine_terms][:10]
        except:
            return clean_entities[:10] if clean_entities else candidates[:5]
