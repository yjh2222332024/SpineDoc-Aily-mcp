# 📜 四色置信度集成日志 (2026-04-15)

**作者**: Karpathy (AI 顾问)  
**状态**: ✅ 完成
**主题**: 四色置信度集成到联邦法庭证据流转

---

## 1. 核心决策

### 决策 1：最小侵入式集成

> "Refactor like a surgeon, not a bulldozer."

**策略**：只在关键节点添加颜色计算，不改变现有证据流转逻辑。

| 修改点 | 修改内容 | 影响范围 |
|--------|----------|----------|
| `InternetWitness` | 初始化时创建 `ColorConfidenceCalculator` | 仅影响联网证据 |
| `Collector` | 初始化时创建 `ColorConfidenceCalculator`，`_load_chunks` 添加颜色计算 | 仅影响本地证据 |
| `spine_cli/main.py` | `ask` 命令显示颜色图标和置信度 | 仅影响 CLI 渲染 |

---

## 2. 实现细节

### 2.1 InternetWitness 修改

**文件**: `backend/app/services/intelligence/court/internet_witness.py`

**核心改动**:
```python
from .color_confidence import ColorConfidenceCalculator, ConfidenceColor

class InternetWitness:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or TAVILY_API_KEY
        # ... 原有代码
        self._semaphore = asyncio.Semaphore(TAVILY_CONCURRENT_LIMIT)
        self.color_calc = ColorConfidenceCalculator()  # ← 新增

    def _search_single(self, query: str, query_type: str) -> List[Dict]:
        # ... 原有代码
        chunk_data = {
            # ... 原有字段
            "query_type": query_type,
            "is_internet": True
        }
        # 计算颜色置信度 ← 新增
        color, confidence = self.color_calc.calculate(
            chunk_data,
            independent_sources=1,
            has_conflict=False
        )
        chunk_data["color"] = color.value
        chunk_data["confidence"] = confidence
```

**删除的代码**:
- `_calculate_dynamic_confidence()` - 旧置信度计算（已废弃）
- `_calculate_recency_weight()` - 旧时间衰减（已废弃）
- `DOMAIN_AUTHORITY` - 硬编码域名权威分（已迁移到配置文件）
- `QUERY_HALF_LIFE` - 硬编码半衰期（已迁移到配置文件）

---

### 2.2 Collector 修改

**文件**: `backend/app/services/intelligence/court/collector.py`

**核心改动**:
```python
from .color_confidence import ColorConfidenceCalculator, ConfidenceColor

class Collector:
    def __init__(self):
        self.session_maker = get_async_sessionmaker()
        self.client = AsyncOpenAI(...)
        self.internet_witness = InternetWitness()
        self.color_calc = ColorConfidenceCalculator()  # ← 新增

    async def _load_chunks(self, selected_chunks: List[Dict]) -> List[Dict]:
        """从数据库加载完整分片内容，并计算颜色置信度"""
        # ... 原有加载逻辑
        for c in chunks:
            chunk_data = {
                "id": str(c.id),
                "content": c.content,
                "page_number": c.page_number,
                "breadcrumb": c.breadcrumb,
                "logic_tags": c.logic_tags,
                "type": "LOCAL_PDF",
                "doc_status": getattr(c, 'doc_status', 'completed'),
            }
            # 计算本地证据颜色置信度 ← 新增
            color, confidence = self.color_calc.calculate(
                chunk_data,
                independent_sources=1,
                has_conflict=False
            )
            chunk_data["color"] = color.value
            chunk_data["confidence"] = confidence
            evidence_chunks.append(chunk_data)
```

---

### 2.3 CLI 渲染修改

**文件**: `spine_cli/main.py`

**核心改动**:
```python
from backend.app.services.intelligence.court.color_confidence import (
    COLOR_ICONS,
    COLOR_LABELS,
    ConfidenceColor,
)

@app.command()
def ask(query: str, ...):
    # ... 原有逻辑
    if len(results) > 1:
        table = Table(...)
        table.add_column("颜色", style="dim")  # ← 新增列
        table.add_column("来源", style="dim")
        table.add_column("页码", justify="center")
        table.add_column("事实描述", style="white")
        for r in results[1:8]:
            color = r.get('color', 'YELLOW')
            confidence = r.get('confidence', 0.0)
            color_icon = COLOR_ICONS.get(ConfidenceColor(color), '🟡')
            table.add_row(
                f"{color_icon} {confidence:.2f}",  # ← 渲染颜色和置信度
                r['breadcrumb'],
                str(r['page_number']),
                r['text'][:80] + "..."
            )
```

---

## 3. 证据流转全景

```
用户提问
    ↓
Scout 拆解查询
    ↓
Collector 并行取证
    ├── 本地证人 → PyramidHarvester → Examiner → _load_chunks → color_calc.calculate() → 颜色字段
    └── 联网证人 → Tavily API → _search_single → color_calc.calculate() → 颜色字段
    ↓
Moderator 裁决（使用证据分片）
    ↓
判决书 + 证据链
    ↓
CLI 渲染 → 显示颜色图标 + 置信度数值
```

---

## 4. 颜色渲染示例

**CLI 输出示例**:
```
┌─ 🔍 逻辑溯源证据链 (Atomic Claims) ──────────────────────┐
│ 颜色       来源           页码   事实描述                │
├─────────────────────────────────────────────────────────┤
│ 🟢 0.87   第 3 章 密码学   P75   AES 被视为对称加密的黄金标准... │
│ 🟡 0.42   互联网证人      P0    对称加密算法包括 AES、DES... │
│ 🔵 0.58   第 5 章 公钥 PKI P120  RSA 算法基于大数分解难题...  │
└─────────────────────────────────────────────────────────┘
```

---

## 5. 测试结果

### 5.1 模块导入测试
```bash
✅ InternetWitness 导入成功
✅ Collector 导入成功
✅ 颜色计算测试：🟢 GREEN (0.874)
```

### 5.2 配置加载测试
```bash
✅ 权威来源数：7
✅ 域名评分数：10
✅ 半衰期配置：{'TECH_NEWS': 30, 'RESEARCH': 180, 'FACTUAL': 730}
✅ 颜色阈值：{'GREEN': 0.65, 'BLUE': 0.45, 'YELLOW': 0.25}
```

---

## 6. 下一步行动

### P0: 待完成

- [ ] **本地证据统一置信度**：当前本地证据只使用了 `ColorConfidenceCalculator`，应改用 `UnifiedConfidenceCalculator` 来整合联网证据进行覆盖判断
- [ ] **Moderator 集成冲突检测**：当检测到证据颜色为 RED 时，自动触发冲突解决流程
- [ ] **颜色阈值热重载**：修改 `backend/storage/confidence_config.json` 后无需重启即可生效

### P1: 优化

- [ ] **多源印证加成**：当本地 + 联网证据指向同一结论时，应触发跨源印证加成
- [ ] **置信度传播**：判决书的整体置信度应基于引用证据的颜色分布计算
- [ ] **Web 界面渲染**：前端页面需要实现颜色渲染（GREEN 用绿色 badge，RED 用红色 badge）

---

## 7. 技术细节

### 7.1 为什么不在 Moderator 中计算颜色？

**理由**：
1. **职责分离**：Moderator 负责裁决冲突，不应负责置信度计算
2. **性能优化**：证据分片在 Collector 阶段已计算好颜色，Moderator 直接使用即可
3. **可测试性**：颜色计算独立于裁决逻辑，便于单元测试

### 7.2 颜色计算时机

| 证据类型 | 计算时机 | 触发点 |
|----------|----------|--------|
| 本地 PDF | `_load_chunks` 加载分片后 | 从数据库读取内容后 |
| 联网证据 | `_search_single` 返回结果后 | Tavily API 调用成功后 |

---

**记录人**: Claude Code (Karpathy 模式)  
**最后更新**: 2026-04-15
