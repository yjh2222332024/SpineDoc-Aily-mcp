# 🚀 OCR/TOC 解耦实现日志 (V50.8)

**日期**: 2026-04-15  
**状态**: ✅ 完成  

---

## 1. 设计原则

### 两个独立维度

| 维度 | 控制什么 | 用户参数 | 自动判断逻辑 |
|------|----------|----------|--------------|
| **TOC 来源** | 目录结构从哪来 | `--toc-range` | Outline → Emergent |
| **正文提取** | 切片内容从哪来 | `--ocr` | 扫描件 → OCR, 数字件 → 原生 |

---

## 2. 修改清单

### 2.1 `spine_engine.py`

#### 修改 1: `need_ocr` 判定逻辑解耦

**修改前**:
```python
need_ocr = force_ocr or (manual_toc_range is not None) or is_scanned or is_emergent
```

**修改后**:
```python
# 🚀 [V50.8] OCR/TOC 解耦：need_ocr 只由 force_ocr 或扫描件判定决定，与 TOC 来源无关
need_ocr = force_ocr or is_scanned
```

#### 修改 2: TOC 识别不再传入 `force_ocr`

**修改前**:
```python
enriched_toc = await hybrid_parser.extract_toc_async(
    str(p), manual_range=manual_toc_range, force_ocr=force_ocr
)
```

**修改后**:
```python
# TOC 识别不用 OCR
enriched_toc = await hybrid_parser.extract_toc_async(
    str(p), manual_range=manual_toc_range, force_ocr=False
)
```

#### 修改 3: 优化日志输出

**Emergent 模式**:
```python
if is_emergent:
    # --- [模式 C]：逻辑涌现模式 (无 TOC，从正文语义中酿造) ---
    if need_ocr:
        print(f"📸 [Pipeline] OCR 模式：正文将使用 OCR 提取 (含公式/图表)")
    else:
        print(f"📄 [Pipeline] 原生模式：正文将使用 PDF 原生文本")
```

**Guided 模式**:
```python
else:
    # --- [模式 A]：引导模式 (Outline 或 VLM 识别 TOC) ---
    if need_ocr:
        print(f"📸 [Pipeline] OCR 模式：正文将使用 OCR 提取 (含公式/图表)")
    else:
        print(f"📄 [Pipeline] 原生模式：正文将使用 PDF 原生文本")
```

---

### 2.2 `parser.py`

**修改**: VLM 失败日志优化

```python
except Exception as e:
    print(f"❌ [Parser] VLM 不可用：{e}")
    print(f"📚 [Parser] 降级为正文语义涌现模式（Emergent）")
    raw_toc = []
```

---

### 2.3 `ocr_process_utils.py`

**修改 1**: 添加 `vlm_failed` 标志（已存在）

**修改 2**: VLM 失败后直接返回 `None`

```python
if high_precision and self.vlm_worker and not self.vlm_failed:
    try:
        result = await self.vlm_worker.ocr_to_markdown(img_np)
        if not result:
            raise Exception("VLM return empty")
        return result
    except Exception as e:
        self.vlm_failed = True
        return None  # 直接返回 None，让上层进入 Emergent
```

---

## 3. 用户命令矩阵

| 场景 | 命令 | TOC 来源 | 正文提取 |
|------|------|----------|----------|
| 数字件快速处理 | `spine ingest paper.pdf` | Outline | 原生文本 |
| 扫描件自动处理 | `spine ingest scan.pdf` | Emergent | OCR |
| 提取公式（数字件） | `spine ingest paper.pdf --ocr` | Outline | **OCR** |
| 提取公式（扫描件） | `spine ingest scan.pdf --ocr` | Emergent | **OCR** |
| 指定目录页（扫描件） | `spine ingest scan.pdf --toc-range 1-5` | VLM | 原生文本 |
| 完全体 | `spine ingest scan.pdf --ocr --toc-range 1-5` | VLM | **OCR** |

---

## 4. 核心流程对比

### 修改前（错误的）

```
--ocr → 跳过 TOC 逻辑 → 直接暴力切片
```

### 修改后（正确的）

```
--ocr → 只影响正文提取方式
        ↓
        TOC 逻辑照常运行
        ↓
        Outline → Guided 模式 + OCR 正文
        Emergent → Emergent 模式 + OCR 正文
```

---

## 5. 测试验证

### 测试 1: 数字件 + Outline + 无 OCR
```bash
spine ingest paper.pdf
```
**预期**: 用 Outline TOC，PDF 原生文本

### 测试 2: 数字件 + Outline + OCR
```bash
spine ingest paper.pdf --ocr
```
**预期**: 用 Outline TOC，OCR 提取正文（含公式）

### 测试 3: 扫描件 + VLM TOC + OCR
```bash
spine ingest scan.pdf --toc-range 1-5 --ocr
```
**预期**: VLM 识别目录页，OCR 提取正文

### 测试 4: VLM 失败降级
```bash
spine ingest scan.pdf --toc-range 1-5
```
**预期**: VLM 失败 → Emergent 模式

---

## 6. 下一步

- [ ] CLI 参数说明文档更新
- [ ] 端到端测试验证
- [ ] 性能基准测试（OCR vs 原生）

---

**记录人**: Claude Code  
**状态**: ✅ 核心逻辑修改完成
