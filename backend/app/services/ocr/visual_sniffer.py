import fitz
from collections import Counter
from typing import List, Dict, Any

class VisualSaliencySniffer:
    """
    VisualSaliencySniffer V34.0: 物理特征探测器
    职责：从 PDF 图层提取字号、加粗等显著性特征。
    """
    def sniff(self, pdf_path: str, scan_limit: int = 50) -> List[Dict[str, Any]]:
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f" 无法打开 PDF: {e}")
            return []

        all_sizes = []
        # 1. 抽样确定基准
        for i in range(min(scan_limit, len(doc))):
            try:
                blocks = doc[i].get_text("dict")["blocks"]
                for b in blocks:
                    if "lines" in b:
                        for l in b["lines"]:
                            for s in l["spans"]:
                                if s["size"] > 5:
                                    all_sizes.append(round(s["size"], 1))
            except: continue
        
        if not all_sizes: return []
        base_size = Counter(all_sizes).most_common(1)[0][0]
        
        candidates = []
        # 2. 全量提取显著行
        for i in range(len(doc)):
            try:
                blocks = doc[i].get_text("dict")["blocks"]
                for b in blocks:
                    if "lines" in b:
                        for l in b["lines"]:
                            line_text = "".join([s["text"] for s in l["spans"]]).strip()
                            if not line_text or len(line_text) < 2: continue
                            
                            max_size = max([s["size"] for s in l["spans"]])
                            is_bold = any([bool(s["flags"] & 2**4) for s in l["spans"]])
                            
                            # 判定逻辑：字号显著大，或是加粗且不小于基准
                            if (max_size > base_size * 1.1 or (is_bold and max_size >= base_size)) and len(line_text) < 150:
                                candidates.append({
                                    "text": line_text,
                                    "size": round(max_size, 1),
                                    "is_bold": is_bold,
                                    "page": i + 1
                                })
            except: continue
        
        doc.close()
        return candidates
