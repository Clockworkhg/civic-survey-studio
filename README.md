# 政府服务满意度问卷 AI 辅助统计分析与报告生成平台

基于 Streamlit 的通用问卷/表格数据分析平台。支持自动变量识别、描述统计、交叉分析、相关分析、回归分析（OLS + 二元逻辑回归）、交互式图表，以及 **AI 自动报告生成**（支持多家 LLM 厂商）。适用于课程作业、调研报告、学术论文、政务决策和商业分析等多种场景。

> **当前版本：v0.1.0** | [变更日志](CHANGELOG.md) | [路线图](docs/roadmap.md) | [已知问题](docs/known_issues.md)

<!-- CI badge: replace with your own after enabling GitHub Actions -->
[![Tests](https://github.com/<user>/<repo>/actions/workflows/tests.yml/badge.svg)](https://github.com/<user>/<repo>/actions/workflows/tests.yml)

## 文档

| 文档 | 说明 |
|------|------|
| [快速开始](docs/quickstart.md) | 5 分钟从零到完整分析流程 |
| [部署说明](docs/deployment.md) | 本地 / Streamlit Cloud / 云服务器部署 |
| [发布检查清单](docs/release_checklist.md) | v0.1.0 发布前逐项确认 |
| [安全说明](docs/security.md) | 数据隐私、API Key 安全、发布前检查 |
| [前端验收](docs/frontend_acceptance.md) | 浏览器手动验收清单 |
| [变更日志](CHANGELOG.md) | 版本更新记录 |
| [路线图](docs/roadmap.md) | 未来版本规划（v0.2.0 → v1.0.0） |
| [已知问题](docs/known_issues.md) | 当前版本限制与注意事项 |
| [AI 使用指南](AI_USAGE.md) | AI 报告功能介绍与配置 |
| [测试指南](TESTING.md) | 测试类型说明与手动测试指南 |

## 示例数据

项目提供了模拟的政府服务满意度问卷数据，可快速体验完整分析流程：

```
examples/
├── government_service_satisfaction_sample.csv  # 150 行模拟数据（11 个变量）
└── variable_dictionary_sample.csv              # 变量说明表
```

示例数据包含满意度结果变量、二分类变量、分类变量、有序变量、数值变量和少量缺失值，**全部为模拟数据，无真实个人信息**。

详见 [快速开始 → 使用示例数据](docs/quickstart.md#第六步使用示例数据体验核心流程)。

## 当前状态

| 指标 | 状态 |
|------|------|
| pytest | 650 passed, 0 failed |
| test_streamlit_app_smoke.py | 15 passed |
| test_run4.py | 73/73 通过 |
| app.py 编译 | ✅ |
| 5 步工作流 | ✅ 完成（数据与变量 → 分析方案 → 统计分析 → 可视化仪表盘 → 报告工作台） |
| 统一状态流 | ✅ 完成（AnalysisContext 作为唯一数据源，precomputed results 模式消除重复分析） |
| 变量元数据统一 | ✅ 完成（中文变量名、取值说明贯穿图表/统计/payload/AI 报告全流程） |
| AI Payload 隐私门控 | ✅ 完成（filter_payload_for_ai 从 9 个 payload 节中移除禁发变量） |
| 报告渲染清洗 | ✅ 完成（统一 Markdown→HTML/DOCX 管线，无 `#`/`**`/`\/`/`\n` 残留） |
| DOCX/HTML 质量验证 | ✅ 完成（ZIP/XML 结构验证、中文编码确认、表格/列表渲染） |
| 安全检查 | ✅ 完成（API Key 脱敏、Secrets 扫描、隐私预检、outputs 安全） |

## 技术栈

| 类别 | 技术 |
|------|------|
| 应用框架 | Streamlit ≥1.28.0 |
| 数据处理 | pandas ≥2.0.0, numpy ≥1.24.0 |
| 文件读取 | openpyxl ≥3.0.0 |
| 可视化 | plotly ≥5.17.0 |
| 统计分析 | scipy ≥1.11.0, statsmodels ≥0.14.0 |
| 报告生成 | python-docx ≥0.8.11 |
| LLM 调用 | requests ≥2.28.0 |
| 配置解析 | pyyaml ≥6.0 |
| 语言 | Python ≥3.11（推荐 3.12；3.13 下 statsmodels 有 DeprecationWarning，不影响功能） |

## 项目结构

```
gov-satisfaction-ai-report/
├── app.py                          # 应用编排入口（5 步工作流：数据→方案→分析→图表→报告）
├── requirements.txt                # Python 依赖清单
├── .env.example                    # 环境变量模板（API Key 参考）
├── run_app.bat                     # Windows 一键启动脚本
├── run_tests.bat                   # Windows 一键测试脚本
├── start.bat                       # Windows 自动创建 venv + 安装依赖 + 启动
│
├── config/
│   ├── llm_providers.yaml          # LLM 厂商配置文件
│   └── user_settings.example.json  # 用户设置模板（复制为 user_settings.json 使用）
├── cache/
│   └── model_catalog.json          # 模型列表缓存
│
├── .github/workflows/
│   └── tests.yml                   # GitHub Actions CI（pytest + test_run4）
│
├── src/
│   ├── ui/                         # Streamlit UI 层
│   │   ├── state.py                #   session_state 初始化
│   │   ├── sidebar.py              #   侧边栏渲染
│   │   ├── styles.py               #   全局 CSS
│   │   ├── analysis_helpers.py     #   分析配置自动建议
│   │   ├── options.py              #   报告选项重导出
│   │   ├── report_generation.py    #   LLM/Report 配置构造 + 报告生成调用
│   │   └── tabs/                   #   各功能模块
│   │       ├── tab_data_upload.py          #   数据上传
│   │       ├── tab_data_overview.py        #   数据概览
│   │       ├── tab_variable_config.py      #   变量识别
│   │       ├── tab_analysis_config.py      #   分析方案配置
│   │       ├── tab_univariate_analysis.py  #   单变量分析
│   │       ├── tab_bivariate_analysis.py   #   双变量分析
│   │       ├── tab_multivariate_analysis.py #  多变量分析
│   │       ├── tab_visualization.py        #   可视化仪表盘
│   │       ├── tab_ai_analysis.py          #   报告工作台（AI + 模板）
│   │       ├── tab_template_report.py      #   模板报告
│   │       ├── tab_quick_report.py         #   快速报告
│   │       └── tab_legacy_report.py        #   旧版报告兼容
│   │
│   ├── analysis.py                 # 统计分析（描述统计、相关、回归、交叉分析）
│   ├── generic_analysis.py         # 通用模式统计分析编排
│   ├── generic_charts.py           # 通用模式图表生成
│   ├── charts.py                   # 示例模式图表
│   ├── data_loader.py              # 数据加载 + 质量报告
│   ├── schema_infer.py             # 变量类型推断 + 隐私评估
│   ├── report_rendering.py         # 统一报告渲染管线（Markdown→HTML/DOCX）（v0.1.0 Phase 4 新增）
│   ├── variable_metadata.py        # 统一变量元数据模块（中文名/取值说明/描述）（v0.1.0 Phase 3 新增）
│   ├── analysis_context.py         # AnalysisContext 统一分析上下文（v0.1.0 Phase 1 新增）
│   ├── analysis_packager.py        # 分析结果 → JSON Payload + AI-safe 隐私过滤
│   ├── ai_report_generator.py      # AI 报告生成编排
│   ├── llm_client.py               # 统一 LLM 调用客户端
│   ├── llm_prompts.py              # AI 提示词模板
│   ├── config_models.py            # LLMConfig / ReportConfig 数据类
│   ├── provider_config.py          # LLM 厂商配置加载
│   ├── model_registry.py           # 模型列表获取与缓存
│   ├── report_options.py           # 报告结构/风格/长度/主题选项定义
│   ├── report_context.py           # 报告上下文管理（文献综述、背景材料）
│   ├── analysis_recipe_runner.py   # AI 分析方案执行器
│   ├── ai_table_planner.py         # AI 数据表理解与规划
│   ├── payload_inspector.py        # Payload 结构检查
│   ├── preset_profiles.py          # 预设分析方案
│   ├── literature_review.py        # 文献综述检索
│   ├── literature_search.py        # 文献检索（Semantic Scholar / OpenAlex / CrossRef）
│   ├── background_research.py      # 政策背景研究
│   ├── table_understanding_packager.py  # 数据表理解 Payload
│   ├── html_report_templates.py    # HTML 报告模板（5 套内置 CSS 主题）
│   ├── user_settings.py            # 用户设置持久化
│   └── utils.py                    # 工具函数
│
├── tests/                          # 测试（30+ 个文件，650 个测试）
│   ├── test_phase2_unified_state.py      # Phase 2: 统一状态流
│   ├── test_phase3_variable_metadata.py  # Phase 3: 变量元数据统一
│   ├── test_phase35_privacy_filter.py     # Phase 3.5: AI Payload 隐私门控
│   ├── test_phase4_report_rendering.py   # Phase 4: 报告渲染清洗
│   ├── test_phase45_verification.py      # Phase 4.5: DOCX 验证 + AI-safe payload
│   ├── test_binary_inference.py
│   ├── test_logistic_regression.py
│   ├── test_no_secrets_committed.py
│   ├── test_security_utils.py
│   ├── test_streamlit_app_smoke.py
│   └── ...（完整列表见 tests/ 目录）
│
├── test_run4.py                    # 集成测试（CSV + 二分类变量，73 项检查）
├── tests/
│   └── test_data/                   # 测试用模拟数据（4 个场景）
└── examples/                        # 内置示例数据
    ├── government_service_satisfaction_sample.csv
    └── variable_dictionary_sample.csv
```

## 安装与运行

### 1. 创建虚拟环境

```bash
python -m venv .venv
```

### 2. 激活虚拟环境

**Windows:**
```bash
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 启动应用

```bash
streamlit run app.py
```

浏览器将自动打开 http://localhost:8501。

### Windows 一键启动

- `run_app.bat` — 激活 .venv（如存在）并启动 Streamlit
- `start.bat` — 自动创建 .venv、安装依赖、启动应用（首次使用推荐）

详细安装步骤见 [快速开始文档](docs/quickstart.md)。

## 运行测试

```bash
# 运行全部 pytest 测试（650 passed, 0 failed）
python -m pytest tests/ -q

# 运行集成测试（CSV 数据 + 二分类变量，73/73 通过）
python test_run4.py

# Windows 一键测试
run_tests.bat
```

## 发布前检查

```bash
# 静态检查（快速）
python scripts/release_check.py

# 静态检查 + 自动运行测试
python scripts/release_check.py --run-tests

# Windows 一键发布检查
run_release_check.bat
```

## API Key 配置

### 方式一：界面输入（推荐）

在应用的「🤖 AI 智能分析」标签页中直接输入 API Key，勾选「记住设置」后自动保存到本地用户配置文件。

### 方式二：环境变量

参考 `.env.example` 文件：

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

支持的厂商包括：
- **OpenAI** — `OPENAI_API_KEY`
- **DeepSeek** — `DEEPSEEK_API_KEY`
- **月之暗面 Moonshot** — `MOONSHOT_API_KEY`
- **硅基流动 SiliconFlow** — `SILICONFLOW_API_KEY`
- **自定义 API** — `CUSTOM_API_BASE_URL` / `CUSTOM_MODEL_NAME` / `CUSTOM_API_KEY`

### 方式三：Streamlit Secrets

在 `.streamlit/secrets.toml` 中配置（详见 [Streamlit 文档](https://docs.streamlit.io/develop/concepts/connections/secrets-management)）。

## 核心功能

### 📊 统计分析

| 功能 | 说明 |
|------|------|
| 变量类型推断 | 自动识别数值、分类、有序、二分类、文本、日期、ID 变量 |
| 描述统计 | 均值、标准差、中位数、四分位数、偏度、峰度 |
| 频数分析 | 分类/有序/二分类变量的频数分布和百分比 |
| 交叉分析 | 卡方检验、交叉表、ANOVA、t 检验 |
| 相关分析 | Pearson 和 Spearman 相关系数 |
| 回归分析 | OLS 多元线性回归 + 二元逻辑回归（OR 值、显著性） |
| 可视化 | 柱状图、饼图、直方图、箱线图、散点图、热力图、雷达图 |

### 🤖 AI 自动报告

| 功能 | 说明 |
|------|------|
| 多厂商支持 | OpenAI、DeepSeek、小米 MiMo、Google Gemini、自定义 API |
| 报告结构 | 通用调研 / 学术论文 / 政务决策 / 商业分析 / 课程作业 |
| 写作风格 | 课程作业风 / 政务汇报风 / 学术报告风 / 商业分析风 |
| 报告长度 | 简短版 / 标准版 / 详细版 |
| HTML 主题 | 学术白底 / 政务蓝白 / 现代看板 / 简洁课程 / 商业咨询 |
| 导出格式 | Markdown / HTML / Word (.docx) |
| 文献综述 | Semantic Scholar / OpenAlex / CrossRef 检索 |
| 背景材料 | 结构化调研数据注入 |

### 🔒 隐私保护

- 原始数据不发送给 LLM，仅发送统计摘要
- 逐变量隐私控制（本地统计 / 分组聚合 / 脱敏示例 / 完整发送）
- API Key 不进入日志、缓存或报告
- HTML 报告无外部 CDN、无脚本、可离线查看

### 🔑 无 API Key 也能用

本平台的 **核心统计分析功能完全离线运行**，不需要任何 API Key：

| 无需 API Key | 需要 API Key |
|-------------|-------------|
| 📁 数据上传与变量识别 | 🤖 AI 报告生成 |
| 📊 描述统计 / 交叉分析 / 回归分析 | 📚 文献综述检索 |
| 📈 可视化图表（Plotly） | 🌐 联网获取模型列表 |
| 📄 模板报告生成（HTML / DOCX） | 🔌 测试 LLM 连接 |
| 📥 报告下载 | |

> 💡 即使没有 API Key，也可以完成从数据上传到报告导出的完整统计分析流程。

### 📦 内置示例数据

项目内置了模拟的政府服务满意度问卷数据，无需准备数据即可体验完整流程：

1. 启动应用后，在左侧边栏点击 **「📥 加载内置示例数据」**
2. 自动加载 150 条模拟问卷数据 + 配套变量说明表
3. 按「快速上手指南」逐步骤体验
4. **全部为模拟数据，无真实个人信息**

详见 [快速开始 → 使用示例数据](docs/quickstart.md#第三步使用内置示例数据体验)。

## 使用流程

本平台采用 **5 步工作流** 设计：

1. **📋 数据与变量** — 上传数据（CSV/Excel）、查看数据质量、识别变量类型、配置变量说明表
2. **⚙️ 分析方案** — 选择目标变量/分组变量/解释变量，支持手动配置或 AI 推荐方案
3. **📊 统计分析** — 执行统计分析，查看单变量/双变量/多变量结果
4. **📈 可视化仪表盘** — 自动生成交互式图表，标题使用中文变量名
5. **📄 报告工作台** — 生成模板报告或 AI 报告，支持 Markdown / HTML / DOCX 导出

## 注意事项

1. **辅助定位** — 本平台用于辅助统计分析和报告生成，不替代专业研究人员的判断
2. **相关≠因果** — 统计分析结果反映统计关联，不代表因果关系
3. **AI 输出需审阅** — AI 生成的报告可能存在误差，建议人工审阅后使用
4. **隐私责任** — 用户对数据隐私负有最终责任，上传前请确认数据已适当脱敏
5. **文献检索限制** — 文献检索 API（Semantic Scholar / OpenAlex / CrossRef）以英文数据库为主，中文文献支持有限
6. **数据格式** — 支持 .xlsx、.xls、.csv 格式。推荐使用 UTF-8 编码的 CSV 文件
7. **浏览器** — 推荐 Chrome、Edge 或 Firefox 最新版本
8. **不要上传敏感数据** — 请勿上传含有真实个人隐私信息的数据文件。平台提供逐变量隐私控制（见「AI 智能分析」→「隐私与变量使用设置」）
9. **Python 版本** — 推荐 Python 3.12；3.13 下 statsmodels 有 DeprecationWarning（不影响功能）
10. **安全** — 发布项目前请阅读 [安全说明](docs/security.md)，运行 `pytest tests/test_no_secrets_committed.py` 检查无泄露

## CI / CD

本项目配置了 GitHub Actions（`.github/workflows/tests.yml`），在每次 push 和 pull request 时自动运行：

- `python -m pytest tests/ -v`（含 AppTest 前端烟雾测试）
- `python test_run4.py`

本地完整测试命令：

```bash
python -m pytest tests/ -v                        # 全部测试（含 AppTest）
python -m pytest tests/test_streamlit_app_smoke.py -v  # 仅 AppTest 前端烟雾测试
python test_run4.py                               # 集成测试
python scripts/release_check.py                   # 发布前静态检查
```

CI 使用 Python 3.12，不访问真实外部 API。

## 许可证

本项目仅供学习和研究使用。
