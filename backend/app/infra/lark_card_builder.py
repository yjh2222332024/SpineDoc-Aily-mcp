
"""
📇 Lark Card Builder - 飞书互动卡片构建器
========================================
职责：将逻辑审计结果转化为符合飞书 2026 规范的交互式卡片 JSON。
"""

import json
from typing import Dict, Any, List

class LarkCardBuilder:
    def __init__(self):
        # 映射置信度到飞书内置主题
        self.color_map = {
            "GREEN": "green",
            "YELLOW": "yellow",
            "RED": "red",
            "BLUE": "blue"
        }

    def _get_template(self, color: str) -> str:
        return self.color_map.get(color.upper(), "grey")

    def build_retrieval_timeline(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建检索过程时间线（法庭日志），注入卡片顶部展示 5 阶段执行状态。
        """
        phase_blocks = []

        def phase(label: str, status: str, detail: str = "") -> Dict[str, str]:
            icon = {"done": "🟢", "warn": "🟡", "fail": "🔴", "skip": "⚪"}.get(status, "⚪")
            return {
                "label": label,
                "icon": icon,
                "detail": detail,
            }

        p1 = phase("Phase 1: 查询路由", "done", f"找到 {meta.get('phase1_source_count', 0)} 个相关来源")
        p2 = phase("Phase 2: 证据采集", "done", f"锁定 {meta.get('phase2_chunk_count', 0)} 个核心分片")

        conflict = meta.get("phase3_conflict_count", 0)
        if conflict > 0:
            p3 = phase("Phase 3: 冲突裁决", "warn", f"发现 {conflict} 处冲突，已裁决")
        else:
            p3 = phase("Phase 3: 冲突裁决", "done", "无冲突")

        rel = meta.get("phase4_relationship_count", 0)
        p4 = phase("Phase 4: 图谱织网", "done" if rel else "skip", f"新增 {rel} 条逻辑关联")

        conf = meta.get("confidence", 0.0)
        color = meta.get("color", "YELLOW")
        color_icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴", "BLUE": "🔵"}.get(color, "⚪")
        p5 = phase("Phase 5: 答案生成", "done", f"置信度 {conf:.0%} {color_icon}")

        for p in [p1, p2, p3, p4, p5]:
            phase_blocks.append({
                "tag": "div",
                "text": {
                    "content": f"{p['icon']} **{p['label']}** {p['detail']}",
                    "tag": "lark_md"
                }
            })

        return {
            "tag": "column_set",
            "flex_mode": "right_nb",
            "background_style": "grey",  # 灰色底区分时间线区域
            "columns": [
                {"tag": "column", "width": "stretch", "elements": phase_blocks}
            ]
        }

    def build_result_card(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """构建检索结果卡片"""
        text = result.get("text", result.get("final_answer", "无结论"))
        confidence = result.get("result_metadata", {}).get("confidence",
            result.get("confidence", 0.0))
        color = result.get("color", "YELLOW")
        cited_sources = result.get("result_metadata", {}).get("cited_sources", [])

        # Build timeline if phase_meta available
        timeline_meta = result.get("result_metadata", {}).get("_phase_meta", {})
        elements = []
        if timeline_meta:
            timeline_block = self.build_retrieval_timeline(timeline_meta)
            elements.append(timeline_block)
            elements.append({"tag": "hr"})

        # Main result text
        elements.append({
            "tag": "div",
            "text": {
                "content": f"**检索结论**：\n{text}",
                "tag": "lark_md"
            }
        })
        elements.append({"tag": "hr"})

        # Confidence columns
        elements.append({
            "tag": "column_set",
            "flex_mode": "stretch",
            "background_style": "default",
            "columns": [
                {
                    "tag": "column", "width": "weighted", "weight": 1,
                    "elements": [{"tag": "div", "text": {"content": f"🎯 **置信度**: `{confidence:.2f}`", "tag": "lark_md"}}]
                },
                {
                    "tag": "column", "width": "weighted", "weight": 1,
                    "elements": [{"tag": "div", "text": {"content": f"📚 **涉及来源**: {len(cited_sources)} 个", "tag": "lark_md"}}]
                }
            ]
        })
        elements.append({"tag": "hr"})

        # Conflict visualization
        resolved_conflicts = result.get("result_metadata", {}).get("resolved_conflicts", [])
        if resolved_conflicts:
            elements.append({
                "tag": "div",
                "text": {"content": f"⚠️ **检测到 {len(resolved_conflicts)} 处知识冲突**", "tag": "lark_md"}
            })
            for c in resolved_conflicts:
                res = c.get("resolution", {})
                elements.append({
                    "tag": "div", "fields": [{
                        "is_short": False,
                        "text": {"tag": "lark_md",
                            "content": f"**{c.get('description', '冲突')}** → 裁决: {res.get('decision')} | 理由: {res.get('reasoning', '')[:80]}"}
                    }]
                })

        # Action buttons
        elements.append({
            "tag": "action",
            "actions": [
                {"tag": "button", "text": {"content": "🔍 查看逻辑演变历史 (Git Diff)", "tag": "plain_text"}, "type": "primary",
                 "value": {"action": "view_diff", "chunk_id": result.get("id", "unknown")}},
                {"tag": "button", "text": {"content": "📊 追溯 Bitable 资产", "tag": "plain_text"}, "type": "default",
                 "multi_url": {"url": "https://www.feishu.cn/base/XbXwbaFh7aNrNjsL80TcSozNnEh", "pc_url": "", "android_url": "", "ios_url": ""}}
            ]
        })

        # Footer
        elements.append({
            "tag": "note",
            "elements": [{"tag": "plain_text", "content": "💡 本结果由 SpineDoc 检索引擎自动生成，不代表法律建议。"}]
        })

        card = {
            "config": {"wide_screen_mode": True, "enable_forward": True},
            "header": {"template": self._get_template(color), "title": {"content": "🔍 SpineDoc 检索分析报告", "tag": "plain_text"}},
            "elements": elements
        }
        return card

    def build_evolution_card(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建知识进化提醒卡片"""
        count = log_data.get("evolution_count", 0)
        details = log_data.get("details", [])
        
        detail_md = "\n".join([f"- **{d['type']}**: {d['reason']}" for d in details])
        
        card = {
            "header": {
                "template": "blue",
                "title": {
                    "content": "🧬 逻辑知识库已自动进化",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"系统在导入过程中发现了 **{count}** 处逻辑关联，已自动完成织网：\n\n{detail_md}",
                        "tag": "lark_md"
                    }
                }
            ]
        }
        return card
