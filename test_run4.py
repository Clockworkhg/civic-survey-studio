"""第四轮测试：CSV 文件 + 二分类变量检测。"""
import sys, os, io
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import pandas as pd
import numpy as np

TEST_FILE = os.path.join(os.path.dirname(__file__), "tests", "test_data", "04_电商用户转化行为_无变量说明.csv")

# 配置 A：购买金额
CONFIG_A = {
    "report_title": "电商用户购买金额分析报告",
    "target_variable": "purchase_amount",
    "group_variables": ["region", "device", "membership_level", "coupon_used"],
    "explanatory_variables": ["age", "page_views", "session_minutes", "service_rating", "price_sensitivity"],
}

# 配置 B：是否转化
CONFIG_B = {
    "report_title": "电商用户转化行为分析报告",
    "target_variable": "converted",
    "group_variables": ["region", "device", "membership_level", "coupon_used"],
    "explanatory_variables": ["age", "page_views", "session_minutes", "service_rating", "price_sensitivity"],
}

passed = 0
failed = 0
errors = []

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        msg = f"  ❌ {name}  — {detail}"
        print(msg)
        errors.append(msg)

# ================================================================
print("=" * 60)
print("1. CSV 文件加载")
print("=" * 60)

# 1a. CSV 编码自动检测
from src.data_loader import load_generic_data, get_data_quality_report
raw_df = load_generic_data(TEST_FILE)
check("CSV 读取成功", raw_df is not None and raw_df.shape == (250, 13),
      f"shape={raw_df.shape if raw_df is not None else 'None'}")

# 验证关键列
for col in ["user_id", "register_date", "converted", "purchase_amount"] + CONFIG_A["group_variables"] + CONFIG_A["explanatory_variables"]:
    check(f"  列「{col}」存在", col in raw_df.columns)

# 1b. 没有变量说明表
check("无变量说明表", True, "故意不上传 — CSV 无附带变量表")

print(f"\n数据预览（前3行）:")
print(raw_df.head(3).to_string())

# ================================================================
print("\n" + "=" * 60)
print("2. 数据类型分布")
print("=" * 60)

print(f"数据类型分布:")
for dtype in raw_df.dtypes.value_counts().items():
    print(f"  {dtype[0]}: {dtype[1]} 列")

check("含 object 列（user_id/register_date/region/device/membership）",
      raw_df.select_dtypes('object').shape[1] >= 5)

# ================================================================
print("\n" + "=" * 60)
print("3. 变量类型自动推断")
print("=" * 60)

from src.schema_infer import infer_variable_schema
schema_df = infer_variable_schema(raw_df, variable_table=None)
check("schema 生成 13 列", len(schema_df) == 13, f"got {len(schema_df)}")

# 重点验证
type_expectations = {
    "user_id": "id",
    "register_date": "datetime",
    "region": "categorical",
    "device": "categorical",
    "membership_level": "categorical",
    "age": "numeric",
    "page_views": "numeric",
    "session_minutes": "numeric",
    "coupon_used": "binary",
    "service_rating": "ordinal",
    "price_sensitivity": "ordinal",
    "purchase_amount": "numeric",
    "converted": "binary",
}

for col, expected in type_expectations.items():
    row = schema_df[schema_df["column"] == col]
    if len(row) > 0:
        actual = row.iloc[0]["inferred_type"]
        ok = actual == expected
        if not ok:
            if expected == "datetime" and actual in ("numeric", "datetime", "categorical"):
                ok = True
            if expected == "numeric" and actual in ("numeric", "ordinal"):
                ok = True
            if expected == "ordinal" and actual in ("ordinal", "numeric"):
                ok = True
            if expected == "categorical" and actual in ("categorical", "ordinal", "numeric"):
                ok = True
        check(f"「{col}」→ {actual}（期望 {expected}）", ok, f"actual={actual}")

for col in ["converted", "coupon_used"]:
    row = schema_df[schema_df["column"] == col]
    actual = row.iloc[0]["inferred_type"]
    check(f"⭐ 「{col}」推断为 binary（非 ordinal）", actual == "binary",
          f"actual={actual} (0/1 应是二分类，非有序)")

print(f"\n推断结果:")
print(schema_df[["column", "inferred_type", "missing_count", "unique_count", "suggested_role"]].to_string())

# ================================================================
print("\n" + "=" * 60)
print("4. 重点：user_id 被识别为 ID")
print("=" * 60)

uid = schema_df[schema_df["column"] == "user_id"]
check("user_id 类型=id", uid.iloc[0]["inferred_type"] == "id")
check("user_id 角色=id", uid.iloc[0]["suggested_role"] == "id")

# ================================================================
print("\n" + "=" * 60)
print("5. 重点：register_date 被识别为日期")
print("=" * 60)

rd = schema_df[schema_df["column"] == "register_date"]
check("register_date 类型=datetime", rd.iloc[0]["inferred_type"] == "datetime",
      f"actual={rd.iloc[0]['inferred_type']}")
check("register_date 角色=skip", rd.iloc[0]["suggested_role"] == "skip")

# ================================================================
print("\n" + "=" * 60)
print("6. 数据质量报告")
print("=" * 60)

quality = get_data_quality_report(raw_df)
check("样本量=250", quality["样本量"] == 250)
check("变量数=13", quality["变量数"] == 13)
check("缺失值=0（CSV 完整）", quality["缺失值总数"] == 0,
      f"missing={quality['缺失值总数']}")
print(f"  质量: {quality}")

# ================================================================
print("\n" + "=" * 60)
print("7. 单变量分析")
print("=" * 60)

from src.generic_analysis import univariate_numeric, univariate_categorical, univariate_ordinal

result = univariate_numeric(raw_df, "purchase_amount", "purchase_amount")
check("数值-purchase_amount", "error" not in result, result.get("error"))
if "error" not in result:
    check("  中位数=0（>50%未转化）", result["中位数"] == 0, f"median={result['中位数']}")
    print(f"  purchase_amount: mean={result['均值']:.1f}, median={result['中位数']}, n={result['样本量']}")

result = univariate_categorical(raw_df, "converted", "converted")
check("分类-converted", "error" not in result, result.get("error"))
if "error" not in result:
    check("  类别数=2", result["类别数"] == 2, f"n={result['类别数']}")
    print(f"  converted: 0={result.get('频数表', {}).get(0, '?')}, 1={result.get('频数表', {}).get(1, '?')}")

result = univariate_categorical(raw_df, "coupon_used", "coupon_used")
check("分类-coupon_used(0/1)", "error" not in result, result.get("error"))
if "error" not in result:
    check("  类别数=2", result["类别数"] == 2, f"n={result['类别数']}")

# ================================================================
print("\n" + "=" * 60)
print("8. 双变量分析：分类 × 转化")
print("=" * 60)

from src.generic_analysis import bivariate_cat_cat, bivariate_cat_num, bivariate_num_num

result = bivariate_cat_cat(raw_df, "coupon_used", "converted",
                           "coupon_used", "converted")
check("cat×cat: coupon_used×converted", "error" not in result, result.get("error"))
if "error" not in result:
    check("  有卡方值", result.get("chi2") is not None)
    check("  有p值", result.get("p_value") is not None)
    print(f"  χ²={result.get('chi2'):.2f}, p={result.get('p_value'):.4f}, sig={result.get('significant')}")

result = bivariate_cat_num(raw_df, "region", "purchase_amount",
                           "region", "purchase_amount")
check("cat×num: region×purchase_amount", "error" not in result, result.get("error"))
if "error" not in result:
    print(f"  ANOVA p={result.get('p_value'):.4f}")

# ================================================================
print("\n" + "=" * 60)
print("9. 配置 A：purchase_amount 为目标的回归分析")
print("=" * 60)

from src.generic_analysis import run_full_analysis, multivariate_regression

config_a = {**CONFIG_A, "report_title": CONFIG_A["report_title"]}
full_a = run_full_analysis(raw_df, schema_df, config_a)
check("全流程 A 成功", isinstance(full_a, dict))

mv_a = full_a.get("multivariate")
check("配置 A 有回归结果", mv_a is not None and "error" not in mv_a,
      f"result={'present' if mv_a else 'None'}")
if mv_a and "error" not in mv_a:
    check("  R² > 0", mv_a.get("r_squared", 0) > 0)
    print(f"  R²={mv_a.get('r_squared'):.4f}, adjR²={mv_a.get('adj_r_squared'):.4f}, n={mv_a.get('n')}")
    coef_df = mv_a.get("coefficients")
    if coef_df is not None:
        sig = coef_df[coef_df["显著性"].str.contains(r"\*", na=False)]
        for _, row in sig.iterrows():
            p_col = [c for c in coef_df.columns if 'p' in str(c).lower()][0]
            print(f"    {row['变量']}: coef={row['回归系数']:.4f} (p={row[p_col]:.4f})")

# ================================================================
print("\n" + "=" * 60)
print("10. 配置 B：converted 为目标的处理")
print("=" * 60)

config_b = {**CONFIG_B, "report_title": CONFIG_B["report_title"]}
full_b = run_full_analysis(raw_df, schema_df, config_b)
check("全流程 B 成功", isinstance(full_b, dict))

mv_b = full_b.get("multivariate")
has_logistic = isinstance(mv_b, dict) and "pseudo_r_squared" in mv_b
check("  配置 B 应产生逻辑回归结果",
      has_logistic,
      f"multivariate={type(mv_b).__name__}: {str(mv_b)[:120]}")
if has_logistic:
    print(f"  Logistic pseudo R² = {mv_b.get('pseudo_r_squared', 0)}")
warnings_b = full_b.get("warnings", [])

bivariate_count = len(full_b.get("bivariate_group", {}))
check("配置 B 有双变量分组分析", bivariate_count > 0, f"count={bivariate_count}")
print(f"  双变量分组分析: {bivariate_count} 组")

# ================================================================
print("\n" + "=" * 60)
print("11. 图表生成")
print("=" * 60)

from src.generic_charts import (
    auto_univariate_chart, auto_bivariate_chart,
    correlation_heatmap_chart, generate_dashboard_charts,
)

fig = auto_univariate_chart(raw_df, "purchase_amount", "numeric", "purchase_amount")
check("单变量图-purchase_amount", fig is not None)

fig = auto_univariate_chart(raw_df, "converted", "categorical", "converted")
check("单变量图-converted(柱状图)", fig is not None)

fig = auto_bivariate_chart(raw_df, "coupon_used", "converted",
                           "categorical", "categorical", "coupon_used", "converted")
check("双变量图-coupon×converted(堆叠柱状)", fig is not None)

dashboard_a = generate_dashboard_charts(raw_df, schema_df, config_a)
valid_a = [(k, t, f) for k, t, f in dashboard_a if f is not None]
check(f"仪表盘 A ≥ 5 张", len(valid_a) >= 5, f"valid={len(valid_a)}")

dashboard_b = generate_dashboard_charts(raw_df, schema_df, config_b)
valid_b = [(k, t, f) for k, t, f in dashboard_b if f is not None]
check(f"仪表盘 B ≥ 5 张", len(valid_b) >= 5, f"valid={len(valid_b)}")

# ================================================================
print("\n" + "=" * 60)
print("12. 报告生成（配置 A：购买金额）")
print("=" * 60)

from src.report_generator import generate_generic_html_report, generate_generic_docx_report

try:
    html_a = generate_generic_html_report(raw_df, schema_df, config_a)
    check("HTML A 生成成功", len(html_a) > 5000)
    check("  包含标题", CONFIG_A["report_title"] in html_a)
    check("  包含 purchase_amount", "purchase_amount" in html_a)
    with open("test_output4a.html", "w", encoding="utf-8") as f:
        f.write(html_a)
    print(f"  HTML A: {len(html_a):,} 字符")
except Exception as e:
    check("HTML A 生成", False, str(e))

try:
    docx_a = generate_generic_docx_report(raw_df, schema_df, config_a)
    check("DOCX A 生成成功", len(docx_a) > 5000)
    with open("test_output4a.docx", "wb") as f:
        f.write(docx_a)
    print(f"  DOCX A: {len(docx_a):,} 字节")
except Exception as e:
    check("DOCX A 生成", False, str(e))

# ================================================================
print("\n" + "=" * 60)
print("13. 报告生成（配置 B：是否转化）")
print("=" * 60)

try:
    html_b = generate_generic_html_report(raw_df, schema_df, config_b)
    check("HTML B 生成成功", len(html_b) > 5000)
    check("  包含标题", CONFIG_B["report_title"] in html_b)
    check("  包含 converted", "converted" in html_b)
    check("  提到二分类/逻辑回归",
          "二分类" in html_b or "逻辑回归" in html_b or "分类变量" in html_b)
    with open("test_output4b.html", "w", encoding="utf-8") as f:
        f.write(html_b)
    print(f"  HTML B: {len(html_b):,} 字符")
except Exception as e:
    check("HTML B 生成", False, str(e))

try:
    docx_b = generate_generic_docx_report(raw_df, schema_df, config_b)
    check("DOCX B 生成成功", len(docx_b) > 5000)
    with open("test_output4b.docx", "wb") as f:
        f.write(docx_b)
    print(f"  DOCX B: {len(docx_b):,} 字节")
except Exception as e:
    check("DOCX B 生成", False, str(e))

# ================================================================
print("\n" + "=" * 60)
print("14. ID/日期变量排除验证")
print("=" * 60)

univariate_vars_a = list(full_a.get("univariate", {}).keys())
uid_result = full_a["univariate"].get("user_id", {})
check("user_id 被标记为跳过", "跳过" in uid_result.get("info", ""),
      f"info={uid_result.get('info', 'N/A')}")

rd_result = full_a["univariate"].get("register_date", {})
check("register_date 被标记为跳过", "跳过" in rd_result.get("info", ""),
      f"info={rd_result.get('info', 'N/A')}")

if full_a.get("multivariate") and "error" not in full_a["multivariate"]:
    preds = full_a["multivariate"].get("predictors", [])
    check("user_id 不在回归中", "user_id" not in preds)
    check("register_date 不在回归中", "register_date" not in preds)

print(f"  配置 A 单变量: {len(full_a.get('univariate', {}))} 个")
print(f"  配置 A 双变量(分组): {len(full_a.get('bivariate_group', {}))} 个")
print(f"  配置 A 双变量(相关): {len(full_a.get('bivariate_corr', {}))} 个")

# ================================================================
print("\n" + "=" * 60)
print("15. 配置对比总结")
print("=" * 60)

print(f"  配置 A (purchase_amount):")
print(f"    目标类型: numeric")
print(f"    回归: {'✅ OLS' if full_a.get('multivariate') else '❌ 无'}")
print(f"    R²: {full_a.get('multivariate', {}).get('r_squared', 'N/A')}")

print(f"  配置 B (converted):")
print(f"    目标类型: categorical (binary)")
print(f"    回归: {'❌ 已跳过（不适合 OLS）' if mv_b is None else '⚠️ 异常'}")
warn_text = " | ".join(str(w) for w in warnings_b) if warnings_b else "无"
print(f"    警告: {warn_text[:200]}")

# ================================================================
print("\n" + "=" * 60)
print(f"测试结果: {passed} 通过, {failed} 失败")
print("=" * 60)

if failed > 0:
    print("\n失败详情:")
    for e in errors:
        print(f"  {e}")

sys.exit(0 if failed == 0 else 1)
