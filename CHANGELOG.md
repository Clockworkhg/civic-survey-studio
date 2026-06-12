# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-12

### Added

- Excel/CSV 问卷数据加载（支持多工作表）
- 变量类型自动推断（数值 / 分类 / 有序 / 二分类 / 文本 / 日期 / ID）
- 数据质量报告（缺失值、异常值检测）
- 单变量分析（描述统计、频数分布）
- 双变量分析（交叉表、卡方检验、ANOVA、t 检验）
- 多变量分析（OLS 多元线性回归、Pearson/Spearman 相关）
- 二元逻辑回归（OR 值、显著性、模型拟合）
- 交互式可视化图表（柱状图、饼图、直方图、箱线图、散点图、热力图、雷达图）
- AI 报告生成（支持 OpenAI、DeepSeek、Moonshot、SiliconFlow、自定义 API）
- 文献综述检索（Semantic Scholar / OpenAlex / CrossRef）
- 政策背景材料注入
- 多种报告导出格式（Markdown / HTML / DOCX）
- 5 套内置 HTML 报告主题（学术白底 / 政务蓝白 / 现代看板 / 简洁课程 / 商业咨询）
- 内置示例数据（150 条模拟政府服务满意度问卷 + 变量说明表）
- 新手引导（快速上手指南、无 API Key 提示）
- 隐私风险提示与逐变量 AI 发送控制
- API Key 脱敏与 secrets 扫描
- CI（GitHub Actions：pytest + test_run4）
- 安全文档（docs/security.md）
- 模块化 UI 架构（app.py 降至 258 行，10 个 Tab 独立模块）
- 统一配置模型（LLMConfig / ReportConfig / PromptSection）
- 用户设置持久化（API Key 记住功能）

### Fixed

- 0/1 二分类变量误判为 ordinal 的问题
- 二分类因变量缺少逻辑回归的缺陷
- 标准差星号转义问题（中文 LaTeX 环境）
- app.py 过度臃肿问题（2,510 行 → 258 行）
- outputs 安全提示缺失
- 真实 API Key 误留在 `config/user_settings.json` 的发布风险
- 变量隐私分类不明确、AI 发送前无确认的问题
- 文献检索空结果/失败时缺乏友好提示

### Security

- API Key 脱敏（`mask_api_key` / `contains_potential_secret` / `redact_potential_secrets`）
- secrets 扫描测试（`tests/test_no_secrets_committed.py`）
- `outputs/` 目录在 `.gitignore` 中忽略，UI 中展示安全提示
- AI 发送前隐私确认（高风险变量汇总 + 逐变量控制）
- `docs/security.md`（7 章节完整安全文档）
- `config/user_settings.json` 已纳入 `.gitignore`
