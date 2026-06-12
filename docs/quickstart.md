# 快速开始（5 分钟）

本指南帮助你在 Windows 环境下从零启动 CivicSurvey Studio（问策 Insight），并使用示例数据完成一次完整的分析流程。

## 环境要求

- Windows 10/11（macOS / Linux 也可使用，相应命令见下文）
- Python 3.11 或 3.12（推荐 3.12；3.13 可用但 statsmodels 有弃用警告，不影响功能）
- Git（可选，用于克隆项目）

## 第一步：获取项目

```bash
git clone https://github.com/Clockworkhg/civic-survey-studio.git
cd civic-survey-studio
```

如果未安装 Git，直接下载 ZIP 解压到本地目录。

## 第二步：创建虚拟环境

```bash
python -m venv .venv
```

## 第三步：激活虚拟环境

**Windows：**

```bash
.venv\Scripts\activate
```

**macOS / Linux：**

```bash
source .venv/bin/activate
```

激活成功后，命令行前会出现 `(.venv)` 标记。

## 第四步：安装依赖

```bash
pip install -r requirements.txt
```

如果下载速度慢，可以使用清华镜像：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 第五步：启动应用

```bash
streamlit run app.py
```

浏览器将自动打开 http://localhost:8501。如果没有自动打开，手动访问该地址。

也可使用项目提供的启动脚本：

```bash
run_app.bat                    # Windows
start.bat                      # Windows 一键创建 venv + 安装 + 启动
```

## 第六步：使用示例数据体验核心流程

### 6.1 加载示例数据

1. 在左侧边栏点击 **「加载内置示例数据」**
2. 系统自动加载 150 条模拟政府服务满意度数据 + 配套变量说明表
3. 页面顶部将显示「已加载示例数据」提示

> 💡 示例数据全部为模拟数据，不包含真实个人信息。

### 6.2 查看数据与变量

1. 查看系统自动推断的变量类型（总体满意度、是否满意、所在区域、年龄段等）
2. 可选：上传变量说明表 `examples/variable_dictionary_sample.csv`

### 6.3 配置分析方案

在「分析方案」步骤中设置：
- **核心结果变量**：`总体满意度`（或 `是否满意` 体验二元逻辑回归）
- **分组变量**：`所在区域`、`办事渠道`
- **解释变量**：`服务态度评分`、`政策清晰度`、`等待时长满意度`、`办理时长_分钟`

### 6.4 查看统计结果

在「统计分析」和「可视化仪表盘」步骤中查看：
- **单变量分析** — 描述统计和频数分布
- **双变量分析** — 交叉分析和组间比较
- **多变量分析** — 回归分析（OLS 或逻辑回归）
- **可视化仪表盘** — 交互式图表

## 导出报告

### 模板报告（无需 API Key）

1. 在「报告工作台」中，选择报告格式（HTML / Word / Markdown）
2. 点击「生成报告」
3. 下载生成的报告文件

### AI 报告（需 API Key）

1. 在侧边栏「AI 设置」或「报告工作台」中配置 API Key 和模型
2. 设置报告参数（结构 / 风格 / 长度）
3. 点击「生成 AI 分析报告」，下载 Markdown / HTML / DOCX 格式报告

---

## 运行测试

```bash
# 运行全部单元测试（687 passed, 0 failed）
python -m pytest tests/ -q

# 运行集成测试（73/73 通过）
python test_run4.py

# 运行发布前检查（28 passed, 1 warning, 0 failed）
python scripts/release_check.py

# Windows 一键测试
run_tests.bat
```

---

## 没有 API Key 时如何体验

CivicSurvey Studio 的核心统计分析功能完全离线运行，不需要任何 API Key。

**无需 API Key 的操作：**
- 上传数据或加载内置示例数据
- 查看自动变量识别和隐私评估结果
- 设置目标变量、分组变量
- 浏览单变量、双变量、多变量分析和可视化图表
- 生成 HTML / DOCX 模板报告
- 下载生成的报告文件

**需要 API Key 的操作：**
- AI 推荐分析方案
- AI 报告生成
- 文献综述检索

> 💡 即使没有 API Key，也可以完成从数据上传到报告导出的完整统计分析流程。

---

## 常见问题

### pip 安装慢怎么办

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### streamlit 命令找不到

确保虚拟环境已激活（命令行前应有 `(.venv)` 标记）：

```bash
python -m streamlit run app.py
```

### API Key 没有怎么办

1. 所有统计分析功能不需要 API Key
2. 报告工作台可生成基于模板的 HTML/Word 报告，无需 API Key
3. 如需 AI 功能，可在 DeepSeek（https://platform.deepseek.com）或 SiliconFlow（https://siliconflow.cn）注册获取

### 端口被占用

```bash
streamlit run app.py --server.port 8502
```

### 浏览器没有自动打开

手动访问 http://localhost:8501。
