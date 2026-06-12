# CivicSurvey Studio

AI 辅助问卷统计分析与报告生成工作台  
中文名：问策 Insight

CivicSurvey Studio 是一个面向问卷数据的统计分析与报告生成工作台，支持数据上传、变量识别、统计分析、可视化仪表盘、AI 辅助报告生成和 HTML / DOCX 导出。AI 仅作为辅助分析和报告草稿生成工具，最终结论仍需人工复核。

> **当前版本：v0.1.1** — UI 优化与入口修复 | [变更日志](CHANGELOG.md) | [路线图](docs/roadmap.md) | [已知问题](docs/known_issues.md)

[![Tests](https://github.com/Clockworkhg/civic-survey-studio/actions/workflows/tests.yml/badge.svg)](https://github.com/Clockworkhg/civic-survey-studio/actions/workflows/tests.yml)

---

## 适用场景

- 政务服务满意度调查
- 社区治理与公共服务评估
- 高校课程评价与学生问卷
- 组织内部调研
- 社会科学课程或小型研究项目
- 需要快速形成统计分析报告的问卷数据场景

---

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

---

## 核心功能

- CSV / Excel 数据上传（支持多工作表）
- 变量说明表导入，贯穿分析全流程
- 变量类型自动识别（数值 / 分类 / 有序 / 二分类 / 文本 / 日期 / ID）
- 数据质量概览（缺失值、异常值检测）
- 手动 / 预设 / AI 推荐分析方案
- 单变量分析（描述统计、频数分布）
- 双变量分析（交叉表、卡方检验、ANOVA、t 检验）
- 多变量分析（OLS 多元线性回归、Pearson/Spearman 相关）
- 二元逻辑回归（OR 值、显著性、模型拟合）
- Plotly 交互式可视化仪表盘
- AI 辅助分析方案生成（需 API Key）
- AI 辅助 Markdown 报告生成（需 API Key）
- 文献检索与研究背景材料注入（需 API Key）
- HTML / DOCX 报告导出
- 5 套内置 HTML 报告主题
- AI-safe payload 隐私过滤
- 697 个 pytest 测试、73 项集成测试、22 个 Streamlit smoke tests

---

## 5 步工作流

```
1. 数据与变量 — 上传数据、变量说明表，查看数据质量与变量类型
2. 分析方案 — 手动配置或 AI 推荐核心变量、分组变量、解释变量
3. 统计分析 — 执行单变量/双变量/多变量分析，查看回归结果
4. 可视化仪表盘 — 自动生成交互式图表，支持中文变量名
5. 报告工作台 — 生成模板报告或 AI 报告，导出 HTML / DOCX
```

---

## 快速开始

```bash
git clone https://github.com/Clockworkhg/civic-survey-studio.git
cd civic-survey-studio
python -m venv .venv
```

**Windows：**

```bash
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

**macOS / Linux：**

```bash
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Windows 用户也可以直接运行一键启动脚本：

```bash
start.bat
```

浏览器将自动打开 http://localhost:8501。

---

## 示例数据

项目提供了模拟的政府服务满意度问卷数据，可快速体验完整分析流程：

```
examples/
├── government_service_satisfaction_sample.csv  # 150 行模拟数据（11 个变量）
└── variable_dictionary_sample.csv              # 变量说明表
```

在侧边栏点击「加载内置示例数据」即可体验完整流程。示例数据全部为模拟数据，无真实个人信息。

---

## AI API 配置

- **本地统计分析不需要任何 API Key。** 无 API Key 也能完成从数据上传到报告导出的完整流程。
- 只有 AI 推荐方案、AI 报告生成、文献综述增强等功能需要 API Key。
- 支持多 LLM Provider，配置来自 `config/llm_providers.yaml`。
- 本地密钥保存在 `config/user_settings.json`，该文件已被 `.gitignore` 排除。

初次配置：

```bash
cp config/user_settings.example.json config/user_settings.json
```

然后编辑 `config/user_settings.json` 填入你自己的 API Key。不要提交真实 API Key 到仓库。

---

## 隐私与安全

- 默认不发送原始逐行问卷数据给 AI。
- 发送给 AI 的 payload 会经过 privacy filter。
- 禁止发送的变量会从 AI payload、变量名称映射、分析结果、warnings、metadata 中移除。
- `send_to_ai_mode="none"` 的变量不会进入 AI prompt。
- `aggregate_only` 只允许聚合统计，不包含原始样例值。
- 用户应自行确认 API 服务商的数据处理政策。

---

## 测试

```bash
pytest tests -q                            # pytest: 697 passed, 0 failed
python test_run4.py                        # 集成测试: 73 passed, 0 failed
python scripts/release_check.py            # 发布检查: 28 passed, 1 warning, 0 failed
pytest tests/test_streamlit_app_smoke.py -q  # Smoke tests: 22 passed
```

---

## 项目结构

```
civic-survey-studio/
├── app.py                          # Streamlit 应用编排入口
├── requirements.txt                # Python 依赖清单
├── start.bat                       # Windows 一键创建 venv + 安装 + 启动
│
├── src/
│   ├── analysis_context.py         # AnalysisContext 统一分析上下文
│   ├── generic_analysis.py         # 通用模式统计分析编排
│   ├── generic_charts.py           # 通用模式图表生成
│   ├── analysis_packager.py        # 分析结果 → JSON Payload + AI-safe 隐私过滤
│   ├── ai_report_generator.py      # AI 报告生成编排
│   ├── report_rendering.py         # Markdown→HTML/DOCX 渲染管线
│   ├── variable_metadata.py        # 统一变量元数据（中文名/取值说明）
│   ├── schema_infer.py             # 变量类型推断 + 隐私评估
│   ├── data_loader.py              # 数据加载 + 质量报告
│   ├── llm_client.py               # 统一 LLM 调用客户端
│   └── ui/                         # Streamlit UI 层
│       ├── sidebar.py              #   侧边栏（5 区段）
│       ├── messages.py             #   产品化首页 HTML
│       ├── styles.py               #   全局 CSS
│       ├── components.py           #   共享组件（配置摘要卡片等）
│       └── tabs/                   #   各功能模块（12 个 Tab）
│
├── examples/                       # 内置示例数据
├── config/                         # LLM 厂商配置 + 用户设置模板
├── docs/                           # 项目文档（7 个文件）
├── tests/                          # pytest 测试（37 个文件）
└── scripts/                        # 发布检查脚本
```

- `src/` — 核心模块（统计分析、图表、报告、AI、UI）
- `examples/` — 内置模拟数据
- `config/` — LLM 厂商配置、用户设置模板
- `docs/` — 完整文档
- `tests/` — pytest 测试（697 个）
- `scripts/` — 发布检查脚本

---

## 版本状态

| 指标 | 状态 |
|------|------|
| pytest | 697 passed, 0 failed |
| test_run4.py | 73/73 通过 |
| release_check.py | 28 passed, 1 warning, 0 failed |
| Streamlit smoke tests | 22 passed |
| 5 步工作流 | ✅ 完成 |
| 安全检查 | ✅ 完成 |
| 统一状态流 | ✅ 完成 |
| 变量元数据统一 | ✅ 完成 |
| AI Payload 隐私门控 | ✅ 完成 |
| 报告渲染清洗 | ✅ 完成 |

v0.1.0 已打通完整链路；v0.1.1 修复了首页入口与品牌展示。UI 体验、报告模板可配置化、中文文献导入、图表导出增强等会在后续版本继续改进。

---

## 已知限制

- v0.1.0 是首个可用版本，不是成熟商业产品。
- AI 报告质量依赖所选模型和 API Key。
- 统计结果需要人工解释，不应直接作为政策或管理决策依据。
- 大型数据集性能尚未系统优化。
- Streamlit UI 仍有继续打磨空间。

详见 [已知问题](docs/known_issues.md)。

---

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
| 语言 | Python ≥3.11（推荐 3.12；3.13 可用但 statsmodels 有弃用警告，不影响功能） |

---

## 许可证

本项目仅供学习和研究使用。
