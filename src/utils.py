"""工具函数模块 —— 通用辅助函数。"""

import re
import pandas as pd
from typing import Optional, Dict


def safe_float_convert(series: pd.Series) -> pd.Series:
    """安全地将 Series 转换为浮点数，非数值替换为 NaN。"""
    return pd.to_numeric(series, errors="coerce")


def filter_valid_responses(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """过滤掉某列中为 NaN 或空字符串的行。"""
    return df[df[col].notna() & (df[col] != "")]


def parse_value_description(text: str) -> Dict[int, str]:
    """从「取值或说明」文本中解析编码值→含义标签的映射。

    支持格式示例：
      - "1=男, 2=女"
      - "1-男；2-女"
      - "1:非常不满意, 2:不满意, 3:一般, 4:满意, 5:非常满意"
      - "1 男\n2 女"

    Args:
        text: 变量赋值表中「取值或说明」列的原始文本

    Returns:
        {编码值(int): 标签(str)} 字典；解析失败返回空字典
    """
    if pd.isna(text) or not str(text).strip():
        return {}

    text = str(text).strip()

    # 尝试多种分隔模式，优先级从高到低
    patterns = [
        # "1=男, 2=女" / "1=男; 2=女"
        (r"[,;，；]\s*", r"(\d+)\s*[=：:]\s*(.+?)(?=\s*$|\s*[,;，；]\s*\d+\s*[=：:])"),
        # "1-男, 2-女"
        (r"[,;，；]\s*", r"(\d+)\s*[-－]\s*(.+?)(?=\s*$|\s*[,;，；]\s*\d+\s*[-－])"),
        # "1 男\n2 女"
        (r"[\n\r]+", r"(\d+)\s+(.+)"),
    ]

    for split_pattern, extract_pattern in patterns:
        parts = re.split(split_pattern, text)
        if len(parts) >= 2:
            mapping = {}
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                m = re.match(extract_pattern, part.strip())
                if m:
                    code = int(m.group(1))
                    label = m.group(2).strip().rstrip(",;，；")
                    mapping[code] = label
            if mapping:
                return mapping

    # 兜底：按数字后跟非数字的模式提取
    fallback = {}
    tokens = re.findall(r"(\d+)\s*[=：:\-－\s]+(.+?)(?=\s*\d+\s*[=：:\-－\s]|$)", text)
    for code_str, label in tokens:
        try:
            fallback[int(code_str)] = label.strip().rstrip(",;，；")
        except ValueError:
            continue
    return fallback


def get_value_label_mapping(
    variable_table: pd.DataFrame, var_name: str
) -> Dict[int, str]:
    """从变量赋值表中获取某个变量的 编码值→标签 映射。

    优先从「取值或说明」列解析；如果该列为空则尝试从其他列推断。

    Args:
        variable_table: 变量赋值表 DataFrame
        var_name: 目标变量名（对应「变量名」列）

    Returns:
        {编码值(int): 标签(str)} 字典
    """
    # 匹配变量名列
    name_col = _find_column(variable_table, ["变量名", "Variable", "variable", "变量"])
    if name_col is None:
        return {}

    row = variable_table[variable_table[name_col] == var_name]
    if row.empty:
        return {}

    row = row.iloc[0]

    # 优先从「取值或说明」解析
    desc_col = _find_column(variable_table, ["取值或说明", "Value", "value", "取值", "说明"])
    if desc_col and pd.notna(row.get(desc_col)):
        mapping = parse_value_description(row[desc_col])
        if mapping:
            return mapping

    return {}


def _find_column(df: pd.DataFrame, candidates: list) -> Optional[str]:
    """在 DataFrame 中查找第一个存在的候选列名。"""
    for col in candidates:
        if col in df.columns:
            return col
    return None


def escape_chinese_asterisks(text: str) -> str:
    """转义包裹中文文本的 Markdown 星号，防止误渲染为加粗/斜体。

    在中文报告中，**和*常被 LLM 用作中文强调标记（而非 Markdown 格式）。
    本函数检测**...**和*...*中是否包含 CJK 字符，若包含则转义为字面量星号。

    Args:
        text: 待处理的文本（Markdown 报告）

    Returns:
        转义后的文本。仅英文的 **...** / *...* 保留不变。
    """
    import re

    CJK = re.compile(r'[一-鿿　-〿＀-￯]')

    def _has_cjk(s: str) -> bool:
        return bool(CJK.search(s))

    # Escape **...** containing CJK → \*\*...\*\*
    def _escape_double(m: re.Match) -> str:
        inner = m.group(1)
        if _has_cjk(inner):
            return '\x5c*\x5c*' + inner + '\x5c*\x5c*'
        return m.group(0)

    text = re.sub(r'\*\*([^*]+)\*\*', _escape_double, text)

    # Escape *...* containing CJK (single asterisks, more conservative)
    def _escape_single(m: re.Match) -> str:
        inner = m.group(1)
        if _has_cjk(inner):
            return '\x5c*' + inner + '\x5c*'
        return m.group(0)

    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', _escape_single, text)
    return text
