"""
Tests for SpineAgent refactoring quality improvements.
Covers: instantiation, state management, phase dispatch, harvest concurrency, singleton safety.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────

def _make_agent():
    """Create a SpineAgent with all external deps mocked."""
    mock_dedup = MagicMock()
    mock_dedup.deduplicate = AsyncMock(side_effect=lambda pool: pool)  # passthrough

    with patch("backend.app.services.spine_agent.LocalRetriever"), \
         patch("backend.app.services.spine_agent.OnlineRetriever"), \
         patch("backend.app.services.spine_agent.SemanticDeduplicator", return_value=mock_dedup), \
         patch("backend.app.services.spine_agent.planner_agent") as mock_planner, \
         patch("backend.app.services.spine_agent.auditor_node") as mock_auditor, \
         patch("backend.app.services.spine_agent.synthesizer_node") as mock_synth, \
         patch("backend.app.services.spine_agent.evolution_node") as mock_evol, \
         patch("backend.app.services.spine_agent.NullMemory") as mock_memory:
        from backend.app.services.spine_agent import SpineAgent
        agent = SpineAgent(memory=mock_memory())
        return agent, mock_planner, mock_auditor, mock_synth, mock_evol


# ── Test 1: Instantiation ────────────────────────────────────

def test_agent_creates_phase_funcs_once():
    """_phase_funcs should be built in __init__, not per-call."""
    agent, *_ = _make_agent()
    assert hasattr(agent, "_phase_funcs")
    assert len(agent._phase_funcs) == 5
    # Same object identity on every access
    assert agent._phase_funcs is agent._phase_funcs


def test_initial_state_is_clean():
    agent, *_ = _make_agent()
    state = agent._state
    assert state["query"] == ""
    assert state["evidence_pool"] == []
    assert state["claim_weights"] == {}
    assert state["conflicts"] == []
    assert state["phase_log"] == []


# ── Test 2: Reset ────────────────────────────────────────────

def test_reset_sets_query():
    agent, *_ = _make_agent()
    agent.reset("test query", doc_id="doc123")
    assert agent._state["query"] == "test query"
    assert agent._state["doc_id"] == "doc123"
    assert agent._state["sub_queries"] == ["test query"]
    assert agent._state["next_step"] == "HARVEST"  # single-doc skips PLAN


def test_reset_multi_doc():
    agent, *_ = _make_agent()
    agent.reset("test query", doc_id="all")
    assert agent._state["sub_queries"] == []
    assert agent._state["next_step"] == "PLAN"


# ── Test 3: _apply_update merge semantics ────────────────────

def test_apply_update_replaces_evidence_pool():
    agent, *_ = _make_agent()
    agent._state["evidence_pool"] = [{"id": "old"}]
    agent._apply_update({"evidence_pool": [{"id": "new"}]})
    assert agent._state["evidence_pool"] == [{"id": "new"}]


def test_apply_update_appends_l3_archive_deduped():
    agent, *_ = _make_agent()
    agent._state["L3_archive"] = [{"id": "a"}, {"id": "b"}]
    agent._apply_update({"L3_archive": [{"id": "b"}, {"id": "c"}]})
    ids = [e["id"] for e in agent._state["L3_archive"]]
    assert ids == ["a", "b", "c"]


def test_apply_update_extends_phase_log():
    agent, *_ = _make_agent()
    agent._state["phase_log"] = [{"step": "A"}]
    agent._apply_update({"phase_log": [{"step": "B"}]})
    assert len(agent._state["phase_log"]) == 2


def test_apply_update_overwrites_other_keys():
    agent, *_ = _make_agent()
    agent._apply_update({"query": "new query", "final_answer": "done"})
    assert agent._state["query"] == "new query"
    assert agent._state["final_answer"] == "done"


# ── Test 4: Phase methods ────────────────────────────────────

@pytest.mark.asyncio
async def test_plan_calls_planner_and_advances():
    agent, mock_planner, *_ = _make_agent()
    mock_planner.plan = AsyncMock(return_value={"sub_queries": ["q1", "q2"]})
    agent._planner = mock_planner

    result = await agent.plan()
    assert result["sub_queries"] == ["q1", "q2"]
    assert agent._state["next_step"] == "HARVEST"
    assert len(agent._state["phase_log"]) == 1
    assert agent._state["phase_log"][0]["step"] == "PLAN"


@pytest.mark.asyncio
async def test_evolve_sets_pending_consent():
    agent, *_ = _make_agent()
    agent._state["next_step"] = "EVOLVE"
    result = await agent.evolve()
    assert result == {}
    assert agent._state["next_step"] == "END"
    assert agent._state["phase_log"][-1]["status"] == "pending_consent"


# ── Test 5: Harvest with mocked subagents ────────────────────

@pytest.mark.asyncio
async def test_harvest_concurrent_gather():
    """Verify harvest runs 3 subagents via asyncio.gather and merges results."""
    from backend.app.services.intelligence.retrieval.graph.harvest_subagents import HarvestSubagentResult

    agent, *_ = _make_agent()
    agent._state["sub_queries"] = ["q1", "q2"]
    agent._state["doc_id"] = "all"

    mock_mem = HarvestSubagentResult(source="A_MEMORY", evidence=[{"id": "m1", "content": "mem"}])
    mock_local = HarvestSubagentResult(source="LOCAL_GALAXY", evidence=[{"id": "l1", "content": "local"}])
    mock_online = HarvestSubagentResult(source="INTERNET_WITNESS", evidence=[{"id": "o1", "content": "online"}])

    with patch("backend.app.services.spine_agent.harvest_memory_subagent", new_callable=AsyncMock, return_value=mock_mem), \
         patch("backend.app.services.spine_agent.harvest_local_subagent", new_callable=AsyncMock, return_value=mock_local), \
         patch("backend.app.services.spine_agent.harvest_online_subagent", new_callable=AsyncMock, return_value=mock_online):
        result = await agent.harvest()

    pool = agent.get_evidence_pool()
    # After dedup, should have 3 unique evidence items
    assert len(pool) == 3
    ids = {e["id"] for e in pool}
    assert ids == {"m1", "l1", "o1"}
    assert agent._state["next_step"] == "AUDIT"


@pytest.mark.asyncio
async def test_harvest_handles_subagent_exception():
    """If one subagent throws, others should still succeed."""
    from backend.app.services.intelligence.retrieval.graph.harvest_subagents import HarvestSubagentResult

    agent, *_ = _make_agent()
    agent._state["sub_queries"] = ["q1"]
    agent._state["doc_id"] = "all"

    mock_local = HarvestSubagentResult(source="LOCAL_GALAXY", evidence=[{"id": "l1"}])

    with patch("backend.app.services.spine_agent.harvest_memory_subagent", new_callable=AsyncMock, side_effect=RuntimeError("boom")), \
         patch("backend.app.services.spine_agent.harvest_local_subagent", new_callable=AsyncMock, return_value=mock_local), \
         patch("backend.app.services.spine_agent.harvest_online_subagent", new_callable=AsyncMock, return_value=HarvestSubagentResult(source="INTERNET_WITNESS")):
        result = await agent.harvest()

    pool = agent.get_evidence_pool()
    assert len(pool) == 1
    assert pool[0]["id"] == "l1"


# ── Test 6: isinstance check (not hasattr) ───────────────────

@pytest.mark.asyncio
async def test_harvest_uses_isinstance_not_hasattr():
    """harvest() should use isinstance(result, HarvestSubagentResult), not hasattr."""
    import inspect
    from backend.app.services.spine_agent import SpineAgent
    source = inspect.getsource(SpineAgent.harvest)
    assert "isinstance(result, HarvestSubagentResult)" in source
    assert "hasattr" not in source


# ── Test 7: _export_result uses top-level import ─────────────

def test_export_result_no_local_import():
    """_export_result should not have a local 'from ... import' statement."""
    import inspect
    from backend.app.services.spine_agent import SpineAgent
    source = inspect.getsource(SpineAgent._export_result)
    assert "from " not in source


# ── Test 8: run_full uses self._phase_funcs ──────────────────

def test_run_full_uses_instance_phase_funcs():
    """run_full should reference self._phase_funcs, not rebuild a dict."""
    import inspect
    from backend.app.services.spine_agent import SpineAgent
    source = inspect.getsource(SpineAgent.run_full)
    assert "self._phase_funcs" in source
    assert "phase_funcs = {" not in source


# ── Test 9: get_agent singleton ──────────────────────────────

@pytest.mark.asyncio
async def test_get_agent_singleton():
    """get_agent() should return the same instance on repeated calls."""
    with patch("spine_interaction.aily.mcp_server.AmemAdapter"), \
         patch("spine_interaction.aily.mcp_server.LarkCliReporter"), \
         patch("spine_interaction.aily.mcp_server.bitable_ledger"):
        import importlib
        import spine_interaction.aily.mcp_server as mcp_mod
        # Reset singleton for test
        mcp_mod._agent = None
        agent1 = await mcp_mod.get_agent()
        agent2 = await mcp_mod.get_agent()
        assert agent1 is agent2
        mcp_mod._agent = None  # cleanup


@pytest.mark.asyncio
async def test_get_agent_is_async():
    """get_agent() should be an async function."""
    import inspect
    import spine_interaction.aily.mcp_server as mcp_mod
    assert inspect.iscoroutinefunction(mcp_mod.get_agent)
