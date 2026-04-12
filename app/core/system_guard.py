"""
SpineDoc System Guard - 硬件监控与保护模块
职责：监控 CPU/内存，防止本地 OCR 模型压垮用户系统。
"""
import psutil
import logging
import os

logger = logging.getLogger(__name__)

class SystemGuard:
    # 临界阈值 (单位: GB)
    DANGER_RAM_TOTAL = 8.0  # 总内存小于 8G 视为弱机
    CRITICAL_RAM_FREE = 2.0 # 剩余内存小于 2G 触发熔断

    @classmethod
    def check_hardware_capability(cls) -> bool:
        """检查硬件是否足以运行本地 OCR 引擎"""
        ram = psutil.virtual_memory()
        total_gb = ram.total / (1024**3)
        free_gb = ram.available / (1024**3)
        
        print(f"🖥️ [SystemGuard] 硬件检测: 总内存 {total_gb:.1f}GB, 当前可用 {free_gb:.1f}GB")
        
        if total_gb < cls.DANGER_RAM_TOTAL:
            print("⚠️ [SystemGuard] 警告：系统总内存不足 8GB，强行运行本地 OCR 可能会导致系统假死。")
            return False
            
        if free_gb < cls.CRITICAL_RAM_FREE:
            print("🚨 [SystemGuard] 熔断：可用内存极低，已禁止加载本地 AI 模型。")
            return False
            
        return True

    @classmethod
    def get_recommended_strategy(cls) -> str:
        """根据硬件自动推荐 OCR 策略"""
        if not cls.check_hardware_capability():
            return "cloud_first"
        return "adaptive"
