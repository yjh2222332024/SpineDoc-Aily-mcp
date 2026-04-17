# 🛡️ LLM 预检与联网降级实现日志 (2026-04-15)

**版本**: V50.6  
**状态**: ✅ 完成  
**测试**: 全部通过  

---

## 1. 需求背景

用户明确指出：
1. **LLM 配置错误不能静默降级** —— 必须直接返回明确错误信息并结束流程
2. **联网搜索失败要优雅降级** —— sleep 3s + 明确日志 + 降级为无联网模式
3. **TOC 不可能没有** —— TOC 是文档入库时就必须有的，不是可选降级

---

## 2. 实现方案

### 2.1 LLM 配置预检 (LLM Probe)

**设计原则**: 在调用 LLM 之前先发送一个轻量级探测请求，验证配置是否可用。

**实现位置**: `backend/app/services/intelligence/court/federated_court.py::FederatedCourt._probe_llm()`

**核心逻辑**:
```python
async def _probe_llm(self) -> Optional[str]:
    """🚀 [V50.6] 轻量级 LLM 可用性探测"""
    from backend.app.core.config import settings
    from openai import AsyncOpenAI

    # 1. 检查配置是否存在
    if not settings.LLM_API_KEY:
        return "LLM_API_KEY 未配置，请在 .env 文件中设置"
    if not settings.LLM_BASE_URL:
        return "LLM_BASE_URL 未配置，请在 .env 文件中设置"

    # 2. 发送一个轻量级探测请求 (10s 超时)
    try:
        client = AsyncOpenAI(...)
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": "OK"}],
                max_tokens=5
            ),
            timeout=10.0
        )
        return None  # LLM 可用
    except asyncio.TimeoutError:
        return "LLM 探测请求超时 (10s)，请检查 API_ENDPOINT 是否可达"
    except Exception as e:
        return f"LLM 探测请求失败：{e}"
```

**调用时机**: `FederatedCourt.hear()` 入口处

**错误返回格式**:
```json
{
  "final_answer": "❌ LLM 服务不可用：LLM_API_KEY 未配置，请在 .env 文件中设置",
  "confidence": 0.0,
  "cited_galaxies": [],
  "reasoning": "LLM 配置验证失败"
}
```

---

### 2.2 联网降级 (Internet Fallback)

**设计原则**: 联网失败时明确告知用户，sleep 3s 后降级为无联网模式。

**实现位置**: `backend/app/services/intelligence/court/collector.py::Collector.collect_evidence()`

**核心逻辑**:
```python
if enable_online:
    print("🌐 [Collector] 正在传唤联网证人...")
    try:
        internet_result = await self.internet_witness.summon(scout_queries)

        # 检查联网结果是否有效
        if internet_result.get("error") or not internet_result.get("evidence_chunks"):
            print(f"⚠️ [Collector] 联网证人返回空结果或错误")
            raise Exception("联网检索无有效结果")

        all_tasks = local_tasks + [internet_result]
        print("✅ [Collector] 联网证人取证成功")
    except Exception as e:
        # 🚀 [V50.6] 联网失败降级：sleep 3s + 明确日志 + 降级为无联网模式
        print(f"⚠️ [Collector] 联网证人取证失败：{e}")
        print(f"💤 [Collector] 联网服务不可用，休眠 {settings.TAVILY_FALLBACK_SLEEP_SECONDS}s 后降级为无联网模式...")
        await asyncio.sleep(settings.TAVILY_FALLBACK_SLEEP_SECONDS)
        print("🔌 [Collector] 已降级为无联网模式，继续本地取证...")
        all_tasks = local_tasks
else:
    all_tasks = local_tasks
```

**日志输出格式**:
```
🌐 [Collector] 正在传唤联网证人...
⚠️ [Collector] 联网证人返回空结果或错误
⚠️ [Collector] 联网证人取证失败：联网检索无有效结果
💤 [Collector] 联网服务不可用，休眠 3s 后降级为无联网模式...
🔌 [Collector] 已降级为无联网模式，继续本地取证...
```

---

### 2.3 InternetWitness 错误返回

**实现位置**: `backend/app/services/intelligence/court/internet_witness.py::InternetWitness.summon()`

**核心逻辑**:
```python
# 🚀 [V50.6] 如果所有查询都失败，返回错误包
if not all_chunks:
    error_msg = "所有联网查询均失败：" + "; ".join(errors) if errors else "联网检索无结果"
    print(f"❌ [InternetWitness] {error_msg}")
    return self._empty_package(error=error_msg)
```

---

### 2.4 配置项新增

**实现位置**: `backend/app/core/config.py`

```python
# --- 🚀 [V49.0] 联网证人配置 (Tavily) ---
TAVILY_API_KEY: Optional[str] = None
TAVILY_MAX_RESULTS: int = 3
TAVILY_SEARCH_DEPTH: str = "advanced"
TAVILY_CONCURRENT_LIMIT: int = 5
TAVILY_FALLBACK_SLEEP_SECONDS: int = 3  # 🚀 [V50.6] 联网失败后休眠秒数
```

---

## 3. 测试验证

### 测试 1: LLM API Key 未配置
```bash
$ python tests/debug_tools/test_llm_probe_and_fallback.py
```
**输出**:
```
❌ [FederatedCourt] LLM 不可用：LLM_API_KEY 未配置，请在 .env 文件中设置
Verdict: {'final_answer': '❌ LLM 服务不可用：LLM_API_KEY 未配置，请在 .env 文件中设置', ...}
✅ 测试 1 通过
```

### 测试 2: 联网证人返回错误信息
**输出**:
```
Result: {'error': 'Tavily API 未配置或不可用'}
✅ 联网证人返回了错误信息
```

### 测试 3: Collector 联网降级完整流程 (含 sleep 3s)
**输出**:
```
⚠️ [Collector] 联网证人取证失败：联网检索无有效结果
💤 [Collector] 联网服务不可用，休眠 3s 后降级为无联网模式...
🔌 [Collector] 已降级为无联网模式，继续本地取证...
耗时：6.43s
✅ 降级逻辑工作正常
```

---

## 4. 文件变更清单

| 文件 | 变更内容 |
|------|----------|
| `backend/app/core/config.py` | 新增 `TAVILY_FALLBACK_SLEEP_SECONDS` |
| `backend/app/services/intelligence/court/federated_court.py` | 新增 `_probe_llm()` 方法，入口验证 |
| `backend/app/services/intelligence/court/collector.py` | 联网失败降级逻辑（sleep 3s） |
| `backend/app/services/intelligence/court/internet_witness.py` | 错误包返回逻辑 |
| `tests/debug_tools/test_llm_probe_and_fallback.py` | 新增测试脚本 |

---

## 5. 用户体验改进

### 之前:
- LLM 配置错误 → 调用时崩溃，错误信息不明确
- 联网失败 → 直接跳过，用户不知道发生了什么

### 现在:
- LLM 配置错误 → **立即返回明确错误**："LLM_API_KEY 未配置，请在 .env 文件中设置"
- 联网失败 → **明确日志 + sleep 3s + 降级**：
  - 用户看到明确的错误原因
  - 系统休眠 3s 后自动降级为无联网模式
  - 本地取证继续进行

---

## 6. 下一步建议

### P1: CLI 渲染优化
在 `spine_cli/main.py` 中渲染错误消息时，使用醒目的颜色：
```python
if result["text"].startswith("❌"):
    print(f"[bold red]{result['text']}[/bold red]")
```

### P2: 错误码规范
定义错误码枚举，便于前端/CLI 处理：
```python
class ErrorCode(Enum):
    LLM_API_KEY_MISSING = "LLM_001"
    LLM_TIMEOUT = "LLM_002"
    TAVILY_API_MISSING = "TAVILY_001"
    TAVILY_SEARCH_FAILED = "TAVILY_002"
```

### P3: 重试逻辑
联网失败前可以尝试重试 1-2 次：
```python
for retry in range(2):
    try:
        result = await witness.summon(...)
        break
    except Exception as e:
        if retry == 1:
            raise  # 最后一次重试失败，降级
```

---

**记录人**: Claude Code  
**日期**: 2026-04-15  
**状态**: ✅ 实现完成，测试通过
