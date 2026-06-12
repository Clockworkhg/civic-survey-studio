"""变量类型自动推断模块 —— 根据数据特征自动识别每个字段的变量类型。

识别依据：
  1. 数据类型（dtype）
  2. 唯一值数量与唯一值比例
  3. 字段名关键词（中英文）
  4. 是否为量表题（1-5、1-7、1-10 等）

输出变量类型：
  - id：编号类变量（唯一值比例 ≈ 1.0）
  - numeric：连续数值变量
  - categorical：无序分类变量（唯一值少）
  - binary：二分类变量（0/1、是/否、男/女等二值变量）
  - ordinal：有序分类变量（量表题 / 等级类）
  - datetime：日期时间变量
  - text：文本变量（长文本 / 唯一值多）
  - high_cardinality：高基数分类变量（唯一值过多不适宜直接做分组）
"""

import re
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Tuple


# ================================================================
# 关键词模式
# ================================================================

# 编号 / ID 类关键词
ID_KEYWORDS = [
    "id", "ID", "Id", "编号", "序号", "code", "Code", "问卷编号",
    "respondent_id", "case_id", "record_id", "流水号",
]

# 日期时间类关键词
DATETIME_KEYWORDS = [
    "时间", "日期", "date", "time", "datetime", "timestamp",
    "年月", "时分", "created", "updated", "提交时间", "填写时间",
    "开始时间", "结束时间", "create_time", "update_time",
]

# 有序 / 量表类关键词
ORDINAL_KEYWORDS = [
    "满意度", "评分", "等级", "level", "score", "rating", "scale",
    "重要", "同意", "满意", "评价", "打分", "程度", "频率",
    "经常", "总是", "agree", "satisfaction", "importance",
    "frequency", "degree", "grade", "rank",
]

# 常见量表范围
SCALE_RANGES = [
    (1, 5), (1, 7), (1, 10), (0, 5), (0, 10),
    (1, 4), (1, 6), (1, 9), (0, 4), (0, 100),
]

# 分类变量最大唯一值数（数值型）
CATEGORICAL_MAX_UNIQUE_NUMERIC = 12

# 分类变量最大唯一值数（文本型）
CATEGORICAL_MAX_UNIQUE_TEXT = 20

# 文本 / 开放题关键词
TEXT_KEYWORDS = [
    "comment", "feedback", "suggestion", "建议", "意见", "反馈",
    "开放", "文本", "备注", "说明", "其他", "补充", "remark", "note",
    "改进", "留言", "评价", "review", "describe", "描述",
]

# 连续数值关键词（不应被判定为有序/量表）
CONTINUOUS_KEYWORDS = [
    "age", "年龄", "duration", "时长", "time", "时间", "min", "分钟",
    "distance", "距离", "income", "收入", "amount", "金额", "price", "价格",
    "percent", "百分比", "rate", "率",
]

# 文本变量最小唯一比例（超过此值且为 object 类型视为文本）
TEXT_MIN_UNIQUE_RATIO = 0.5


# ================================================================
# 隐私风险评估
# ================================================================

# ── 隐私风险等级关键词 ──
# 格式: (风险等级, 隐私分类) → 关键词列表
# 原则: 系统识别风险、标记分类；用户决定是否发送给 AI

PRIVACY_KEYWORD_MAP: Dict[str, List[Tuple[str, str]]] = {
    # 低风险 — 人口统计属性（正常统计分析变量）
    "demographic_attribute_low": [
        "年龄", "age", "年龄组", "age_group", "出生年份", "birth_year",
        "性别", "gender", "sex",
        "学历", "education", "教育程度", "degree", "edu",
        "职业", "occupation", "job", "profession", "工作",
        "年级", "grade", "班级", "class",
        "专业", "major", "discipline",
        "部门", "department", "dept", "单位",
        "地区", "region", "省份", "province", "城市", "city",
        "区县", "district", "county", "prefecture",
        "收入区间", "income_range", "income_level", "income_bracket", "薪资区间",
        "婚姻", "marriage", "marital", "婚否",
        "民族", "ethnicity", "ethnic",
        "户口", "hukou", "户籍",
        "会员等级", "membership", "等级", "level",
        "设备", "device", "平台", "platform",
        "渠道", "channel", "来源", "source",
        "年龄段", "age_range",
        "学历段", "edu_level",
    ],

    # 高风险 — 直接身份标识
    "direct_identifier_high": [
        "姓名", "名字", "name", "full_name", "real_name", "username",
        "身份证", "id_card", "id_number", "身份证号", "证件号",
        "学号", "student_id", "stu_id", "学籍号",
        "工号", "employee_id", "emp_id", "staff_id", "员工号",
        "护照", "passport", "护照号",
        "病历号", "patient_id", "medical_record",
        "车牌号", "license_plate", "plate_number",
        "社保号", "social_security", "ssn", "社保",
    ],

    # 高风险 — 联系方式
    "contact_info_high": [
        "手机", "电话", "mobile", "phone", "tel", "cell", "cellphone",
        "邮箱", "email", "e-mail", "mail", "电子邮箱",
        "微信", "wechat", "weixin", "微信号",
        "qq", "QQ", "qq号",
        "微博", "weibo",
        "whatsapp", "telegram", "line_id",
        "住址", "地址", "address", "addr", "家庭住址", "详细地址",
        "街道", "street", "门牌",
        "邮编", "zip", "zipcode", "postal",
    ],

    # 高风险 — 金融信息
    "financial_high": [
        "银行卡", "bank_card", "credit_card", "debit_card", "卡号",
        "银行账号", "bank_account", "account_number",
        "密码", "password", "passwd", "pin", "支付密码",
    ],

    # 中风险 — 敏感属性
    "sensitive_attribute_medium": [
        "健康状况", "health", "健康",
        "疾病", "disease", "illness", "病史",
        "宗教信仰", "religion", "宗教", "信仰",
        "政治面貌", "political", "政治",
        "收入", "income", "薪资", "salary", "工资", "月收入",
        "犯罪记录", "criminal", "犯罪",
        "性取向", "sexual_orientation",
        "生物特征", "biometric", "指纹", "fingerprint",
    ],

    # 中风险 — 地理位置（详细地址已是高风险，这里是区域级）
    "location_info_medium": [
        "街道", "street", "社区", "community",
        "小区", "neighborhood", "楼盘",
        "邮编", "zipcode", "postal_code",
    ],

    # 中风险 — 自由文本（可能含个人信息）
    "free_text_medium": [
        "意见", "建议", "suggestion", "feedback",
        "备注", "remark", "note", "说明", "comment",
        "评价内容", "review", "评价",
        "投诉", "complaint", "投诉内容",
        "开放", "open_comment", "open_text", "主观题",
        "改进", "improvement", "期望", "expectation",
        "其他", "other", "补充", "additional",
    ],
}

# ── 隐私风险值模式 ──
# 用于检测列值中是否包含明显个人信息
PRIVACY_VALUE_PATTERNS = [
    (re.compile(r'^1[3-9]\d{9}$'), "high", "contact_info"),          # 中国手机号
    (re.compile(r'^\d{17}[\dXx]$'), "high", "direct_identifier"),     # 中国身份证
    (re.compile(r'^[^@]+@[^@]+\.[^@]+$'), "high", "contact_info"),    # 邮箱
    (re.compile(r'^\d{3}[-.]?\d{3}[-.]?\d{4}$'), "high", "contact_info"),  # 美国电话
    (re.compile(r'^\d{16,19}$'), "high", "financial"),                # 银行卡号
    (re.compile(r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青川藏宁琼]'
                r'[A-Z][A-HJ-NP-Z0-9]{4}[A-HJ-NP-Z0-9挂学警港澳]{1}$'), "high", "direct_identifier"),  # 中国车牌
]

# ── 默认使用策略 ──
DEFAULT_USAGE_POLICIES = {
    "none": {
        "allow_local_stats": True,
        "allow_as_group_variable": True,
        "allow_in_model": True,
        "allow_send_to_ai": True,
        "send_to_ai_mode": "aggregate_only",
    },
    "low": {
        "allow_local_stats": True,
        "allow_as_group_variable": True,
        "allow_in_model": True,
        "allow_send_to_ai": True,
        "send_to_ai_mode": "aggregate_only",
    },
    "medium": {
        "allow_local_stats": True,
        "allow_as_group_variable": True,
        "allow_in_model": True,
        "allow_send_to_ai": True,
        "send_to_ai_mode": "aggregate_only",
    },
    "high": {
        "allow_local_stats": True,
        "allow_as_group_variable": False,
        "allow_in_model": False,
        "allow_send_to_ai": False,
        "send_to_ai_mode": "exclude",
    },
}


# ================================================================
# 主入口
# ================================================================

def infer_variable_schema(
    df: pd.DataFrame,
    variable_table: Optional[pd.DataFrame] = None,
    variable_dict_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> pd.DataFrame:
    """推断数据集中每个变量的类型和分析建议。

    Args:
        df: 原始数据 DataFrame
        variable_table: 可选的变量说明表。如果提供，其中的类型定义
            将优先于自动推断结果。
        variable_dict_map: 可选的预解析变量说明字典。
            如果提供，优先用于 display_name、类型和 value_labels。

    Returns:
        变量说明 DataFrame，包含以下列：
          - column: 变量名
          - display_name: 显示名称（优先使用变量表中的中文含义）
          - inferred_type: 推断的变量类型
          - missing_count: 缺失值数量
          - missing_rate: 缺失值比例
          - unique_count: 唯一值数量
          - example_values: 示例值（最多 5 个）
          - suggested_role: 建议的角色（target/group/predictor/id/skip）
          - suggested_analysis: 建议的分析方法
          - privacy_risk: 隐私风险等级（none/low/medium/high）
          - privacy_category: 隐私分类（none/demographic_attribute/contact_info/
              direct_identifier/location_info/free_text/sensitive_attribute/financial/unknown）
          - allow_local_stats: 是否允许本地统计
          - allow_as_group_variable: 是否允许作为分组变量
          - allow_in_model: 是否允许进入相关/回归模型
          - allow_send_to_ai: 是否允许发送给 AI
          - send_to_ai_mode: AI 发送方式（exclude/aggregate_only/masked_examples/full）
          - user_confirmed_privacy: 用户是否已确认隐私设置
    """
    n_rows = len(df)
    results = []

    # 解析变量表（如果提供）
    if variable_dict_map is not None:
        var_table_map = variable_dict_map
    elif variable_table is not None:
        var_table_map = build_variable_dict_map(variable_table)
    else:
        var_table_map = {}

    for col in df.columns:
        series = df[col]

        # 缺失值统计
        missing_count = int(series.isna().sum())
        missing_rate = round(missing_count / n_rows, 4) if n_rows > 0 else 0.0

        # 唯一值
        unique_vals = series.dropna().unique()
        unique_count = len(unique_vals)
        unique_ratio = unique_count / max(n_rows - missing_count, 1)

        # 示例值
        example_values = _get_example_values(series, unique_vals)

        # 推断类型
        inferred_type = _infer_single_column(
            series=series,
            col_name=col,
            n_rows=n_rows,
            unique_count=unique_count,
            unique_ratio=unique_ratio,
        )

        # 变量表覆盖
        display_name = ""
        if col in var_table_map:
            vt_info = var_table_map[col]
            display_name = vt_info.get("中文含义", "")
            user_type = vt_info.get("类型", "")
            if user_type:
                inferred_type = _normalize_type(user_type)

        # 合理性修正：var_dict 可能将 Likert 量表误标为 categorical
        # 但绝不覆盖 binary 类型（0/1 唯一值=2 但符合量表范围如 (0,5)）
        if inferred_type == "categorical" and pd.api.types.is_numeric_dtype(df[col]):
            clean = df[col].dropna()
            if _detect_scale_pattern(clean):
                inferred_type = "ordinal"

        # 建议角色
        suggested_role = _suggest_role(col, inferred_type, unique_count, unique_ratio, n_rows, display_name)
        # 建议分析方法
        suggested_analysis = _suggest_analysis(inferred_type)
        # 隐私风险评估
        privacy = _assess_privacy_risk(col, series, inferred_type)

        results.append({
            "column": col,
            "display_name": display_name,
            "inferred_type": inferred_type,
            "missing_count": missing_count,
            "missing_rate": round(missing_rate * 100, 2),
            "unique_count": unique_count,
            "example_values": example_values,
            "suggested_role": suggested_role,
            "suggested_analysis": suggested_analysis,
            "privacy_risk": privacy["privacy_risk"],
            "privacy_category": privacy["privacy_category"],
            "allow_local_stats": privacy["allow_local_stats"],
            "allow_as_group_variable": privacy["allow_as_group_variable"],
            "allow_in_model": privacy["allow_in_model"],
            "allow_send_to_ai": privacy["allow_send_to_ai"],
            "send_to_ai_mode": privacy["send_to_ai_mode"],
            "user_confirmed_privacy": privacy["user_confirmed_privacy"],
        })

    return pd.DataFrame(results)


# ================================================================
# 类型推断核心
# ================================================================

def _infer_single_column(
    series: pd.Series,
    col_name: str,
    n_rows: int,
    unique_count: int,
    unique_ratio: float,
) -> str:
    """推断单个列的类型。

    决策优先级（从高到低）：
      1. ID 类 → id
      2. 日期时间 → datetime
      3. 唯一值极多的文本 → text
      4. 唯一值较多的文本 → high_cardinality
      5. 二分类检测（0/1、是/否等）→ binary
      6. 数值量表 → ordinal
      7. 数值少唯一 → categorical
      8. 数值连续 → numeric
      9. 文本少唯一 → categorical（先检查二分类）
      9. 兜底 → text
    """
    dtype = series.dtype
    col_lower = col_name.lower()
    effective_n = max(n_rows - int(series.isna().sum()), 1)

    # ---- 1. 日期时间检测（最高优先级）----
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if _match_keywords(col_lower, DATETIME_KEYWORDS):
        if _try_parse_datetime(series):
            return "datetime"

    # ---- 2. ID 检测（数值型 或 字符串型如 V00001/S0001）----
    if pd.api.types.is_numeric_dtype(series):
        if unique_ratio >= 0.98 and unique_count >= effective_n * 0.95:
            return "id"
    # 字符串型 ID：全部唯一 + 名称含 id 关键词
    if (dtype == object or pd.api.types.is_string_dtype(series)):
        if unique_ratio >= 0.98 and _match_keywords(col_lower, ID_KEYWORDS):
            return "id"
    # 名称强匹配 ID 关键词
    if _match_keywords(col_lower, ID_KEYWORDS) and unique_ratio >= 0.8:
        return "id"

    # ---- 3. 文本检测（包含文本/评论/开放题关键词即使唯一值少也是文本）----
    if (dtype == object or pd.api.types.is_string_dtype(series)):
        # 文本关键词显式标记 → 即使唯一值少也是文本
        if _match_keywords(col_lower, TEXT_KEYWORDS):
            return "text"
        if unique_ratio >= TEXT_MIN_UNIQUE_RATIO:
            return "text"
        if unique_count > CATEGORICAL_MAX_UNIQUE_TEXT:
            return "high_cardinality"
        # object 但唯一值少 → 先检查二分类，再归为分类变量
        if _detect_binary_pattern(series):
            return "binary"
        return "categorical"

    # ---- 4. 数值型检测 ----
    if pd.api.types.is_numeric_dtype(series):
        clean = series.dropna()

        # 二分类变量（0/1 等）→ binary（必须在量表检测前）
        if unique_count == 2:
            return "binary"

        # 连续数值关键词 → 跳过量表检测
        is_continuous_kw = _match_keywords(col_lower, CONTINUOUS_KEYWORDS)

        # 检查是否为量表模式（排除明显连续变量）
        if not is_continuous_kw and _detect_scale_pattern(clean):
            return "ordinal"

        # 关键词匹配有序
        if _match_keywords(col_lower, ORDINAL_KEYWORDS):
            return "ordinal"

        # 唯一值很少 → 分类变量
        if unique_count <= CATEGORICAL_MAX_UNIQUE_NUMERIC:
            if _is_integer_sequence(clean):
                return "ordinal"
            return "categorical"

        # 连续数值
        return "numeric"

    # ---- 5. 兜底 ----
    if unique_count <= CATEGORICAL_MAX_UNIQUE_TEXT:
        return "categorical"
    return "text"


# ================================================================
# 辅助检测函数
# ================================================================

def _detect_scale_pattern(series: pd.Series) -> bool:
    """检测一个数值序列是否符合量表模式（如 1-5, 1-7, 1-10）。

    判断条件：
      - 所有非空值都是整数
      - 值的范围恰好落入某个常见量表范围
      - 值不包含超出范围的离群点
    """
    clean = series.dropna()
    if len(clean) < 5:
        return False

    # 检查是否都是整数
    if not np.all(clean == clean.astype(int)):
        return False

    clean_int = clean.astype(int)
    min_val = int(clean_int.min())
    max_val = int(clean_int.max())
    unique_vals = sorted(clean_int.unique())
    spread = max_val - min_val + 1

    # 量表通常跨度小（≤ 12 个不同值）
    if len(unique_vals) > 15 or spread > 15:
        return False

    for low, high in SCALE_RANGES:
        if min_val >= low and max_val <= high:
            coverage = len(unique_vals) / spread
            if coverage >= 0.5:
                return True

    return False


def _is_integer_sequence(series: pd.Series) -> bool:
    """判断数值序列是否由连续整数构成（通常意味着编码/等级）。"""
    clean = series.dropna()
    if len(clean) == 0:
        return False
    if not np.all(clean == clean.astype(int)):
        return False
    unique_sorted = sorted(clean.astype(int).unique())
    if len(unique_sorted) <= 1:
        return False
    # 连续整数检查
    return unique_sorted == list(range(unique_sorted[0], unique_sorted[-1] + 1))


def _detect_binary_pattern(series: pd.Series) -> bool:
    """检测一个序列是否为二分类变量（binary）。

    规则：
      - 数值型：任何恰好有 2 个唯一值的数值列 → True
      - 文本型：必须匹配已知的二分类值对（是/否、男/女等）

    注意：数值型宽泛匹配是因为两个唯一值的数值列在实践中≈二分类；
    文本型保守匹配是为了避免将不相关的两值文本（如 red/green）误判。
    """
    clean = series.dropna()
    if len(clean) == 0:
        return False
    unique_vals = set(clean.unique())
    if len(unique_vals) != 2:
        return False

    # 数值型：任意两值 → binary
    if pd.api.types.is_numeric_dtype(clean):
        return True

    # 文本/对象型：检查已知二分类对
    str_vals = {str(v).strip() for v in unique_vals}
    if len(str_vals) != 2:
        return False

    binary_text_pairs = [
        {"是", "否"}, {"是", "不是"},
        {"y", "n"}, {"yes", "no"},
        {"男", "女"}, {"male", "female"},
        {"有", "无"}, {"true", "false"},
        {"满意", "不满意"}, {"通过", "未通过"},
        {"成功", "失败"}, {"赞成", "反对"},
        {"支持", "反对"}, {"同意", "不同意"},
        {"会", "不会"}, {"愿意", "不愿意"},
    ]
    for pair in binary_text_pairs:
        if str_vals == pair:
            return True
    return False


# ================================================================
# 隐私风险评估
# ================================================================

def _assess_privacy_risk(
    col_name: str,
    series: pd.Series,
    inferred_type: str,
) -> Dict[str, Any]:
    """评估单个变量的隐私风险等级和分类。

    优先级（从高到低）：
      1. 列名关键词匹配（demographic → low, direct_identifier → high, etc.）
      2. 列值模式匹配（phone/email/ID card → high）
      3. 文本类型兜底（text → medium free_text）
      4. 默认 → none

    Args:
        col_name: 列名
        series: 数据列
        inferred_type: 已推断的变量类型

    Returns:
        {
            "privacy_risk": str,        # none / low / medium / high
            "privacy_category": str,    # none / demographic_attribute / contact_info /
                                        #   direct_identifier / location_info / free_text /
                                        #   sensitive_attribute / financial / unknown
            "allow_local_stats": bool,
            "allow_as_group_variable": bool,
            "allow_in_model": bool,
            "allow_send_to_ai": bool,
            "send_to_ai_mode": str,     # exclude / aggregate_only / masked_examples / full
            "user_confirmed_privacy": bool,
        }
    """
    col_lower = col_name.lower()
    # 标准化：用于关键词匹配的版本（用分隔符分词）
    col_normalized = col_name.lower().replace("_", " ").replace("-", " ")

    risk = "none"
    category = "none"
    matched_keyword = ""

    # ── 辅助：关键词匹配（要求单词边界） ──
    def _kw_match(kw: str) -> bool:
        """检查关键词是否在列名中作为独立词出现。
        短关键词（≤3字符）要求严格单词边界。
        长关键词允许子串匹配。"""
        kw_lower = kw.lower()
        kw_normalized = kw.lower().replace("_", " ").replace("-", " ")
        if len(kw) <= 3:
            # 严格匹配：关键词必须是列名中的完整词
            words = col_normalized.split()
            return kw_normalized in words
        else:
            # 长关键词：子串匹配即可
            clean_col = col_lower.replace("_", "").replace("-", "").replace(" ", "")
            clean_kw = kw_lower.replace("_", "").replace("-", "").replace(" ", "")
            return clean_kw in clean_col

    # ── Step 1: 列名关键词匹配 ──
    # 收集所有匹配，选择最长关键词匹配（更具体的匹配优先）
    all_matches: List[Tuple[str, str, str, int]] = []  # (risk, category, keyword, kw_len)

    # 定义匹配顺序（任意顺序均可，最终按关键词长度选最优）
    all_categories = [
        ("financial_high", "high", "financial"),
        ("contact_info_high", "high", "contact_info"),
        ("direct_identifier_high", "high", "direct_identifier"),
        ("sensitive_attribute_medium", "medium", "sensitive_attribute"),
        ("location_info_medium", "medium", "location_info"),
        ("free_text_medium", "medium", "free_text"),
        ("demographic_attribute_low", "low", "demographic_attribute"),
    ]

    for map_key, cat_risk, cat_name in all_categories:
        for kw in PRIVACY_KEYWORD_MAP[map_key]:
            if _kw_match(kw):
                all_matches.append((cat_risk, cat_name, kw, len(kw)))

    if all_matches:
        # 选最长关键词匹配（更具体）；同长度时高风险优先
        risk_order = {"high": 3, "medium": 2, "low": 1, "none": 0}
        all_matches.sort(key=lambda x: (x[3], risk_order.get(x[0], 0)), reverse=True)
        risk = all_matches[0][0]
        category = all_matches[0][1]
        matched_keyword = all_matches[0][2]

    # ── Step 2: 值模式检测（提升风险等级） ──
    if risk in ("none", "low"):
        sample = series.dropna().head(50).astype(str)
        if len(sample) > 0:
            for pat, pat_risk, pat_cat in PRIVACY_VALUE_PATTERNS:
                match_count = sum(1 for val in sample if pat.match(val.strip()))
                if match_count / len(sample) >= 0.3:  # 30% 匹配即升级
                    if pat_risk == "high":
                        risk = "high"
                        category = pat_cat
                        break

    # ── Step 3: 文本类型兜底 ──
    if risk == "none" and inferred_type in ("text", "high_cardinality"):
        risk = "medium"
        category = "free_text"

    # ── Step 4: 应用默认策略 ──
    policy = DEFAULT_USAGE_POLICIES.get(risk, DEFAULT_USAGE_POLICIES["none"])

    return {
        "privacy_risk": risk,
        "privacy_category": category,
        "allow_local_stats": policy["allow_local_stats"],
        "allow_as_group_variable": policy["allow_as_group_variable"],
        "allow_in_model": policy["allow_in_model"],
        "allow_send_to_ai": policy["allow_send_to_ai"],
        "send_to_ai_mode": policy["send_to_ai_mode"],
        "user_confirmed_privacy": False,
    }


def _try_parse_datetime(series: pd.Series) -> bool:
    """尝试将序列解析为日期时间，成功比例高则返回 True。"""
    sample = series.dropna().head(20)
    if len(sample) == 0:
        return False
    try:
        parsed = pd.to_datetime(sample, errors="coerce")
        success_rate = parsed.notna().sum() / len(sample)
        return success_rate >= 0.8
    except Exception:
        return False


def _match_keywords(col_lower: str, keywords: List[str]) -> bool:
    """检查列名（小写）是否包含任何关键词。"""
    for kw in keywords:
        if kw.lower() in col_lower:
            return True
    return False


def _get_example_values(series: pd.Series, unique_vals: np.ndarray) -> str:
    """获取示例值字符串（最多 5 个，逗号分隔）。"""
    examples = unique_vals[:5]
    examples_str = ", ".join(
        str(v) for v in examples if not pd.isna(v)
    )
    if len(examples_str) > 80:
        examples_str = examples_str[:77] + "..."
    return examples_str


# ================================================================
# 类型归一化
# ================================================================

def _normalize_type(raw_type: str) -> str:
    """将变量表中的类型描述归一化为标准类型名。"""
    t = str(raw_type).strip().lower()
    type_map = {
        "数值": "numeric",
        "数值变量": "numeric",
        "连续": "numeric",
        "连续变量": "numeric",
        "numeric": "numeric",
        "continuous": "numeric",
        "分类": "categorical",
        "分类变量": "categorical",
        "定类": "categorical",
        "无序": "categorical",
        "categorical": "categorical",
        "nominal": "categorical",
        "有序": "ordinal",
        "定序": "ordinal",
        "有序分类": "ordinal",
        "等级": "ordinal",
        "ordinal": "ordinal",
        "日期": "datetime",
        "时间": "datetime",
        "datetime": "datetime",
        "date": "datetime",
        "量表": "ordinal",
        "量表变量": "ordinal",
        "likert": "ordinal",
        "likert 量表": "ordinal",
        "满意度评分": "ordinal",
        "评分": "ordinal",
        "文本": "text",
        "开放题": "text",
        "text": "text",
        "string": "text",
        "二分类": "binary",
        "二分": "binary",
        "二元": "binary",
        "binary": "binary",
        "boolean": "binary",
        "bool": "binary",
        "id": "id",
        "编号": "id",
        "identifier": "id",
    }
    for cn_key, en_type in type_map.items():
        if cn_key in t:
            return en_type
    # 无法识别则返回 original
    return raw_type


# ================================================================
# 角色建议
# ================================================================

def _suggest_role(
    col_name: str,
    inferred_type: str,
    unique_count: int,
    unique_ratio: float,
    n_rows: int,
    display_name: str = "",
) -> str:
    """根据变量类型和特征建议分析角色。"""
    col_lower = col_name.lower()

    if inferred_type == "id":
        return "id"
    if inferred_type == "datetime":
        return "skip"
    if inferred_type == "text":
        return "skip"
    if inferred_type == "high_cardinality":
        return "skip"

    # 检查名称是否为典型目标变量
    target_kw = ["overall", "总体", "总满意度", "target", "因变量", "y", "result"]
    if _match_keywords(col_lower, target_kw):
        return "target"

    # 检查名称是否为典型分组变量
    group_kw = ["district", "gender", "age_group", "education", "channel",
                "区域", "性别", "年龄", "学历", "渠道", "group", "分组"]
    if _match_keywords(col_lower, group_kw):
        return "group"

    # 数值 → 可作为解释变量，分类/二分类 → 可作为分组变量
    if inferred_type in ("numeric", "ordinal"):
        return "predictor"
    if inferred_type in ("categorical", "binary"):
        if unique_count <= 15:
            return "group"
        return "skip"

    return "predictor"


# ================================================================
# 分析方法建议
# ================================================================

def _suggest_analysis(inferred_type: str) -> str:
    """根据变量类型建议分析方法。"""
    suggestions = {
        "id": "无需分析",
        "numeric": "描述统计（均值/标准差/分位数）、直方图、箱线图",
        "categorical": "频数分析、柱状图、饼图；可作为分组变量进行交叉分析",
        "binary": "频数分析、二分类逻辑回归；可作为二分类目标变量或分组变量",
        "ordinal": "频数分析、均值/中位数、柱状图；可参与相关分析",
        "datetime": "时间趋势分析（如需要）",
        "text": "文本挖掘（当前版本暂不支持）",
        "high_cardinality": "不宜直接分组，建议降维或转为分类变量后分析",
    }
    return suggestions.get(inferred_type, "根据实际需求选择分析方法")


# ================================================================
# 变量表解析
# ================================================================

def _parse_variable_table(vt: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    """解析变量说明表为 {变量名: {中文含义, 类型, ...}} 的字典。

    自动检测列名（支持中英文）。当列名为乱码无法识别时，使用位置回退。

    回退规则（当表有 4-6 列且列名不匹配时）：
      列0 → 变量名，列1 → 中文含义，列2 → 类型
      并通过列2的值验证（必须含已知类型关键词）。
    """
    if vt is None or vt.empty:
        return {}

    # 寻找变量名列
    name_col = None
    for cand in ["变量名", "Variable", "variable", "变量", "字段名", "字段", "column"]:
        if cand in vt.columns:
            name_col = cand
            break

    # 寻找中文含义列
    cn_col = None
    for cand in ["中文含义", "含义", "说明", "描述", "Label", "label", "变量含义"]:
        if cand in vt.columns:
            cn_col = cand
            break

    # 寻找类型列
    type_col = None
    for cand in ["类型", "变量类型", "Type", "type", "数据类型"]:
        if cand in vt.columns:
            type_col = cand
            break

    # ---- 位置回退：当列名完全不匹配时 ----
    if name_col is None and len(vt.columns) >= 3:
        # 检查是否可使用位置回退：第3列值是否看起来像类型
        col2_vals = vt.iloc[:, 2].dropna().astype(str).str.strip().str.lower()
        valid_types = {"id", "numeric", "categorical", "ordinal", "datetime",
                       "text", "high_cardinality", "连续", "分类", "有序", "日期", "文本"}
        type_hits = col2_vals.isin(valid_types).sum()
        if type_hits >= max(len(col2_vals) * 0.5, 2):
            name_col = vt.columns[0]
            cn_col = vt.columns[1] if len(vt.columns) > 1 else None
            type_col = vt.columns[2] if len(vt.columns) > 2 else None
            # 不覆盖已找到的列

    if name_col is None:
        name_col = vt.columns[0]

    result = {}
    for _, row in vt.iterrows():
        var_name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
        if not var_name:
            continue
        result[var_name] = {
            "中文含义": str(row[cn_col]).strip() if cn_col and pd.notna(row.get(cn_col)) else "",
            "类型": str(row[type_col]).strip() if type_col and pd.notna(row.get(type_col)) else "",
        }

    return result


# ================================================================
# 变量用途检测（从变量说明表推断变量角色）
# ================================================================

# 变量用途关键词 → 建议角色映射
VARIABLE_USAGE_KEYWORDS: Dict[str, List[str]] = {
    "target": [
        "核心结果变量", "因变量", "结果变量", "目标变量",
        "总体评价", "满意度", "总体满意度", "总满意度",
        "target", "dependent", "outcome", "response",
        "overall", "总体", "综合", "整体评价",
    ],
    "group": [
        "分组变量", "分类变量", "组别变量", "分层变量",
        "group", "分组", "类别", "分类",
        "demographic", "人口学", "人口统计",
        "地区", "区域", "性别", "年龄组", "学历", "渠道",
    ],
    "predictor": [
        "自变量", "解释变量", "预测变量", "控制变量",
        "independent", "predictor", "explanatory", "covariate",
        "影响因素", "影响因子", "驱动因素",
    ],
    "improve": [
        "改进事项", "优先改进", "改进方向", "待改善",
        "priority", "improve", "improvement",
    ],
    "recommend": [
        "推荐意愿", "是否推荐", "推荐", "recommend",
        "净推荐值", "nps",
    ],
    "complaint": [
        "投诉意向", "投诉意愿", "投诉", "complaint",
    ],
    "id": [
        "编号", "序号", "ID", "标识", "唯一标识",
        "流水号", "问卷编号", "被访者编号",
    ],
    "text": [
        "开放题", "开放问题", "文本", "建议意见",
        "open", "text", "comment", "意见", "备注",
    ],
}


def detect_variable_usage(
    col_name: str,
    display_name: str = "",
    usage_text: str = "",
) -> Optional[str]:
    """从变量说明表的「变量用途」列中检测推荐的变量角色。

    Args:
        col_name: 变量名
        display_name: 中文含义
        usage_text: 变量用途文本（来自变量说明表）

    Returns:
        推荐的角色（"target"/"group"/"predictor"/None）
    """
    search_text = f"{usage_text} {display_name} {col_name}".lower()

    # 按优先级匹配：target > group > predictor > improve > recommend > complaint
    priority_order = ["target", "group", "predictor", "improve", "recommend", "complaint", "id", "text"]
    for role in priority_order:
        for kw in VARIABLE_USAGE_KEYWORDS.get(role, []):
            if kw.lower() in search_text:
                if role in ("improve", "recommend", "complaint"):
                    return "predictor"  # 这类变量通常作为解释变量
                if role == "text":
                    return "skip"
                return role

    return None


def build_variable_dict_map(
    variable_table: Optional[pd.DataFrame],
) -> Dict[str, Dict[str, Any]]:
    """将变量说明表 DataFrame 转换为便于查询的字典。

    自动检测列名（中英文兼容）。当列名不匹配时使用位置回退。

    Args:
        variable_table: 变量说明表 DataFrame

    Returns:
        {变量名: {"中文含义": str, "类型": str, "取值或说明": str, "变量用途": str, "labels": dict}}
    """
    if variable_table is None or variable_table.empty:
        return {}

    from src.utils import parse_value_description

    vt = variable_table
    cols = list(vt.columns)

    # ── 列名检测 ──
    name_col = None
    cn_col = None
    type_col = None
    value_col = None
    usage_col = None

    for cand in ["变量名", "Variable", "variable", "变量", "字段名", "字段", "column"]:
        if cand in cols:
            name_col = cand
            break

    for cand in ["中文含义", "中文名称", "含义", "变量含义", "变量说明", "display_name", "label"]:
        if cand in cols:
            cn_col = cand
            break

    for cand in ["类型", "变量类型", "type", "var_type"]:
        if cand in cols:
            type_col = cand
            break

    for cand in ["取值或说明", "取值说明", "值说明", "编码说明", "value_desc", "values"]:
        if cand in cols:
            value_col = cand
            break

    for cand in ["变量用途", "用途", "分析用途", "角色", "usage", "role"]:
        if cand in cols:
            usage_col = cand
            break

    # ── 位置回退 ──
    if name_col is None and len(cols) >= 1:
        name_col = cols[0]
    if cn_col is None and len(cols) >= 2:
        cn_col = cols[1]
    if type_col is None and len(cols) >= 3:
        type_col = cols[2]
    if value_col is None and len(cols) >= 4:
        value_col = cols[3]
    if usage_col is None and len(cols) >= 5:
        usage_col = cols[4]

    # ── 构建字典 ──
    result: Dict[str, Dict[str, Any]] = {}
    for _, row in vt.iterrows():
        var_name = str(row[name_col]).strip() if name_col and pd.notna(row.get(name_col)) else ""
        if not var_name:
            continue

        entry: Dict[str, Any] = {
            "中文含义": str(row[cn_col]).strip() if cn_col and pd.notna(row.get(cn_col)) else "",
            "类型": str(row[type_col]).strip() if type_col and pd.notna(row.get(type_col)) else "",
            "取值或说明": str(row[value_col]).strip() if value_col and pd.notna(row.get(value_col)) else "",
            "变量用途": str(row[usage_col]).strip() if usage_col and pd.notna(row.get(usage_col)) else "",
            "labels": {},
        }

        # 解析取值说明获取标签映射
        value_text = entry["取值或说明"]
        if value_text:
            entry["labels"] = parse_value_description(value_text)

        # 检测变量用途
        entry["detected_usage"] = detect_variable_usage(
            var_name,
            entry["中文含义"],
            entry["变量用途"],
        )

        result[var_name] = entry

    return result

