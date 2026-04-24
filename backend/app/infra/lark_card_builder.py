
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

    def build_verdict_card(self, verdict: Dict[str, Any]) -> Dict[str, Any]:
        """构建质证判决书卡片"""
        text = verdict.get("text", verdict.get("final_answer", "无结论"))
        confidence = verdict.get("verdict_metadata", {}).get("confidence", 0.0)
        color = verdict.get("color", "YELLOW")
        cited_galaxies = verdict.get("verdict_metadata", {}).get("cited_galaxies", [])
        
        # 🚀 [V52.10] 构造工业级互动卡片 JSON
        card = {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True
            },
            "header": {
                "template": self._get_template(color),
                "title": {
                    "content": "🏛️ SpineDoc 逻辑审计判决书",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"**审计结论**：\n{text}",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "column_set",
                    "flex_mode": "stretch",
                    "background_style": "default",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "elements": [
                                {
                                    "tag": "div",
                                    "text": {
                                        "content": f"🎯 **置信度**: `{confidence:.2f}`",
                                        "tag": "lark_md"
                                    }
                                }
                            ]
                        },
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "elements": [
                                {
                                    "tag": "div",
                                    "text": {
                                        "content": f"🛰️ **涉及星系**: {len(cited_galaxies)} 个",
                                        "tag": "lark_md"
                                    }
                                }
                            ]
                        }
                    ]
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "content": "🔍 查看逻辑演变历史 (Git Diff)",
                                "tag": "plain_text"
                            },
                            "type": "primary",
                            "value": {
                                "action": "view_diff",
                                "chunk_id": verdict.get("id", "unknown")
                            }
                        },
                        {
                            "tag": "button",
                            "text": {
                                "content": "📊 追溯 Bitable 资产",
                                "tag": "plain_text"
                            },
                            "type": "default",
                            "multi_url": {
                                "url": "https://www.feishu.cn/base/XbXwbaFh7aNrNjsL80TcSozNnEh", # 占位符，后期动态注入
                                "pc_url": "",
                                "android_url": "",
                                "ios_url": ""
                            }
                        }
                    ]
                }
            ],
            "footer": {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "💡 本判决由 SpineDoc 逻辑主权引擎自动生成，不代表法律建议。"
                    }
                ]
            }
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
