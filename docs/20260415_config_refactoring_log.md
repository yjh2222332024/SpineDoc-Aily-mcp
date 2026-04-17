# 📜 配置化重构日志 (2026-04-15)

**作者**: Karpathy (AI 顾问)  
**状态**: ✅ 完成
**主题**: 硬编码参数迁移到用户可配置文件

---

## 1. 核心洞察

### 洞察 1：配置与代码分离

> "Hard-coded parameters are technical debt waiting to happen."

**问题**：域名白名单、置信度阈值、半衰期等参数硬编码在 Python 文件中，用户无法自定义。

**解决**：所有用户可能需要调整的参数迁移到 `backend/storage/*.json`，代码只保留算法逻辑。

---

### 洞察 2：配置的层次结构

| 配置类型 | 存储位置 | 理由 |
|----------|----------|------|
| 域名列表/评分 | `backend/storage/*.json` | 用户需要频繁调整，数据量大 |
| 半衰期/阈值 | `backend/storage/confidence_config.json` | 领域适配需要调整 |
| 数学公式 | 代码中保留 | 算法逻辑，不应被配置改变 |

**关键设计**：配置加载器提供默认回退值，配置文件不存在时系统仍可运行。

---

## 2. 文件清单

### 2.1 新建配置文件

| 文件 | 行数 | 描述 |
|------|------|------|
| `backend/storage/domain_whitelist.json` | ~25 | 权威来源列表 + 域名稳定性 |
| `backend/storage/domain_scores.json` | ~30 | 域名基础权威分 |
| `backend/storage/domain_stats.json` | ~100 | 域名详细统计（h5-index, Alexa） |
| `backend/storage/confidence_config.json` | ~20 | 半衰期、颜色阈值、覆盖条件 |

### 2.2 新建代码文件

| 文件 | 行数 | 描述 |
|------|------|------|
| `backend/app/services/intelligence/court/config_loader.py` | ~180 | 配置加载器（单例模式） |

### 2.3 修改代码文件

| 文件 | 修改内容 |
|------|----------|
| `color_confidence.py` | 移除硬编码字典，改用 `_load_*()` 函数从配置加载 |
| `unified_confidence.py` | 移除硬编码列表，`LocalEvidenceIntegrityChecker` 从配置加载参数 |

---

## 3. 配置加载器设计

### 3.1 API 设计

```python
from .config_loader import get_config_loader, reload_config

loader = get_config_loader()

# 获取配置项
loader.get_authoritative_sources()      # List[str]
loader.get_domain_stability()           # Dict[str, float]
loader.get_domain_base_scores()         # Dict[str, float]
loader.get_domain_stats()               # Dict[str, DomainStats]
loader.get_query_half_life()            # Dict[str, int]
loader.get_color_percentiles()          # Dict[str, float]
loader.get_override_conditions()        # Dict[str, Any]
loader.get_min_authoritative_sources()  # int
loader.get_integrity_penalty()          # float

# 热重载（用于 Web 管理界面）
reload_config()
```

### 3.2 默认回退策略

```python
DEFAULT_DOMAIN_WHITELIST = {
    "authoritative_sources": ["arxiv.org", "ieee.org", ...],
    "domain_stability": {"arxiv.org": 0.95, ...}
}

def _load_json(self, filename: str, default: Dict) -> Dict:
    filepath = self.storage_path / filename
    if not filepath.exists():
        return default  # 文件不存在时返回默认值
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except:
        return default  # 解析失败时返回默认值
```

---

## 4. 配置示例

### 4.1 添加自定义域名

编辑 `backend/storage/domain_whitelist.json`：

```json
{
  "authoritative_sources": [
    "arxiv.org",
    "ieee.org",
    "your-custom-domain.com"  // ← 添加自定义权威域名
  ],
  "domain_stability": {
    "your-custom-domain.com": 0.80  // ← 添加稳定性评分
  }
}
```

编辑 `backend/storage/domain_scores.json`：

```json
{
  "domain_base_scores": {
    "your-custom-domain.com": 0.75  // ← 添加权威分
  }
}
```

### 4.2 调整半衰期（适配特定领域）

编辑 `backend/storage/confidence_config.json`：

```json
{
  "query_half_life": {
    "TECH_NEWS": 30,       // 科技新闻：30 天
    "RESEARCH": 180,       // 学术研究：6 个月
    "FACTUAL": 730,        // 经典理论：2 年
    "MEDICAL_NEWS": 7,     // ← 医疗新闻：7 天（快速变化）
    "LEGAL": 3650          // ← 法律条文：10 年（极稳定）
  }
}
```

### 4.3 调整颜色阈值（更严格/更宽松）

编辑 `backend/storage/confidence_config.json`：

```json
{
  "color_percentiles": {
    "GREEN": 0.65,   // 调高到 0.75 更严格，调低到 0.55 更宽松
    "BLUE": 0.45,
    "YELLOW": 0.25
  }
}
```

### 4.4 调整覆盖条件（更严苛/更宽松）

编辑 `backend/storage/confidence_config.json`：

```json
{
  "override_conditions": {
    "min_authoritative_sources": 2,  // 调高到 3 更严苛，调低到 1 更宽松
    "integrity_penalty": 0.5         // 被推翻时的置信度惩罚（0.5=减半）
  }
}
```

---

## 5. 测试结果

### 5.1 配置加载测试

```python
from backend.app.services.intelligence.court.config_loader import ConfidenceConfigLoader

loader = ConfidenceConfigLoader()

# 测试配置文件加载
assert len(loader.get_authoritative_sources()) >= 7  # 默认权威来源
assert 'arxiv.org' in loader.get_domain_base_scores()
assert loader.get_query_half_life()['RESEARCH'] == 180

# 测试缺失文件回退
# （临时重命名配置文件）
loader2 = ConfidenceConfigLoader(storage_path="/nonexistent/path")
assert len(loader2.get_authoritative_sources()) == 7  # 默认值
```

### 5.2 模块导入测试

```bash
cd /e/study/code/spine-close/Spine-close
.venv/Scripts/python -c "
from backend.app.services.intelligence.court.color_confidence import ColorConfidenceCalculator
from backend.app.services.intelligence.court.unified_confidence import UnifiedConfidenceCalculator
print('✅ 配置化重构后模块导入成功')
"
```

---

## 6. 迁移指南

### 6.1 从旧版本升级

如果你之前修改过硬编码的域名列表，需要手动迁移：

**旧代码**（`color_confidence.py` 第 39-71 行）:
```python
DOMAIN_STATS = {
    'arxiv.org': DomainStats(h5_index=350, peer_reviewed=True),
    # ... 其他域名
}
```

**新配置**（`backend/storage/domain_stats.json`）:
```json
{
  "domain_stats": {
    "arxiv.org": {"h5_index": 350, "peer_reviewed": true}
  }
}
```

### 6.2 配置文件位置

配置文件必须位于 `backend/storage/` 目录：

```
backend/
├── storage/
│   ├── domain_whitelist.json    ← 必须
│   ├── domain_scores.json       ← 必须
│   ├── domain_stats.json        ← 必须
│   └── confidence_config.json   ← 必须
├── app/
│   └── services/
│       └── intelligence/
│           └── court/
│               ├── config_loader.py
│               ├── color_confidence.py
│               └── unified_confidence.py
```

如果配置文件缺失，系统会使用内置默认值。

---

## 7. 下一步行动

### P0: 主逻辑集成

- [ ] 修改 `InternetWitness` 使用配置化的域名白名单
- [ ] 修改 `Moderator` 使用配置化的颜色阈值
- [ ] 修改 `Collector` 使用配置化的半衰期

### P1: Web 管理界面

- [ ] 配置管理页面（查看/编辑 JSON）
- [ ] 热重载 API 端点 `POST /config/reload`
- [ ] 配置变更日志（记录用户修改历史）

### P2: 配置验证

- [ ] JSON Schema 验证（防止无效配置）
- [ ] 配置冲突检测（例如 GREEN 阈值 < BLUE 阈值）
- [ ] 配置导入/导出功能

---

## 8. 技术细节

### 8.1 为什么不使用环境变量？

| 方案 | 优点 | 缺点 | 选择理由 |
|------|------|------|----------|
| 环境变量 | 适合密钥、简单开关 | 不适合复杂数据结构（嵌套字典） | 保留给密钥（如 TAVILY_API_KEY） |
| JSON 文件 | 结构清晰、易编辑、支持注释 | 需要文件 I/O | ✅ 选择用于复杂配置 |
| YAML 文件 | 支持注释、更简洁 | 需要额外依赖、解析慢 | ❌ 不选 |
| 数据库 | 支持热更新、权限控制 | 过度设计、增加复杂度 | ❌ 不选 |

### 8.2 为什么使用单例模式？

```python
_global_loader: Optional[ConfidenceConfigLoader] = None

def get_config_loader() -> ConfidenceConfigLoader:
    global _global_loader
    if _global_loader is None:
        _global_loader = ConfidenceConfigLoader()
    return _global_loader
```

**理由**：
1. 避免重复加载配置文件（性能优化）
2. 全局状态一致（防止不同模块加载不同配置）
3. 支持热重载（通过 `reload_config()`）

---

**记录人**: Claude Code (Karpathy 模式)  
**最后更新**: 2026-04-15
