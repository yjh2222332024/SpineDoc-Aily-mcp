#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断脚本：检查 Reranker 状态
"""
import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("🔍 Reranker 状态诊断")
print("=" * 60)

# Step 1: 检查 settings
print("\n[Step 1] 加载 settings...")
try:
    from app.core.config import settings
    print(f"✅ settings 加载成功")
    print(f"   EMBEDDING_API_KEY: {settings.EMBEDDING_API_KEY[:20] if settings.EMBEDDING_API_KEY else 'None'}...")
    print(f"   EMBEDDING_BASE_URL: {settings.EMBEDDING_BASE_URL}")
except Exception as e:
    print(f"❌ settings 加载失败：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: 检查 SpineReranker
print("\n[Step 2] 加载 SpineReranker...")
try:
    from spine_cli.core.reranker import SpineReranker
    print(f"✅ SpineReranker 加载成功")
except Exception as e:
    print(f"❌ SpineReranker 加载失败：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: 创建 Reranker 实例
print("\n[Step 3] 创建 Reranker 实例...")
try:
    reranker = SpineReranker()
    print(f"✅ Reranker 创建成功")
    print(f"   reranker.enabled: {reranker.enabled}")
except Exception as e:
    print(f"❌ Reranker 创建失败：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: 检查 SpineEngine
print("\n[Step 4] 加载 SpineEngine...")
try:
    from spine_cli.core.engine import SpineEngine
    print(f"✅ SpineEngine 加载成功")
except Exception as e:
    print(f"❌ SpineEngine 加载失败：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 5: 创建 SpineEngine 实例
print("\n[Step 5] 创建 SpineEngine 实例...")
try:
    engine = SpineEngine()
    print(f"✅ SpineEngine 创建成功")
    print(f"   engine.reranker.enabled: {engine.reranker.enabled}")
except Exception as e:
    print(f"❌ SpineEngine 创建失败：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ 诊断完成！所有组件正常加载")
print("=" * 60)
