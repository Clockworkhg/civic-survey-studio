"""数据加载模块 —— 读取调查数据与变量赋值表，构建变量字典。

变量赋值表结构（public_service_variable_diction）：
  - 变量名：对应调查数据中的英文列名
  - 中文含义：变量在问卷中的中文表述
  - 类型：变量类型（如 分类变量、数值变量）
  - 取值或说明：编码值与含义标签的说明文本（如 "1=男, 2=女"）
  - 变量用途：该变量在分析中的用途说明
"""

import pandas as pd
import streamlit as st
from typing import Optional, List, Dict, Any, Union

from src.utils import parse_value_description


# ---- 工作表名称 ----
SURVEY_SHEET_NAME = "SPSS_Data"
VARIABLE_SHEET_NAME = "public_service_variable_diction"

# ---- 变量赋值表的期望列 ----
VAR_NAME_COL = "变量名"
VAR_CN_MEANING_COL = "中文含义"
VAR_TYPE_COL = "类型"
VAR_VALUE_DESC_COL = "取值或说明"
VAR_USAGE_COL = "变量用途"


# ================================================================
# 数据读取
# ================================================================

@st.cache_data(show_spinner="正在加载调查数据…")
def load_survey_data(uploaded_file) -> Optional[pd.DataFrame]:
    """从上传的 Excel 文件读取调查数据（工作表：SPSS_Data）。

    Args:
        uploaded_file: Streamlit UploadedFile 对象

    Returns:
        原始数据 DataFrame；读取失败时返回 None
    """
    if uploaded_file is None:
        return None

    try:
        df = pd.read_excel(uploaded_file, sheet_name=SURVEY_SHEET_NAME)
        if df.empty:
            st.warning(f"工作表「{SURVEY_SHEET_NAME}」为空。")
        return df
    except ValueError as e:
        st.error(f"未找到工作表「{SURVEY_SHEET_NAME}」，请确认文件是否正确。\n\n({e})")
        return None
    except Exception as e:
        st.error(f"读取调查数据失败：{e}")
        return None


@st.cache_data(show_spinner="正在加载变量赋值表…")
def load_variable_table(uploaded_file) -> Optional[pd.DataFrame]:
    """从上传的 Excel 文件读取变量赋值表（工作表：public_service_variable_diction）。

    Args:
        uploaded_file: Streamlit UploadedFile 对象

    Returns:
        变量赋值表 DataFrame；读取失败时返回 None
    """
    if uploaded_file is None:
        return None

    try:
        df = pd.read_excel(uploaded_file, sheet_name=VARIABLE_SHEET_NAME)
        if df.empty:
            st.warning(f"工作表「{VARIABLE_SHEET_NAME}」为空。")
            return None
        _validate_variable_columns(df)
        return df
    except ValueError as e:
        st.error(f"未找到工作表「{VARIABLE_SHEET_NAME}」，请确认文件是否正确。\n\n({e})")
        return None
    except Exception as e:
        st.error(f"读取变量赋值表失败：{e}")
        return None


# ================================================================
# 变量字典构建
# ================================================================

def build_variable_dict(variable_table: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """从变量赋值表构建 英文字段名 → 变量元信息 的字典。

    返回结构示例：
    {
        "gender": {
            "变量名": "gender",
            "中文含义": "性别",
            "类型": "分类变量",
            "取值或说明": "1=男, 2=女",
            "变量用途": "用于描述受访者性别分布",
            "labels": {1: "男", 2: "女"},
        },
        ...
    }

    Args:
        variable_table: 变量赋值表 DataFrame

    Returns:
        变量字典，key 为英文变量名
    """
    if variable_table is None or variable_table.empty:
        return {}

    name_col = _resolve_column(variable_table, [VAR_NAME_COL, "Variable"])
    if name_col is None:
        return {}

    var_dict = {}
    for _, row in variable_table.iterrows():
        var_name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
        if not var_name:
            continue

        # 避免重复变量名（取首次出现）
        if var_name in var_dict:
            continue

        # 提取各字段
        cn_meaning = _safe_get(row, variable_table, [VAR_CN_MEANING_COL])
        var_type   = _safe_get(row, variable_table, [VAR_TYPE_COL])
        value_desc = _safe_get(row, variable_table, [VAR_VALUE_DESC_COL])
        usage      = _safe_get(row, variable_table, [VAR_USAGE_COL])

        # 解析编码→标签映射
        labels = parse_value_description(value_desc) if value_desc else {}

        var_dict[var_name] = {
            "变量名":     var_name,
            "中文含义":   cn_meaning,
            "类型":       var_type,
            "取值或说明": value_desc,
            "变量用途":   usage,
            "labels":     labels,
        }

    return var_dict


def create_display_dataframe(
    survey_df: pd.DataFrame,
    var_dict: Dict[str, Dict[str, Any]],
) -> pd.DataFrame:
    """生成带中文标签的展示用 DataFrame。

    - 分类变量：将编码值替换为中文标签（如 1→"男"）
    - 数值变量：保持原始数值不变
    - 原始 survey_df **不会被修改**

    Args:
        survey_df: 原始调查数据（数值编码）
        var_dict: build_variable_dict 构建的变量字典

    Returns:
        中文标签化的 DataFrame（仅供展示）
    """
    display_df = survey_df.copy()

    for col in display_df.columns:
        info = var_dict.get(col)
        if info is None:
            continue

        labels = info.get("labels", {})
        if not labels:
            continue

        # 仅对有标签映射的列做替换（即分类变量）
        try:
            mapped = display_df[col].map(labels)
            # 只替换成功映射的值，保留未映射的原始值
            display_df[col] = mapped.where(mapped.notna(), display_df[col])
        except Exception:
            # map 失败则保持原值
            continue

    return display_df


# ================================================================
# 变量信息查询
# ================================================================

def get_variable_list(variable_table: pd.DataFrame) -> List[str]:
    """获取调查数据中所有变量的名称列表（去重）。"""
    if variable_table is None or variable_table.empty:
        return []
    col = _resolve_column(variable_table, [VAR_NAME_COL, "Variable", "variable"])
    if col is None:
        return []
    return variable_table[col].dropna().astype(str).unique().tolist()


def get_variable_detail(
    variable_table: pd.DataFrame,
    var_name: str,
) -> Dict[str, str]:
    """获取某个变量的完整说明信息。

    Returns:
        {"变量名": ..., "中文含义": ..., "类型": ...,
         "取值或说明": ..., "变量用途": ...}
        未找到的字段值为空字符串。
    """
    default: Dict[str, str] = {
        "变量名": var_name,
        "中文含义": "",
        "类型": "",
        "取值或说明": "",
        "变量用途": "",
    }
    if variable_table is None or variable_table.empty:
        return default

    name_col = _resolve_column(variable_table, [VAR_NAME_COL, "Variable"])
    if name_col is None:
        return default

    row = variable_table[variable_table[name_col].astype(str) == str(var_name)]
    if row.empty:
        return default

    row = row.iloc[0]
    result: Dict[str, str] = {}
    for field, candidates in [
        ("变量名",     [VAR_NAME_COL, "Variable"]),
        ("中文含义",   [VAR_CN_MEANING_COL]),
        ("类型",       [VAR_TYPE_COL]),
        ("取值或说明", [VAR_VALUE_DESC_COL]),
        ("变量用途",   [VAR_USAGE_COL]),
    ]:
        col = _resolve_column(variable_table, candidates)
        result[field] = str(row[col]) if col and pd.notna(row.get(col)) else ""
    return result


def get_data_overview(survey_df: pd.DataFrame) -> Dict[str, Any]:
    """生成数据概览摘要。

    Returns:
        {"样本量": int, "变量数": int, "缺失值总数": int, "缺失率": float}
    """
    total_cells = survey_df.size
    missing_total = int(survey_df.isnull().sum().sum())
    return {
        "样本量": len(survey_df),
        "变量数": len(survey_df.columns),
        "缺失值总数": missing_total,
        "缺失率": round(missing_total / total_cells * 100, 2) if total_cells > 0 else 0.0,
    }


# ================================================================
# 内部辅助
# ================================================================

def _resolve_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """返回 DataFrame 中第一个存在的候选列名。"""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _safe_get(
    row: pd.Series,
    df: pd.DataFrame,
    candidates: List[str],
) -> str:
    """从一行中安全获取字段值（按候选列名查找）。"""
    col = _resolve_column(df, candidates)
    if col is None:
        return ""
    val = row.get(col)
    return str(val).strip() if pd.notna(val) else ""


def _validate_variable_columns(df: pd.DataFrame) -> None:
    """检查变量赋值表是否包含期望列，缺失时给出警告。"""
    expected = {
        VAR_NAME_COL, VAR_CN_MEANING_COL,
        VAR_TYPE_COL, VAR_VALUE_DESC_COL, VAR_USAGE_COL,
    }
    actual = set(df.columns)
    missing = expected - actual
    if missing:
        st.warning(
            f"变量赋值表缺少以下列：{', '.join(sorted(missing))}。"
            f"部分功能可能受限。"
        )


# ================================================================
# 通用模式：灵活数据读取（支持 Excel 多 Sheet / CSV / 表头行配置）
# ================================================================

def get_excel_sheets(uploaded_file) -> list:
    """获取 Excel 文件中的所有工作表名称。

    Args:
        uploaded_file: Streamlit UploadedFile 对象

    Returns:
        工作表名称列表；失败时返回空列表
    """
    if uploaded_file is None:
        return []
    try:
        import openpyxl
        wb = openpyxl.load_workbook(uploaded_file, read_only=True)
        sheets = wb.sheetnames
        wb.close()
        return sheets
    except Exception:
        # 回退：使用 pandas
        try:
            xl = pd.ExcelFile(uploaded_file)
            return xl.sheet_names
        except Exception:
            return []


@st.cache_data(show_spinner="正在加载数据…")
def load_generic_data(
    uploaded_file,
    sheet_name: str = None,
    header_row: int = 0,
) -> "pd.DataFrame | None":
    """通用数据加载器，支持 Excel（.xlsx/.xls）和 CSV（.csv）。

    对于 Excel 文件：
      - 如果指定 sheet_name，读取对应工作表
      - 如果未指定，读取第一个工作表
    对于 CSV 文件：
      - 自动尝试常见编码（utf-8, gbk, gb2312, utf-8-sig）

    Args:
        uploaded_file: Streamlit UploadedFile 对象
        sheet_name: Excel 工作表名称（仅对 Excel 有效）
        header_row: 表头所在行（0=第一行，默认）

    Returns:
        读取的 DataFrame；失败时返回 None
    """
    if uploaded_file is None:
        return None

    # 兼容字符串路径（测试用）和 Streamlit UploadedFile
    if isinstance(uploaded_file, str):
        file_name = uploaded_file.lower()
    else:
        file_name = uploaded_file.name.lower()

    try:
        # 兼容字符串路径和 UploadedFile
        file_obj = uploaded_file

        # --- CSV ---
        if file_name.endswith(".csv"):
            # 尝试多种编码
            for encoding in ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin-1"]:
                try:
                    df = pd.read_csv(
                        file_obj,
                        header=header_row if header_row is not None else 0,
                        encoding=encoding,
                    )
                    if not df.empty:
                        return df
                except (UnicodeDecodeError, UnicodeError):
                    continue
            # 最后一次尝试
            df = pd.read_csv(file_obj, header=header_row if header_row is not None else 0)
            return df if not df.empty else None

        # --- Excel ---
        elif file_name.endswith((".xlsx", ".xls")):
            # 获取所有工作表
            all_sheets = get_excel_sheets(file_obj)

            if sheet_name and sheet_name in all_sheets:
                target_sheet = sheet_name
            elif all_sheets:
                target_sheet = all_sheets[0]  # 默认第一个
            else:
                target_sheet = 0  # pandas 默认

            df = pd.read_excel(
                file_obj,
                sheet_name=target_sheet,
                header=header_row if header_row is not None else 0,
            )
            if df.empty:
                st.warning(f"工作表「{target_sheet}」为空。")
            return df

        else:
            st.error(f"不支持的文件格式：{file_name}。请上传 .xlsx、.xls 或 .csv 文件。")
            return None

    except Exception as e:
        st.error(f"读取数据失败：{e}")
        return None


def load_generic_variable_table(uploaded_file) -> "pd.DataFrame | None":
    """通用变量说明表加载器（可选上传）。

    支持 Excel 和 CSV 格式。
    自动检测包含变量名/中文含义/类型的列。

    Args:
        uploaded_file: Streamlit UploadedFile 对象（可为 None）

    Returns:
        变量说明表 DataFrame；uploaded_file 为 None 时返回 None
    """
    if uploaded_file is None:
        return None

    try:
        df = load_generic_data(uploaded_file)
        if df is None:
            return None
        # 确保至少有一列看起来像变量名
        if len(df.columns) == 0:
            st.warning("变量说明表为空。")
            return None
        return df
    except Exception as e:
        st.warning(f"读取变量说明表失败：{e}。将使用自动推断的变量类型。")
        return None


def get_data_quality_report(df: pd.DataFrame) -> dict:
    """生成数据质量报告。

    Args:
        df: 数据 DataFrame

    Returns:
        {
            "样本量": int,
            "变量数": int,
            "缺失值总数": int,
            "缺失率": float,
            "重复行数": int,
            "重复率": float,
            "内存占用": str,
        }
    """
    total_cells = df.size
    missing_total = int(df.isnull().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    # 内存占用
    mem_bytes = df.memory_usage(deep=True).sum()
    if mem_bytes < 1024:
        mem_str = f"{mem_bytes} B"
    elif mem_bytes < 1024 * 1024:
        mem_str = f"{mem_bytes / 1024:.1f} KB"
    else:
        mem_str = f"{mem_bytes / (1024 * 1024):.1f} MB"

    return {
        "样本量": len(df),
        "变量数": len(df.columns),
        "缺失值总数": missing_total,
        "缺失率": round(missing_total / total_cells * 100, 2) if total_cells > 0 else 0.0,
        "重复行数": duplicate_rows,
        "重复率": round(duplicate_rows / len(df) * 100, 2) if len(df) > 0 else 0.0,
        "内存占用": mem_str,
    }
