"""
SpineDoc Aily 联邦检索桥接器 (AilyBridge) - V1.0
================================================
职责：通过 Aily OpenAPI 调动云端向量检索能力。
特性：借力打力，将 Bitable 里的逻辑切片转化为可搜索的语义资产。
"""
import json
import httpx
import asyncio
import logging
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class AilyBridge:
    def __init__(self):
        self.base_url = "https://open.feishu.cn/open-apis/aily/v1"
        self.app_id = settings.FEISHU_AILY_APP_ID # 需在 .env 补全
        self.api_key = settings.FEISHU_APP_SECRET # 复用 Lark Secret 换取 Token

    async def _get_tenant_token(self) -> str:
        """换取飞书租户凭证"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json={
                "app_id": settings.FEISHU_APP_ID,
                "app_secret": settings.FEISHU_APP_SECRET
            })
            return resp.json().get("tenant_access_token", "")

    async def ask_knowledge(self, query: str, knowledge_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        🚀 语义撞击：调动 Aily 云端向量索引 (支持 Markdown 表格解析)
        """
        if not self.app_id:
            print("⚠️ [AilyBridge] FEISHU_AILY_APP_ID 未配置，跳过联邦检索。")
            return []

        token = await self._get_tenant_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        url = f"https://open.feishu.cn/open-apis/aily/v1/apps/{self.app_id}/knowledges/ask"
        payload = {
            "message": query,
            "knowledge_ids": knowledge_ids or [],
            "config": {
                "top_k": 10,
                "score_threshold": 0.2
            }
        }

        print(f"📡 [Aily] 正在向云端发起语义撞击请求: '{query}'")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    raw_body = resp.text
                    # 🏛️ 清理非法控制字符防止 JSON 解析失败
                    import re
                    clean_body = re.sub(r'[\x00-\x1f\x7f]', '', raw_body)
                    data = json.loads(clean_body)
                    
                    # 兼容 recallChunks 或 references 格式
                    chunks = data.get("data", {}).get("recallChunks") or data.get("data", {}).get("references", [])
                    return self._parse_aily_results(chunks)
                else:
                    logger.error(f"❌ [Aily] 请求失败: {resp.text}")
                    return []
            except Exception as e:
                logger.error(f"❌ [Aily] 通信异常: {e}")
                return []

    def _parse_aily_results(self, chunks: List[Dict]) -> List[Dict]:
        """
        🏛️ 逻辑萃取：将 Aily 原始数据（含 Markdown 表格）转为 Spine 节点
        """
        refined_results = []
        import re
        
        for chunk in chunks:
            source_val = chunk.get("sourceValue", {})
            raw_content = source_val.get("content") or chunk.get("content", "")
            
            # 识别 Markdown 表格行
            if "| NO." in raw_content:
                rows = [row for row in raw_content.split('\n') if row.strip().startswith('| NO.')]
                for row in rows:
                    cols = [col.strip() for col in row.split('|') if col.strip()]
                    if len(cols) < 10: continue
                    
                    page_match = re.search(r'【页码：P(\d+)】', cols[2])
                    refined_results.append({
                        "id": cols[1], 
                        "content": cols[2],
                        "page_number": int(page_match.group(1)) if page_match else 0,
                        "breadcrumb": cols[5],
                        "logic_coord": cols[9],
                        "score": chunk.get("recallScore") or chunk.get("score", 0.0)
                    })
            else:
                refined_results.append({
                    "id": chunk.get("id") or chunk.get("record_id"),
                    "content": raw_content,
                    "score": chunk.get("recallScore") or chunk.get("score", 0.0),
                    "breadcrumb": chunk.get("title", "")
                })
        return refined_results


aily_bridge = AilyBridge()
