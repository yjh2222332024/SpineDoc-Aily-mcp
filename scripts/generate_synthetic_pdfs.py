#!/usr/bin/env python3
"""
SpineDoc 合成 PDF 数据集生成器
用于大规模性能测试
"""

import os
import random
import uuid
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("⚠️  reportlab 未安装，运行: pip install reportlab")

# 中文教材模板
CHINESE_TEXTBOOK_TITLES = [
    "人工智能导论", "机器学习实战", "深度学习原理", 
    "计算机网络", "数据结构与算法", "操作系统概念",
    "数据库系统概论", "编译原理", "计算机组成原理",
    "高等数学", "线性代数", "概率论与数理统计"
]

ENGLISH_TEXTBOOK_TITLES = [
    "Introduction to AI", "Machine Learning in Action", 
    "Deep Learning Principles", "Computer Networks",
    "Data Structures and Algorithms", "Operating Systems"
]

CHAPTER_PREFIXES_CN = ["第", "第", "第"]
CHAPTER_NAMES_CN = ["章", "章", "章"]

SECTION_TEMPLATES_CN = [
    "{num}.1 {title}",
    "{num}.2 {title}",
    "{num}.3 {title}"
]

@dataclass
class DocumentConfig:
    title: str
    num_chapters: int = 8
    sections_per_chapter: int = 3
    pages_per_section: int = 5
    is_chinese: bool = True

class SyntheticPDFGenerator:
    def __init__(self, output_dir: str = "./test_data/synthetic"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.styles = getSampleStyleSheet() if HAS_REPORTLAB else None
        self._init_styles()
    
    def _init_styles(self):
        if not HAS_REPORTLAB:
            return
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        self.chapter_style = ParagraphStyle(
            'CustomChapter',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceAfter=20,
            spaceBefore=20
        )
        self.section_style = ParagraphStyle(
            'CustomSection',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12
        )
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14
        )
    
    def _generate_lorem_text(self, paragraphs: int = 3) -> str:
        lorem = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
            "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. "
            "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. "
            "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. "
        )
        chinese_text = (
            "人工智能是计算机科学的一个重要分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。 "
            "机器学习是人工智能的核心，是使计算机具有智能的根本途径，其应用遍及人工智能的各个领域。 "
            "深度学习是机器学习的一个子集，它使用包含复杂结构或由多重非线性变换构成的多个处理层对数据进行高层抽象的算法。 "
        )
        return (chinese_text + lorem) * paragraphs
    
    def generate_pdf(self, config: DocumentConfig) -> str:
        if not HAS_REPORTLAB:
            print("❌ 需要先安装 reportlab")
            return ""
        
        doc_id = str(uuid.uuid4())[:8]
        filename = f"{config.title.replace(' ', '_')}_{doc_id}.pdf"
        filepath = self.output_dir / filename
        
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        story.append(Paragraph(config.title, self.title_style))
        story.append(PageBreak())
        
        current_page = 2
        toc_entries = []
        
        for ch_num in range(1, config.num_chapters + 1):
            if config.is_chinese:
                chapter_title = f"第 {ch_num} 章  {self._random_chapter_title_cn()}"
            else:
                chapter_title = f"Chapter {ch_num}: {self._random_chapter_title_en()}"
            
            toc_entries.append((1, chapter_title, current_page))
            story.append(Paragraph(chapter_title, self.chapter_style))
            
            for sec_num in range(1, config.sections_per_chapter + 1):
                if config.is_chinese:
                    section_title = f"{ch_num}.{sec_num}  {self._random_section_title_cn()}"
                else:
                    section_title = f"{ch_num}.{sec_num}  {self._random_section_title_en()}"
                
                toc_entries.append((2, section_title, current_page))
                story.append(Paragraph(section_title, self.section_style))
                
                for _ in range(config.pages_per_section):
                    story.append(Paragraph(self._generate_lorem_text(5), self.body_style))
                    story.append(Spacer(1, 0.2 * inch))
                    current_page += 1
                
                story.append(PageBreak())
        
        doc.build(story)
        print(f"✅ 生成: {filepath} ({current_page} 页)")
        return str(filepath)
    
    def _random_chapter_title_cn(self) -> str:
        titles = ["概述", "核心概念", "算法原理", "实现方法", "应用案例", "进阶技术", "总结与展望", "习题"]
        return random.choice(titles)
    
    def _random_section_title_cn(self) -> str:
        titles = ["基本定义", "数学推导", "伪代码实现", "实验结果", "相关工作", "局限性分析"]
        return random.choice(titles)
    
    def _random_chapter_title_en(self) -> str:
        titles = ["Introduction", "Core Concepts", "Algorithm", "Implementation", "Case Studies", "Advanced Topics", "Summary", "Exercises"]
        return random.choice(titles)
    
    def _random_section_title_en(self) -> str:
        titles = ["Definition", "Mathematical Derivation", "Pseudocode", "Experiments", "Related Work", "Limitations"]
        return random.choice(titles)
    
    def generate_batch(self, num_docs: int, chinese_ratio: float = 0.7) -> List[str]:
        generated_files = []
        for i in range(num_docs):
            is_chinese = random.random() < chinese_ratio
            titles = CHINESE_TEXTBOOK_TITLES if is_chinese else ENGLISH_TEXTBOOK_TITLES
            
            config = DocumentConfig(
                title=random.choice(titles),
                num_chapters=random.randint(5, 12),
                sections_per_chapter=random.randint(2, 5),
                pages_per_section=random.randint(3, 8),
                is_chinese=is_chinese
            )
            
            filepath = self.generate_pdf(config)
            if filepath:
                generated_files.append(filepath)
        
        print(f"\n🎉 批量生成完成: {len(generated_files)} 个 PDF 文件")
        return generated_files

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SpineDoc 合成 PDF 生成器")
    parser.add_argument("--num", type=int, default=10, help="生成 PDF 数量")
    parser.add_argument("--output", type=str, default="./test_data/synthetic", help="输出目录")
    args = parser.parse_args()
    
    if not HAS_REPORTLAB:
        print("请先安装: pip install reportlab")
        return
    
    generator = SyntheticPDFGenerator(output_dir=args.output)
    generator.generate_batch(args.num)

if __name__ == "__main__":
    main()
