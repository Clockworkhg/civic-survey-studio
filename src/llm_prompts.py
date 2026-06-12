"""LLM 提示词模板。

提供两套提示词：
  1. build_ai_report_prompt()    — 新版多结构/多风格/多长度
  2. build_ai_report_prompt()    — 新版多结构/多风格/多长度

新版支持：
  - 5 种报告结构（通用调研 / 学术论文 / 政务决策 / 商业分析 / 课程作业）
  - 4 种写作风格（课程作业风 / 政务汇报风 / 学术报告风 / 商业分析风）
  - 3 种报告长度（简短版 / 标准版 / 详细版）
"""

import json
from datetime import date, datetime
from typing import Any, List, Optional, Tuple

import numpy as np
import pandas as pd


def _make_json_safe(obj: Any) -> Any:
    """递归将 numpy/pandas 类型转为 JSON 可序列化类型。"""
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    try:
        if pd.isna(obj) and not isinstance(obj, (str, list, dict, tuple, set)):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        val = float(obj)
        return None if np.isnan(val) or np.isinf(val) else val
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.ndarray,)):
        return [_make_json_safe(v) for v in obj.tolist()]
    if isinstance(obj, dict):
        return {str(k): _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_make_json_safe(v) for v in obj]
    return obj


# ================================================================
# 核心原则（所有报告共用）
# ================================================================

_CORE_PRINCIPLES = """## 核心原则（必须严格遵守）

1. **只基于给定数据撰写**：你必须严格基于下面提供的分析结果 payload 撰写报告内容。分析结果全部存储在 `analysis_results` 列表中，请遍历该列表获取所有可用分析。
2. **不编造数据**：不得编造任何数据、数字、百分比、统计量。所有数值必须来自 payload。如果 payload 中没有某项分析（如线性回归），绝不能假装该分析存在。
3. **正确解读显著性**：
   - p < 0.01 可描述为"高度显著"或"在 1% 水平上显著"
   - p < 0.05 可描述为"显著"或"在 5% 水平上显著"
   - p ≥ 0.05 应描述为"未达到统计显著性"或"无显著差异"
   - 绝对不能把不显著的 p 值写成显著影响
4. **相关不等于因果**：相关分析结果只能描述为"存在相关关系"、"正相关"或"负相关"。绝对不能使用"导致"、"引起"、"影响"、"决定了"等因果性措辞。回归分析结果只能描述为"统计关联"，不能断言因果关系。
5. **谨慎用语**：使用"数据表明"、"分析结果显示"、"样本中呈现"、"结果提示"等数据驱动措辞。避免"证明了"、"必然说明"等绝对表达。如果数据不足以支持某项结论，必须明确写"当前数据不足以证明……"。
6. **缺失值处理**：如果变量有缺失值，报告中应提及，并说明分析基于有效样本量。
7. **隐私变量处理**：如果 `user_analysis_config.excluded_sensitive_variables` 非空，在数据概述中提及已排除的变量及排除原因。对于 `privacy_restricted_variables` 中的变量，说明其因隐私设置仅以聚合统计形式纳入分析。**不得**编造这些变量的原始数据或具体值。
8. **跳过分析处理**：对于 `analysis_results` 中 `analysis_type` 为 `skipped` 的条目，在报告中无需展开，但可在"研究局限"中简要说明。
9. **变量名显示规则（必须严格遵守）**：
   - 报告中所有变量必须使用中文显示名。`project_meta.variable_name_map` 提供了每个英文列名对应的中文显示名的完整映射。
   - **绝对禁止**在报告正文中出现英文列名（如 overall_satisfaction、wait_time_min、exhibit_quality 等）。这些是后台数据库的内部索引名，读者不应该看到。
   - **禁止**使用 "exhibit_quality（展陈质量）" 这种同时暴露英文名和中文名的写法。应直接写"展陈质量"，完全不出现英文列名。
   - 英文列名仅供内部索引，不对报告读者暴露。
   - 如果某个变量在 variable_name_map 中找不到中文名，使用 `variable_schema` 中该变量的 `display_name` 字段。如果所有映射中都没有中文名，**你必须根据变量含义自行给出合理的中文名称**（如 exhibit_quality → 展陈质量，service_rating → 服务评分），并全程使用该中文名。
   - 表格中同样禁止出现英文列名，表头必须使用中文显示名。
   - **变量首次出现时必须用中文名，后续也始终保持中文名。正文中绝不能出现一次英文字段名。**
"""

_LANGUAGE_QUALITY_RULES = """## AI 输出质量约束

1. 不要出现"根据您提供的数据，我认为一定……"这种绝对表达。
2. 不要出现"显著影响"，除非对应 p 值小于 0.05。
3. 不要编造政策建议或业务建议（不能编造 analysis_payload 中不存在的政策背景、机构名称或业务场景）。
4. 不要编造变量中文名。必须先查 `project_meta.variable_name_map`，再查 `variable_schema[].display_name`。**绝对禁止**在报告正文中出现英文列名（如 overall_satisfaction、wait_time_min 等后台英文字段名）。所有变量引用必须使用中文显示名。
5. 不要说"本研究证明了……"，应使用"数据显示"、"样本中呈现"、"结果提示"等谨慎说法。
6. 如果无法判断，就写"不足以判断"。
7. 如果需要引用外部文献，但 analysis_payload 没有提供文献，不能伪造参考文献。
8. 不能编造文献综述、理论模型或外部事实（如 analysis_payload 中没有背景材料，只能进行一般性、谨慎的背景说明）。
"""


# ================================================================
# 报告结构定义
# ================================================================

_REPORT_STRUCTURES = {
    "通用调研报告": """## 报告结构：通用调研报告

请按以下 8 个章节生成报告正文（Markdown 格式）。

### 一、数据来源与样本概况
- 说明样本量、变量数量、缺失值、重复行、数据结构。
- 如存在排除的变量，说明排除原因。

### 二、变量结构与数据质量
- 说明变量类型分布、缺失值情况、是否存在不适合分析的变量。
- 提及隐私受限变量的处理方式。

### 三、核心变量分析
- 围绕 target_variable 进行描述统计或频数分析。
- 如果没有 target_variable，则写探索性总体分析。
- 如为数值型：均值、中位数、标准差、分布形态。
- 如为分类/有序型：频数分布、众数类别。

### 四、群体差异分析
- 围绕 group_variables 总结差异。
- 如果有卡方检验、t 检验、方差分析结果，要谨慎说明。
- 如果没有显著差异，不能写成显著。

### 五、变量关系分析
- 围绕 explanatory_variables 与 target_variable 的关系进行说明。
- 如果有相关分析，说明相关方向和强弱。
- 如果有回归分析，说明显著变量和不显著变量。
- 必须写明相关或回归不等于因果。

### 六、主要发现
- 生成 3 到 5 条主要发现。
- 每条发现必须能在 analysis_payload 中找到依据。

### 七、分析建议
- 生成 3 到 5 条建议。
- 建议要和数据结果相关。
- 建议不能写得过度绝对。

### 八、方法说明与局限
- 说明使用了描述统计、频数分析、交叉分析、卡方检验、相关分析、回归分析等方法。
- 说明统计分析用于辅助判断，不替代人工判断。
- 说明样本来源、样本量、变量测量方式可能影响结论解释。
""",

    "学术论文式报告": """## 报告结构：学术论文式报告

请按以下结构生成报告正文（Markdown 格式），使用正式学术论文的风格和组织方式。

### 摘要
- 用 200 到 400 字概括研究背景、数据来源、样本规模、主要方法、核心发现、研究假设验证情况和研究局限。
- 摘要中不能编造不存在的研究结论。
- 不能把相关关系写成因果关系。

### 关键词
- 生成 3 到 5 个关键词。
- 关键词应来自报告主题、研究对象、核心变量、分析方法或理论框架。
- 不要生成 analysis_payload 中完全没有依据的关键词。

### 一、研究背景与问题提出
- 说明为什么该数据或问题值得分析，结合相关领域的现实背景。
- ⚠️ **背景材料规则**：
  - 如果用户提示词中提供了「预生成研究背景」（基于政策调研或文献检索），请基于这些真实材料撰写研究背景。你可以整合和概括其中的内容，但必须保留关键的政策名称、时间节点和发现。
  - 如果用户提示词中**未提供**预生成研究背景，则只能进行一般性、谨慎的背景说明，不能编造具体政策、机构名称或改革细节。
- 明确提出本文关注的 2 到 4 个核心研究问题。

### 二、理论基础与研究假设
- 结合 analysis_payload 中的变量结构，构建一个简明的理论分析框架。
- 可以参考但不限于以下通用理论框架（这是方法论的合理说明，不是编造具体文献）：
  - SERVQUAL 服务质量模型（响应性、可靠性、保证性、移情性、有形性五个维度）
  - 期望不一致理论（Expectation-Disconfirmation Theory）：满意度 = 感知绩效 − 期望
  - 公众满意度影响因素模型（服务质量感知 → 满意度 → 行为意向 / 推荐意愿）
  - 社会人口学变量（性别、年龄、学历等）对服务评价的影响机制
- 基于理论框架和分析变量，提出 3 到 5 条可检验的研究假设（Research Hypotheses），编号 H1、H2、...
- 每条假设必须：
  - 明确指出自变量与因变量之间的预期关系方向（如「预期 X 与 Y 呈正相关」或「预期不同 X 组的 Y 存在显著差异」）
  - 基于合理的理论逻辑（一句话说明理论依据即可）
  - 使用「本文假设」「本研究预期」「根据……理论，预期……」等学术表达
- 假设格式示例：
  - 「H1：等待时间满意度与总体满意度之间存在显著正相关关系」
  - 「H2：不同办理渠道的公众总体满意度存在显著差异」
  - 「H3：工作人员态度满意度对总体满意度的正向影响强于流程便利性满意度」
- ⚠️ **文献引用规则**：
  - 如果用户提示词中提供了「预生成文献综述」（基于真实学术文献检索），请保持其核心内容、引用文献（包括作者、年份、标题和 APA 格式引注）和研究假设不变。你可以微调过渡句和连接词以使章节风格与报告整体一致。
  - 如果用户提示词中**未提供**预生成文献综述，则仅引用理论框架的通用名称（如 SERVQUAL、期望不一致理论等），不得虚构具体论文标题、作者姓名、发表年份、期刊名称。
- 假设必须对应 analysis_payload 中实际存在的变量，不能假设不存在的变量间关系。

### 三、数据来源与变量说明
- 说明样本量、变量数量、数据结构、核心变量、分组变量、解释变量。
- 说明变量类型（数值型/分类变量/Likert 量表）和数据质量（缺失率等）。
- 如存在缺失值、重复行或高隐私风险字段，应谨慎说明处理方式。

### 四、研究方法
- 说明使用的统计方法，包括但不限于：描述统计、频数分析、交叉分析、卡方检验、t 检验或方差分析、相关分析、回归分析。
- 对每种方法简要说明其适用场景（如「由于目标变量为连续数值型，使用 OLS 多元线性回归分析各自变量的独立贡献」）。
- 如果某些方法没有实际出现在 analysis_payload 中，不要写成已经使用。
- 必须说明统计分析只能揭示样本中的关联或差异，不能直接证明因果关系。

### 五、实证结果分析
- 本节是报告的核心，必须以统计检验结果为主线组织内容，而非简单的频数罗列。
- 写作原则：先报告检验方法、检验统计量和 p 值，再辅以描述统计作为补充说明。
- 对各分析类型的呈现要求：
  - **群体差异**：先报告卡方检验 / t 检验 / ANOVA 的检验统计量和 p 值，判断是否存在统计显著差异，再描述各组的具体分布特征
  - **相关分析**：先报告 Pearson r 或 Spearman ρ 系数及其显著性水平，再解释相关方向和强度
  - **回归分析**：先报告模型整体解释力（R²、Adj R²、F 检验 p 值），再逐一分析各自变量的回归系数、标准误、t 值和 p 值，区分显著与不显著自变量
- 对于达到统计显著的结果，使用「在 5% 水平上显著」「具有统计显著性（p = X.XXX）」等标准学术表达
- 对于未达到统计显著的结果，如实报告「未达到统计显著性（p = X.XXX > 0.05）」
- 所有报告的数值必须直接引用 analysis_payload 中的数据，不得编造
- 可以按子节组织：样本基本特征、核心变量分布、群体差异检验、变量相关分析、回归结果分析（如果分析结果中存在对应内容）
- 如果没有回归结果，不要编造回归章节；如果没有显著性检验，不要编造 p 值
- 可以引用 1 到 2 张关键数据表（以 Markdown 表格呈现），但表格数据必须来自 analysis_payload

### 六、讨论
- 对照「理论基础与研究假设」章节中提出的研究假设，逐一讨论每条假设是否得到实证支持。
- 对每条假设的讨论格式建议：「H1（……）得到支持 / 未得到支持：……（结合具体统计结果说明）」
- 对得到支持的假设，讨论其理论含义和实践意义
- 对未得到支持的假设，分析可能的解释（如样本特征、变量测量方式、遗漏变量等），但不能编造未在数据中出现的信息
- 对结果进行谨慎解释。可以提出可能原因，但必须使用「可能」「或许」「在样本中呈现」「数据表明」等表达
- 不得使用「证明了」「导致了」「必然说明」等绝对表达
- 讨论应结合数据结果，而不是脱离结果空泛发挥

### 七、结论与建议
- 总结 3 到 5 条主要结论，每条结论应与实证结果直接对应。
- 可在结论末尾加入「假设检验汇总」简表（假设编号 / 假设内容简述 / 检验方法 / 是否得到支持），便于读者快速了解验证情况。
- 提出 3 到 5 条建议。建议应与分析结果对应，并保留必要的谨慎表达。
- 建议应具体、可操作，避免空泛的「加强管理」「提升服务」等套话。

### 八、研究局限与后续展望
- 说明样本规模、样本来源、抽样方式（如未知则说明未知）、变量测量方式、横截面数据限制、模型设定等可能限制。
- 如果 analysis_payload 中没有提供抽样方式，不要假设随机抽样。
- 可提出后续研究方向，例如扩大样本、采用随机抽样、补充定性访谈、引入纵向追踪设计、使用更丰富的量表测量、纳入更多解释变量等。
""",

    "政务决策报告": """## 报告结构：政务决策报告

请按以下 6 个章节生成报告正文（Markdown 格式）。语言要求稳健、规范、谨慎。

### 一、基本情况
- 概述数据来源、样本规模、主要指标概况。
- 不能编造政策背景或机构名称。

### 二、主要数据表现
- 围绕核心变量和主要分组变量，说明数据呈现的主要特征。
- 使用描述统计和频数分析结果。

### 三、突出问题与风险点
- 基于 analysis_payload 中的数据特征和显著性检验结果，识别需要关注的问题。
- 不能夸大问题，也不能编造 payload 中不存在的问题。

### 四、原因分析
- 对发现的问题或特征进行谨慎的原因推测。
- 必须使用"可能"、"或许"、"初步判断"等谨慎表达。
- 不能将相关关系等同于因果关系。

### 五、对策建议
- 提出 3 到 5 条具体、可操作的建议。
- 建议应与数据分析结果对应，避免空泛或脱离数据的建议。
- 语言稳健，不使用过度承诺的表达。

### 六、方法说明与注意事项
- 说明使用的统计方法和分析口径。
- 说明数据局限性和结论适用范围。
- 强调"统计关联不等于因果关系"。
""",

    "商业分析报告": """## 报告结构：商业分析报告

请按以下 7 个章节生成报告正文（Markdown 格式）。语言可以更重视洞察和行动建议，但不能把相关写成因果。

### 一、分析概览
- 概述分析背景、数据规模、核心指标。
- 简要说明分析目标和范围。

### 二、核心指标表现
- 围绕 target_variable 展示核心业务指标的表现。
- 使用描述统计结果。

### 三、用户 / 群体差异
- 围绕 group_variables 总结不同群体的差异特征。
- 标注统计显著性。

### 四、影响因素与业务解释
- 围绕 explanatory_variables 分析影响核心指标的因素。
- 如果有相关分析或回归分析，说明各因素的影响方向和强弱。
- 必须强调"统计关联不等于因果影响"。

### 五、机会点与风险点
- 基于数据发现，识别业务机会和潜在风险。
- 必须基于 analysis_payload 中实际存在的数据模式。

### 六、行动建议
- 提出 3 到 5 条具体行动建议。
- 建议应与数据发现直接关联。

### 七、数据口径与局限
- 说明数据来源、样本规模、分析口径。
- 说明数据局限性和结论适用范围。
""",

    "课程作业报告": """## 报告结构：课程作业报告

请按以下 7 个章节生成报告正文（Markdown 格式）。语言适合课堂展示，清楚、自然、不过度学术化。

### 一、选题说明
- 说明为什么选择该数据或主题进行分析。
- 语言自然，不要过度正式。

### 二、数据说明
- 说明样本量、变量数量、数据来源概况。
- 说明数据质量和处理方式。

### 三、变量说明
- 说明核心变量、分组变量、解释变量的含义和类型。
- 可以适度解释变量测量方式的含义。

### 四、统计分析过程
- 说明使用了哪些统计方法及其适用条件。
- 可以适度解释为什么选择这些方法（如"因为目标变量是数值型，选择 t 检验比较组间差异"）。

### 五、主要分析结果
- 展示描述统计、群体差异、相关分析等主要结果。
- 标注统计显著性。

### 六、结论与反思
- 总结 3 到 5 条主要发现。
- 反思分析过程中遇到的问题或局限。

### 七、方法局限
- 说明统计方法的局限性和结果适用条件。
- 说明样本代表性等限制。
""",
}


# ================================================================
# 写作风格定义
# ================================================================

_STYLE_GUIDES = {
    "课程作业风": """
## 写作风格：课程作业风

- 语言清楚自然，适合课堂展示。
- 不要太像正式公文，避免过度官方的措辞。
- 可以适度解释统计方法含义（如"卡方检验用于判断两个分类变量之间是否存在关联"）。
- 保持专业但不失亲和力。
""",

    "政务汇报风": """
## 写作风格：政务汇报风

- 语言稳健、规范、谨慎。
- 多使用"数据显示"、"样本中呈现"、"建议进一步关注"、"有待持续跟踪"等表达。
- 不要写成商业营销口吻。
- 避免夸张和绝对化表述。
- 用词正式但不僵硬。
""",

    "学术报告风": """
## 写作风格：学术报告风

- 强调研究问题、变量、方法、显著性、局限。
- 多使用"本文"、"样本"、"变量"、"统计检验"、"相关关系"、"回归系数"等表达。
- 不要写成绝对因果判断。
- 使用规范的统计分析术语（如"在 5% 水平上显著"而非"很明显"）。
- 保持客观、严谨的学术语气。
""",

    "商业分析风": """
## 写作风格：商业分析风

- 强调指标表现、群体差异、业务解释和改进方向。
- 可以提出行动建议，但建议必须基于数据发现。
- 不能夸大因果关系或显著性。
- 语言清晰、直接，适合商业决策场景。
- 可以使用"洞察"、"机会点"、"行动项"等商业分析常用表达。
""",
}


# ================================================================
# 报告长度定义
# ================================================================

_LENGTH_GUIDES = {
    "简短版": """
## 报告长度：简短版（硬性字数目标：800-1500 字）

- **字数硬性约束**：报告正文总字数必须在 800-1500 字之间。超出 1500 字视为不合格。
- 每个部分只写 1-2 句话，直奔结论，不展开解释。
- 主要发现和建议各 **最多 2 条**。
- **不写方法说明章节**，方法用一句话带过即可。
- 关键统计量（p 值、r 值、R²）仍需标注，但不解释其含义。
- **最多 1 个表格**，表格只放最核心的数据。
- 示例值引用全部省略。
- 适合快速浏览（2-3 分钟阅读），像执行摘要。
""",

    "标准版": """
## 报告长度：标准版（硬性字数目标：2500-4000 字）

- **字数硬性约束**：报告正文总字数必须在 2500-4000 字之间。不足 2500 字或超出 4000 字视为不合格。
- 每个部分写 2-4 句话，对核心分析结果进行必要的解释。
- 主要发现和建议各 **3 到 5 条**。
- 方法说明和局限部分适度展开（各 1-2 段）。
- 关键统计量标注完整（p 值、r 值、R²、样本量）。
- 表格控制在 **2-4 个**，覆盖核心描述统计和关键检验结果。
- 适合普通调研报告或课程报告（8-12 分钟阅读）。
""",

    "详细版": """
## 报告长度：详细版（硬性字数目标：5000-8000 字）

- **字数硬性约束**：报告正文总字数必须在 5000-8000 字之间。不足 5000 字视为不合格。
- 对数据概况、方法、结果、讨论和局限进行充分展开，每个分析结果都要深入解读。
- 主要发现和建议各 **5 到 8 条**，每条都要有数据支撑和解释。
- **方法说明必须完整**：列出所有使用的统计方法、选择理由、适用条件和局限性。
- 对方法选择、局限性、适用范围进行详细讨论（至少 3 段）。
- 对于不显著的结果，讨论可能的解释，但必须使用谨慎措辞。
- 表格可以覆盖所有分析结果，**4-8 个表格**均可。
- 适合正式报告或论文初稿（15-25 分钟阅读）。
- 但仍然不能编造 analysis_payload 中不存在的信息。
""",
}


# ================================================================
# Payload 结构说明（供 AI 理解数据格式）
# ================================================================

_PAYLOAD_STRUCTURE_DOC = """## Payload 结构说明

- `project_meta` — 报告标题、研究对象、报告风格、生成时间、**variable_name_map（英文列名→中文显示名映射表）**
- `data_overview` — 样本量、变量数、缺失值总数、工作表/文件信息
- `variable_schema` — 每个变量的类型、缺失率、唯一值数、示例值（≤5个）、隐私设置：
  - `privacy_risk` — 隐私风险等级（none/low/medium/high）
  - `privacy_category` — 隐私分类（demographic_attribute/contact_info/direct_identifier/location_info/free_text/sensitive_attribute/financial）
  - `allow_local_stats` / `allow_as_group_variable` / `allow_in_model` / `allow_send_to_ai` — 使用权限
  - `send_to_ai_mode` — AI 发送方式（exclude/aggregate_only/masked_examples/full）
  - **注意**：example_values 为空或类别明细缺失时，可能是因为隐私设置阻止了原始数据发送
- `user_analysis_config` — 目标变量、分组变量、解释变量、各类排除变量：
  - `excluded_id_variables` / `excluded_text_variables` / `excluded_datetime_variables` — 按类型排除
  - `excluded_sensitive_variables` — 因高隐私风险未向 AI 发送明细的变量
  - `privacy_restricted_variables` — 受限但仍以聚合形式纳入分析的变量
- `analysis_plan` — 所有计划执行的分析列表，每项含 analysis_type、variables、method、status（planned/skipped/completed）、skipped_reason
- `analysis_results` — **统一分析结果列表**（核心）。每项含：
  - `analysis_id` — 唯一标识
  - `analysis_type` — 分析类型（categorical_frequency / numeric_descriptive / categorical_categorical_chi_square / categorical_numeric_group_compare / numeric_numeric_correlation / linear_regression / logistic_regression / text_summary / skipped）
  - `variables` / `display_names` / `variable_types` — 涉及的变量信息
  - `method` — 统计方法
  - `result` — 具体结果（格式因 analysis_type 而异）
  - `p_value` / `significant` — 显著性信息
  - `interpretation_hint` — AI 可引用的解读提示
  - `limitations` — 该分析方法的局限性
- `chart_summaries` — 图表的文字摘要（chart_title / chart_type / variables / summary），不含图片
- `warnings` — 分析过程中的警告和注意事项

## analysis_results 中各 analysis_type 的 result 格式

- `categorical_frequency`: `{"valid_count": N, "category_count": N, "mode": "...", "mode_percentage": N, "categories": [{"category": "...", "count": N, "percentage": N}, ...]}`。注意：如果 `categories` 为 `null` 且存在 `_privacy_note` 字段，说明该变量的类别明细因隐私设置未发送，AI 报告中应仅描述其聚合统计量（如类别数、有效样本量），不得编造类别名称。
- `numeric_descriptive`: `{"count": N, "mean": N, "std": N, "median": N, "min": N, "max": N, "q25": N, "q75": N, "skewness": N, "kurtosis": N}`
- `categorical_categorical_chi_square`: `{"chi2": N, "p_value": N, "dof": N, "significant": bool, "crosstab_preview": [...]}`
- `categorical_numeric_group_compare`: `{"group_means": [{"group": "...", "mean": N}, ...], "p_value": N, "significant": bool}`
- `numeric_numeric_correlation`: `{"pearson_r": N, "pearson_p_value": N, "pearson_significant": bool, "spearman_rho": N, "spearman_p_value": N, "sample_size": N, "strength": "..."}`
- `linear_regression`: `{"dependent_variable": "...", "independent_variables": [...], "sample_size": N, "r_squared": N, "adj_r_squared": N, "coefficients": [{"variable": "...", "coefficient": N, "std_error": N, "t_value": N, "p_value": N, "significant": bool}, ...]}`
- `logistic_regression`: `{"dependent_variable": "...", "independent_variables": [...], "sample_size": N, "pseudo_r_squared": N, "log_likelihood": N, "llr_pvalue": N, "coefficients": [{"variable": "...", "coefficient": N, "std_error": N, "z_value": N, "p_value": N, "odds_ratio": N, "or_ci_lower": N, "or_ci_upper": N, "significant": bool}, ...]}`
- `text_summary`: `{"non_null_count": N, "unique_count": N, "avg_length_approx": N}`

## 撰写要求

1. 报告标题从 `project_meta.report_title` 获取。
2. 所有数值请直接引用 payload 中的数据，不得编造。
3. 请遍历 `analysis_results` 列表，根据其中实际存在的条目撰写报告。如果 `analysis_results` 中没有 `linear_regression` 或 `logistic_regression` 类型的条目，不要在报告中出现"回归分析"章节。如果用户选择的结构要求有该章节，请在章节内说明"当前数据未执行回归分析"。
4. 如果某个变量在 `variable_schema` 中 `missing_rate` > 10%，在报告中提及。
5. 对于 `warnings` 中提到的问题，在报告相应章节中加以说明。
6. 如果 p ≥ 0.05，请如实描述为"未达到统计显著性"或"无显著差异"。
7. 相关分析结果只能说"相关"，不能说"导致"、"引起"、"影响"。引用 `analysis_results` 中 `numeric_numeric_correlation` 类型条目时，必须使用其 `interpretation_hint` 中的措辞指引。
8. 对于 `user_analysis_config.privacy_restricted_variables` 中的变量，说明其因隐私设置仅以聚合统计形式纳入分析。
9. 使用中文撰写。
10. 在报告末尾，单独一行输出一个推荐展示风格标签：`推荐展示风格：xxx`，其中 xxx 只能是以下五个选项之一：学术论文白底风、政务蓝白汇报风、现代数据看板风、简洁课程作业风、商业咨询报告风。根据报告的实际内容和风格，推荐最匹配的展示风格。
"""


# ================================================================
# 新版：build_ai_report_prompt()
# ================================================================

def build_ai_report_prompt(
    analysis_payload: dict,
    report_structure: str = "通用调研报告",
    report_style: str = "学术报告风",
    report_length: str = "标准版",
    literature_review_content: Optional[str] = None,
    background_context: Optional[str] = None,
) -> Tuple[str, str]:
    """构建 AI 报告生成的系统提示词和用户提示词。

    根据用户选择的报告结构、写作风格和篇幅，组装对应的提示词模板。

    Args:
        analysis_payload: build_analysis_payload 输出的字典（注意是 dict，不是 JSON 字符串）
        report_structure: 报告结构类型
            - "通用调研报告"
            - "学术论文式报告"
            - "政务决策报告"
            - "商业分析报告"
            - "课程作业报告"
        report_style: 写作语言风格
            - "课程作业风"
            - "政务汇报风"
            - "学术报告风"
            - "商业分析风"
        report_length: 报告篇幅
            - "简短版"
            - "标准版"
            - "详细版"
        literature_review_content: 可选。预生成的文献综述内容（基于真实学术文献检索）。
            仅在 report_structure == "学术论文式报告" 时生效。
            如果提供，将注入到报告的「理论基础与研究假设」章节中。
        background_context: 可选。预生成的研究背景材料（基于政策调研或文献检索）。
            如果提供，将注入到报告的「研究背景与问题提出」章节中。
            适用于学术论文式报告和政务决策报告。

    Returns:
        (system_prompt, user_prompt) 元组
    """
    # ── 组装系统提示词 ──
    system_parts = [
        "你是一个严谨的数据分析报告撰写助手。",
        "你只能根据用户提供的 analysis_payload 撰写报告。",
        "不得编造 analysis_payload 中不存在的数据、变量、显著性结果、回归结果或图表结论。",
        "如果数据不足以支持某项结论，必须明确写「当前数据不足以证明……」。",
        "不能把相关关系写成因果关系。",
        "不能把不显著的 p 值写成显著影响。",
        "",
        "## ⚠️ 字数硬性约束（最高优先级）",
        "报告中明确标注了硬性字数目标。你必须严格遵守：",
        "- 简短版必须在 800-1500 字之间，超出即不合格",
        "- 标准版必须在 2500-4000 字之间",
        "- 详细版必须在 5000-8000 字之间",
        "字数差异是核心需求，简短版要真的短（像执行摘要），详细版要真的详（像论文初稿）。",
        "写完报告后，请在末尾注明实际总字数：`[总字数：XXX 字]`。",
        "",
        "你必须区分以下四种表述层次：",
        "  1. 描述性发现（数据表格呈现的客观数字）",
        "  2. 统计检验发现（假设检验的结果，标注 p 值）",
        "  3. 可能解释（谨慎的推测，使用「可能」「或许」「在样本中呈现」等表达）",
        "  4. 分析建议（基于数据发现的行动方向，保留必要的谨慎表达）",
        "",
        "报告语言正式、清楚，适合课程展示、调研报告、政务汇报、教学评价、商业分析或学术论文式报告场景。",
        "",
        _CORE_PRINCIPLES,
        "",
        _LANGUAGE_QUALITY_RULES,
    ]

    # 获取结构模板
    structure_template = _REPORT_STRUCTURES.get(report_structure)
    if structure_template:
        system_parts.append(structure_template)
    else:
        # fallback 到通用调研报告
        system_parts.append(_REPORT_STRUCTURES["通用调研报告"])

    # 获取风格指南
    style_guide = _STYLE_GUIDES.get(report_style)
    if style_guide:
        system_parts.append(style_guide)
    else:
        system_parts.append(_STYLE_GUIDES["学术报告风"])

    # 获取长度指南
    length_guide = _LENGTH_GUIDES.get(report_length)
    if length_guide:
        system_parts.append(length_guide)
    else:
        system_parts.append(_LENGTH_GUIDES["标准版"])

    # 添加输出格式要求
    system_parts.append("""
## 输出格式

- 使用 Markdown 格式
- 章节标题使用 ### 三级标题（学术论文式报告中，摘要和关键词部分使用 ### 三级标题）
- 重要数据使用 **加粗**
- 表格使用 Markdown 表格语法
- 直接输出报告正文，无需在开头或结尾添加"好的，以下是报告："等说明性文字
""")

    system_prompt = "\n".join(system_parts)

    # ── 组装用户提示词 ──
    # 将 payload 转为 JSON 字符串（先转换 numpy/pandas 类型）
    payload_json = json.dumps(_make_json_safe(analysis_payload), ensure_ascii=False, indent=2)

    # 检查 payload 特征以添加条件提示
    from src.payload_inspector import (
        payload_has_target,
        payload_has_regression,
        payload_has_logistic_regression,
        payload_has_significance,
    )
    target = analysis_payload.get("user_analysis_config", {}).get("target_variable", "")
    has_regression = payload_has_regression(analysis_payload)
    has_logistic = payload_has_logistic_regression(analysis_payload)
    has_significance = payload_has_significance(analysis_payload)

    conditional_notes = []
    if not target:
        conditional_notes.append(
            "- ⚠️ 当前未指定核心结果变量（target_variable），请按探索性分析方式写作，"
            "关注各变量的分布特征和变量间的关联关系。"
        )
    if not has_regression:
        conditional_notes.append(
            "- ⚠️ 当前 analysis_payload 中没有回归分析结果，请勿在报告中撰写回归分析相关章节。"
            "如果所选报告结构要求有该章节，请在章节内简要说明「当前数据未执行回归分析」即可。"
        )
    if not has_significance:
        conditional_notes.append(
            "- ⚠️ 当前 analysis_payload 中没有显著性检验结果，请勿编造 p 值或显著性判断。"
            "报告中应聚焦于描述统计和探索性分析。"
        )

    # 积极提示：当有显著性/回归结果且为学术报告时，引导 AI 以检验结果为主线
    if has_significance and report_structure == "学术论文式报告":
        conditional_notes.append(
            "- ✅ 当前 analysis_payload 中包含显著性检验结果（卡方检验、t 检验/ANOVA、相关分析等）。"
            "请在「实证结果分析」章节中以检验方法 + p 值为核心组织内容，"
            "先报告检验统计量和显著性水平，再辅以描述统计。不要仅罗列频数分布而忽略显著性检验。"
        )
    if has_regression and report_structure == "学术论文式报告":
        if has_logistic:
            conditional_notes.append(
                "- ✅ 当前 analysis_payload 中包含二元逻辑回归分析结果。"
                "请在「实证结果分析」章节中重点报告：模型拟合优度（伪R²、似然比检验）、"
                "各自变量的优势比（OR）及其 95% 置信区间、z 值和 p 值，"
                "区分显著与不显著自变量。请注意优势比（OR）表示自变量每变化 1 个单位，"
                "目标事件发生几率的变化倍数（OR > 1 为增加，OR < 1 为降低）。"
                "在「讨论」中结合回归结果逐条验证研究假设。"
            )
        conditional_notes.append(
            "- ✅ 当前 analysis_payload 中包含回归分析结果。"
            "请在「实证结果分析」章节中重点报告：模型整体解释力、"
            "各自变量的回归系数或优势比、标准误、显著性（p 值），"
            "区分显著与不显著的自变量。在「讨论」中结合回归结果逐条验证研究假设。"
        )

    # ── 组装 PromptSection 列表（统一注入逻辑）──
    from src.config_models import PromptSection, inject_prompt_sections
    from src.report_options import LIT_APPLICABLE_STRUCTURES, BG_APPLICABLE_STRUCTURES

    sections: List[PromptSection] = []

    # 条件提示（最高优先级 → 出现在最前面）
    if conditional_notes:
        sections.append(PromptSection(
            key="conditional_notes",
            title="⚠️ 条件提示",
            content="\n".join(conditional_notes),
            priority=100,
        ))

    # 文献综述（仅适用结构生效）
    if literature_review_content and report_structure in LIT_APPLICABLE_STRUCTURES:
        sections.append(PromptSection(
            key="literature_review",
            title="⚠️ 预生成文献综述（基于真实学术文献检索）",
            content=literature_review_content,
            instructions=(
                "以下是基于你的研究主题通过学术数据库检索并合成的文献综述。"
                "请在报告的「二、理论基础与研究假设」章节中使用此内容。\n"
                "保持其核心内容、引用文献和研究假设不变。"
                "你可以微调过渡句和连接词以匹配报告整体风格。"
            ),
            priority=50,
        ))

    # 研究背景（仅适用结构生效）
    if background_context and report_structure in BG_APPLICABLE_STRUCTURES:
        sections.append(PromptSection(
            key="background_context",
            title="⚠️ 预生成研究背景（基于政策/文献调研）",
            content=background_context,
            instructions=(
                "以下是基于你的研究主题通过结构化调研获取的背景材料。"
                "请在报告的「研究背景与问题提出」（或相应章节）中使用此内容。\n"
                "可以整合和概括其中的信息，但需保留关键的政策名称、时间节点和发现。"
            ),
            priority=40,
        ))

    user_prompt = f"""请基于以下统计分析结果撰写数据分析报告。

报告结构类型：{report_structure}
写作风格：{report_style}
报告长度：{report_length}
"""

    # 统一注入所有 section（按 priority 排序，空 content 跳过，同 key 去重）
    user_prompt = inject_prompt_sections(user_prompt, sections)

    user_prompt += f"""
## 分析结果数据 (Analysis Payload)

下面是经过程序统计计算后的结构化分析结果。**你只能基于这些数据撰写报告，不能编造任何数据。**

```json
{payload_json}
```

{_PAYLOAD_STRUCTURE_DOC}

请现在开始撰写完整的数据分析报告。"""

    return system_prompt, user_prompt

# ================================================================
# 文献综述合成提示词
# ================================================================

_LITERATURE_REVIEW_SYSTEM_PROMPT = """你是一位严谨的学术文献综述撰写助手。你的任务是根据提供的真实学术文献列表和调查报告上下文，撰写一份高质量的「理论基础与研究假设」章节。

## 核心原则

1. **只引用提供的文献**：你只能引用下方用户提示词中列出的论文。绝对不能编造任何未在列表中的论文标题、作者姓名、发表年份、DOI 或期刊名称。
2. **真实引用优先**：优先引用有 DOI 的论文。在正文中使用 APA 第7版格式的括号引注，如 (Author, Year) 或 Author et al. (Year)。
3. **理论与数据结合**：将文献中的理论框架与调查数据中涉及的变量联系起来。解释为什么已有的研究发现可以为当前调查的研究假设提供理论基础。
4. **提出可检验假设**：基于文献综述，提出 3 到 5 条具体、可检验的研究假设（编号 H1、H2、...），每条假设必须：
   - 明确指出自变量与因变量之间的预期关系方向
   - 基于文献中的理论逻辑（一句话说明依据即可）
   - 对应调查数据中实际存在的变量
5. **结构清晰**：
   - 以 2-4 段综述开头，概括该领域的研究现状和主要理论视角
   - 然后按主题组织文献（如「服务质量维度与满意度」、「人口学变量的调节作用」等）
   - 在每个主题下，合成多篇文献的发现（不要写成逐篇摘要）
   - 最后过渡到研究假设
6. **谨慎表达**：使用「研究表明」「X 等人发现」「文献提示」等学术表达。不要使用「证明了」「必然说明」等绝对措辞。
7. **语言**：使用正式学术中文。英文文献的作者名和关键术语可以保留英文。
8. **格式**：使用 Markdown 格式。在正文中使用 APA 括号引注：(Author, Year)。不要单独列出参考文献列表（这由程序自动附加）。

## 输出格式

直接输出「二、理论基础与研究假设」章节的完整内容，不要添加章节标记以外的其他说明。

### 二、理论基础与研究假设

[你的文献综述和假设推导内容写在这里]
"""


def build_literature_review_prompt(
    papers: list,
    survey_context: dict,
) -> Tuple[str, str]:
    """构建文献综述合成的 LLM 提示词。

    Args:
        papers: PaperRecord.to_dict() 的列表，每项包含:
            title, authors, year, doi, abstract, source, url, venue, apa_citation
        survey_context: 调查上下文，包含:
            report_title, research_subject, target_variable,
            variable_descriptions, key_findings_summary

    Returns:
        (system_prompt, user_prompt) 元组
    """
    # ── 构建论文列表文本 ──
    papers_text_parts = []
    for i, paper in enumerate(papers, 1):
        parts = [f"**[{i}] {paper.get('title', 'Unknown Title')}**"]
        if paper.get("authors"):
            parts.append(f"  作者: {', '.join(paper['authors'])}")
        if paper.get("year"):
            parts.append(f"  年份: {paper['year']}")
        if paper.get("venue"):
            parts.append(f"  期刊: {paper['venue']}")
        if paper.get("doi"):
            parts.append(f"  DOI: {paper['doi']}")
        if paper.get("abstract"):
            abs_text = paper["abstract"]
            # 截断过长摘要
            if len(abs_text) > 500:
                abs_text = abs_text[:500] + "..."
            parts.append(f"  摘要: {abs_text}")
        parts.append(f"  APA引注: {paper.get('apa_citation', '')}")
        parts.append("")
        papers_text_parts.append("\n".join(parts))

    papers_text = "\n".join(papers_text_parts)

    # ── 构建调查上下文文本 ──
    ctx_parts = []
    if survey_context.get("report_title"):
        ctx_parts.append(f"- 报告主题: {survey_context['report_title']}")
    if survey_context.get("research_subject"):
        ctx_parts.append(f"- 研究对象: {survey_context['research_subject']}")
    if survey_context.get("target_variable"):
        ctx_parts.append(f"- 核心因变量: {survey_context['target_variable']}")
    if survey_context.get("variable_descriptions"):
        ctx_parts.append(f"- 关键变量说明:\n{survey_context['variable_descriptions']}")
    if survey_context.get("key_findings_summary"):
        ctx_parts.append(f"- 已有统计发现（供假设推导参考）:\n{survey_context['key_findings_summary']}")
    ctx_text = "\n".join(ctx_parts)

    # ── 组装用户提示词 ──
    user_prompt = f"""请基于以下真实学术文献，为调查报告撰写「二、理论基础与研究假设」章节。

## 调查背景

{ctx_text}

## 检索到的学术文献（共 {len(papers)} 篇）

{papers_text}

## 写作要求

1. 将这些文献合成为连贯的理论综述（不要逐篇摘要，要按主题组织）
2. 将文献中的理论框架与调查变量联系起来
3. 基于文献和调查变量，提出 3-5 条可检验的研究假设（H1, H2, ...）
4. 使用 APA 第7版括号引注格式引用文献
5. 绝对不编造上述列表中没有的论文

请现在开始撰写「二、理论基础与研究假设」章节。"""

    return _LITERATURE_REVIEW_SYSTEM_PROMPT, user_prompt
