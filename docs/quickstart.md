# 快速开始（5 分钟）

本指南帮助你在 Windows 环境下从零启动项目，并使用示例数据完成一次完整的分析流程。

## 环境要求

- Windows 10/11
- Python 3.11 或 3.12（推荐 3.12；3.13 可用但 statsmodels 有弃用警告，不影响功能）
- Git（可选，用于克隆项目）

## 第一步：获取项目

```bash
git clone <your-repo-url> gov-satisfaction-ai-report
cd gov-satisfaction-ai-report
```

如果未安装 Git，直接下载 ZIP 解压到本地目录。

## 第二步：创建虚拟环境

```bash
python -m venv .venv
```

## 第三步：激活虚拟环境

```bash
.venv\Scripts\activate
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
run_app.bat
```

## 第三步（备选）：使用内置示例数据体验

如果暂时没有自己的数据，可以使用内置的示例数据快速体验：

1. 启动应用后，在左侧边栏找到「📦 示例数据」区域
2. 点击 **「📥 加载内置示例数据」** 按钮
3. 系统自动加载 150 条模拟政府服务满意度数据 + 配套变量说明表
4. 页面顶部将显示「已加载示例数据」提示
5. 继续按步骤查看变量识别、分析配置、统计结果

> 💡 示例数据全部为模拟数据，不包含真实个人信息。

## 第六步：使用示例数据体验核心流程

### 6.1 上传数据

**方式一：一键加载（推荐）**

1. 在左侧边栏「📦 示例数据」区域，点击 **「📥 加载内置示例数据」**  
2. 自动加载 150 条模拟数据 + 变量说明表

**方式二：手动上传**

1. 在左侧边栏中，点击「上传数据文件」，选择 `examples/government_service_satisfaction_sample.csv`
2. 系统自动识别 CSV 文件并加载

### 6.2 查看变量识别

1. 切换到 Tab「🔍 变量识别」
2. 查看系统自动推断的变量类型：
   - `总体满意度` / `是否满意` → 结果变量
   - `所在区域` / `年龄段` → 分类变量
   - `服务态度评分` / `政策清晰度` → 有序变量
   - `办理时长_分钟` → 数值变量
   - `意见建议` → 文本变量

### 6.3 上传变量说明表（可选）

1. 在左侧边栏上传变量说明表：`examples/variable_dictionary_sample.csv`
2. 在 Tab「🔍 变量识别」中点击「从变量说明表自动识别」，系统将自动填充变量用途
3. 点击「应用变量用途到分析配置」，配置将自动同步

### 6.4 配置分析

1. 切换到 Tab「⚙️ 分析配置」
2. 设置：
   - **核心结果变量**：`总体满意度`（或 `是否满意` 体验二元逻辑回归）
   - **分组变量**：`所在区域`、`办事渠道`
   - **解释变量**：`服务态度评分`、`政策清晰度`、`等待时长满意度`、`办理时长_分钟`

### 6.5 查看统计结果

浏览以下标签页：
- **📊 单变量分析** — 各变量的描述统计和频数分布
- **🔗 双变量分析** — 交叉分析和组间比较
- **📈 多变量分析** — 回归分析（OLS 或逻辑回归）
- **📉 可视化图表** — 自动生成的交互式图表

### 6.6 生成报告

1. 切换到 Tab「📄 报告生成」
2. 选择报告格式（HTML / Word / 两种）
3. 点击「生成报告」
4. 下载生成的报告文件

### 6.7 使用 AI 生成报告（可选，需 API Key）

1. 切换到 Tab「🤖 AI 智能分析」
2. 选择 AI 厂商（如 OpenAI）
3. 输入 API Key（如在 DeepSeek 官网注册可获取）
4. 设置报告参数（结构 / 风格 / 长度）
5. 点击「生成分析 Payload」→「生成 AI 报告」
6. 下载 Markdown / HTML / Word 格式报告

## 运行测试

```bash
# 运行全部单元测试
python -m pytest tests/ -v

# 运行集成测试
python test_run4.py

# Windows 一键测试
run_tests.bat
```

预期结果：250+ 个测试全部通过，test_run4.py 73/73 通过。

## 没有 API Key 时如何体验

本平台的核心统计分析功能 **完全离线运行**，不需要任何 API Key：

**你可以完成的操作：**
1. 📁 上传自己的数据或加载内置示例数据
2. 🔍 查看自动变量识别和隐私评估结果
3. ⚙️ 在「分析配置」中设置目标变量、分组变量
4. 📊 浏览单变量、双变量、多变量分析和可视化图表
5. 📄 在「报告生成」标签页生成 HTML / DOCX 模板报告
6. 📥 下载生成的报告文件

**需要 API Key 的操作：**
- 🤖 在「AI 智能分析」标签页生成 AI 报告
- 📚 文献综述自动检索（AI 报告的可选功能）

> 💡 即使没有 API Key，你也可以完成从数据上传到报告导出的完整统计分析流程。
> AI 报告是基于统计结果自动撰写的，人工也可以参考统计图表自行撰写。

## 导出报告

### 模板报告（无需 API Key）

1. 切换到「📄 报告生成」标签页
2. 选择报告格式：HTML / Word / 两种
3. 点击「🔍 生成报告」
4. 生成完成后，在预览下方点击下载按钮：
   - 📥 下载报告（HTML）— 可在浏览器中查看
   - 📥 下载报告（Word .docx）— 可用 Word 打开编辑

### AI 报告（需 API Key）

1. 在「🤖 AI 智能分析」标签页配置 API Key 和模型
2. 设置报告参数（结构、风格、长度、HTML 主题）
3. 点击「📦 生成 Payload」→「🤖 生成 AI 分析报告」
4. 生成完成后下载 Markdown / HTML / DOCX 格式

> 📂 导出的文件同时保存在 `outputs/` 目录下（自动创建）。
> 如遇导出失败，请检查 outputs/ 目录权限和磁盘空间。

## 常见问题

### pip 安装慢怎么办

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

或使用其他国内镜像：
- 阿里云：`https://mirrors.aliyun.com/pypi/simple/`
- 中科大：`https://pypi.mirrors.ustc.edu.cn/simple/`

### streamlit 命令找不到

确保虚拟环境已激活。激活后命令行前应有 `(.venv)` 标记。

如果问题持续：

```bash
python -m streamlit run app.py
```

### API Key 没有怎么办

1. **不影响统计分析** — 所有统计分析功能完全不需要 API Key
2. **报告生成** — Tab「📄 报告生成」可生成基于模板的 HTML/Word 报告，无需 API Key
3. **如需 AI 功能** — 可在以下平台免费注册获取：
   - DeepSeek：https://platform.deepseek.com（新用户有免费额度）
   - 硅基流动 SiliconFlow：https://siliconflow.cn（提供免费模型）

### 文献检索为空怎么办

文献检索（Semantic Scholar / OpenAlex / CrossRef）以英文数据库为主：
1. 尝试使用英文关键词
2. 中文文献支持有限，建议人工补充
3. 不勾选文献综述功能不会影响报告生成

### 生成 DOCX 失败

提示 `python-docx` 相关错误：

```bash
pip install python-docx --upgrade
```

如果仍有问题，可以暂时只生成 HTML 格式，在浏览器中查看后手动打印为 PDF。

### 端口被占用

```bash
streamlit run app.py --server.port 8502
```

将使用 8502 端口。

### 浏览器没有自动打开

手动访问 http://localhost:8501。Windows 防火墙可能阻止浏览器启动，不影响应用使用。
