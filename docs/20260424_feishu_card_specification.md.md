   1 # 📇 SpineDoc: 飞书互动卡片 - 工业级视觉规格书 (2026)
       2
       3 **作者**: Uncle Bob & UI Architect
       4 **状态**: 设计稿
       5 **目的**: 将后端的“逻辑主权”具象化为用户可感知的飞书交互体验。
       6
       7 ---
       8
       9 ## 🎨 一、 置信度色彩语义 (Color Confidence System)
      10
      11 我们不只是给一个分数，我们给出的是“立场”：
      12
      13 | 颜色 | 状态 | 触发条件 | 视觉反馈 |
      14 | :--- | :--- | :--- | :--- |
      15 | **🟢 绿色** | **确权支撑** | 多个独立卫星节点/联网证据均指向同一结论，且无冲突。 | 进度条 100%，显示“逻辑闭环” |
      16 | **🟡 黄色** | **疑似孤证** | 仅有单一来源，或证据链存在时间跨度过大的风险。 | 进度条 40-70%，显示“建议人工复核” |
      17 | **🔴 红色** | **逻辑断层** | **A-mem 发现 Contradict 链接**，或 Git 历史显示曾有重大回滚。 | 进度条闪烁，显示“法律风险/逻辑冲突”
         |
      18 | **🔵 蓝色** | **推论模拟** | 由 LLM 根据现有规则生成的补充建议（非原件）。 | 虚线进度条，显示“AI 生成推论” |
      19
      20 ---
      21
      22 ## 📱 二、 卡片结构定义 (Card Schema)
      23
      24 ### 1. 头部 (Header)
      25 -   **标题**: `🏛️ SpineDoc 联邦判决书`
      26 -   **状态标签**: 根据置信度动态显示 `[已验证]` 或 `[存在冲突]`。
      27
      28 ### 2. 内容主体 (Content)
      29 -   **审计结论**: 精炼的 Markdown 文本，描述逻辑问题。
      30 -   **置信度可视化**: 飞书进度条组件 (Progress bar)。
      31 -   **证据来源**: 自动列出关联的 PDF 文件名和页码。
      32
      33 ### 3. 交互动作区 (Actions)
      34 -   **【查看逻辑演变】 (Primary Button)**:
      35     -   *后端动作*: 调用 `GitVersionControl.diff_chunks()`。
      36     -   *前端效果*: 弹出一个新卡片或跳转到网页，展示逻辑 Diff (红绿对比)。
      37 -   **【追溯 Bitable 资产】 (Link)**:
      38     -   跳转到对应多维表格，查看该逻辑点的全生命周期记录。
      39 -   **【申请人工介入】 (Button)**:
      40     -   触发飞书工作流，转发给法务/导师。
      41
      42 ---
      43
      44 ## 🛠️ 三、 开发实现逻辑 (Implementation)
      45
      46 在 `backend/app/infra/lark_card_builder.py` 中实现：
      47
      48 ```python
      49 class VerdictCardBuilder:
      50     def build_verdict_card(self, verdict_data: Dict):
      51         # 1. 映射置信度颜色
      52         color = self._map_confidence_to_color(verdict_data['confidence'])
      53         
      54         # 2. 构建飞书消息卡片 JSON (符合 2026 最新开放平台规范)
      55         card_json = {
      56             "config": {"wide_screen_mode": True},
      57             "header": {
      58                 "title": {"tag": "plain_text", "content": "🏛️ SpineDoc 逻辑审计判定"},
      59                 "template": color  # "red", "green", etc.
      60             },
      61             "elements": [
      62                 {
      63                     "tag": "div",
      64                     "text": {"tag": "lark_md", "content": verdict_data['text']}
      65                 },
      66                 {
      67                     "tag": "hr"
      68                 },
      69                 {
      70                     "tag": "action",
      71                     "actions": [
      72                         {
      73                             "tag": "button",
      74                             "text": {"tag": "plain_text", "content": "🔍 查看逻辑 Diff"},
      75                             "type": "primary",
      76                             "value": {"action": "view_diff", "chunk_id": verdict_data['id']}
      77                         }
      78                     ]
      79                 }
      80             ]
      81         }
      82         return card_json
      83 ```
      84
      85 ---
      86
      87 ## 💡 四、 给评委的“必杀技”
      88
      89 在演示时，我们可以手动修改一个 PDF 的内容（比如修改金额），再次导入。
      90 1.  **A-mem** 立即在飞书卡片上报出 **🔴 红色**。
      91 2.  点击 **【查看逻辑 Diff】**，评委能直接在飞书里看到 Git 记录下的“金额由 100 变为 1000”的物理变更证据。
      92 3.  **这不仅是 AI，这是拥有“记忆主权”的专业级审计工具。**