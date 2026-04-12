import os
import sys

def create_bridge():
    site_packages = os.path.join(os.getcwd(), ".venv", "Lib", "site-packages")
    zai_dir = os.path.join(site_packages, "zai")
    os.makedirs(zai_dir, exist_ok=True)
    
    init_path = os.path.join(zai_dir, "__init__.py")
    with open(init_path, "w", encoding="utf-8") as f:
        f.write("from zhipuai import ZhipuAI as ZhipuAiClient\n")
    
    print(f"✅ Bridge successfully created at {init_path}")
    print("Now 'from zai import ZhipuAiClient' will work.")

if __name__ == "__main__":
    create_bridge()
