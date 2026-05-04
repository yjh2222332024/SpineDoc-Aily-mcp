"""
📇 Lark Card Builder - 飞书互动卡片构建器
========================================
职责：将逻辑审计结果转化为符合飞书 2026 规范的交互式卡片 JSON。
      合并自 AilyPresenter，消费 phase_log 渲染可视化时间线。
"""

import json
from typing import Dict, Any, List, Optional
from spine_interaction.cards.themes import FEISHU_THEME, COLOR_ICONS


class LarkCardBuilder:
    def __init__(self):
        self.color_map = FEISHU_THEME

    def _get_template(self, color: str) -> str:
        return self.color_map.get(color.upper(), "grey")

    def _status_icon(self, status: str) -> str:
        return {"done": "🟢", "dispatched": "🟡", "failed": "🔴", "skip": "⚪"}.get(status, "⚪")

    def build_phase_timeline(self, phase_log: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Render phase_log entries as a visual timeline column_set."""
        if not phase_log:
            return {"tag": "div", "text": {"tag": "lark_md", "content": "⚪ 无阶段记录"}}

        rows = []
        for entry in phase_log:
            step = entry.get("step", "?")
            status = entry.get("status", "done")
            duration = entry.get("duration_s", 0)
            detail = entry.get("detail", "")
            icon = self._status_icon(status)
            dur_str = f"{duration:.0f}s" if isinstance(duration, (int, float)) else str(duration)
            rows.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"{icon} **{step}**　{dur_str}　{detail}",
                }
            })

        return {
            "tag": "column_set",
            "flex_mode": "right_nb",
            "background_style": "grey",
            "columns": [
                {"tag": "column", "width": "stretch", "elements": rows}
            ]
        }

    def build_result_card(self, result: Dict[str, Any],
                          query: Optional[str] = None,
                          evidence_trace: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """构建检索结果卡片 - 合并 AilyPresenter 功能，消费 phase_log 渲染时间线。"""
        text = result.get("text", result.get("final_answer", "无结论"))
        confidence = (result.get("result_metadata", {}) or {}).get("confidence",
                     result.get("confidence", 0.0))
        color = result.get("color", "YELLOW")
        cited_sources = (result.get("result_metadata", {}) or {}).get("cited_sources", [])
        phase_log = result.get("phase_log", [])

        elements = []

        # 1. 查询回顾 (from AilyPresenter)
        if query:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**🔍 查询：** {query}"}
            })
            elements.append({"tag": "hr"})

        # 2. 执行时间线 (from phase_log)
        if phase_log:
            timeline_block = self.build_phase_timeline(phase_log)
            elements.append(timeline_block)
            elements.append({"tag": "hr"})

        # 3. 结论正文
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**判决书：**\n{text}"}
        })
        elements.append({"tag": "hr"})

        # 4. 置信度 + 来源数
        color_icon = COLOR_ICONS.get(color.upper() if isinstance(color, str) else "YELLOW", "⚪")
        elements.append({
            "tag": "column_set",
            "flex_mode": "stretch",
            "background_style": "default",
            "columns": [
                {
                    "tag": "column", "width": "weighted", "weight": 1,
                    "elements": [{"tag": "div", "text": {"content": f"🎯 **置信度**: `{confidence:.2f}` {color_icon}", "tag": "lark_md"}}]
                },
                {
                    "tag": "column", "width": "weighted", "weight": 1,
                    "elements": [{"tag": "div", "text": {"content": f"📚 **采信来源**: {len(cited_sources)} 个", "tag": "lark_md"}}]
                }
            ]
        })
        elements.append({"tag": "hr"})

        # 5. 证据溯源列表 (from evidence_trace)
        if evidence_trace:
            trace_header = {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**📎 证据溯源：**"}
            }
            elements.append(trace_header)
            for ev in evidence_trace:
                ev_color = ev.get("color", "YELLOW")
                if isinstance(ev_color, str) and "." in ev_color:
                    ev_color = ev_color.split(".")[-1]
                ev_icon = COLOR_ICONS.get(ev_color, "⚪")
                ev_text = ev.get("text", "")[:150]
                origin = ev.get("origin", ev.get("breadcrumb", "未知"))
                page = ev.get("page_number", 0)
                page_str = f" P{page}" if page else ""
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"{ev_icon} [{origin}]{page_str} {ev_text}"
                    }
                })

            elements.append({"tag": "hr"})

        # 6. 冲突检测
        resolved_conflicts = (result.get("result_metadata", {}) or {}).get("resolved_conflicts", [])
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
            elements.append({"tag": "hr"})

        # 7. Action buttons
        actions = [
            {"tag": "button", "text": {"content": "🔍 溯源原始分片", "tag": "plain_text"}, "type": "primary",
             "value": {"action": "view_evidence", "doc_id": result.get("id", "unknown")}},
            {"tag": "button", "text": {"content": "🚩 报告逻辑偏差", "tag": "plain_text"}, "type": "danger",
             "value": {"action": "report_bias", "query": query or ""}}
        ]
        # Only add bitable link if we have a token context
        elements.append({"tag": "action", "actions": actions})

        # 8. Footer
        elements.append({
            "tag": "note",
            "elements": [{"tag": "plain_text", "content": "💡 本结果由 SpineDoc 检索引擎自动生成，不代表法律建议。"}]
        })

        return {
            "config": {"wide_screen_mode": True, "enable_forward": True},
            "header": {
                "template": self._get_template(color),
                "title": {"content": "🔍 SpineDoc 检索分析报告", "tag": "plain_text"}
            },
            "elements": elements
        }

    def build_evolution_card(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建知识进化提醒卡片"""
        count = log_data.get("evolution_count", 0)
        details = log_data.get("details", [])

        detail_md = "\n".join([f"- **{d['type']}**: {d['reason']}" for d in details])

        return {
            "header": {
                "template": "blue",
                "title": {"content": "🧬 逻辑知识库已自动进化", "tag": "plain_text"}
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
