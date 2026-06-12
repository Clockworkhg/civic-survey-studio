# 发布检查清单 v0.1.0

在打 tag `v0.1.0` 之前，请逐项确认以下检查项。

---

## 一、测试 ✅

- [x] `python -m pytest tests/ -v` 全部通过（当前：**650 passed, 0 failed**）
- [x] `python test_run4.py` 全部通过（当前：73/73）
- [x] `python -c "import py_compile; py_compile.compile('app.py', doraise=True)"` 编译成功
- [x] Streamlit AppTest 前端烟雾测试通过（`tests/test_streamlit_app_smoke.py`，当前：15 passed）
- [ ] 无新增测试失败
- [ ] 无因路径变化导致的 import 错误
- [ ] 示例数据加载正常（`tests/test_examples.py` 通过）
- [ ] 文档存在性检查通过（`tests/test_docs_exist.py` 通过）
- [ ] UI 消息模块测试通过（`tests/test_ui_messages.py` 通过）
- [ ] 示例数据流程测试通过（`tests/test_example_data_flow.py` 通过）
- [ ] 用户友好错误测试通过（`tests/test_user_friendly_errors.py` 通过）

## 二、文档 ✅

- [ ] `README.md` 内容完整，链接有效
  - [ ] 项目名称与简介
  - [ ] 技术栈
  - [ ] 项目结构
  - [ ] 安装与运行说明
  - [ ] 测试说明
  - [ ] API Key 配置说明
  - [ ] 核心功能介绍
  - [ ] 注意事项
  - [ ] 指向 `docs/quickstart.md` 的链接
  - [ ] 指向 `docs/deployment.md` 的链接
  - [ ] 指向 `docs/release_checklist.md` 的链接
- [ ] `docs/quickstart.md` 内容完整
  - [ ] 5 分钟快速开始流程
  - [ ] 常见问题解答
- [ ] `docs/deployment.md` 内容完整
  - [ ] 本地运行
  - [ ] Streamlit Community Cloud
  - [ ] 云服务器部署
  - [ ] Docker 未来方案说明
- [ ] `AI_USAGE.md`（如存在）内容准确
- [ ] `TESTING.md`（如存在）内容准确
- [ ] `docs/frontend_acceptance.md` 存在且内容完整

## 三、安全 🔒

- [ ] 代码中无硬编码 API Key
- [ ] `.env` 未提交到 Git（已在 `.gitignore` 中）
- [ ] `.env.example` 仅包含模板变量，无真实值
- [ ] 示例数据全部为模拟数据，无真实个人信息
  - [ ] `examples/government_service_satisfaction_sample.csv` 无手机号、身份证、真实地址、真实姓名
  - [ ] `examples/variable_dictionary_sample.csv` 为通用变量说明模板
- [ ] `config/user_settings.json` 无敏感信息（如已纳入 `.gitignore` 则忽略）
- [ ] `.streamlit/secrets.toml` 未提交（已在 `.gitignore` 中）

## 四、功能 🚀

### 数据加载
- [ ] CSV 文件上传正常
- [ ] Excel (.xlsx) 文件上传正常
- [ ] 多工作表选择正常
- [ ] 变量说明表上传正常

### 变量识别
- [ ] 自动类型推断正确（数值/分类/有序/二分类/文本/日期/ID）
- [ ] 隐私风险评估正常
- [ ] 变量用途检测正常（结合变量说明表）

### 统计分析
- [ ] 单变量分析正常（描述统计、频数分布）
- [ ] 双变量分析正常（交叉分析、卡方检验、ANOVA）
- [ ] 多变量分析正常（OLS 回归）
- [ ] 二元逻辑回归正常（OR 值、显著性）
- [ ] 可视化图表正常（柱状图、饼图、直方图、热力图等）

### 报告生成
- [ ] HTML 报告生成正常
- [ ] DOCX 报告生成正常（需 `python-docx` 已安装）
- [ ] 报告包含正确的统计分析结果
- [ ] 中文显示正常（无乱码）

### AI 报告（可选）
- [ ] Analysis Payload 正常生成
- [ ] LLM 连接测试正常（需有效 API Key）
- [ ] AI 报告正常生成（需有效 API Key）
- [ ] Markdown / HTML / DOCX 导出正常

### 文献检索（可选）
- [ ] Semantic Scholar 检索正常
- [ ] 文献预览正常

### 体验优化（P3-3 新增）
- [ ] **示例数据一键加载** — 侧边栏「📥 加载内置示例数据」按钮可见且可用
- [ ] **新手引导** — 首页显示「快速上手指南」6 步骤表
- [ ] **无 API Key 提示** — AI 分析页面在无 API Key 时显示友好引导文案
- [ ] **文献为空提示** — 文献检索为空时显示中英文关键词建议
- [ ] **文献检索失败提示** — 网络/API 异常时显示可操作建议
- [ ] **AI 报告错误分类** — 常见错误（Key 无效、网络、模型名、超时等）有分类中文提示
- [ ] **隐私风险汇总** — 检测到中高风险变量时显示汇总提醒
- [ ] **隐私字段说明** — 每个隐私变量的展开面板显示类别说明文字
- [ ] **导出成功提示** — 报告生成后显示格式列表和下载指引
- [ ] **导出失败提示** — 包含 outputs 目录权限、文件占用等排查建议
- [ ] **Markdown 导出** — 正常下载
- [ ] **HTML 导出** — 正常预览和下载
- [ ] **DOCX 导出** — 正常下载

### 前端手动验收（P3-6 新增）

- [ ] 按 `docs/frontend_acceptance.md` 完成手动浏览器验收
- [ ] A. 基础加载 — 全部通过
- [ ] B. 示例数据流程 — 人工点击通过
- [ ] C. 统计分析流程 — 全部通过
- [ ] D. 无 API Key 流程 — 人工检查通过
- [ ] F. 导出下载 — 人工检查通过
- [ ] G. 安全检查 — 全部通过

## 五、发布前安全检查 🔐（P3-4 新增）

- [ ] `python -m pytest tests/test_no_secrets_committed.py -v` 全部通过
- [ ] 无硬编码真实 API Key（自动扫描 + 人工确认）
- [ ] `.env` 未提交到 Git（`.gitignore` 已覆盖）
- [ ] `.streamlit/secrets.toml` 未提交（`.gitignore` 已覆盖）
- [ ] `outputs/` 已清理或无敏感报告（`.gitignore` 已覆盖）
- [ ] 示例数据无真实个人信息（`tests/test_example_data_flow.py` 隐私测试通过）
- [ ] `config/user_settings.json` 无真实 API Key（或文件不存在）
- [ ] Security 模块测试通过：`pytest tests/test_security_utils.py -v`
- [ ] Outputs 安全测试通过：`pytest tests/test_outputs_safety.py -v`
- [ ] AI 隐私摘要测试通过：`pytest tests/test_ai_privacy_summary.py -v`
- [ ] `docs/security.md` 存在且内容完整

## 六、Git 📦

- [ ] `.gitignore` 已配置并生效
  - [ ] `.venv/` 被忽略
  - [ ] `__pycache__/` 被忽略
  - [ ] `.env` 被忽略
  - [ ] `outputs/` 被忽略
- [ ] 不包含临时文件（`.tmp.*`、`*.pyc` 等）
- [ ] 不包含 IDE 配置（`.vscode/`、`.idea/`）
- [ ] CI 配置存在（`.github/workflows/tests.yml`）
- [ ] CI 能否正常运行（GitHub Actions）

## 七、依赖 📋

- [ ] `requirements.txt` 包含所有必需依赖
- [ ] `requirements.txt` 无不必要依赖
- [ ] 干净环境 `pip install -r requirements.txt` 成功
- [ ] 干净环境下测试全部通过
- [ ] 推荐 Python 版本已注明（≥3.11，推荐 3.12）

## 八、发布前最终确认

- [ ] `git status` 显示无意外变更
- [ ] `git diff` 审查通过
- [ ] 所有 commit message 清晰
- [ ] 运行发布检查脚本：`python scripts/release_check.py` 或 `run_release_check.bat`
- [ ] 如需创建 tag：

  ```bash
  git tag -a v0.1.0 -m "v0.1.0: 初始版本"
  git push origin v0.1.0
  ```

## 九、v0.1.0 发布流程（操作指南）

以下为打 v0.1.0 tag 的完整流程，**请勿由 Claude Code 自动执行**：

1. **跑测试**
   ```bash
   python -m pytest tests/ -v
   python test_run4.py
   ```
   确认全部通过。

2. **跑发布检查**
   ```bash
   python scripts/release_check.py --run-tests
   ```
   确认 0 失败。

3. **确认无真实 API Key**
   ```bash
   python -m pytest tests/test_no_secrets_committed.py -v
   ```
   确认 8 passed。

4. **确认 outputs/ 不提交**
   ```bash
   git status outputs/
   ```
   应无输出（已被 .gitignore 忽略），或目录为空。

5. **更新 CHANGELOG 日期**
   编辑 `CHANGELOG.md`，将 `[0.1.0]` 的日期改为实际发布日期（如 `2026-06-12`）。

6. **提交 commit**
   ```bash
   git add -A
   git status
   git commit -m "v0.1.0: 初始版本 — 统计分析、逻辑回归、AI 报告、文献检索"
   ```

7. **打 tag**
   ```bash
   git tag -a v0.1.0 -m "v0.1.0: 初始版本"
   ```

8. **推送**
   ```bash
   git push origin main
   git push origin v0.1.0
   ```

9. **在 GitHub Releases 写摘要**
   在 GitHub 仓库的 Releases 页面创建 v0.1.0 Release，内容可引用 `CHANGELOG.md` 的 [0.1.0] 章节。

---

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.1.0 | TBD | 初始版本：统计分析、二元逻辑回归、AI 报告、文献检索、HTML/DOCX 导出 |
