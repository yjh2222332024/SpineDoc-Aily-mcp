# 🧪 SpineDoc 测试与量化评估指南 (V1.0.0)

SpineDoc 坚持“验证是唯一终点”的工程准则。本项目包含三级严密的测试体系。

## 1. 组件原子化测试 (Unit/Atomic)
**目的**：确保每个逻辑节点（ Witness, Moderator, Integrator 等）的功能正确。

```bash
# 设置路径并运行
$env:PYTHONPATH="."
python tests/atomic_runner.py
```
**关注指标**：
- 解析器鲁棒性 (Witness Regex)
- 物理原点中值校准精度 (LogicAligner)
- 冲突嗅探漏报率 (Moderator)

## 2. 性能基准测试 (Performance Baseline)
**目的**：测量单用户在真实负载（17+ 文档）下的全链路闭环耗时。

```bash
python evaluation/baseline_test.py
```
**关注指标**：
- **Avg Latency**: 全流程耗时（目标 < 30s）。
- **Radar Filter Rate**: 星系雷达的文档剔除效率（目标 > 70%）。

## 3. 精度透析测试 (Precision Audit)
**目的**：针对特定复杂文档，透析检索证据链与大法官判决的真实质量。

```bash
python scripts/test_rag_precision.py
```
**关注指标**：
- **PCD (Physical Coordinate Delta)**: 物理页码绝对误差（目标 ≤ 0.5页）。
- **ACD (Atomic Claim Density)**: 判决书事实干货密度。

## 4. 边界审计 (Robustness)
**目的**：在极端条件下（如超长 Query、空结果、高噪音）验证系统生存能力。

```bash
python evaluation/comprehensive_boundary_test.py
```
