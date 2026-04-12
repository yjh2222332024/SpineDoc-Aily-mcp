"""
SpineDoc V41.5 - QuantMarketWitness (Logic Assassin Edition)
===========================================================
职责：提供实时金融行情、个股快讯及宏观经济作为“外部物证”。
"""
import asyncio
import httpx
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings
from .state import FederatedState
from .types import AtomicClaim
from .witness_node import parse_atomic_claims

logger = logging.getLogger(__name__)

MARKET_WITNESS_PROMPT = """你是一个冷酷、精确的【金融取证专家】。
你的任务是根据提供的原始市场数据（行情、新闻、日历），提取与用户问题相关的“原子论点”。

【核心准则】：
1. 只说事实：严禁进行任何技术分析（如“我认为会涨”）、联想或预测。
2. 数据溯源：每一条论点必须标注来源 (例如：Finnhub, DailyFX, Serper)。
3. 物理标记：对于市场数据，统一使用页码 P0 作为占位符。

【输出格式】：
[CLAIM] (P0) [Finnhub] 事实描述内容
[CLAIM] (P0) [DailyFX] 事实描述内容
...
如果不相关，输出：[STATUS: NO_EVIDENCE]
"""

class QuantMarketWitnessNode:
    def __init__(self, override_api_key: Optional[str] = None):
        self.api_key = override_api_key or settings.LLM_API_KEY
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=settings.LLM_BASE_URL)
        self.finnhub_key = getattr(settings, "FINNHUB_API_KEY", None)
        self.serper_key = getattr(settings, "SERPER_API_KEY", None)

    async def extract_ticker(self, query: str) -> Optional[str]:
        """利用 LLM 从问题中提取股票/加密货币代码"""
        prompt = f"从以下问题中提取最相关的股票代码或加密货币代码（如 NVDA, AAPL, BTC, ETH）。如果没发现，只返回 NONE：\n\n问题：{query}"
        try:
            res = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            ticker = res.choices[0].message.content.strip().upper()
            return None if ticker == "NONE" else ticker
        except:
            return None

    async def fetch_finnhub_news(self, ticker: str) -> str:
        """获取 Finnhub 个股新闻精华"""
        if not self.finnhub_key: return "Finnhub API Key 未配置。"
        
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={self.finnhub_key}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(url)
                data = res.json()
                if not data: return f"未能发现 {ticker} 的今日新闻。"
                
                news_text = f"--- {ticker} 实时新闻 (Finnhub) ---\n"
                for item in data[:5]:
                    news_text += f"- {item['datetime']}: {item['headline']} (Summary: {item['summary'][:100]}...)\n"
                return news_text
            except Exception as e:
                return f"Finnhub 数据抓取失败: {e}"

    async def fetch_dailyfx_calendar(self) -> str:
        """获取 DailyFX 宏观经济日历"""
        today = datetime.now().strftime("%Y/%m/%d")
        url = f"https://www.dailyfx.com/calendar/static/daily/{today}.json"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(url)
                data = res.json()
                if not data: return "今日无重大宏观经济事件。"
                
                cal_text = "--- 今日宏观经济日历 (DailyFX) ---\n"
                # 仅展示重要程度高 (importance: High) 的事件
                high_impact = [d for d in data if d.get('importance') == 'High']
                for item in high_impact[:8]:
                    cal_text += f"- {item['time']}: {item['event']} (Actual: {item.get('actual','N/A')}, Forecast: {item.get('forecast','N/A')})\n"
                return cal_text
            except Exception as e:
                return f"DailyFX 日历抓取失败: {e}"

    async def fetch_serper_search(self, query: str) -> str:
        """执行 Serper.dev 谷歌搜索获取大盘情报"""
        if not self.serper_key: return "Serper API Key 未配置。"
        
        url = "https://google.serper.dev/news"
        headers = {"X-API-KEY": self.serper_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": 5}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(url, headers=headers, json=payload)
                data = res.json()
                news = data.get("news", [])
                
                search_text = f"--- 联网搜索结果 (Serper) ---\n"
                for n in news:
                    search_text += f"- {n['title']} (Source: {n['source']}, Date: {n['date']})\n  Snippet: {n.get('snippet','')[:100]}...\n"
                return search_text
            except Exception as e:
                return f"Serper 搜索失败: {e}"

async def quant_market_witness_node(state: FederatedState) -> Dict[str, Any]:
    """
    量化市场证人节点：作为联邦图谱中的一员，提供实时外部证据。
    """
    print("📈 [Quant Witness] 正在采集实时金融情报...")
    
    agent = QuantMarketWitnessNode()
    query = state['query']
    
    # 1. 识别标的
    ticker = await agent.extract_ticker(query)
    
    # 2. 并行取证
    tasks = [agent.fetch_dailyfx_calendar()]
    if ticker:
        tasks.append(agent.fetch_finnhub_news(ticker))
        tasks.append(agent.fetch_serper_search(f"{ticker} 股票最新分析"))
    else:
        tasks.append(agent.fetch_serper_search(query))
        
    raw_evidence_list = await asyncio.gather(*tasks)
    full_market_context = "\n\n".join(raw_evidence_list)
    
    # 3. 逻辑脱水：转化为原子论点
    try:
        res = await agent.client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": MARKET_WITNESS_PROMPT},
                {"role": "user", "content": f"问题：{query}\n\n原始数据：\n{full_market_context}"}
            ],
            temperature=0
        )
        content = res.choices[0].message.content.strip()
        
        if "[STATUS: NO_EVIDENCE]" in content:
            claims = []
        else:
            # 复用原有的鲁棒解析器，市场证言统一标记为 P0 页码
            claims = parse_atomic_claims(content, "QuantMarket")
            
        print(f"✅ [Quant Witness] 采证完成，获得 {len(claims)} 条原子事实。")
        
        # 将市场证据合并到全局状态
        opinions = state.get("witness_opinions", {})
        opinions["QuantMarket"] = claims
        
        contexts = state.get("witness_contexts", {})
        contexts["QuantMarket"] = full_market_context
        
        return {
            "witness_opinions": opinions,
            "witness_contexts": contexts
        }
        
    except Exception as e:
        print(f"❌ [Quant Witness] 逻辑合成崩溃: {e}")
        return {}
