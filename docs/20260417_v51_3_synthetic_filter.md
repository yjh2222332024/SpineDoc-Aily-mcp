# 🚀 [V51.3] 修复 "synthetic" 关键词污染

**日期**: 2026-04-17  
**状态**: ✅ 完成

---

## 问题发现

联邦法庭查询 "武汉大学国家网络安全学院推免规则" 时，返回的答案完全无关：

```
所有六个星系的证据材料，内容均与原始问题无关。具体表现为：
* Galaxy_Training_Rephrasing：LLM 训练数据增强
* Galaxy_Gfm：学术论文伦理声明
* Galaxy_信息安全_概论：密码学原理
...
```

但数据库中明明有 `tuimian.pdf` 和 `tuimian2.pdf` 两个推免文档！

---

## 根因分析

### 1. 文档未关联星系

```
📄 tuimian.pdf [⚠️ 未关联任何星系]
📄 tuimian2.pdf [⚠️ 未关联任何星系]
```

推免文档入库时，TOC 扫描失败，只有一个 Synthetic 标题：
```
TOC 项数：1
   - P5: [Synthetic] 推免工作实施细则总则 (L-2)
```

### 2. 关键词提取被 "synthetic" 污染

GalaxyScout 提取文档指纹时，第一个关键词是 "synthetic"：
```
关键词：['synthetic', 'synthetic 推免', '工作 实施细则', ...]
```

导致：
- 创建的星系是 `Galaxy_Synthetic`，而不是 `Galaxy_推免`
- Thesaurus Map 没有推免相关的 cluster

### 3. Distributor 无法找到相关星系

查询 "武汉大学国家网络安全学院推免规则" 时：
- Thesaurus 匹配不到 "推免" 相关的 cluster
- 走兜底逻辑：返回所有 cluster
- Distributor 按 member_count 排序，传唤了无关星系

---

## 修复方案

### 修复 1: GalaxyScout 过滤 "synthetic"

**文件**: `backend/app/services/intelligence/galaxy/scout.py`

```python
# 🚀 [V51.3] 过滤 "synthetic" 污染词（TOC 扫描失败时的兜底标记）
fingerprints = [kw for kw in fingerprints 
                if kw.lower() != "synthetic" and "synthetic" not in kw.lower()]
```

### 修复 2: 重新对齐星系

运行 `scripts/realign_real_galaxies.py`：
- 清空所有星系关联
- 为每篇文档重新投影到星系

**结果**：
```
🚀 投影文档：tuimian.pdf...
   ↳ 已归入星系：['Galaxy_实施细则', 'Galaxy_工作', 'Galaxy_工作_实施细则']

🚀 投影文档：tuimian2.pdf...
   ↳ 已归入星系：['Galaxy_推荐', 'Galaxy_概述', 'Galaxy_推荐_免试']
```

### 修复 3: 重建 Thesaurus Map

运行 `scripts/generate_thesaurus_map.py`：

**推免相关 cluster**：
```
cluster_4 (3 个星系): ['工作', '实施细则']
   - Galaxy_实施细则
   - Galaxy_工作
   - Galaxy_工作_实施细则

cluster_5 (2 个星系): ['推荐', '免试']
   - Galaxy_推荐
   - Galaxy_推荐_免试
```

---

## 验证结果

### 测试：Distributor 传唤推免文档

```
查询："武汉大学国家网络安全学院推免规则"

传唤到的证人文档:
  - Galaxy_工作_实施细则：619eab29 (tuimian.pdf)  ✅
  - Galaxy_推荐_免试：bb2ddb6a (tuimian2.pdf)  ✅
  ...
```

### 对比：修复前后

| 阶段 | 修复前 | 修复后 |
|------|--------|--------|
| 文档关键词 | `['synthetic', ...]` | `['工作 实施细则', '推免', ...]` |
| 关联星系 | 0 个 | 3-5 个 |
| Thesaurus cluster | 无推免相关 | cluster_4/5 |
| Distributor 传唤 | ❌ 未传唤 | ✅ 正确传唤 |

---

## 遗留问题

### 1. TOC 扫描失败

推免文档的 TOC 只有 1 项，且是 Synthetic 标题：
```
is_scanned: False (tuimian.pdf)
is_scanned: True, processed_pages: 0 (tuimian2.pdf)
```

**建议**：运行 OCR 扫描，获取完整目录结构。

### 2. 星系过于细碎

推免文档被分配到 5 个星系，而不是 1 个聚合的 "推免" 星系：
- `Galaxy_实施细则`
- `Galaxy_工作`
- `Galaxy_工作_实施细则`
- `Galaxy_推荐`
- `Galaxy_推荐_免试`

**原因**：每篇文档创建 3 个锚点星系，导致星系数量爆炸。

**建议**：后续优化 GalaxyScout 的锚点合并逻辑。

---

## 关键教训

1. **兜底标记不能成为关键词**："synthetic" 是 TOC 失败的标记，必须过滤
2. **星系对齐是必需的**：文档入库后必须运行 `project_document_to_galaxies`
3. **Thesaurus Map 需要定期重建**：每次星系变更后应重新生成

---

**记录人**: Claude  
**审核**: 用户确认
