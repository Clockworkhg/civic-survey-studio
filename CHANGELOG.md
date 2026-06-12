# Changelog

All notable changes to CivicSurvey Studio (问策 Insight) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-06-13

### Fixed

- 「查看快速开始」按钮跳转 `/docs/quickstart.md` 导致空白页（Streamlit 不服务该路径）
- 首页 Hero 与侧边栏各有一个「加载示例数据」按钮，造成入口重复
- 首页 Hero 视觉偏散（间距、字号、卡片宽度收紧）
- 侧面栏标题 "变量识别精度" → "变量类型推断精度"

### Changed

- 「查看快速开始」改为当前页面 Toggle 展开内置 5 步指南（无 URL 跳转）
- 首页 Hero 移除重复的加载示例数据按钮，改为引导文字指向侧边栏
- 首页 Hero 区域、3 张起步卡片、5 步流程卡片的间距和字号做收敛式调整
- `app.py` 对 landing 函数使用 `getattr` 防御性调用，避免缺失时整页崩溃
- `src/ui/messages.py` 新增 `__all__` 显式导出

### Added

- `get_quickstart_guide()` 内置 5 步快速开始 HTML（不依赖文件读取）
- AppTest 集成测试（`test_app_starts_without_exception`）验证真实 Streamlit 启动
- Import guard 测试（`test_landing_functions_importable_and_callable` 等 4 个）
- 首页 HTML 不含 `/docs/quickstart.md` 路由的回归测试

### Test Suite

- pytest: 687 → 697 passed
- Streamlit smoke tests: 15 → 22 passed
- 新增：2 个 AppTest 集成测试 + 2 个 quickstart 安全测试 + 2 个 smoke 回归测试

## [0.1.0] - 2026-06-12

### Added

- 5 步工作流（数据与变量 → 分析方案 → 统计分析 → 可视化仪表盘 → 报告工作台）
- 统一状态流（AnalysisContext 作为唯一数据源，precomputed results 模式消除重复分析）
- Excel/CSV 问卷数据加载（支持多工作表）
- 变量类型自动推断（数值 / 分类 / 有序 / 二分类 / 文本 / 日期 / ID）
- 变量说明表贯穿（中文变量名、取值说明贯穿图表/统计/payload/AI 报告全流程）
- 数据质量报告（缺失值、异常值检测）
- 单变量分析（描述统计、频数分布）
- 双变量分析（交叉表、卡方检验、ANOVA、t 检验）
- 多变量分析（OLS 多元线性回归、Pearson/Spearman 相关）
- 二元逻辑回归（OR 值、显著性、模型拟合）
- 交互式可视化图表（柱状图、饼图、直方图、箱线图、散点图、热力图、雷达图）
- AI 推荐分析方案生成
- AI 辅助 Markdown 报告生成（支持 OpenAI、DeepSeek、Moonshot、SiliconFlow、自定义 API）
- AI-safe payload 隐私过滤（filter_payload_for_ai 从 9 个 payload 节中移除排除变量）
- 文献综述检索（Semantic Scholar / OpenAlex / CrossRef）
- 政策背景材料注入
- 多种报告导出格式（Markdown / HTML / DOCX）
- 统一报告渲染管线（Markdown→HTML/DOCX 结构化渲染）
- 5 套内置 HTML 报告主题（学术白底 / 政务蓝白 / 现代看板 / 简洁课程 / 商业咨询）
- 内置示例数据（150 条模拟政府服务满意度问卷 + 变量说明表）
- 多 LLM Provider 配置（config/llm_providers.yaml）
- Streamlit 工作台界面（产品化首页、5 区段侧边栏、卡片式配置摘要）
- 用户设置持久化（API Key 记住功能）
- CI（GitHub Actions：pytest + test_run4）
- 安全文档（docs/security.md）
- DESIGN.md 设计系统驱动的界面风格约束
- 模块化 UI 架构（12 个 Tab 独立模块）

### Fixed

- AI 推荐方案采用后下游不同步（selectbox 回退覆盖 config 导致"尚未设置核心变量"误报）
- Streamlit widget session_state 写入时机错误
- Tab 割裂和重复分析（所有分析展示 Tab 从 precomputed results 读取）
- 0/1 二分类变量误判为 ordinal 的问题
- 二分类因变量缺少逻辑回归的缺陷
- DOCX Markdown 残留（`#`/`**`/Markdown 语法）
- HTML `\/` 和 JSON 转义残留
- AI 输出 JSON 包裹未解包
- 隐私过滤覆盖不全（data_overview.column_names、analysis_plan、warnings 等）
- user_settings.json API Key 泄露风险
- UI release blocker（旧 Markdown 表格、emoji 标题、AI 配置入口回归）
- 文献检索空结果/失败时缺乏友好提示

### Security

- `config/user_settings.json` 被 .gitignore 排除
- 只保留 `config/user_settings.example.json` 模板（不含真实 API Key）
- AI prompt 使用 privacy-filtered payload（filter_payload_for_ai 全面过滤 9 个 payload 节）
- 禁发变量不进入 AI prompt（变量名称映射、分析结果、warnings、metadata 中移除）
- API Key 脱敏（mask_api_key / contains_potential_secret / redact_potential_secrets）
- secrets 扫描测试（tests/test_no_secrets_committed.py）
- outputs/ 目录在 .gitignore 中忽略
- AI 发送前隐私确认（高风险变量汇总 + 逐变量控制）
