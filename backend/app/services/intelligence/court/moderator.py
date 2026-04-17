"""
👨‍⚖️ Moderator - 联邦法庭大法官 (v2.0 证据分片裁决版)
=====================================================
职责：基于证据分片检测冲突，裁决矛盾，生成最终判决书。
不再比较证词，而是直接在证据分片层面进行冲突分析和裁决。

🚀 [V51.2] 移除向量过滤：Distributor 已完成相关性筛选，Moderator 专注冲突检测
"""

import json
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from backend.app.core.config import settings


class Moderator:
    """
    👨‍⚖️ 大法官 (The Chief Justice)

    职责：
    1. 在证据分片层面检测逻辑冲突
    2. 对冲突进行裁决
    3. 基于裁决结果生成最终判决书
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL
        )

    async def adjudicate(self, evidence_packages: List[Dict], query: str) -> Dict[str, Any]:
        """
        对所有证据包进行裁决，生成最终判决书

        Args:
            evidence_packages: 证据包列表 [
                {
                    "doc_id": "...",
                    "galaxy_id": "...",
                    "galaxy_name": "...",
                    "evidence_chunks": [{"id": "...", "content": "...", "page_number": ..., "breadcrumb": "...", "logic_tags": [...]}],
                    "scout_queries": [...]
                }
            ]
            query: 原始查询

        Returns:
            verdict: 判决书 {
                "final_answer": str,
                "confidence": float,
                "cited_galaxies": List[str],
                "cited_chunks": List[Dict],
                "conflicts_resolved": List[Dict],
                "reasoning": str
            }
        """
        print(f"👨‍⚖️ [Moderator] 开始裁决，共 {len(evidence_packages)} 份证据包...")

        # 1. 检测证据分片之间的冲突（同时返回过滤后的证据包）
        conflicts, valid_packages = await self._detect_conflicts(evidence_packages, query)

        # 使用过滤后的证据包进行后续步骤
        evidence_packages = valid_packages if valid_packages else evidence_packages

        # 2. 裁决冲突
        resolved_conflicts = []
        for conflict in conflicts:
            verdict = await self._resolve_conflict(conflict, query, evidence_packages)
            conflict["verdict"] = verdict
            resolved_conflicts.append(conflict)

        # 3. 生成最终判决书
        verdict = await self._generate_verdict(evidence_packages, conflicts, query)
        verdict["conflicts_resolved"] = resolved_conflicts

        # 4. 识别知识增量（用于自动更新知识库）
        verdict["knowledge_delta"] = self._identify_knowledge_delta(
            evidence_packages, conflicts, resolved_conflicts, query
        )

        print(f"✅ [Moderator] 裁决完成")
        if verdict.get("knowledge_delta", {}).get("has_delta"):
            print(f"📈 [Moderator] 检测到知识增量：{len(verdict['knowledge_delta'].get('updated_chunks', []))} 个 Chunk 需要更新")

        return verdict

    def _identify_knowledge_delta(
        self,
        evidence_packages: List[Dict],
        conflicts: List[Dict],
        resolved_conflicts: List[Dict],
        query: str
    ) -> Dict:
        """
        识别知识增量（哪些 Chunk 需要更新）

        触发条件：
        1. 有冲突被裁决
        2. 有联网证据补充本地证据
        3. 证据颜色为 RED/YELLOW 需要标记
        """
        updated_chunks = []

        # 条件 1: 冲突裁决 → 被推翻的证据需要更新
        for conflict in resolved_conflicts:
            if conflict.get("verdict", {}).get("decision") != "无法裁决":
                for pkg in conflict.get("packages", []):
                    # 找到对应的 evidence_chunks
                    for pkg_data in evidence_packages:
                        if pkg_data.get("doc_id", "").startswith(pkg.get("doc_id", "")[:8]):
                            for chunk in pkg_data.get("evidence_chunks", []):
                                updated_chunks.append({
                                    "chunk_id": chunk.get("id"),
                                    "galaxy_name": pkg_data.get("galaxy_name"),
                                    "change_type": "update",
                                    "reason": f"冲突裁决：{conflict.get('description', '未知')[:settings.CONTEXT_EVIDENCE_REASON_PREFIX]}",
                                    "old_content": chunk.get("content", "")[:settings.CONTEXT_CHUNK_PREVIEW_CONTENT],
                                    "color": chunk.get("color", "YELLOW")
                                })

        # 条件 2: 联网证据补充 → 标记为待验证或已验证
        for pkg in evidence_packages:
            if pkg.get("is_internet"):
                for chunk in pkg.get("evidence_chunks", []):
                    if chunk.get("color") in ["GREEN", "BLUE"]:
                        updated_chunks.append({
                            "chunk_id": chunk.get("id"),
                            "galaxy_name": "互联网证人",
                            "change_type": "create",
                            "reason": f"联网证据补充：{chunk.get('source_title', '未知')[:settings.CONTEXT_EVIDENCE_REASON_PREFIX]}",
                            "new_content": chunk.get("content", "")[:settings.CONTEXT_CHUNK_PREVIEW_CONTENT],
                            "color": chunk.get("color", "YELLOW"),
                            "metadata": {
                                "source_url": chunk.get("source_url"),
                                "published_date": chunk.get("published_date")
                            }
                        })

        # 生成提交消息
        if conflicts:
            commit_message = f"裁决 \"{query[:settings.CONTEXT_COMMIT_QUERY_PREFIX]}\" - {len(conflicts)} 处冲突"
        elif updated_chunks:
            commit_message = f"更新 \"{query[:settings.CONTEXT_COMMIT_QUERY_PREFIX]}\" - {len(updated_chunks)} 个证据"
        else:
            commit_message = ""

        return {
            "has_delta": len(updated_chunks) > 0,
            "updated_chunks": updated_chunks,
            "commit_message": commit_message,
            "conflict_count": len(conflicts),
            "resolved_count": len(resolved_conflicts)
        }

    async def _detect_conflicts(
        self,
        evidence_packages: List[Dict],
        query: str
    ) -> tuple[List[Dict], List[Dict]]:
        """
        检测证据分片之间的逻辑冲突

        策略：
        1. 提取每个证据包的核心主张
        2. 使用 LLM 判断主张之间是否存在矛盾
        3. 【V7.0】如果存在冲突/关联，必须声明 proposed_relationships

        注意：
        - 不再进行向量相似度过滤，因为 Distributor 已经根据查询相关性选择了星系
        - 只处理真正的逻辑冲突，不处理"同名异义"（那应该在 Distributor 层解决）
        """
        if len(evidence_packages) < 2:
            print(f"  ⚠️ [Moderator] 证据包不足 2 个，跳过冲突检测")
            return [], list(evidence_packages)

        # 🚀 [V51.2] 移除向量过滤：Distributor 已经完成了相关性筛选
        # 直接使用所有证据包进行冲突检测
        valid_packages = list(evidence_packages)

        # 构造冲突检测上下文
        evidence_summaries = []
        for pkg in valid_packages:
            chunk_texts = [f"[P{c['page_number']}] {c['content'][:settings.CONTEXT_EVIDENCE_CONTENT_PREFIX]}..." for c in pkg['evidence_chunks'][:settings.CONTEXT_FALLBACK_CHUNKS]]
            summary = {
                "galaxy_name": pkg["galaxy_name"],
                "doc_id": pkg["doc_id"][:settings.CONTEXT_COMMIT_DOC_ID_PREFIX],
                "evidence_summary": "\n".join(chunk_texts)
            }
            evidence_summaries.append(summary)

        prompt = f"""你是一个严谨的逻辑审计员。请分析以下证据包，检测是否存在逻辑冲突。

【原始问题】
{query}

【证据包列表】
{json.dumps(evidence_summaries, ensure_ascii=False, indent=2)}

你的任务：
1. 提取每个证据包的核心主张（事实性陈述）
2. 识别主张之间的矛盾或不一致
3. 如果没有明显冲突，返回空列表
4. 【V7.0 严格模式】如果检测到冲突/关联，必须声明 proposed_relationships

【关系类型定义】（严格枚举，不可私造）
- causality: A 导致 B，或 A 是 B 的前提
- contradiction: A 与 B 存在逻辑冲突（需要裁决）
- support: A 为 B 提供物理层面的证据支撑
- evolution: B 是 A 的修正版本（跨文档知识更迭）
- complement: A 和 B 描述同一实体的不同维度

输出格式（严格 JSON）：
{{
    "conflicts": [
        {{
            "description": "冲突描述",
            "packages": [
                {{"galaxy_name": "星系名", "doc_id": "文档 ID", "claim": "主张内容", "chunk_id": "Chunk ID"}}
            ],
            "severity": "CRITICAL" 或 "MINOR",
            "proposed_relationships": [
                {{
                    "source_chunk_id": "Chunk ID 1",
                    "target_chunk_id": "Chunk ID 2",
                    "rel_type": "contradiction",
                    "strength": 0.95,
                    "description": "两个 Chunk 在 XX 描述上存在直接矛盾"
                }}
            ]
        }}
    ]
}}

注意：
- proposed_relationships 是可选的，只有当你确定存在关系时才声明
- rel_type 必须是上述枚举值之一
- strength 范围 0.0-1.0
- 不要强行找冲突！没有明显矛盾就返回空列表！
"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            data = json.loads(response.choices[0].message.content)
            conflicts = data.get("conflicts", [])

            print(f"  ↳ 检测到 {len(conflicts)} 个冲突")
            if conflicts:
                for c in conflicts:
                    print(f"      - {c.get('description', '未知')[:100]}...")
            return conflicts, valid_packages

        except Exception as e:
            print(f"⚠️ [Moderator] 冲突检测失败：{e}")
            return [], valid_packages

    async def _resolve_conflict(
        self,
        conflict: Dict,
        query: str,
        evidence_packages: List[Dict]
    ) -> Dict:
        """
        裁决单个冲突

        策略：
        1. 基于证据可信度（星系权威性、证据充分性、交叉印证）
        2. 使用 LLM 进行裁决
        """
        # 找到冲突相关的完整证据包
        conflict_packages = []
        for pkg in evidence_packages:
            for p in conflict["packages"]:
                if pkg["doc_id"][:settings.CONTEXT_COMMIT_DOC_ID_PREFIX] == p["doc_id"]:
                    conflict_packages.append(pkg)
                    break

        prompt = f"""你是联邦法庭的大法官。请对以下冲突进行裁决。

【原始问题】
{query}

【冲突描述】
{conflict['description']}

【冲突双方证据】
{json.dumps(conflict['packages'], ensure_ascii=False, indent=2)}

裁决原则：
1. 优先采信证据更充分、逻辑更清晰的证词
2. 如果双方证据相当，采取兼容性解释
3. 如果有外部佐证（多个文档指向同一结论），优先采信
4. 如果无法调和，明确说明原因

输出格式（严格 JSON）：
{{
    "decision": "支持证人 1" / "支持证人 2" / "兼容性解释" / "无法调和",
    "reasoning": "裁决理由",
    "confidence": 0.0-1.0
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            data = json.loads(response.choices[0].message.content)
            return data

        except Exception as e:
            print(f"⚠️ [Moderator] 冲突裁决失败：{e}")
            return {
                "decision": "无法裁决",
                "reasoning": str(e),
                "confidence": 0.0
            }

    async def _generate_verdict(
        self,
        evidence_packages: List[Dict],
        conflicts: List[Dict],
        query: str
    ) -> Dict:
        """
        生成最终判决书

        基于所有证据分片和冲突裁决结果，合成最终答案
        """
        # 构造证据上下文
        evidence_context = []
        for pkg in evidence_packages:
            chunks_text = []
            for c in pkg['evidence_chunks']:
                chunks_text.append(
                    f"[{pkg['galaxy_name']} | P{c['page_number']} | {c['breadcrumb']}]\n"
                    f"{c['content']}"
                )
            evidence_context.append({
                "galaxy_name": pkg["galaxy_name"],
                "doc_id": pkg["doc_id"][:settings.CONTEXT_COMMIT_DOC_ID_PREFIX],
                "evidence": "\n---\n".join(chunks_text)
            })

        # 构造冲突摘要
        conflict_summary = []
        for c in conflicts:
            if c.get("verdict"):
                conflict_summary.append(
                    f"冲突：{c['description']} → 裁决：{c['verdict'].get('decision', '未知')}"
                )

        prompt = f"""你是联邦法庭的首席大法官。请生成最终判决书。

【原始问题】
{query}

【证据包】
{json.dumps(evidence_context, ensure_ascii=False, indent=2)}

【冲突裁决】
{chr(10).join(conflict_summary) if conflict_summary else "无冲突"}

判决书要求：
1. 直接回答问题
2. 综合所有证据包的可信部分
3. 在关键陈述后标注来源星系 (星系名)
4. 如果有未解决的冲突，明确说明
5. 如果证据不足，如实说明

输出格式（严格 JSON）：
{{
    "final_answer": "最终答案（可包含多个段落）",
    "confidence": 0.0-1.0,
    "cited_galaxies": ["星系名 1", "星系名 2", ...],
    "cited_chunks": [
        {{"id": "chunk_id", "galaxy_name": "星系名", "page_number": 1, "breadcrumb": "路径"}}
    ],
    "reasoning": "推理过程说明"
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            data = json.loads(response.choices[0].message.content)
            return data

        except Exception as e:
            print(f"⚠️ [Moderator] 判决书生成失败：{e}")
            return {
                "final_answer": "判决书生成失败：" + str(e),
                "confidence": 0.0,
                "cited_galaxies": [],
                "reasoning": str(e)
            }
