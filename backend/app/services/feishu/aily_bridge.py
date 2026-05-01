"""
SpineDoc Aily 联邦检索桥接器 (AilyBridge) - 2026 生产级版
=========================================================
职责：利用飞书 Aily 技能 API 触发工作流，并精准解析召回的逻辑分片。
特性：支持双重 JSON 解析，从嵌套 Markdown 中萃取 Spine 节点。
"""
import json
import httpx
import asyncio
import logging
import re
import os
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class AilyBridge:
    def __init__(self):
        # 🏛️ 2026 生产级配置：基于用户实测验证的座标
        self.feishu_host = "https://open.feishu.cn"
        self.app_id = "spring_b0ece7655e__c"
        self.skill_id = "skill_4686c04514dd"

    async def _get_tenant_token(self) -> str:
        """换取飞书租户凭证"""
        # 🚀 [V86.0] 确权优先：如果 .env 里直接给了 Token (来自用户 curl 验证)，直接使用
        manual_token = os.getenv("FEISHU_AILY_TOKEN")
        if manual_token:
            print("🔑 [Aily] 正在使用手动注入的‘黄金令牌’...")
            return manual_token.strip()

        url = f"{self.feishu_host}/open-apis/auth/v3/tenant_access_token/internal"
        # 🏛️ 策略：如果常规 cli_id 不行，尝试使用 Spring 应用标识
        auth_id = os.getenv("FEISHU_AILY_AUTH_ID") or settings.FEISHU_APP_ID
        auth_secret = os.getenv("FEISHU_AILY_AUTH_SECRET") or settings.FEISHU_APP_SECRET

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json={
                "app_id": auth_id,
                "app_secret": auth_secret
            })
            return resp.json().get("tenant_access_token", "")


    async def ask_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """
        🚀 语义撞击：通过 Aily 技能触发工作流执行‘粗筛’。
        """
        token = await self._get_tenant_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        url = f"{self.feishu_host}/open-apis/aily/v1/apps/{self.app_id}/skills/{self.skill_id}/start"
        
        # 🏛️ 严格对齐 Workflow 契约
        payload = {
            "global_variable": {
                "query": query
            }
        }

        print(f"📡 [Aily] 正在通过技能接口质询云端: '{query[:20]}...'")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    # 🏛️ 鲁棒性清洗：处理可能存在的控制字符
                    clean_body = re.sub(r'[\x00-\x1f\x7f]', '', resp.text)
                    data = json.loads(clean_body)
                    
                    if data.get("code") != 0:
                        logger.error(f"❌ [Aily] 业务错误: {data.get('msg')}")
                        return []

                    # 1. 提取 output 字符串
                    raw_output = data.get("data", {}).get("output", "{}")
                    # 2. 二次反序列化 (工作流输出通常是字符串 JSON)
                    output_data = json.loads(raw_output)
                    
                    # 3. 寻找 recallChunks
                    chunks = output_data.get("data", {}).get("recallChunks") or []
                    if not chunks:
                        return []
                        
                    return self._parse_aily_results(chunks)
                else:
                    logger.error(f"❌ [Aily] 网络失败: {resp.status_code}")
                    return []
            except Exception as e:
                logger.error(f"❌ [Aily] 通信异常: {e}")
                return []

    def _parse_aily_results(self, chunks: List[Dict]) -> List[Dict]:
        """
        🏛️ 逻辑解析：将 recallChunks 转为结构化证据节点。
        """
        refined_results = []
        
        for chunk in chunks:
            # 提取核心数据，优先看 sourceValue.content
            source_val = chunk.get("sourceValue", {})
            raw_content = source_val.get("content") or chunk.get("content", "")
            
            # 如果内容是带 | NO. 的 Markdown 表格
            if "| NO." in raw_content:
                # 🏛️ 利用正则一次性提取所有匹配行
                rows = re.findall(r'^\| NO\..*?\|$', raw_content, re.MULTILINE)
                for row in rows:
                    cols = [col.strip() for col in row.split('|') if col.strip()]
                    if len(cols) < 10: continue
                    
                    # 提取页码 (【页码：Px】)
                    page_match = re.search(r'P(\d+)', cols[4]) # 优先看物理页码列
                    if not page_match: page_match = re.search(r'P(\d+)', cols[2]) # 其次看正文前缀
                    
                    refined_results.append({
                        "id": cols[1], # record_id (这是 RRF 的连接主键)
                        "content": cols[3], # 正文内容列
                        "page_number": int(page_match.group(1)) if page_match else 0,
                        "breadcrumb": cols[5], # 面包屑
                        "logic_coord": cols[9], # 坐标
                        "score": chunk.get("recallScore") or 0.0
                    })
            else:
                # 兼容普通文本格式
                refined_results.append({
                    "id": chunk.get("id") or chunk.get("knowledgeID"),
                    "content": raw_content,
                    "score": chunk.get("recallScore") or 0.0,
                    "breadcrumb": "Generic Cloud"
                })
        
        return refined_results

aily_bridge = AilyBridge()
