
import json
from typing import Dict, Any, List

class AilyPresenter:
    """
    Aily Presenter Adapter
    Responsibility: Convert retrieval results into Feishu interactive cards.
    """

    @staticmethod
    def format_result_to_card(result: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Aily Interactive Protocol: Convert retrieval result into a visual card.
        """
        confidence = result.get("confidence", 0.0)
        # 根据置信度决定主题颜色
        theme = "blue"
        if confidence > 0.8: theme = "green"
        elif confidence < 0.4: theme = "red"

        # 1. 构造卡片基础结构
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": theme,
                "title": {
                    "content": "🔍 SpineDoc 检索分析报告",
                    "tag": "plain_text"
                }
            },
            "elements": []
        }

        # 2. 注入查询回顾
        card["elements"].append({
            "tag": "div",
            "text": {
                "content": f"**🔍 查询：** {query}",
                "tag": "lark_md"
            }
        })

        # 3. 注入最终答案正文
        card["elements"].append({
            "tag": "div",
            "text": {
                "content": result.get("final_answer", "证据不足，无法给出确定性答案。"),
                "tag": "lark_md"
            }
        })

        # 4. 注入采信来源（白盒化第一层：主权来源）
        cited_sources = ", ".join(result.get("cited_sources", ["未知"]))
        card["elements"].append({
            "tag": "note",
            "elements": [
                {"tag": "plain_text", "content": f"📚 采信来源：{cited_sources}"},
                {"tag": "plain_text", "content": f"🎯 置信得分：{int(confidence * 100)}%"}
            ]
        })

        # 5. 注入逻辑冲突点（白盒化第二层：博弈透明）
        resolved = result.get("resolved_conflicts", [])
        if resolved:
            card["elements"].append({"tag": "hr"})
            card["elements"].append({
                "tag": "div",
                "text": {
                    "content": "**⚠️ 检测到知识冲突：**",
                    "tag": "lark_md"
                }
            })
            for conflict in resolved:
                resolution = conflict.get("resolution", {})
                card["elements"].append({
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": False,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**冲突点：** {conflict['description']}\n**解决方案：** {resolution.get('decision')} (理由: {resolution.get('reasoning')})"
                            }
                        }
                    ]
                })

        # 6. 注入交互 Action（白盒化第三层：溯源与反馈）
        card["elements"].append({"tag": "hr"})
        card["elements"].append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🔍 溯源原始分片"},
                    "type": "primary",
                    "value": {"action": "view_evidence", "doc_id": result.get("bitable_id")}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🚩 报告逻辑偏差"},
                    "type": "danger",
                    "value": {"action": "report_bias", "query": query}
                }
            ]
        })

        return card


aily_presenter = AilyPresenter()