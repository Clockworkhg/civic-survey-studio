# CivicSurvey Studio（问策 Insight）— 视觉系统

## 1. 产品定位

CivicSurvey Studio 是 AI 辅助问卷统计分析与报告生成工作台。

5 步工作流：数据与变量 → 分析方案 → 统计分析 → 可视化仪表盘 → 报告工作台。

界面应呈现为严肃的数据分析工作台，而非花哨的 AI Demo。

### 品牌关键词

- 克制
- 正式
- 清爽
- 专业
- 可信
- 数据感
- 轻量 AI 辅助感

### 不应呈现的

- 默认 Streamlit Demo 拼装感
- 过多 emoji
- 大面积彩色警告块
- 霓虹渐变
- 玻璃拟态
- 过度装饰的 AI 产品风格
- 老旧政务门户感

---

## 2. 色彩系统

### 主色板

```text
Background:        #F7F8FA
Surface:           #FFFFFF
Surface Subtle:    #F2F4F7
Surface Muted:     #EEF2F6

Primary:           #245B7D
Primary Hover:     #1E4C69
Primary Soft:      #E8F1F6

Secondary:         #6B7280
Secondary Soft:    #F3F4F6

Accent:            #B7791F
Accent Soft:       #FFFCF5

Success:           #2F855A
Success Soft:      #EAF7F0

Warning:           #B7791F
Warning Soft:      #FFF8E5

Error:             #C2410C
Error Soft:        #FFF1EC

Text Strong:       #18212F
Text:              #344054
Text Muted:        #667085
Text Subtle:       #98A2B3

Border:            #E4E7EC
Border Strong:     #D0D5DD
Divider:           #EAECF0
```

### 使用规则

- `Primary` 用于主操作、激活步骤、选中态
- `Accent` 仅用于 AI 建议和推荐高亮
- `Success` 仅用于已完成的工作流步骤
- `Warning` 仅用于非阻塞提示
- `Error` 仅用于阻塞性错误
- 禁止大面积使用饱和红/绿/蓝/紫背景
- 禁止渐变用于主布局区域
- 避免彩虹分类色

---

## 3. 字体

```text
font-family:
  Inter, ui-sans-serif, system-ui, -apple-system,
  BlinkMacSystemFont, "Segoe UI", "PingFang SC",
  "Microsoft YaHei", "Noto Sans CJK SC", sans-serif
```

### 字号层级

```text
Page Title:        28px / 36px / 700
Section Title:     20px / 28px / 650
Card Title:        16px / 24px / 650
Body:              14px / 22px / 400
Small Body:        13px / 20px / 400
Caption:           12px / 18px / 400
Metric Value:      28px / 34px / 700
```

### 规则

- 页面标题简短具体
- 不在每页顶部放冗长说明段落
- 次要说明用 muted caption
- 不过度使用加粗
- UI 里不出现 Markdown 格式文字
- 中文 UI 文案简洁自然

---

## 4. 布局

```text
最大内容宽度: 1180px
主页面 padding: 24px 32px
分区间距: 24px
卡片间距: 16px
```

### 每页结构

1. 页面 Header
2. 流程状态条
3. 主操作区
4. 内容卡片区
5. 详情/高级选项放入 expander

---

## 5. 形状与阴影

```text
小圆角:      6px
默认圆角:    10px
大圆角:      14px
胶囊圆角:    999px
```

- 优先使用边框而非阴影
- 默认边框: `1px solid #E4E7EC`
- 卡片阴影: `0 1px 2px rgba(16, 24, 40, 0.04)`
- 浮起卡片: `0 4px 12px rgba(16, 24, 40, 0.06)`
- 避免大面积浮动面板、玻璃拟态、重阴影、过度圆角

---

## 6. 导航

5 个主 Tab：

1. 数据与变量
2. 分析方案
3. 统计分析
4. 可视化仪表盘
5. 报告工作台

- Tab 呈现为分段导航
- 激活态使用 Primary Soft 背景 + Primary 文字
- 不用大 emoji 在 Tab 标签
- 每个 Tab 代表一个工作流阶段

---

## 7. 流程状态条

每页顶部紧凑显示：

```
数据已加载 → 变量已识别 → 方案已配置 → 分析已完成 → 报告可生成
```

状态类型：

- Pending: 灰
- Current: 蓝
- Done: 绿
- Warning: 琥珀
- Blocked: 红

---

## 8. 卡片

### 标准卡片

```text
背景: #FFFFFF
边框: 1px solid #E4E7EC
圆角: 10px
内间距: 18px
阴影: 0 1px 2px rgba(16, 24, 40, 0.04)
```

### 指标卡片

- 小标签
- 大数值
- 可选 muted 提示
- 可选状态指示

### 推荐卡片（AI）

```text
背景: #FFFCF5
边框: 1px solid #F5D78E
强调色: #B7791F
```

### 错误卡片

仅用于阻塞性问题：

```text
背景: #FFF1EC
边框: 1px solid #FDBA9A
文字: #9A3412
```

---

## 9. 按钮

### 主按钮

```text
背景: #245B7D
悬停: #1E4C69
文字: #FFFFFF
圆角: 8px
高度: 38px
```

### 次按钮

```text
背景: #FFFFFF
边框: 1px solid #D0D5DD
文字: #344054
悬停: #F9FAFB
```

### 幽灵按钮

```text
背景: transparent
文字: #245B7D
悬停: #E8F1F6
```

- 每区域仅一个主按钮
- 按钮文案动词导向
- emoji 仅必要时用于扫描辅助

---

## 10. 表单

- 短标签、长解释放入 help text / caption
- 不堆叠过多控件
- 高级选项收入 expander
- 空必填字段显示冷静的内联 warning

### Select / Multiselect

- 优先显示中文标签
- 原始列名作为次要文本
- 例: `总体满意度 satisfaction_total`

---

## 11. 表格

- 紧凑可读行高
- 有限变量字典时使用中文标签
- 元数据用 muted 文字
- 变量类型和隐私风险用小 badge

### 变量显示格式

```
中文名称
raw_column_name
```

---

## 12. 图表

- 描述性中文标题
- 使用变量标签而非裸列名
- 主系列用 Primary 蓝色
- 网格线 muted
- 无法生成时显示空状态而非空白

### 空图表状态

```
"尚未选择核心变量"
"当前目标变量不是数值型，无法生成箱线图"
"解释变量不足，无法生成相关性热力图"
```

---

## 13. AI 元素

- 推荐卡片用琥珀强调
- 不用魔法棒、星星过量
- 不用"智能一键完成"类说法
- 用"AI 推荐方案""建议采用""需要人工确认"

### AI 透明度

推荐分析配置时显示：

- 推荐的核心变量
- 推荐的分组变量
- 推荐的解释变量
- 每条推荐的理由
- 风险提示
- 已跳过的变量

---

## 14. 空状态

结构：简短标题 + 明确原因 + 下一步操作

```
还不能生成图表

请先在"分析方案"中选择核心变量，并执行统计分析。
```

- 绝不允许页面空白
- 默认不暴露原始 Python 异常
- 默认不展示大段 JSON

---

## 15. 报告工作台

布局：左侧参数面板 + 右侧预览面板

- 报告预览使用白色文档面
- 最大宽度约 820px
- 良好中文行高
- 无 Markdown 残留
- 无 JSON 转义字符

---

## 16. 侧边栏

仅含全局输入：

- 数据文件上传
- 变量说明表上传
- 预设方案
- API 设置

不放重复的分析配置。

---

## 17. 文案语调

- 清晰、冷静、专业、人类可读、不夸张

禁用：

- "AI 智能赋能""一键洞察全部""秒出专业报告"
- "革命性分析""全自动替你完成"

推荐：

- "生成分析建议""采用推荐方案""执行统计分析"
- "生成报告草稿""请人工复核关键结论"

---

## 18. Streamlit 规则

1. 隐藏或弱化默认 Streamlit 视觉噪音
2. 用自定义 CSS 实现卡片、状态条、badge、报告预览
3. 避免深层嵌套 expander
4. 减少 `st.info/warning/error` 块数量
5. 用自定义空状态卡替代空白页
6. 用 `st.container()` + styled HTML wrapper 做布局
7. 保持原生 widget 功能和可访问性
8. 不破坏 Streamlit 状态规则

---

## 19. 组件命名

`src/ui/components.py` 提供：

- `render_page_header(title, subtitle=None, step=None)`
- `render_pipeline_status(ctx)`
- `render_status_card(title, value, help_text=None, status="neutral")`
- `render_metric_card(label, value, hint=None, status="neutral")`
- `render_empty_state(title, message, action_label=None)`
- `render_config_summary(config, schema_df=None)`
- `render_section(title, description=None)`
- `render_warning_list(warnings)`
- `render_action_bar(primary=None, secondary=None)`

---

## 20. 质量验收标准

每页必须满足：

1. 用户知道当前所在位置
2. 用户知道已完成哪些步骤
3. 用户知道下一步该做什么
4. 视觉层级清晰
5. 没有重复的说明文字
6. 主操作明显
7. 空状态有说明
8. AI 建议明确标记为建议
9. 导出报告像正式文档
