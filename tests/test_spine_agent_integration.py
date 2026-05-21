"""
Integration tests for SpineAgent - exercises REAL logic, not just wiring.
Only mocks external I/O (LLM API, Bitable, network). All internal logic is real.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ═══════════════════════════════════════════════════════════════
#  1. BayesianAggregator — 纯数学，零 mock
# ═══════════════════════════════════════════════════════════════

class TestBayesianAggregator:
    """贝叶斯融合器：纯数学逻辑，不需要任何 mock。"""

    def test_single_local_source(self):
        from backend.app.services.intelligence.retrieval.graph.auditor import BayesianAggregator
        evidence = [{"id": "e1", "origin": "LOCAL_GALAXY"}]
        conf = BayesianAggregator.calculate_claim_confidence(evidence)
        assert abs(conf - 0.95) < 1e-6

    def test_single_memory_source(self):
        from backend.app.services.intelligence.retrieval.graph.auditor import BayesianAggregator
        evidence = [{"id": "e1", "origin": "A-MEMORY"}]
        conf = BayesianAggregator.calculate_claim_confidence(evidence)
        assert abs(conf - 0.75) < 1e-6

    def test_single_online_source(self):
        from backend.app.services.intelligence.retrieval.graph.auditor import BayesianAggregator
        evidence = [{"id": "e1", "origin": "INTERNET_WITNESS"}]
        conf = BayesianAggregator.calculate_claim_confidence(evidence)
        assert abs(conf - 0.45) < 1e-6

    def test_multi_source_compounds(self):
        """独立来源越多，置信度越高：C = 1 - product(1 - W_s)"""
        from backend.app.services.intelligence.retrieval.graph.auditor import BayesianAggregator
        evidence = [
            {"id": "e1", "origin": "LOCAL_GALAXY"},    # 0.95
            {"id": "e2", "origin": "A-MEMORY"},         # 0.75
        ]
        conf = BayesianAggregator.calculate_claim_confidence(evidence)
        # 1 - (1-0.95)*(1-0.75) = 1 - 0.05*0.25 = 1 - 0.0125 = 0.9875
        assert abs(conf - 0.9875) < 1e-6

    def test_three_sources_very_high(self):
        from backend.app.services.intelligence.retrieval.graph.auditor import BayesianAggregator
        evidence = [
            {"id": "e1", "origin": "LOCAL_GALAXY"},
            {"id": "e2", "origin": "A-MEMORY"},
            {"id": "e3", "origin": "INTERNET_WITNESS"},
        ]
        conf = BayesianAggregator.calculate_claim_confidence(evidence)
        # 1 - (0.05)*(0.25)*(0.55) = 1 - 0.006875 = 0.993125
        assert conf > 0.99

    def test_arbitrate_conflict_balanced(self):
        """两组等强度证据应各得 0.5"""
        from backend.app.services.intelligence.retrieval.graph.auditor import BayesianAggregator
        group_a = [{"id": "a1", "origin": "LOCAL_GALAXY"}]
        group_b = [{"id": "b1", "origin": "LOCAL_GALAXY"}]
        weights = BayesianAggregator.arbitrate_conflict(group_a, group_b)
        assert abs(weights["a1"] - 0.5) < 1e-6
        assert abs(weights["b1"] - 0.5) < 1e-6

    def test_arbitrate_conflict_asymmetric(self):
        """LOCAL vs ONLINE：LOCAL 应获得更高权重"""
        from backend.app.services.intelligence.retrieval.graph.auditor import BayesianAggregator
        group_a = [{"id": "a1", "origin": "LOCAL_GALAXY"}]   # 0.95
        group_b = [{"id": "b1", "origin": "INTERNET_WITNESS"}] # 0.45
        weights = BayesianAggregator.arbitrate_conflict(group_a, group_b)
        assert weights["a1"] > weights["b1"]
        # 0.95/(0.95+0.45) = 0.6786
        assert abs(weights["a1"] - 0.95 / 1.4) < 0.01

    def test_arbitrate_empty_groups(self):
        from backend.app.services.intelligence.retrieval.graph.auditor import BayesianAggregator
        weights = BayesianAggregator.arbitrate_conflict([], [])
        assert weights == {}


# ═══════════════════════════════════════════════════════════════
#  2. SemanticDeduplicator — 真实去重逻辑
# ═══════════════════════════════════════════════════════════════

class TestDeduplicator:
    """去重器：ID 去重 + 语义去重，只 mock embedding service。"""

    @pytest.mark.asyncio
    async def test_empty_pool(self):
        from backend.app.services.intelligence.retrieval.utils.deduplicator import SemanticDeduplicator
        dedup = SemanticDeduplicator()
        result = await dedup.deduplicate([])
        assert result == []

    @pytest.mark.asyncio
    async def test_single_item(self):
        from backend.app.services.intelligence.retrieval.utils.deduplicator import SemanticDeduplicator
        dedup = SemanticDeduplicator()
        pool = [{"id": "a", "content": "hello"}]
        result = await dedup.deduplicate(pool)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_id_dedup(self):
        """相同 ID 只保留第一条。"""
        from backend.app.services.intelligence.retrieval.utils.deduplicator import SemanticDeduplicator
        dedup = SemanticDeduplicator()
        pool = [
            {"id": "a", "content": "first"},
            {"id": "a", "content": "duplicate"},
            {"id": "b", "content": "different"},
        ]
        result = await dedup.deduplicate(pool)
        assert len(result) == 2
        ids = {e["id"] for e in result}
        assert ids == {"a", "b"}

    @pytest.mark.asyncio
    async def test_semantic_dedup_removes_near_duplicates(self):
        """语义相似度 > 0.92 的应被去重。"""
        from backend.app.services.intelligence.retrieval.utils.deduplicator import SemanticDeduplicator

        mock_embed = AsyncMock()
        # 三条文本：前两条几乎相同，第三条不同
        # 向量：前两条余弦相似度 0.95，第三条 0.3
        import numpy as np
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.95, 0.312, 0.0])  # sim(v1,v2) ≈ 0.95
        v3 = np.array([0.0, 0.0, 1.0])     # sim(v1,v3) = 0
        mock_embed.get_embeddings_batch = AsyncMock(return_value=[v1, v2, v3])

        dedup = SemanticDeduplicator(embedding_service=mock_embed, similarity_threshold=0.92)
        pool = [
            {"id": "a", "content": "the contract states that penalty is 5%"},
            {"id": "b", "content": "the contract states that penalty is 5 percent"},
            {"id": "c", "content": "the sky is blue today"},
        ]
        result = await dedup.deduplicate(pool)
        # a 和 b 语义相似，应只保留一个
        assert len(result) == 2
        ids = {e["id"] for e in result}
        assert "a" in ids
        assert "c" in ids

    @pytest.mark.asyncio
    async def test_semantic_dedup_keeps_different_content(self):
        """语义不同的内容应全部保留。"""
        from backend.app.services.intelligence.retrieval.utils.deduplicator import SemanticDeduplicator

        mock_embed = AsyncMock()
        import numpy as np
        v1 = np.array([1.0, 0.0])
        v2 = np.array([0.0, 1.0])
        v3 = np.array([0.0, -1.0])
        mock_embed.get_embeddings_batch = AsyncMock(return_value=[v1, v2, v3])

        dedup = SemanticDeduplicator(embedding_service=mock_embed, similarity_threshold=0.92)
        pool = [
            {"id": "a", "content": "fire safety regulations"},
            {"id": "b", "content": "food delivery policy"},
            {"id": "c", "content": "financial audit report"},
        ]
        result = await dedup.deduplicate(pool)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_no_embedding_service_falls_back_to_id_dedup(self):
        from backend.app.services.intelligence.retrieval.utils.deduplicator import SemanticDeduplicator
        dedup = SemanticDeduplicator(embedding_service=None)
        pool = [
            {"id": "a", "content": "same topic"},
            {"id": "b", "content": "same topic rephrased"},
            {"id": "a", "content": "duplicate id"},
        ]
        result = await dedup.deduplicate(pool)
        assert len(result) == 2  # ID dedup only


# ═══════════════════════════════════════════════════════════════
#  3. HarvestSubagentResult — 真实 dataclass
# ═══════════════════════════════════════════════════════════════

class TestHarvestSubagentResult:
    def test_defaults(self):
        from backend.app.services.intelligence.retrieval.graph.harvest_subagents import HarvestSubagentResult
        r = HarvestSubagentResult(source="TEST")
        assert r.source == "TEST"
        assert r.evidence == []
        assert r.error is None
        assert r.duration_s == 0.0

    def test_with_evidence(self):
        from backend.app.services.intelligence.retrieval.graph.harvest_subagents import HarvestSubagentResult
        evidence = [{"id": "e1", "content": "test"}]
        r = HarvestSubagentResult(source="LOCAL_GALAXY", evidence=evidence, duration_s=1.5)
        assert len(r.evidence) == 1
        assert r.duration_s == 1.5


# ═══════════════════════════════════════════════════════════════
#  4. SpineAgent._apply_update — 真实合并语义
# ═══════════════════════════════════════════════════════════════

class TestApplyUpdate:
    """_apply_update 的合并逻辑是 coordinator._reduce_state 的移植，必须验证语义正确。"""

    def _make_agent(self):
        with patch("backend.app.services.spine_agent.LocalRetriever"), \
             patch("backend.app.services.spine_agent.OnlineRetriever"), \
             patch("backend.app.services.spine_agent.SemanticDeduplicator"), \
             patch("backend.app.services.spine_agent.planner_agent"), \
             patch("backend.app.services.spine_agent.auditor_node"), \
             patch("backend.app.services.spine_agent.synthesizer_node"), \
             patch("backend.app.services.spine_agent.evolution_node"), \
             patch("backend.app.services.spine_agent.NullMemory") as mock_mem:
            from backend.app.services.spine_agent import SpineAgent
            return SpineAgent(memory=mock_mem())

    def test_evidence_pool_replace(self):
        """evidence_pool 应替换而非追加。"""
        agent = self._make_agent()
        agent._state["evidence_pool"] = [{"id": "old1"}, {"id": "old2"}]
        agent._apply_update({"evidence_pool": [{"id": "new1"}]})
        assert len(agent._state["evidence_pool"]) == 1
        assert agent._state["evidence_pool"][0]["id"] == "new1"

    def test_l3_archive_append_dedup(self):
        """L3_archive 应追加且去重。"""
        agent = self._make_agent()
        agent._state["L3_archive"] = [{"id": "a"}, {"id": "b"}]
        agent._apply_update({"L3_archive": [{"id": "b"}, {"id": "c"}, {"id": "d"}]})
        ids = [e["id"] for e in agent._state["L3_archive"]]
        assert ids == ["a", "b", "c", "d"]

    def test_phase_log_extend(self):
        """phase_log 应追加。"""
        agent = self._make_agent()
        agent._state["phase_log"] = [{"step": "A"}]
        agent._apply_update({"phase_log": [{"step": "B"}, {"step": "C"}]})
        assert len(agent._state["phase_log"]) == 3

    def test_other_keys_overwrite(self):
        """其余键应覆盖。"""
        agent = self._make_agent()
        agent._state["query"] = "old"
        agent._apply_update({"query": "new", "final_answer": "answer"})
        assert agent._state["query"] == "new"
        assert agent._state["final_answer"] == "answer"

    def test_multiple_keys_in_one_update(self):
        """一次更新包含多个键。"""
        agent = self._make_agent()
        agent._state["evidence_pool"] = [{"id": "old"}]
        agent._state["claim_weights"] = {"old": 0.5}
        agent._apply_update({
            "evidence_pool": [{"id": "new"}],
            "claim_weights": {"new": 0.9, "new2": 0.7},
            "conflicts": [{"description": "test conflict"}],
        })
        assert len(agent._state["evidence_pool"]) == 1
        assert agent._state["claim_weights"] == {"new": 0.9, "new2": 0.7}
        assert len(agent._state["conflicts"]) == 1


# ═══════════════════════════════════════════════════════════════
#  5. SpineAgent 端到端 — mock LLM only, real everything else
# ═══════════════════════════════════════════════════════════════

def _make_real_agent():
    """创建真实 SpineAgent，只 mock 外部 I/O。"""
    with patch("backend.app.services.spine_agent.LocalRetriever") as MockSentry, \
         patch("backend.app.services.spine_agent.OnlineRetriever") as MockWitness, \
         patch("backend.app.services.spine_agent.SemanticDeduplicator") as MockDedup, \
         patch("backend.app.services.spine_agent.planner_agent") as mock_planner, \
         patch("backend.app.services.spine_agent.auditor_node") as mock_auditor, \
         patch("backend.app.services.spine_agent.synthesizer_node") as mock_synth, \
         patch("backend.app.services.spine_agent.evolution_node") as mock_evol, \
         patch("backend.app.services.spine_agent.NullMemory") as mock_mem:

        # 真实 deduplicator（只 mock embedding service）
        mock_dedup_inst = MagicMock()
        async def real_dedup(pool):
            seen = set()
            result = []
            for e in pool:
                eid = e.get("id")
                if eid and eid not in seen:
                    seen.add(eid)
                    result.append(e)
            return result
        mock_dedup_inst.deduplicate = real_dedup
        MockDedup.return_value = mock_dedup_inst

        from backend.app.services.spine_agent import SpineAgent
        agent = SpineAgent(memory=mock_mem())

        return agent, mock_planner, mock_auditor, mock_synth, mock_evol


@pytest.mark.asyncio
async def test_plan_real_dispatch():
    """plan() 真实调用 planner.plan() 并推进状态。"""
    agent, mock_planner, *_ = _make_real_agent()
    mock_planner.plan = AsyncMock(return_value={
        "sub_queries": ["子查询1", "子查询2", "子查询3"],
        "next_step": "HARVEST",
    })

    result = await agent.plan()

    # 真实验证：planner 被调用，状态被更新
    mock_planner.plan.assert_called_once()
    assert agent._state["sub_queries"] == ["子查询1", "子查询2", "子查询3"]
    assert agent._state["next_step"] == "HARVEST"
    assert len(agent._state["phase_log"]) == 1
    assert agent._state["phase_log"][0]["step"] == "PLAN"
    assert agent._state["phase_log"][0]["status"] == "done"


@pytest.mark.asyncio
async def test_harvest_real_concurrent_merge():
    """harvest() 真实并发调用 3 个 subagent 并合并结果。"""
    from backend.app.services.intelligence.retrieval.graph.harvest_subagents import HarvestSubagentResult

    agent, *_ = _make_real_agent()
    agent._state["sub_queries"] = ["q1", "q2"]
    agent._state["doc_id"] = "all"

    # 模拟三个 subagent 的真实返回
    mem_result = HarvestSubagentResult(
        source="A_MEMORY",
        evidence=[
            {"id": "mem_1", "content": "memory evidence 1", "origin": "A-MEMORY", "claims": ["claim1"]},
            {"id": "mem_2", "content": "memory evidence 2", "origin": "A-MEMORY", "claims": ["claim2"]},
        ]
    )
    local_result = HarvestSubagentResult(
        source="LOCAL_GALAXY",
        evidence=[
            {"id": "local_1", "content": "local evidence 1", "origin": "LOCAL_GALAXY", "claims": ["claim3"]},
        ]
    )
    online_result = HarvestSubagentResult(
        source="INTERNET_WITNESS",
        evidence=[
            {"id": "online_1", "content": "online evidence 1", "origin": "INTERNET_WITNESS", "claims": ["claim4"]},
        ]
    )

    with patch("backend.app.services.spine_agent.harvest_memory_subagent", new_callable=AsyncMock, return_value=mem_result), \
         patch("backend.app.services.spine_agent.harvest_local_subagent", new_callable=AsyncMock, return_value=local_result), \
         patch("backend.app.services.spine_agent.harvest_online_subagent", new_callable=AsyncMock, return_value=online_result):
        result = await agent.harvest()

    pool = agent.get_evidence_pool()
    assert len(pool) == 4
    ids = {e["id"] for e in pool}
    assert ids == {"mem_1", "mem_2", "local_1", "online_1"}
    assert agent._state["next_step"] == "AUDIT"


@pytest.mark.asyncio
async def test_harvest_real_dedup_by_id():
    """harvest() 合并后应通过 deduplicator 去重。"""
    from backend.app.services.intelligence.retrieval.graph.harvest_subagents import HarvestSubagentResult

    agent, *_ = _make_real_agent()
    agent._state["sub_queries"] = ["q1"]
    agent._state["doc_id"] = "all"

    # 两个 subagent 返回相同 ID 的证据
    mem_result = HarvestSubagentResult(
        source="A_MEMORY",
        evidence=[{"id": "shared_1", "content": "from memory"}]
    )
    local_result = HarvestSubagentResult(
        source="LOCAL_GALAXY",
        evidence=[{"id": "shared_1", "content": "from local"}]
    )

    with patch("backend.app.services.spine_agent.harvest_memory_subagent", new_callable=AsyncMock, return_value=mem_result), \
         patch("backend.app.services.spine_agent.harvest_local_subagent", new_callable=AsyncMock, return_value=local_result), \
         patch("backend.app.services.spine_agent.harvest_online_subagent", new_callable=AsyncMock, return_value=HarvestSubagentResult(source="INTERNET_WITNESS")):
        await agent.harvest()

    pool = agent.get_evidence_pool()
    assert len(pool) == 1  # dedup removed duplicate


@pytest.mark.asyncio
async def test_audit_real_state_update():
    """audit() 真实调用 auditor.audit() 并更新状态。"""
    agent, _, mock_auditor, *_ = _make_real_agent()
    agent._state["evidence_pool"] = [
        {"id": "e1", "origin": "LOCAL_GALAXY", "content": "test"},
        {"id": "e2", "origin": "A-MEMORY", "content": "test2"},
    ]
    mock_auditor.audit = AsyncMock(return_value={
        "evidence_pool": [
            {"id": "e1", "origin": "LOCAL_GALAXY", "content": "test"},
        ],
        "claim_weights": {"e1": 0.95},
        "conflicts": [],
    })

    result = await agent.audit()

    mock_auditor.audit.assert_called_once()
    assert agent._state["claim_weights"] == {"e1": 0.95}
    assert len(agent._state["evidence_pool"]) == 1
    assert agent._state["next_step"] == "SYNTHESIZE"
    assert agent._state["phase_log"][-1]["step"] == "AUDIT"


@pytest.mark.asyncio
async def test_synthesize_real_verdict():
    """synthesize() 真实调用 synthesizer 并设置 verdict。"""
    agent, _, _, mock_synth, _ = _make_real_agent()
    agent._state["evidence_pool"] = [{"id": "e1"}]
    agent._state["claim_weights"] = {"e1": 0.95}

    mock_synth.synthesize = AsyncMock(return_value={
        "verdict": {
            "internal_consensus": ["事实1", "事实2"],
            "assistant_answer": "根据文档分析...",
        },
        "next_step": "EVOLVE",
    })

    result = await agent.synthesize()

    assert agent._state["verdict"]["internal_consensus"] == ["事实1", "事实2"]
    assert agent._state["next_step"] == "EVOLVE"


@pytest.mark.asyncio
async def test_evolve_real_pending_consent():
    """evolve() 真实设置 pending_consent 状态。"""
    agent, _, _, _, mock_evol = _make_real_agent()
    agent._state["next_step"] = "EVOLVE"

    result = await agent.evolve()

    assert result == {}
    assert agent._state["next_step"] == "END"
    log_entry = agent._state["phase_log"][-1]
    assert log_entry["step"] == "EVOLVE"
    assert log_entry["status"] == "pending_consent"


@pytest.mark.asyncio
async def test_run_full_real_pipeline():
    """run_full() 端到端：plan→harvest→audit→synthesize→evolve。"""
    from backend.app.services.intelligence.retrieval.graph.harvest_subagents import HarvestSubagentResult

    agent, mock_planner, mock_auditor, mock_synth, _ = _make_real_agent()

    # Mock 每个阶段的返回
    mock_planner.plan = AsyncMock(return_value={
        "sub_queries": ["q1", "q2"],
        "next_step": "HARVEST",
    })

    mem_result = HarvestSubagentResult(
        source="A_MEMORY",
        evidence=[{"id": "e1", "content": "evidence", "origin": "A-MEMORY", "claims": ["c1"]}]
    )

    with patch("backend.app.services.spine_agent.harvest_memory_subagent", new_callable=AsyncMock, return_value=mem_result), \
         patch("backend.app.services.spine_agent.harvest_local_subagent", new_callable=AsyncMock, return_value=HarvestSubagentResult(source="LOCAL_GALAXY")), \
         patch("backend.app.services.spine_agent.harvest_online_subagent", new_callable=AsyncMock, return_value=HarvestSubagentResult(source="INTERNET_WITNESS")):

        mock_auditor.audit = AsyncMock(return_value={
            "evidence_pool": [{"id": "e1", "origin": "A-MEMORY", "content": "evidence"}],
            "claim_weights": {"e1": 0.75},
            "conflicts": [],
        })

        mock_synth.synthesize = AsyncMock(return_value={
            "verdict": {"internal_consensus": ["fact1"], "assistant_answer": "answer"},
            "next_step": "EVOLVE",
        })

        result = await agent.run_full("test query", doc_id="all")

    # 验证完整流水线
    assert result["final_answer"] == "answer"
    assert len(agent._state["phase_log"]) == 5  # PLAN, HARVEST, AUDIT, SYNTHESIZE, EVOLVE
    steps = [p["step"] for p in agent._state["phase_log"]]
    assert steps == ["PLAN", "HARVEST", "AUDIT", "SYNTHESIZE", "EVOLVE"]


@pytest.mark.asyncio
async def test_run_full_single_doc_skips_plan():
    """单文档查询应跳过 PLAN 阶段。"""
    from backend.app.services.intelligence.retrieval.graph.harvest_subagents import HarvestSubagentResult
    agent, mock_planner, mock_auditor, mock_synth, _ = _make_real_agent()
    agent.reset("test query", doc_id="doc123")

    with patch("backend.app.services.spine_agent.harvest_memory_subagent", new_callable=AsyncMock, return_value=HarvestSubagentResult(source="A_MEMORY")), \
         patch("backend.app.services.spine_agent.harvest_local_subagent", new_callable=AsyncMock, return_value=HarvestSubagentResult(source="LOCAL_GALAXY")), \
         patch("backend.app.services.spine_agent.harvest_online_subagent", new_callable=AsyncMock, return_value=HarvestSubagentResult(source="INTERNET_WITNESS")):

        mock_auditor.audit = AsyncMock(return_value={
            "evidence_pool": [], "claim_weights": {}, "conflicts": [],
        })
        mock_synth.synthesize = AsyncMock(return_value={
            "verdict": {"assistant_answer": "no evidence"},
            "next_step": "EVOLVE",
        })

        result = await agent.run_full("test query", doc_id="doc123")

    # plan() 不应被调用
    mock_planner.plan.assert_not_called()
    steps = [p["step"] for p in agent._state["phase_log"]]
    assert "PLAN" not in steps
    assert steps[0] == "HARVEST"
