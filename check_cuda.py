import torch
import sys

print("--- Hardware Check ---")
print(f"Python: {sys.version}")
print(f"Torch: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU Model: {torch.cuda.get_device_name(0)}")
    print(f"Device Count: {torch.cuda.device_count()}")
else:
    print("❌ NO CUDA DEVICE DETECTED BY TORCH")
print("----------------------")
