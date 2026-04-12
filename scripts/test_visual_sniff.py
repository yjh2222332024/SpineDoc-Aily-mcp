import fitz
import json
from collections import Counter

def sniff_document(pdf_path):
    doc = fitz.open(pdf_path)
    all_sizes = []
    candidates = []
    
    # 1. 第一遍扫描：收集字号分布，确定基准
    print(f"🔍 正在扫描前 20 页确定字号基准...")
    for i in range(min(20, len(doc))):
        page = doc[i]
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    for s in l["spans"]:
                        all_sizes.append(round(s["size"], 1))
    
    if not all_sizes:
        print("❌ 未能提取到文本特征。")
        return
        
    size_counts = Counter(all_sizes)
    # 过滤掉极小的字号（可能是噪点）
    valid_sizes = [s for s in all_sizes if s > 5]
    if not valid_sizes: return
    base_size = Counter(valid_sizes).most_common(1)[0][0]
    print(f"📊 文档基准字号: {base_size}pt")
    
    # 2. 第二遍扫描：提取显著大于基准或加粗的行
    print(f"🚀 正在提取候选标题...")
    for i in range(len(doc)):
        page = doc[i]
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    # 合并行内的 span
                    line_text = "".join([s["text"] for s in l["spans"]]).strip()
                    if not line_text or len(line_text) < 2: continue
                    
                    # 取行内最大的字号作为代表
                    max_size = max([s["size"] for s in l["spans"]])
                    is_bold = any([bool(s["flags"] & 2**4) for s in l["spans"]])
                    
                    # 启发式过滤：显著大于基准 1.1 倍，或者加粗且大于基准
                    if (max_size > base_size * 1.1 or (is_bold and max_size >= base_size)) and len(line_text) < 150:
                        candidates.append({
                            "text": line_text,
                            "size": round(max_size, 1),
                            "is_bold": is_bold,
                            "page": i + 1
                        })
    
    # 3. 展示前 30 个候选标题，验证质量
    print("\n📍 嗅探到的潜在“幻影脊梁”候选 (Top 30):")
    for c in candidates[:30]:
        print(f"  [P{c['page']}] {c['text']} (Size: {c['size']}, Bold: {c['is_bold']})")

if __name__ == "__main__":
    import sys
    pdf = sys.argv[1] if len(sys.argv) > 1 else "1.pdf"
    sniff_document(pdf)
