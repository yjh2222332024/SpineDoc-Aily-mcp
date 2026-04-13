"""
SpineDoc KeyBERT 原子测试 (The Semantic Probe)
===========================================
目的：验证 LogicRefiner V2.0 在复杂正文下的关键词提取质量。
"""

import asyncio
import sys
from pathlib import Path

# 🏛️ 确保导入路径
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.app.services.rag.logic_refiner import LogicRefiner

TEST_TEXT = """
度。在实际应用中可以通过降低速率来提高安全性。例如，通过增大容量c的取值，减小
位速率r的取值来提高安全性，反之亦然。SHA-3的默认值是c=1024位，r=576位，于
是b=1600位
海绵结构包括两个阶段，吸水阶段和挤水阶段
①吸水阶段
吸水阶段的过程如下：在每轮的选代处理中，对长度为r的数据块，填充c个0，使
输人数据块的长度从r位扩展为b位，b=r+c；然后将扩展后的数据分组和状态变量S进
行异或得到b位的结果，并作为迭代函数f的输人。选代函数f的输出作为下一轮迭代中
的状态变量S。因为输入数据经过填充后被分为k个r位的数据块，所以吸水阶段要迭代
处理k次结束。
如果需要的Hash码的长度/≤b，那么在吸水阶段完成后，则返回状态变量S的前！
位作为Hash码，海绵结构的运行结束，如图5-5（a）所示。否则，海绵结构进入挤水阶
段。
在吸水阶段，每一轮选代处理前都要给r位的数据分组填充c个0，使数据块长度变
成b位。这一过程很像海绵吸水，这里的"水”就是填充的c个0。
②挤水阶段
在挤水阶段阶段，首先把S的前r位保留作为输出分组Z，然后选代函数f对S进行
处理。如此继续。在每轮选代中都是通过执行f函数来更新S的值，S的前r位被依次保
留作为输出分组Z，并与前面已生成的各分组连接起来。该处理过程共需要（-1）次选
system
You should follow the instructions carefully and explain your answers in detail.user
 OCR with format: assistant
代, 直到满足 \((j-1) \times r<l \leqslant j \times r\) 时, 得到 \(Z=Z_{0} \| Z_{1} \| \cdots \| Z_{j-1} \|\) 。最后, 输 出 \(Z\) 的前 \(l\)
位作为Logb 研
位作为Hash码。如图5-5（b）所示。
在挤水阶段，每一轮迭代处理前都要从长度为6的状态变量S中取出r位的分组，并
丢弃其余的c位分组。这一过程很像海绵挤水，这里的“水”就是丢弃的c位分组
（3）输出数据处理完毕，输出Hash码。
当Hash码长度1小于等于输入数据的分组长度6时，海绵结构在吸水阶段完成后结
束，输出状态变量S的前I位作为Hash码。
当Hash码长度l大于输人数据的分组长度b时，海绵结构还要进行挤水处理，在挤
水阶段完成后产生输出块Z=Z，Z，"，Z-1，并输出Z的前I位作为Hash码。
海绵结构灵活，除了用作密码学Hash函数之外，还可用作伪随机数发生器。把长度
为r的短数据作为输人种子，海绵函数处理得结果就是随机性良好的伪随机数。
由图5-5可知，海绵结构的一大特点是，无论是在吸水阶段还是在挤水阶段，其选代
处理都是等长的数据变换，并没有进行压缩。这一点与Merkle提出的选代压缩结构不同，
从根本上避免了内部压缩函数在客观上存在的碰撞。海绵结构的压缩是通过在吸水阶段或
挤水阶段最后的截出Hash码、丢弃其余数据来实现的。
(4）海绵函数的形式化描述。
海绵函数由以下参数定义：
M是输人数据。
I是输出Hash码的长度。
"""

async def test_refiner_quality():
    print("🚀 [Probe] 正在启动语义指纹提取测试...")
    refiner = LogicRefiner()
    
    # 执行精炼
    result = await refiner.refine_chunk(TEST_TEXT, "Test Chapter")
    
    print("\n" + "="*40)
    print("🏛️ [Probe] 语义解析报告：")
    print(f"标签数量: {len(result['logic_tags'])}")
    print(f"标签内容: {', '.join(result['logic_tags'])}")
    print("-"*20)
    print(f"摘要预览: {result['summary']}")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(test_refiner_quality())
