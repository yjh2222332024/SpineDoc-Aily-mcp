"""
智能OCR策略选择器
根据文档特征、用户配置、系统资源自动选择最优OCR方案
"""
import os
import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import psutil
import GPUtil
from .ocr_worker import OCRWorker
from .cloud_ocr_client import OCRProvider, CloudOCRService, cloud_ocr_service
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """文档类型枚举"""
    SCANNED_PDF = "scanned_pdf"      # 扫描PDF
    DIGITAL_PDF = "digital_pdf"      # 数字PDF（可选中文本）
    MIXED_PDF = "mixed_pdf"          # 混合PDF
    IMAGE = "image"                  # 图片文档
    TABLE = "table"                  # 表格文档
    FORM = "form"                    # 表单文档
    UNKNOWN = "unknown"


class SystemResource:
    """系统资源监控"""
    
    @staticmethod
    def get_memory_usage() -> float:
        """获取内存使用率"""
        return psutil.virtual_memory().percent
    
    @staticmethod
    def get_cpu_usage() -> float:
        """获取CPU使用率"""
        return psutil.cpu_percent(interval=0.1)
    
    @staticmethod
    def get_gpu_usage() -> Optional[float]:
        """获取GPU使用率"""
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                return gpus[0].load * 100  # 第一个GPU的使用率
        except:
            pass
        return None
    
    @staticmethod
    def get_available_memory_mb() -> int:
        """获取可用内存（MB）"""
        return psutil.virtual_memory().available // (1024 * 1024)
    
    @staticmethod
    def is_gpu_available() -> bool:
        """检查GPU是否可用"""
        try:
            gpus = GPUtil.getGPUs()
            return len(gpus) > 0
        except:
            return False


class DocumentAnalyzer:
    """文档分析器"""
    
    @staticmethod
    def analyze_document_type(file_path: str) -> DocumentType:
        """分析文档类型"""
        import fitz
        try:
            doc = fitz.open(file_path)
            
            # 检查前5页
            text_length = 0
            has_images = False
            
            for i in range(min(5, len(doc))):
                page = doc[i]
                page_text = page.get_text("text").strip()
                text_length += len(page_text)
                
                # 检查是否有图像
                image_list = page.get_images()
                if image_list:
                    has_images = True
            
            doc.close()
            
            # 判断文档类型
            if text_length < 100 and has_images:
                return DocumentType.SCANNED_PDF
            elif text_length > 1000 and not has_images:
                return DocumentType.DIGITAL_PDF
            elif text_length > 100 and has_images:
                return DocumentType.MIXED_PDF
            else:
                return DocumentType.UNKNOWN
                
        except Exception as e:
            logger.error(f"文档分析失败: {str(e)}")
            return DocumentType.UNKNOWN
    
    @staticmethod
    def get_document_size_mb(file_path: str) -> float:
        """获取文档大小（MB）"""
        return os.path.getsize(file_path) / (1024 * 1024)
    
    @staticmethod
    def estimate_ocr_time(pages: int, doc_type: DocumentType) -> float:
        """估计OCR时间（秒）"""
        # 基础时间估计
        base_time_per_page = {
            DocumentType.SCANNED_PDF: 2.0,
            DocumentType.DIGITAL_PDF: 0.1,  # 数字PDF很快
            DocumentType.MIXED_PDF: 1.5,
            DocumentType.IMAGE: 1.0,
            DocumentType.TABLE: 3.0,
            DocumentType.FORM: 2.5,
            DocumentType.UNKNOWN: 1.5
        }
        
        return base_time_per_page[doc_type] * pages


class OCROptimizer:
    """OCR优化器"""
    
    def __init__(self):
        self.resource = SystemResource()
        self.analyzer = DocumentAnalyzer()
        
    async def get_optimal_strategy(self, file_path: str) -> Dict[str, Any]:
        """获取最优OCR策略"""
        
        # 分析文档
        doc_type = self.analyzer.analyze_document_type(file_path)
        file_size_mb = self.analyzer.get_document_size_mb(file_path)
        
        import fitz
        doc = fitz.open(file_path)
        total_pages = len(doc)
        doc.close()
        
        # 获取系统资源
        memory_usage = self.resource.get_memory_usage()
        cpu_usage = self.resource.get_cpu_usage()
        gpu_usage = self.resource.get_gpu_usage()
        available_memory = self.resource.get_available_memory_mb()
        gpu_available = self.resource.is_gpu_available()
        
        # 评估各项分数
        scores = {
            "local_rapid": 0,
            "local_paddle": 0,
            "cloud_glm": 0,
            "cloud_deepseek": 0
        }
        
        # 1. 本地RapidOCR评分
        scores["local_rapid"] += 50  # 基础分
        if total_pages <= 20:
            scores["local_rapid"] += 20  # 小文档适合本地
        if memory_usage < 70:
            scores["local_rapid"] += 15  # 内存充足
        if doc_type != DocumentType.SCANNED_PDF:
            scores["local_rapid"] += 10  # Rapid对非扫描件效果不错
        
        # 2. 本地PaddleOCR评分
        scores["local_paddle"] += 40  # 基础分
        if gpu_available and gpu_usage and gpu_usage < 70:
            scores["local_paddle"] += 30  # GPU可用且充足
        if doc_type == DocumentType.SCANNED_PDF:
            scores["local_paddle"] += 25  # Paddle对扫描件效果好
        if available_memory > 2000:  # 2GB以上可用内存
            scores["local_paddle"] += 15
        
        # 3. 云端GLM OCR评分
        scores["cloud_glm"] += 60  # 基础分（云端默认较高）
        if total_pages > 50:
            scores["cloud_glm"] += 30  # 大文档适合云端
        if memory_usage > 80:
            scores["cloud_glm"] += 20  # 内存紧张时用云端
        if doc_type == DocumentType.TABLE:
            scores["cloud_glm"] += 25  # GLM表格识别好
        if file_size_mb > 50:
            scores["cloud_glm"] += 15  # 大文件用云端
        
        # 4. 云端DeepSeek OCR评分
        scores["cloud_deepseek"] += 65  # 基础分
        if total_pages > 50:
            scores["cloud_deepseek"] += 30
        if memory_usage > 80:
            scores["cloud_deepseek"] += 20
        if doc_type == DocumentType.SCANNED_PDF:
            scores["cloud_deepseek"] += 25  # DeepSeek扫描件识别好
        if file_size_mb > 50:
            scores["cloud_deepseek"] += 15
        
        # 根据配置策略调整
        if settings.OCR_STRATEGY == "local_only":
            scores["cloud_glm"] = 0
            scores["cloud_deepseek"] = 0
        elif settings.OCR_STRATEGY == "cloud_first":
            scores["local_rapid"] -= 20
            scores["local_paddle"] -= 20
        
        # 选择最高分
        best_strategy = max(scores, key=scores.get)
        best_score = scores[best_strategy]
        
        # 估算时间
        estimated_time = self.analyzer.estimate_ocr_time(total_pages, doc_type)
        
        # 构建结果
        result = {
            "strategy": best_strategy,
            "score": best_score,
            "scores": scores,
            "document_info": {
                "type": doc_type.value,
                "pages": total_pages,
                "size_mb": round(file_size_mb, 2)
            },
            "system_info": {
                "memory_usage": memory_usage,
                "cpu_usage": cpu_usage,
                "gpu_usage": gpu_usage,
                "available_memory_mb": available_memory,
                "gpu_available": gpu_available
            },
            "estimated_time_seconds": round(estimated_time, 1),
            "recommendation": self._get_recommendation(best_strategy, doc_type, total_pages)
        }
        
        return result
    
    def _get_recommendation(self, strategy: str, doc_type: DocumentType, pages: int) -> str:
        """获取推荐说明"""
        recommendations = {
            "local_rapid": f"使用本地RapidOCR（轻量级），适合{pages}页{doc_type.value}",
            "local_paddle": f"使用本地PaddleOCR（高性能），适合{pages}页{doc_type.value}",
            "cloud_glm": f"使用云端GLM OCR（表格识别强），适合{pages}页{doc_type.value}",
            "cloud_deepseek": f"使用云端DeepSeek OCR（扫描件识别好），适合{pages}页{doc_type.value}"
        }
        return recommendations.get(strategy, "使用默认OCR策略")


class HybridOCRProcessor:
    """混合OCR处理器"""
    
    def __init__(self):
        self.optimizer = OCROptimizer()
        
    async def process_document(self, file_path: str, user_preference: str = None) -> List[Dict[str, Any]]:
        """处理文档（主入口）"""
        
        logger.info(f"开始处理文档: {file_path}")
        
        # 1. 获取最优策略
        strategy_result = await self.optimizer.get_optimal_strategy(file_path)
        logger.info(f"OCR策略分析结果: {strategy_result['strategy']} (得分: {strategy_result['score']})")
        
        # 2. 根据策略执行OCR
        strategy = strategy_result["strategy"]
        
        if strategy.startswith("local_"):
            # 使用本地OCR
            return await self._process_local(file_path, strategy)
        else:
            # 使用云端OCR
            return await self._process_cloud(file_path, strategy)
    
    async def _process_local(self, file_path: str, strategy: str) -> List[Dict[str, Any]]:
        """处理本地OCR"""
        import fitz
        
        # 确定本地引擎
        if strategy == "local_paddle":
            engine_type = "paddle"
        else:  # local_rapid
            engine_type = "rapid"
        
        # 创建OCR Worker
        worker = OCRWorker(
            engine_type=engine_type,
            use_gpu=settings.OCR_USE_GPU
        )
        
        # 处理文档
        doc = fitz.open(file_path)
        results = []
        
        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_results = worker.ocr_page(page)
                
                for result in page_results:
                    result["page"] = page_idx + 1
                    result["engine"] = engine_type
                
                results.extend(page_results)
                
                # 进度提示
                if (page_idx + 1) % 10 == 0:
                    logger.info(f"本地OCR进度: {page_idx + 1}/{len(doc)}页")
        
        finally:
            doc.close()
        
        logger.info(f"本地OCR完成: {len(results)}条结果")
        return results
    
    async def _process_cloud(self, file_path: str, strategy: str) -> List[Dict[str, Any]]:
        """处理云端OCR"""
        # 确定云端提供商
        if strategy == "cloud_glm":
            provider = OCRProvider.GLM_OCR
        else:  # cloud_deepseek
            provider = OCRProvider.DEEPSEEK_OCR
        
        # 使用云端OCR服务
        all_results = await cloud_ocr_service.ocr_pdf(file_path)
        
        # 格式化结果
        results = []
        for page_idx, page_results in enumerate(all_results):
            for result in page_results:
                result_dict = result.to_dict()
                result_dict["page"] = page_idx + 1
                result_dict["provider"] = provider.value
                results.append(result_dict)
        
        logger.info(f"云端OCR完成: {len(results)}条结果")
        return results


# 全局实例
ocr_processor = HybridOCRProcessor()