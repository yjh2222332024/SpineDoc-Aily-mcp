import pytest
import os
from backend.app.services.toc.aligner import LogicAligner
from backend.app.services.rag.cascading_retriever import CascadingRetriever

# 1. 测试 LogicAligner (钢铁级 Offset 修正)
def test_logic_aligner_offset_calculation():
    """测试 Offset 探测逻辑：验证中值标定逻辑"""
    toc_mock = [
        {"title": "前言", "page": 1, "physical_page": 5},
        {"title": "目录", "page": 1, "physical_page": 10},
        {"title": "第一章 正文开始", "page": 1, "physical_page": 45}, 
        {"title": "1.1 背景", "page": 2, "physical_page": 46}
    ]
    # 当前 V37.1 算法: [5, 10, 45] -> median is 10 -> offset = 10 - 1 = 9
    offset = LogicAligner.calculate_offset(toc_mock)
    assert offset == 9

# 2. 测试 CascadingRetriever (航道合并算法)
def test_cascading_retriever_range_merge():
    """测试航道合并逻辑：相邻或重叠的检索区间是否能合并"""
    retriever = CascadingRetriever(router=None, reranker=None)
    
    # 场景 A: 相邻航道 -> P10-20
    ranges = [(10, 15), (16, 20)]
    merged = retriever._merge_ranges(ranges)
    assert merged == [(10, 20)]
    
    # 场景 B: 重叠航道 -> P10-18
    ranges = [(10, 15), (12, 18)]
    merged = retriever._merge_ranges(ranges)
    assert merged == [(10, 18)]

# 3. 测试数据模型一致性 (简化版，避开 SQLAlchemy 注册表冲突)
def test_model_definition_sanity():
    """确保核心模型类可以被正确识别且字段完备"""
    from backend.app.core.models import Document, Chunk
    assert Document.__tablename__ == "document"
    assert Chunk.__tablename__ == "chunk"
    
    # 检查我们 SPEC V43 关心的字段
    # 注意：如果 DB 还没迁移，这里测的是类定义
    assert "metadata_json" in Chunk.__fields__
