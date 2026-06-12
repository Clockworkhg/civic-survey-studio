"""HTML 报告模板模块。

提供 5 套内置 HTML 报告主题（CSS 样式），以及 Markdown → HTML 渲染函数。

设计原则：
  - 所有 CSS 由程序内置，不让 AI 随机生成 HTML/CSS
  - 不依赖外部 CDN，保证离线可查看
  - 不插入不安全脚本
  - 不把 API Key、原始隐私数据写入 HTML
  - 支持中文字体
"""

import re
from typing import Optional


# ================================================================
# HTML 转义
# ================================================================

def _escape_html(text: str) -> str:
    """转义 HTML 特殊字符。"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ================================================================
# 5 套 CSS 主题
# ================================================================

_THEME_CSS = {
    # ── 1. 学术论文白底风 ──
    "学术论文白底风": """
/* === 学术论文白底风 === */
body {
    font-family: "SimSun", "宋体", "Noto Serif CJK SC", "Source Han Serif SC", serif;
    max-width: 800px;
    margin: 40px auto;
    padding: 40px 60px;
    color: #1a1a1a;
    line-height: 2.0;
    background: #ffffff;
    font-size: 15px;
}
h1 {
    text-align: center;
    font-size: 22px;
    font-weight: bold;
    color: #000;
    margin-bottom: 0.8em;
    letter-spacing: 2px;
}
h2 {
    font-size: 18px;
    font-weight: bold;
    color: #1a1a1a;
    border-bottom: 1px solid #333;
    padding-bottom: 4px;
    margin-top: 2em;
    margin-bottom: 0.8em;
}
h3 {
    font-size: 16px;
    font-weight: bold;
    color: #333;
    margin-top: 1.5em;
    margin-bottom: 0.6em;
}
p {
    text-indent: 2em;
    margin: 0.4em 0;
}
strong {
    color: #1a1a1a;
    font-weight: bold;
}
.report-table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 0.9em;
}
.report-table th {
    background: #f0f0f0;
    color: #1a1a1a;
    padding: 6px 10px;
    text-align: center;
    border: 1px solid #999;
    font-weight: bold;
}
.report-table td {
    border: 1px solid #999;
    padding: 4px 10px;
    text-align: center;
}
.report-table tr:nth-child(even) { background: #fafafa; }
pre { font-size: 0.85em; background: #f5f5f5; padding: 1em; border: 1px solid #ddd; overflow-x: auto; }
.footer {
    margin-top: 3em;
    padding-top: 1em;
    border-top: 1px solid #ccc;
    color: #999;
    font-size: 0.85em;
    text-align: center;
    text-indent: 0;
}
""",

    # ── 2. 政务蓝白汇报风 ──
    "政务蓝白汇报风": """
/* === 政务蓝白汇报风 === */
body {
    font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
    max-width: 900px;
    margin: 0 auto;
    padding: 30px 50px;
    color: #2c3e50;
    line-height: 1.9;
    background: #f4f7fa;
}
h1 {
    text-align: center;
    font-size: 24px;
    font-weight: bold;
    color: #1a3a5c;
    padding: 20px 0;
    margin-bottom: 1em;
    background: linear-gradient(180deg, #ffffff 0%, #e8edf3 100%);
    border-left: 6px solid #1a5276;
    border-right: 6px solid #1a5276;
}
h2 {
    font-size: 18px;
    font-weight: bold;
    color: #1a5276;
    border-left: 4px solid #2980b9;
    padding: 6px 0 6px 14px;
    margin-top: 2em;
    margin-bottom: 0.8em;
    background: #eaf0f8;
}
h3 {
    font-size: 16px;
    font-weight: bold;
    color: #2471a3;
    margin-top: 1.2em;
    margin-bottom: 0.5em;
    padding-left: 8px;
    border-left: 3px solid #85c1e9;
}
p { margin: 0.5em 0; }
strong { color: #1a5276; }
.report-table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 0.92em;
    background: #fff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.report-table th {
    background: #1a5276;
    color: #ffffff;
    padding: 8px 12px;
    text-align: left;
    font-weight: bold;
}
.report-table td {
    border: 1px solid #d5dbdb;
    padding: 6px 12px;
}
.report-table tr:nth-child(even) { background: #f8fafb; }
pre { font-size: 0.85em; background: #f0f3f5; padding: 1em; border-radius: 4px; overflow-x: auto; }
.footer {
    margin-top: 3em;
    padding: 16px 0;
    border-top: 2px solid #1a5276;
    color: #7f8c8d;
    font-size: 0.85em;
    text-align: center;
}
""",

    # ── 3. 现代数据看板风 ──
    "现代数据看板风": """
/* === 现代数据看板风 === */
body {
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
    max-width: 1000px;
    margin: 0 auto;
    padding: 30px 40px;
    color: #2d3436;
    line-height: 1.8;
    background: #f0f2f5;
}
h1 {
    text-align: center;
    font-size: 26px;
    font-weight: 700;
    color: #2d3436;
    margin-bottom: 1em;
    padding: 24px;
    background: #ffffff;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
h2 {
    font-size: 18px;
    font-weight: 600;
    color: #2d3436;
    margin-top: 2em;
    margin-bottom: 1em;
    padding: 12px 20px;
    background: #ffffff;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    border-left: 4px solid #0984e3;
}
h3 {
    font-size: 16px;
    font-weight: 600;
    color: #636e72;
    margin-top: 1.2em;
    margin-bottom: 0.6em;
}
p {
    margin: 0.5em 0;
    padding:  0 8px;
}
strong { color: #0984e3; font-weight: 600; }
.report-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin: 1em 0;
    font-size: 0.92em;
    background: #fff;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.report-table th {
    background: #0984e3;
    color: #ffffff;
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 0.9em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.report-table td {
    border-bottom: 1px solid #eee;
    padding: 8px 14px;
}
.report-table tr:last-child td { border-bottom: none; }
.report-table tr:nth-child(even) { background: #f8f9fa; }
pre {
    font-size: 0.85em;
    background: #ffffff;
    padding: 1em;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    overflow-x: auto;
}
.footer {
    margin-top: 3em;
    padding: 16px 20px;
    background: #ffffff;
    border-radius: 8px;
    color: #b2bec3;
    font-size: 0.85em;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
""",

    # ── 4. 简洁课程作业风 ──
    "简洁课程作业风": """
/* === 简洁课程作业风 === */
body {
    font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
    max-width: 780px;
    margin: 30px auto;
    padding: 24px 40px;
    color: #444;
    line-height: 1.8;
    background: #ffffff;
    border: 1px solid #e0e0e0;
}
h1 {
    text-align: center;
    font-size: 20px;
    font-weight: bold;
    color: #333;
    margin-bottom: 1em;
    padding-bottom: 12px;
    border-bottom: 2px solid #ddd;
}
h2 {
    font-size: 17px;
    font-weight: bold;
    color: #555;
    margin-top: 1.8em;
    margin-bottom: 0.6em;
    padding-bottom: 4px;
    border-bottom: 1px solid #eee;
}
h3 {
    font-size: 15px;
    font-weight: bold;
    color: #666;
    margin-top: 1.2em;
    margin-bottom: 0.5em;
}
p { margin: 0.4em 0; }
strong { color: #e74c3c; }
.report-table {
    width: 100%;
    border-collapse: collapse;
    margin: 0.8em 0;
    font-size: 0.9em;
}
.report-table th {
    background: #666;
    color: #ffffff;
    padding: 6px 10px;
    text-align: left;
    font-weight: bold;
}
.report-table td {
    border: 1px solid #ddd;
    padding: 5px 10px;
}
.report-table tr:nth-child(even) { background: #fafafa; }
pre {
    font-size: 0.85em;
    background: #f8f8f8;
    padding: 0.8em;
    border: 1px solid #e8e8e8;
    border-radius: 4px;
    overflow-x: auto;
}
.footer {
    margin-top: 2.5em;
    padding-top: 1em;
    border-top: 1px solid #e0e0e0;
    color: #bbb;
    font-size: 0.8em;
    text-align: center;
}
""",

    # ── 5. 商业咨询报告风 ──
    "商业咨询报告风": """
/* === 商业咨询报告风 === */
body {
    font-family: "Arial", "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
    max-width: 860px;
    margin: 0 auto;
    padding: 30px 50px;
    color: #2c3e50;
    line-height: 1.8;
    background: #fcfcfc;
}
h1 {
    text-align: left;
    font-size: 26px;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 0.3em;
    padding-bottom: 16px;
    border-bottom: 3px solid #e74c3c;
}
h2 {
    font-size: 18px;
    font-weight: 700;
    color: #1a1a2e;
    margin-top: 2.2em;
    margin-bottom: 0.8em;
    padding: 10px 16px;
    background: #f5f5f5;
    border-left: 5px solid #e74c3c;
}
h3 {
    font-size: 15px;
    font-weight: 700;
    color: #c0392b;
    margin-top: 1.2em;
    margin-bottom: 0.5em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 14px;
}
p { margin: 0.5em 0; line-height: 1.85; }
strong { color: #e74c3c; font-weight: 700; }
blockquote {
    margin: 1em 0;
    padding: 12px 20px;
    background: #fdf2f2;
    border-left: 4px solid #e74c3c;
    font-style: italic;
    color: #555;
}
.report-table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 0.9em;
}
.report-table th {
    background: #1a1a2e;
    color: #ffffff;
    padding: 8px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 0.85em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.report-table td {
    border: 1px solid #e0e0e0;
    padding: 7px 14px;
}
.report-table tr:nth-child(even) { background: #f9f9f9; }
pre {
    font-size: 0.85em;
    background: #f5f5f5;
    padding: 1em;
    border: 1px solid #e0e0e0;
    overflow-x: auto;
}
.footer {
    margin-top: 4em;
    padding-top: 20px;
    border-top: 1px solid #e0e0e0;
    color: #999;
    font-size: 0.8em;
    text-align: left;
}
.extract-box {
    background: #fdf2f2;
    border: 1px solid #f5c6cb;
    border-radius: 4px;
    padding: 16px 20px;
    margin: 1.5em 0;
}
.extract-box h4 {
    color: #e74c3c;
    margin: 0 0 8px 0;
    font-size: 14px;
    text-transform: uppercase;
}
""",
}


# ================================================================
# 公开接口
# ================================================================

def get_html_theme_css(theme_name: str) -> str:
    """获取指定主题的 CSS 样式。

    Args:
        theme_name: 主题名称，支持：
            - "学术论文白底风"
            - "政务蓝白汇报风"
            - "现代数据看板风"
            - "简洁课程作业风"
            - "商业咨询报告风"

    Returns:
        CSS 字符串
    """
    if theme_name in _THEME_CSS:
        return _THEME_CSS[theme_name]
    # fallback 到简洁课程作业风
    return _THEME_CSS.get("简洁课程作业风", "")


def get_available_themes() -> list:
    """返回所有可用主题名称列表。"""
    return list(_THEME_CSS.keys())


def render_html_report(
    markdown_content: str,
    html_theme: str = "简洁课程作业风",
    report_title: Optional[str] = None,
) -> str:
    """将 Markdown 报告渲染为完整 HTML 页面。

    Args:
        markdown_content: Markdown 格式的报告正文
        html_theme: HTML 展示主题，支持 5 种内置主题
        report_title: 报告标题（用于 <title> 和 <h1>）。如果为 None，尝试从 markdown 第一行提取。

    Returns:
        完整的 HTML 文档字符串
    """
    # ── 确定标题 ──
    if report_title is None:
        # 尝试从 markdown 第一行提取
        lines = markdown_content.strip().split("\n")
        first_line = lines[0].strip() if lines else ""
        if first_line.startswith("# "):
            report_title = first_line[2:].strip()
            markdown_content = "\n".join(lines[1:]).strip()  # 移除已有标题行，后续统一用 h1
        else:
            report_title = "数据分析报告"

    # ── 获取 CSS ──
    css = get_html_theme_css(html_theme)

    # ── Markdown → HTML 正文 ──
    body_html = _markdown_to_body_html(markdown_content)

    # ── 组装完整 HTML ──
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape_html(report_title)}</title>
<style>
{css}
</style>
</head>
<body>
<h1>{_escape_html(report_title)}</h1>
{body_html}
<div class="footer">
  <p>本报告由 AI 辅助生成 · 统计结果由程序计算 · 文字由大语言模型撰写</p>
</div>
</body>
</html>"""


# ================================================================
# 内部：Markdown → HTML 正文
# ================================================================

def _markdown_to_body_html(markdown_text: str) -> str:
    """将 Markdown 文本转换为 HTML 正文（不含 <html>/<head>/<body> 外层标签）。

    支持：标题（#/##/###）、加粗、表格、代码块、段落。
    """
    # 预处理：转义中文星号（**标准差** → \*\*标准差\*\*），防止误渲染
    from src.utils import escape_chinese_asterisks
    markdown_text = escape_chinese_asterisks(markdown_text)

    lines = markdown_text.split("\n")
    html_lines = []
    in_table = False
    in_code_block = False
    in_paragraph = False

    def _flush_paragraph():
        nonlocal in_paragraph
        if in_paragraph:
            html_lines.append("</p>")
            in_paragraph = False

    for line in lines:
        # ── 代码块 ──
        if line.startswith("```"):
            _flush_paragraph()
            _flush_table(html_lines, in_table)
            in_table = False
            if in_code_block:
                html_lines.append("</pre>")
                in_code_block = False
            else:
                html_lines.append('<pre>')
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(_escape_html(line))
            continue

        # ── 表格处理 ──
        if "|" in line and line.strip().startswith("|"):
            _flush_paragraph()
            cells = [c.strip() for c in line.strip().strip("|").split("|")]

            # 分隔行（如 |---|---|）
            if all(re.match(r'^:?-{2,}:?$', c) for c in cells):
                continue

            if not in_table:
                in_table = True
                html_lines.append('<table class="report-table">')
                # 第一行是表头
                html_lines.append("<thead><tr>")
                for c in cells:
                    html_lines.append(f"<th>{_escape_html(c)}</th>")
                html_lines.append("</tr></thead><tbody>")
            else:
                html_lines.append("<tr>")
                for c in cells:
                    html_lines.append(f"<td>{_escape_html(c)}</td>")
                html_lines.append("</tr>")
            continue
        else:
            if in_table:
                html_lines.append("</tbody></table>")
                in_table = False

        # ── 标题 ──
        if line.startswith("### "):
            _flush_paragraph()
            html_lines.append(f"<h3>{_escape_html(line[4:])}</h3>")
            continue
        elif line.startswith("## "):
            _flush_paragraph()
            html_lines.append(f"<h2>{_escape_html(line[3:])}</h2>")
            continue
        elif line.startswith("# "):
            _flush_paragraph()
            html_lines.append(f"<h1>{_escape_html(line[2:])}</h1>")
            continue

        # ── 空行 → 段落结束 ──
        if line.strip() == "":
            _flush_paragraph()
            continue

        # ── 普通文本（处理加粗） ──
        processed = _process_inline_formatting(line)
        if not in_paragraph:
            html_lines.append("<p>")
            in_paragraph = True
        html_lines.append(processed)

    # ── 收尾 ──
    _flush_paragraph()
    if in_table:
        html_lines.append("</tbody></table>")
    if in_code_block:
        html_lines.append("</pre>")

    return "\n".join(html_lines)


def _flush_table(html_lines, in_table):
    """辅助：如果正在表格中，关闭表格标签。"""
    if in_table:
        html_lines.append("</tbody></table>")


def _process_inline_formatting(text: str) -> str:
    """处理行内格式：加粗（**text**）、斜体（*text*）。"""
    # 加粗
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # 斜体
    text = re.sub(r"(?<![\\*])\*(?!\*)(.+?)(?<![\\*])\*(?!\*)", r"<em>\1</em>", text)
    return _escape_html_except_tags(text)


def _escape_html_except_tags(text: str) -> str:
    """转义 HTML 特殊字符，但保留已有的 <strong>/<em>/<a> 标签。"""
    # 先把已有的 HTML 标签替换为占位符
    placeholders = {}

    def _replace_tag(match):
        key = f"\x00TAG{len(placeholders)}\x00"
        placeholders[key] = match.group(0)
        return key

    text = re.sub(r"<(/?)(strong|em|a)(\s[^>]*)?>", _replace_tag, text)

    # 转义剩余 HTML 字符
    text = _escape_html(text)

    # 恢复占位符标签
    for key, tag in placeholders.items():
        text = text.replace(key, tag)

    return text
