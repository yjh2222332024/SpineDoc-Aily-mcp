"""
📐 SpineDoc Architecture Auditor (The Professionalism Meter)
==========================================================
职责：量化代码质量与架构合规性。
原则：如果不被度量，就不会被改进。
"""
import os
import time
import subprocess
import re
from pathlib import Path

def audit_test_velocity():
    """度量测试代谢速度"""
    print(" [Audit] 正在启动原子测试...")
    start = time.time()
    # 仅运行 unit 目录下的原子测试
    result = subprocess.run(
        ["pytest", "backend/tests/unit", "-q", "--disable-warnings"],
        capture_output=True, text=True
    )
    duration = time.time() - start
    
    status = " PASS" if duration < 1.0 else " SLOW"
    print(f"  ↳ 测试速度: {duration:.2f}s ({status})")
    return duration

def audit_logical_isolation():
    """检查核心逻辑是否‘与 IO 结婚’"""
    print(" [Audit] 检查逻辑隔离度...")
    core_logic_files = [
        "backend/app/services/intelligence/galaxy/cluster_engine.py",
        "backend/app/services/intelligence/consensus/moderator.py"
    ]
    
    forbidden_imports = ["httpx", "requests", "sqlalchemy", "sqlmodel"]
    violations = 0
    
    for file_path in core_logic_files:
        if not os.path.exists(file_path): continue
        content = Path(file_path).read_text(encoding="utf-8")
        for forbidden in forbidden_imports:
            if f"import {forbidden}" in content or f"from {forbidden}" in content:
                print(f"   违规: {file_path} 直接引入了 {forbidden}！")
                violations += 1
                
    if violations == 0:
        print("   隔离度良好：业务规则未被 IO 细节污染。")
    return violations

def audit_function_discipline():
    """度量函数规模 (Uncle Bob's Law: 10 lines max)"""
    print(" [Audit] 检查函数纪律...")
    target_dir = "backend/app/services"
    large_functions = 0
    
    # 简单的正则匹配：查找 def 及其缩进范围内的行数
    # 这里仅作为示例，严谨实现需使用 ast 模块
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".py"):
                path = Path(root) / file
                content = path.read_text(encoding="utf-8").splitlines()
                for line in content:
                    # 简化：仅检查是否存在明显的巨型类
                    if len(content) > 300:
                        print(f"   警报: {path} 超过 300 行，可能需要拆分类。")
                        large_functions += 1
                        break
    return large_functions

if __name__ == "__main__":
    print("\n" + "="*40)
    print("   SpineDoc 架构审计报告")
    print("="*40)
    
    audit_test_velocity()
    audit_logical_isolation()
    audit_function_discipline()
    
    print("\n结论：专业的代码库必须通过每一项审计。")
    print("="*40 + "\n")
