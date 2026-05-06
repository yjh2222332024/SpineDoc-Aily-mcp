"""
SpineDoc 飞书原生 OCR 工作器 (V1.0 逻辑原矿版)
===========================================
职责：调用飞书 Open-APIs (通过 lark-cli) 获取原始文本块与物理坐标。
     它是“逻辑熔断（Logic Smelting）”策略的基石：0 成本、高覆盖。
     主要用于“显式唤醒”模式下的扫描件目录恢复。
"""
import os
import json
import base64
import cv2
import asyncio
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path

class FeishuBasicWorker:
    def __init__(self, cli_path: str = "bin/lark-cli.exe"):
        self.cli_path = str(Path(cli_path).resolve())
        if not os.path.exists(self.cli_path):
            print(f" [FeishuOCR] 未找到 lark-cli 二进制文件: {self.cli_path}")

    async def recognize(self, img_np: np.ndarray, max_retries: int = 3) -> List[Dict[str, Any]]:
        """
         核心逻辑：将图片发给飞书，带重试机制。
        """
        # 0. 强制直连：绝不走本地代理
        env = os.environ.copy()
        env["LARK_CLI_NO_PROXY"] = "1"
        for key in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
            env.pop(key, None)

        for attempt in range(max_retries):
            try:
                # 1. 图像预处理与编码
                success, buffer = cv2.imencode('.jpg', img_np, [cv2.IMWRITE_JPEG_QUALITY, 90])
                if not success: return []
                b64_str = base64.b64encode(buffer).decode('utf-8')

                # 2. 构建 API 调用 JSON
                api_data = {"image": b64_str}
                json_payload = json.dumps(api_data)

                # 3. 异步调用 lark-cli (采用管道模式 + Bot 身份)
                cmd = [
                    self.cli_path, "api", "POST", 
                    "/open-apis/optical_char_recognition/v1/image/basic_recognize", 
                    "--as", "bot", 
                    "--data", "-"
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                )

                #  [V54.7] 管道灌入数据并等待响应
                stdout, stderr = await process.communicate(input=json_payload.encode('utf-8'))

                raw_response = stdout.decode().strip()
                raw_error = stderr.decode().strip()

                # 4.  无论状态码，只要有响应就尝试解析
                if not raw_response:
                    print(f" [FeishuOCR] 空响应 (尝试 {attempt+1}) | Stderr: {raw_error}")
                    await asyncio.sleep(2)
                    continue

                try:
                    resp_json = json.loads(raw_response)
                except json.JSONDecodeError:
                    print(f" [FeishuOCR] JSON 解析失败 (尝试 {attempt+1}) | Raw: {raw_response[:100]}")
                    continue
                
                # 提取错误码
                code = resp_json.get("code") or resp_json.get("error", {}).get("code")
                
                if code == 99991400: # 限流错误
                    wait_time = 10 #  物理降频：给 10 秒冷却期
                    print(f"⏳ [FeishuOCR] 触发频率限制，静默等待 {wait_time} 秒后进行第 {attempt+1} 次重试...")
                    await asyncio.sleep(wait_time)
                    continue
                
                if code != 0 and not resp_json.get("ok", True) == True:
                    print(f" [FeishuOCR] 接口报错: {resp_json}")
                    return []

                # 5. 提取逻辑原矿
                data = resp_json.get("data") or {}
                text_list = data.get("text_list", [])
                
                refined_results = []
                for item in text_list:
                    refined_results.append({
                        "text": item.get("text", ""),
                        "bbox": item.get("coordinates", []),
                        "confidence": 1.0
                    })
                return refined_results

            except Exception as e:
                print(f" [FeishuOCR] 识别过程异常 (尝试 {attempt+1}): {e}")
                await asyncio.sleep(1)
        
        return []

    async def ocr_to_text(self, img_np: np.ndarray) -> str:
        """
        简单封装：仅返回纯文本（用于后续 LLM 逻辑纠偏）
        """
        blocks = await self.recognize(img_np)
        return "\n".join([b['text'] for b in blocks])
