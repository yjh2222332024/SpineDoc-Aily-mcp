"""
SpineDoc Coze 官方 API 桥接器 (CozeBridge) - V1.0
================================================
职责：实现本地切片向 Coze 知识库的实时同步。
架构：采用后台异步任务模式，确保同步不阻塞主审计流程。
"""
import json
import httpx
import logging
import asyncio
import base64
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class CozeBridge:
    def __init__(self):
        # 🏛️ 架构师：优先从 settings 读取，如果缺失则无法工作
        self.api_key = settings.COZE_API_KEY
        self.dataset_id = settings.COZE_KNOWLEDGE_ID or "7633427337036234771"
        self.base_url = "https://api.coze.cn"

    async def sync_chunk_to_knowledge(self, record_id: str, content: str, metadata: Dict[str, Any]):
        """
        🚀 灌入：将 Bitable 分片推送至 Coze 知识库。
        采用“文本注入”策略，将元数据直接缝合进正文，确保检索召回时的确定性。
        """
        if not self.api_key:
            print("⚠️ [CozeBridge] COZE_API_KEY 未配置，跳过同步。")
            return

        # 🚀 [V60.4] 再次尝试：Coze.cn 官方 open_api 路径 (不带 /v1)
        url = "https://api.coze.cn/open_api/knowledge/document/create"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 1. 语义缝合
        semantic_content = f"---BITABLE_ID: {record_id}---\n{content}"
        # 2. Base64 编码 (官方文档有时要求 Base64)
        b64_content = base64.b64encode(semantic_content.encode("utf-8")).decode("utf-8")
        
        payload = {
            "dataset_id": self.dataset_id,
            "document_bases": [
                {
                    "name": f"Chunk_{record_id}",
                    "source_info": {
                        "document_source": 0, # 0: 本地上传
                        "content": b64_content,
                        "file_type": "txt"
                    }
                }
            ],
            "chunk_strategy": {
                "chunk_type": 0 # 自动分段
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                print(f"📡 [CozeBridge] 响应状态码: {resp.status_code}")
                try:
                    data = resp.json()
                    if resp.status_code == 200 and data.get("code") == 0:
                        print(f"✅ [CozeBridge] 语义切片已成功上云 (BitableID: {record_id})")
                    else:
                        print(f"❌ [CozeBridge] 同步失败 (API返回): {json.dumps(data, ensure_ascii=False)}")
                except Exception:
                    print(f"❌ [CozeBridge] 同步失败 (非JSON响应): {resp.text}")
            except Exception as e:
                logger.error(f"❌ [CozeBridge] 通信异常: {e}")

coze_bridge = CozeBridge()
