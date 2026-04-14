import torch
from sentence_transformers import SentenceTransformer
import os

os.environ["TORCH_SKIP_CHECK_FOR_CVE_2025_32434"] = "1"

model_path = r"E:\ai_models\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181"

print(f"DEBUG: Trying to load model from {model_path}")
try:
    model = SentenceTransformer(model_path, device="cuda")
    print("DEBUG: Success loading on CUDA!")
except Exception as e:
    print(f"DEBUG: CUDA Load Failed: {e}")
    try:
        model = SentenceTransformer(model_path, device="cpu")
        print("DEBUG: Success loading on CPU!")
    except Exception as e2:
        print(f"DEBUG: CPU Load Failed: {e2}")
