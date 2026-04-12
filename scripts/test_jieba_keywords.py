"""
测试 jieba 关键词提取是否正常工作
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.app.services.rag.splitter import ContextAwareSplitter

# 测试文本
test_text = """
SM4 算法是中国国家密码管理局发布的商用密码标准算法，
全称为 SMS4（Secret Message Service 4）。该算法于 2006 年正式发布，
2012 年被发布为国家密码行业标准（GM/T 0002-2012），
2016 年被发布为国家标准（GB/T 32907-2016）。

SM4 算法在国际标准化方面也取得了重要进展：
- 2017 年 11 月，SM4 算法被 ISO/IEC 采纳为国际标准（ISO/IEC 18033-4）
- 这是我国首个成为国际标准的密码算法
- 标志着我国商用密码算法在国际上的认可度大幅提升

ZUC（祖冲之）算法是另一个重要的中国商用密码算法，
主要用于移动通信领域的加密和完整性保护。
ZUC 算法于 2011 年被 3GPP 采纳为 LTE 国际加密标准，
是我国首个在国际上被广泛采用的密码算法。
"""

splitter = ContextAwareSplitter()

print("=" * 80)
print("🧪 测试 jieba 关键词提取")
print("=" * 80)

keywords = splitter._extract_keywords(test_text, "第五章 > 商用密码算法")

print(f"\n提取到 {len(keywords)} 个关键词:")
for i, kw in enumerate(keywords[:15]):
    print(f"  [{i+1}] {kw}")

# 验证是否提取到了核心术语
expected_keywords = ["SM4", "ZUC", "SM2", "国际", "标准", "密码", "算法"]
found = [kw for kw in expected_keywords if kw in keywords]

print(f"\n✅ 核心术语覆盖：{len(found)}/{len(expected_keywords)}")
print(f"   找到：{found}")
print(f"   缺失：{[kw for kw in expected_keywords if kw not in keywords]}")
