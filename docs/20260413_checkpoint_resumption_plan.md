# 🏛️ SpineDoc 断点续传与高效收割重构日志 - 2026/04/13

## 1. 核心目标：实现生产级“存档点”机制 (Checkpointing)
- **背景：** 406 页长文档处理耗时长，且极易受网络、显存或进程中断影响。
- **痛点：** 目前中断后需从 P1 重新 OCR，造成严重的算力资源浪费。

## 2. 断点续传设计 (V50.0 Resumption)

### 2.1 磁盘缓存确权 (OCR Level)
- **方案：** 强化 `.ocr_cache.json` 的“真理源”地位。
- **动作：** `BodyAlchemist` 在生成任务队列前，强制比对物理磁盘缓存。已存在的 Page 直接从生产队列中物理剔除。

### 2.2 数据库幂等写入 (DB Level)
- **方案：** 利用 `Document.processed_pages` 追踪物理进度。
- **逻辑：** 引擎启动时检查已存在的 Chunks。若 `force=False` 且存在同哈希文档，自动识别空洞页码并进行增量补全。

### 2.3 资源极致回收 (Zero-Leak)
- **方案：** 引入“50页阈值”强力清理。
- **动作：** 在 OCR 消费者与分片器之间插入硬性的显存/内存回收点，确保长周期运行下系统压力呈锯齿状平稳分布，而非直线爬升。

## 3. 实现优先级
1. **[Urgent]** `BodyAlchemist` 磁盘缓存过滤逻辑注入。
2. **[High]** `SpineEngine` 增量模式逻辑开关。
3. **[Med]** 进度持久化与 `processed_pages` 实时更新。

---
**Plan Certified by:** Uncle Bob (Clean Architecture Group)
