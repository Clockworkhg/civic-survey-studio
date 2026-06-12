# 数据安全与隐私说明

本文档说明项目的安全设计、API Key 使用建议、隐私保护机制以及发布前的安全检查步骤。

---

## 一、数据隐私说明

### 1.1 你的数据在哪里

- **所有数据处理均在本地进行**（pandas / scipy / statsmodels）。
- 问卷数据仅在你的浏览器/本机内存中，不会自动上传到任何远程服务器。
- AI 报告生成时，发送给 LLM 服务商的是**统计摘要和结构化分析结果**，而非原始数据行。系统通过 `analysis_packager` 将分析结果打包为 JSON payload 发送。

### 1.2 什么数据会被发送给 AI

发送给 AI 模型的内容包括：

- 项目元信息（报告标题、研究对象、样本量）
- 变量结构（变量名、类型、中文含义）
- 按变量设置的隐私发送模式：
  - `exclude` — 完全不发送
  - `aggregate_only` — 仅发送聚合统计（均值、频率、比例等）
  - `masked_examples` — 发送聚合统计 + 脱敏样例
  - `full` — 完整发送（需用户二次确认）

**不会发送给 AI 的内容：**

- 原始逐行数据（除非你手动勾选 `full` 模式）
- 被标记为「不发送 AI」的变量
- 上传的原始文件

### 1.3 隐私风险评估

系统在数据加载时自动评估每个变量的隐私风险：

| 风险等级 | 说明 | 默认行为 |
|---------|------|---------|
| 🔴 **高风险** | 直接身份标识（姓名、身份证号、手机号等） | 不发送 AI |
| 🟡 **中风险** | 联系方式、自由文本、地理位置等 | 仅发送聚合统计 |
| 🟢 **低风险** | 人口统计属性（年龄、性别、学历等） | 允许发送 |
| ⚪ **无风险** | 评分、满意度等纯数值变量 | 允许发送 |

在 Tab 10（AI 分析）的「7. 🔒 隐私与变量使用设置」中，你可以逐变量调整发送策略。

### 1.4 重要提醒

- **不要上传包含真实个人身份信息（PII）的问卷数据**到任何部署在公共网络的应用实例。
- 本地使用相对安全，但如果通过 Streamlit Cloud 或公共服务器部署，任何能访问该 URL 的人都可以上传数据并查看分析结果（Streamlit 没有内置用户认证）。
- 如需在团队内使用，建议部署在内网环境或添加 VPN/认证层（本项目不包含认证功能）。

---

## 二、API Key 使用建议

### 2.1 输入方式（优先级从高到低）

1. **UI 直接输入**（推荐） — 在 Tab 10「AI 分析」页面的 API Key 输入框中填入。
2. **Streamlit Secrets** — 在 `.streamlit/secrets.toml` 中配置（仅 Streamlit Cloud 推荐）。
3. **环境变量** — 设置系统环境变量（如 `DEEPSEEK_API_KEY`）。

### 2.2 记住设置功能

Tab 10 提供了「💾 记住设置」功能，勾选后 API Key 将以**明文**保存在 `config/user_settings.json` 中。

**安全提示：**

- ✅ 个人设备上可以使用此功能以方便使用。
- ⚠️ **不要在公共或共享设备上使用「记住设置」。**
- ⚠️ `config/user_settings.json` 已被 `.gitignore` 忽略，不会被 Git 跟踪。
- ⚠️ 如担心泄露，可在使用完毕后取消勾选「记住设置」或手动删除 `config/user_settings.json`。
- ⚠️ 注意：明文存储意味着任何能访问你电脑文件系统的人都可以读取 API Key。

### 2.3 API Key 安全检查

项目内置了 API Key 脱敏机制：

- UI 中的错误提示会自动脱敏 API Key（显示为 `sk-****abcd` 格式）。
- 错误日志和调试信息不会包含完整 API Key。
- 连接测试失败时，错误消息中的 API Key 已被替换为脱敏形式。

### 2.4 API Key 发布检查

发布项目前，请确认：

- [ ] `.env` 文件未被提交（已在 `.gitignore` 中）
- [ ] `.streamlit/secrets.toml` 未被提交（已在 `.gitignore` 中）
- [ ] `config/user_settings.json` 不包含真实 API Key（或已被删除）。**注意：`config/user_settings.json` 不在 Git 中，如需配置模板请复制 `config/user_settings.example.json`**
- [ ] 代码中无硬编码的 API Key
- [ ] `python -m pytest tests/test_no_secrets_committed.py -v` 全部通过

---

## 三、不要上传真实敏感问卷到公共环境

### 3.1 风险说明

Streamlit 应用默认无用户认证。如果在公共服务器上部署：

- 任何知道 URL 的人都可以访问应用。
- 上传的数据在 `st.session_state` 中，仅在当前会话内。
- 但如果多人同时使用，Streamlit 会为每个用户创建独立会话，数据不会交叉。
- 风险在于：无法控制谁能访问应用。

### 3.2 建议

- **本地使用最安全** — 数据不会离开你的设备。
- 如果必须部署，建议使用 **Streamlit Cloud 的私有应用**（需要登录）。
- 或者在内网/VPN 环境中部署。
- **无论如何，请勿上传包含真实身份证号、手机号、银行卡号等敏感信息的原始问卷。**

---

## 四、AI Payload 隐私过滤机制

发送给 AI 的 payload 在构建后还会经过 `filter_payload_for_ai()` 二次过滤，确保隐私变量不会泄露。

### 4.0 过滤覆盖范围

隐私过滤器从以下 **9 个** payload 节中移除排除变量：

| Payload Section | 过滤动作 |
|----------------|---------|
| `variables` | 移除排除变量条目 |
| `variable_schema` | 移除排除变量条目 |
| `variable_name_map` | 移除排除变量映射 |
| `analysis_results` | 移除涉及排除变量的结果 |
| `data_overview.column_names` | 移除排除列名 |
| `analysis_plan` | 移除排除变量的计划项 |
| `warnings` | 移除涉及排除变量的警告文本 |
| `user_analysis_config` | 清除排除列表中的变量名 |
| metadata | 用计数代替具体名称（`_privacy_excluded_count`） |

### 4.1 send_to_ai_mode 规则

| 模式 | 行为 |
|------|------|
| `exclude` | 从 payload 中完全移除该变量 |
| `none` | 等同于 `exclude` |
| `aggregate_only` | 保留变量结构但剥离 example_values / value_labels |
| `masked_examples` | 保留脱敏后的样例 |
| `full` | 完整发送（需二次确认） |

## 五、AI 报告生成前如何排除高风险变量

### 4.1 自动评估

数据加载后，系统自动评估每个变量的隐私风险（见 1.3 节）。

### 4.2 逐变量控制

在 Tab 10「AI 分析」→「7. 🔒 隐私与变量使用设置」中：

1. 展开高风险变量（红色标记，默认已展开）。
2. 取消勾选「🤖 发送 AI」。
3. 或选择 AI 发送方式为「仅发送聚合统计」或「不发送」。
4. 点击「💾 应用设置」。

### 4.3 生成前确认

在点击「🤖 生成 AI 分析报告」之前，页面会显示变量发送摘要：

- 总变量数、将发送给 AI 的变量数
- 高风险变量数及其发送状态
- 中风险变量数
- 自由文本变量数

如果仍有高风险变量将被发送，页面会显示 **⚠️ 醒目标警告**，建议回到隐私设置中取消勾选。

只有**所有高风险变量均已排除**时，才会显示 ✅ 绿色安全确认。

---

## 六、outputs/ 目录清理说明

### 6.1 outputs/ 中有什么

`outputs/` 目录保存了生成的报告文件：

- `.md` — Markdown 格式报告
- `.html` — HTML 格式报告
- `.docx` — Word 格式报告

### 6.2 安全风险

- 报告中可能包含统计结果、数据摘要甚至（如选择了 `full` 发送模式）变量原文引用。
- **发布项目到 GitHub 前，建议清理 `outputs/` 目录。**

### 6.3 清理方法

`outputs/` 已在 `.gitignore` 中被忽略，不会被 Git 跟踪。

如需手动清理：

```bash
# Windows PowerShell
Remove-Item -Path outputs\* -Force

# macOS / Linux
rm -rf outputs/*
```

或使用项目内置工具：

```python
from src.ui.security import clean_output_files

# 查看有哪些文件（不删除）
result = clean_output_files(dry_run=True)
print(result["deleted"])

# 实际删除
result = clean_output_files(dry_run=False)
print(f"Deleted {len(result['deleted'])} files")
```

---

## 七、发布前 Secrets 检查

### 7.1 自动扫描

项目提供了 secrets 扫描测试：

```bash
python -m pytest tests/test_no_secrets_committed.py -v
```

该测试会扫描所有文本文件，检测：

- `sk-...` 格式的 API Key（≥25 字符）
- `Bearer ...` 格式的 Token（≥30 字符）
- 环境变量中非空的 API Key 值
- `.env` 和 `.streamlit/secrets.toml` 是否存在于仓库中
- `.gitignore` 是否正确配置

### 7.2 手动检查清单

- [ ] 代码中无硬编码 API Key
- [ ] `.env.example` 中所有值为空
- [ ] `.gitignore` 包含 `.env`、`outputs/`、`.streamlit/secrets.toml`
- [ ] `config/user_settings.json` 不存在（或仅包含测试数据）
- [ ] 示例数据（`examples/`）不包含真实个人信息
- [ ] `outputs/` 已清理或不存在
- [ ] 无包含真实 API Key 的日志文件

---

## 八、公共部署的风险提醒

### 8.1 Streamlit 特性

- **无内置用户认证** — 任何知道 URL 的人都可以访问。
- **无内置权限控制** — 所有访问者看到相同的界面和功能。
- **会话隔离** — 每个用户有独立的 `session_state`，数据不会在用户间泄露。

### 8.2 风险矩阵

| 部署方式 | 数据暴露风险 | API Key 风险 | 建议 |
|---------|------------|-------------|------|
| 本地 (localhost) | 低 | 低 | ✅ 推荐用于个人分析 |
| 内网部署 | 低 | 低 | ✅ 适合团队使用 |
| Streamlit Cloud (公开) | **高** | **高** | ⚠️ 不建议；使用私有应用 |
| 云服务器 (公开) | **高** | **高** | ⚠️ 需额外添加认证层 |

### 8.3 降低风险的措施

如果必须在非本地环境运行：

1. **不要保存 API Key** — 不要勾选「💾 记住设置」，每次都手动输入。
2. **使用临时 API Key** — 创建有预算限制/使用限制的 API Key。
3. **添加认证层** — 使用 Nginx 反向代理 + Basic Auth 或 OAuth。
4. **定期清理 outputs/** — 确保报告不被公开访问。
5. **提醒用户** — 在应用首页添加醒目的数据隐私提醒。

---

## 参考

- [Streamlit Security](https://docs.streamlit.io/streamlit-community-cloud/get-started/trust-and-security)
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [OpenAI API Key Best Practices](https://platform.openai.com/docs/guides/production-best-practices)
