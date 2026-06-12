"""
===============================================================================
  全数据集自动化测试脚本 v2
  对文件夹内所有 6 个数据文件逐一执行：
    数据加载 → 变量推断 → 质量检查 → 统计分析 → AI 分析方案 → AI 生成报告
  输出至 test_results/ 目录，并生成综合测试报告。
===============================================================================
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

# ================================================================
# 日志系统 —— 同时输出到文件和 stdout
# ================================================================
PROJECT_ROOT = Path(__file__).resolve().parent
LOG_PATH = PROJECT_ROOT / "test_results" / f"test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

def _log(msg: str) -> None:
    """写日志（文件 + stdout，立刻刷新）。"""
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
    except Exception:
        pass

# 重定向未捕获异常
def _log_excepthook(exc_type, exc_val, exc_tb):
    tb_lines = traceback.format_exception(exc_type, exc_val, exc_tb)
    for line in tb_lines.split('\n'):
        if line.strip():
            _log(f"FATAL: {line}")
sys.excepthook = _log_excepthook

# ================================================================
# 配置
# ================================================================
TEST_RESULTS_DIR = PROJECT_ROOT / "test_results"
NOW_STR = datetime.now().strftime("%Y%m%d_%H%M%S")
GENERIC_DATA_DIR = PROJECT_ROOT / "tests" / "test_data"

_log(f"=== 全数据集自动化测试开始 ===")
_log(f"输出目录: {TEST_RESULTS_DIR}")

DATASETS = [
    {
        "id": "ds01_gov_satisfaction",
        "name": "政务服务满意度调查（预设方案）",
        "data_path": str(PROJECT_ROOT / "政务服务中心公众满意度调查数据(1).xlsx"),
        "var_table_path": str(PROJECT_ROOT / "变量赋值表(1).xlsx"),
        "data_sheet": "SPSS_Data",
        "var_table_sheet": "public_service_variable_diction",
        "file_type": "xlsx",
        "use_preset": True,
        "preset_key": "gov_satisfaction",
    },
    {
        "id": "ds02_course_eval",
        "name": "课程教学评价数据（含变量说明）",
        "data_path": str(GENERIC_DATA_DIR / "01_课程教学评价数据_含变量说明.xlsx"),
        "var_table_path": None,
        "data_sheet": None,
        "file_type": "xlsx",
        "use_preset": False,
        "preset_key": None,
    },
    {
        "id": "ds03_museum",
        "name": "博物馆观众体验调查（无变量说明）",
        "data_path": str(GENERIC_DATA_DIR / "02_博物馆观众体验调查_无变量说明.xlsx"),
        "var_table_path": None,
        "data_sheet": None,
        "file_type": "xlsx",
        "use_preset": False,
        "preset_key": None,
    },
    {
        "id": "ds04_employee",
        "name": "员工满意度调查（含缺失和英文变量）",
        "data_path": str(GENERIC_DATA_DIR / "03_员工满意度调查_含缺失和英文变量.xlsx"),
        "var_table_path": None,
        "data_sheet": None,
        "file_type": "xlsx",
        "use_preset": False,
        "preset_key": None,
    },
    {
        "id": "ds05_ecommerce",
        "name": "电商用户转化行为（无变量说明CSV）",
        "data_path": str(GENERIC_DATA_DIR / "04_电商用户转化行为_无变量说明.csv"),
        "var_table_path": None,
        "data_sheet": None,
        "file_type": "csv",
        "use_preset": False,
        "preset_key": None,
    },
    {
        "id": "ds06_gov_generic",
        "name": "政务服务数据（纯通用模式，无预设）",
        "data_path": str(PROJECT_ROOT / "政务服务中心公众满意度调查数据(1).xlsx"),
        "var_table_path": str(PROJECT_ROOT / "变量赋值表(1).xlsx"),
        "data_sheet": "SPSS_Data",
        "var_table_sheet": "public_service_variable_diction",
        "file_type": "xlsx",
        "use_preset": False,
        "preset_key": None,
    },
]

# ================================================================
# 数据加载（本地实现，不依赖 streamlit）
# ================================================================

def _parse_value_description(text: str) -> Dict[int, str]:
    """解析取值说明文本为编码→标签映射。从 src/utils.py 复制。"""
    if not text or not isinstance(text, str):
        return {}
    labels = {}
    # 以逗号或中文逗号分隔
    parts = [p.strip() for p in text.replace("，", ",").split(",") if p.strip()]
    for part in parts:
        part = part.strip(";；")
        if "=" in part:
            k, v = part.split("=", 1)
        elif " " in part and any(ch.isdigit() for ch in part[:2]):
            # "1 男" 格式
            idx = next(i for i, ch in enumerate(part) if ch in (" ", "\t"))
            k, v = part[:idx], part[idx:]
        else:
            continue
        try:
            labels[int(k.strip())] = v.strip()
        except ValueError:
            pass
    return labels


def build_var_dict(vt_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """从变量说明表构建变量字典。"""
    if vt_df is None or vt_df.empty:
        return {}
    # 查找列名
    cols = [c.lower() for c in vt_df.columns]
    name_col = None
    cn_col = None
    type_col = None
    desc_col = None
    usage_col = None
    for i, c in enumerate(vt_df.columns):
        cl = c.lower()
        if name_col is None and any(k in cl for k in ["变量名", "variable", "var"]):
            name_col = c
        if cn_col is None and any(k in cl for k in ["中文含义", "中文", "含义", "display", "label"]):
            cn_col = c
        if type_col is None and any(k in cl for k in ["类型", "type"]):
            type_col = c
        if desc_col is None and any(k in cl for k in ["取值", "说明", "value", "code"]):
            desc_col = c
        if usage_col is None and any(k in cl for k in ["用途", "usage", "role"]):
            usage_col = c
    if name_col is None:
        return {}

    var_dict = {}
    for _, row in vt_df.iterrows():
        vn = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
        if not vn or vn == "nan":
            continue
        if vn in var_dict:
            continue
        cn = str(row[cn_col]).strip() if cn_col and pd.notna(row.get(cn_col)) else ""
        vt = str(row[type_col]).strip() if type_col and pd.notna(row.get(type_col)) else ""
        vd = str(row[desc_col]).strip() if desc_col and pd.notna(row.get(desc_col)) else ""
        vu = str(row[usage_col]).strip() if usage_col and pd.notna(row.get(usage_col)) else ""
        labels = _parse_value_description(vd) if vd else {}

        # 尝试从变量用途/类型检测角色
        detected_usage = ""
        full_text = f"{vt} {vu} {vd}".lower()
        if any(k in full_text for k in ["目标", "结果", "因变量", "target", "outcome", "dependent", "满意", "score", "rating"]):
            detected_usage = "target"
        elif any(k in full_text for k in ["分组", "group", "分类变量", "demographic", "性别", "年龄"]):
            detected_usage = "group"
        elif any(k in full_text for k in ["解释", "预测", "自变量", "predictor", "independent", "因素", "影响"]):
            detected_usage = "predictor"

        var_dict[vn] = {
            "变量名": vn, "中文含义": cn, "类型": vt,
            "取值或说明": vd, "变量用途": vu,
            "labels": labels, "detected_usage": detected_usage,
        }
    return var_dict


def get_quality_report(df: pd.DataFrame) -> dict:
    """数据质量报告。"""
    total_cells = df.size
    missing_total = int(df.isnull().sum().sum())
    duplicate_rows = int(df.duplicated().sum())
    mem_bytes = df.memory_usage(deep=True).sum()
    if mem_bytes < 1024:
        mem_str = f"{mem_bytes} B"
    elif mem_bytes < 1024 * 1024:
        mem_str = f"{mem_bytes / 1024:.1f} KB"
    else:
        mem_str = f"{mem_bytes / (1024 * 1024):.1f} MB"
    return {
        "样本量": len(df), "变量数": len(df.columns),
        "缺失值总数": missing_total,
        "缺失率": round(missing_total / total_cells * 100, 2) if total_cells > 0 else 0.0,
        "重复行数": duplicate_rows,
        "重复率": round(duplicate_rows / len(df) * 100, 2) if len(df) > 0 else 0.0,
        "内存占用": mem_str,
    }


def load_data(ds: dict) -> Tuple[Optional[pd.DataFrame], Optional[dict], str]:
    """加载单个数据集。"""
    path = ds["data_path"]
    if not os.path.exists(path):
        return None, None, f"文件不存在: {path}"

    try:
        if ds["file_type"] == "csv":
            df = None
            for enc in ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin-1"]:
                try:
                    df = pd.read_csv(path, encoding=enc)
                    if df is not None and not df.empty:
                        break
                except Exception:
                    continue
            if df is None or df.empty:
                return None, None, "CSV 读取后为空"
        else:
            sheet = ds.get("data_sheet")
            if sheet:
                df = pd.read_excel(path, sheet_name=sheet)
            else:
                xl = pd.ExcelFile(path)
                sheet = xl.sheet_names[0]
                df = pd.read_excel(path, sheet_name=sheet)
        if df is None or df.empty:
            return None, None, "数据为空"

        # 变量说明表
        var_dict = {}
        vtp = ds.get("var_table_path")
        if vtp and os.path.exists(vtp):
            try:
                vt_sheet = ds.get("var_table_sheet")
                vt = pd.read_excel(vtp, sheet_name=vt_sheet) if vt_sheet else pd.read_excel(vtp)
                var_dict = build_var_dict(vt)
            except Exception as e:
                _log(f"  [WARN] 变量说明表加载失败: {e}")

        # 自动检测内嵌变量说明表
        if not var_dict and ds["file_type"] == "xlsx":
            try:
                xl = pd.ExcelFile(path)
                for sn in xl.sheet_names:
                    sl = sn.lower()
                    if any(kw in sl for kw in ["variable", "diction", "说明", "字典", "赋值", "codebook"]):
                        vt = pd.read_excel(path, sheet_name=sn)
                        if vt is not None and not vt.empty:
                            embedded = build_var_dict(vt)
                            if embedded:
                                var_dict = embedded
                                _log(f"  [INFO] 检测到内嵌变量说明表 '{sn}': {len(var_dict)} 变量")
                                break
            except Exception:
                pass

        return df, var_dict, ""
    except Exception as e:
        return None, None, f"加载异常: {e}"


# ================================================================
# 延迟导入（避免 Streamlit 模块在日志配置前触发）
# ================================================================

_schema_infer = None
_generic_analysis = None
_analysis_context = None
_preset_profiles = None
_provider_config = None
_table_understanding_packager = None
_ai_table_planner = None
_analysis_packager = None
_ai_report_generator = None
_user_settings = None

def _import_modules():
    global _schema_infer, _generic_analysis, _get_analysis_summary, _analysis_context, _preset_profiles
    global _provider_config, _table_understanding_packager, _ai_table_planner
    global _analysis_packager, _to_json_payload, _ai_report_generator, _user_settings
    if _schema_infer is not None:
        return
    _log("加载 Python 模块...")
    from src.schema_infer import infer_variable_schema
    from src.generic_analysis import run_full_analysis, get_analysis_summary
    from src.analysis_context import AnalysisContext
    from src.preset_profiles import get_profile
    from src.provider_config import get_provider
    from src.table_understanding_packager import build_table_understanding_payload
    from src.ai_table_planner import generate_analysis_blueprint
    from src.analysis_packager import build_analysis_payload, to_json_payload
    from src.ai_report_generator import generate_ai_report
    from src.user_settings import load_user_settings
    _schema_infer = infer_variable_schema
    _generic_analysis = run_full_analysis
    _get_analysis_summary = get_analysis_summary
    _analysis_context = AnalysisContext
    _preset_profiles = get_profile
    _provider_config = get_provider
    _table_understanding_packager = build_table_understanding_payload
    _ai_table_planner = generate_analysis_blueprint
    _analysis_packager = build_analysis_payload
    _to_json_payload = to_json_payload
    _ai_report_generator = generate_ai_report
    _user_settings = load_user_settings
    _log("模块加载完成。")


# ================================================================
# 自动配置
# ================================================================

def _auto_suggest_config(ctx) -> None:
    cfg = ctx.user_analysis_config
    vdict = ctx.variable_dict_map
    if not vdict:
        return
    st, sg, se = [], [], []
    for col in ctx.columns:
        e = vdict.get(col, {})
        du = e.get("detected_usage", "")
        if not du:
            usage = e.get("变量用途", "")
            if any(k in usage for k in ["目标", "结果", "因变量"]):
                du = "target"
            elif any(k in usage for k in ["分组", "group", "分类变量", "demographic"]):
                du = "group"
            elif any(k in usage for k in ["解释", "预测", "自变量", "predictor"]):
                du = "predictor"
        if du == "target": st.append(col)
        elif du == "group": sg.append(col)
        elif du == "predictor": se.append(col)
    if st and not cfg.get("target_variable"):
        cfg["target_variable"] = st[0]
    if sg and not cfg.get("group_variables"):
        valid = [v for v in sg if v in ctx.columns and ctx.get_type(v) in ("categorical", "ordinal")]
        if valid: cfg["group_variables"] = valid[:5]
    if se and not cfg.get("explanatory_variables"):
        valid = [v for v in se if v in ctx.columns and ctx.get_type(v) in ("numeric", "ordinal")]
        if valid: cfg["explanatory_variables"] = valid[:10]


def _auto_pick_target(ctx) -> None:
    cfg = ctx.user_analysis_config
    if cfg.get("target_variable"): return
    for col in ctx.columns:
        cn = ctx.get_display_name(col).lower()
        if any(k in cn for k in ["satisfaction", "满意", "score", "评分", "rating", "评价", "总分", "total", "overall"]):
            if ctx.get_type(col) in ("numeric", "ordinal"):
                cfg["target_variable"] = col; return
    for col in ctx.columns:
        if ctx.get_type(col) == "numeric":
            cfg["target_variable"] = col; return


def _auto_pick_groups(ctx) -> None:
    cfg = ctx.user_analysis_config
    if cfg.get("group_variables"): return
    groups = []
    target = cfg.get("target_variable", "")
    for col in ctx.columns:
        if col == target: continue
        if ctx.get_type(col) in ("categorical", "ordinal"):
            if ctx.df is not None and ctx.df[col].nunique() <= 15:
                groups.append(col)
            if len(groups) >= 5: break
    if groups: cfg["group_variables"] = groups


def _auto_pick_explanatory(ctx) -> None:
    cfg = ctx.user_analysis_config
    if cfg.get("explanatory_variables"): return
    expls = []
    target = cfg.get("target_variable", "")
    for col in ctx.columns:
        if col == target: continue
        if ctx.get_type(col) in ("numeric", "ordinal"):
            expls.append(col)
        if len(expls) >= 10: break
    if expls: cfg["explanatory_variables"] = expls


# ================================================================
# AI 调用
# ================================================================

def call_ai_blueprint(df, schema_df, quality, var_dict, ctx, provider_config, api_key, model):
    result = {"success": False, "blueprint": None, "error": ""}
    try:
        tu_payload = _table_understanding_packager(
            df=df, schema_df=schema_df, quality=quality,
            variable_dict_map=var_dict,
            user_goal="请全面分析此数据集",
            preset_profile=ctx.preset_profile,
            dataset_name=ctx.dataset_name,
        )
        bp_result = _ai_table_planner(
            table_understanding_payload=tu_payload,
            provider_config=provider_config, api_key=api_key, model=model,
            provider_key="deepseek", temperature=0.3, max_tokens=8192,
        )
        if bp_result.get("success") and bp_result.get("blueprint"):
            result["success"] = True
            result["blueprint"] = bp_result["blueprint"]
        else:
            result["error"] = bp_result.get("error", "未返回 blueprint")
    except Exception as e:
        result["error"] = str(e)
        traceback.print_exc()
    return result


def call_ai_report(df, schema_df, config, analysis_results, quality, provider_config, api_key, model):
    result = {"success": False, "markdown": "", "html": "", "docx": b"", "error": ""}
    try:
        ai_result = _ai_report_generator(
            df=df, schema_df=schema_df, config=config,
            analysis_results=analysis_results, quality=quality,
            provider_config=provider_config, api_key=api_key, model=model,
            provider_key="deepseek", temperature=0.3, max_tokens=8192,
            report_structure=config.get("report_structure", "通用调研报告"),
            report_style=config.get("report_style", "学术报告风"),
            report_length="标准版", html_theme="政务蓝白汇报风",
        )
        if ai_result.get("success"):
            result["success"] = True
            result["markdown"] = ai_result.get("markdown_report", "")
            result["html"] = ai_result.get("html_report", "")
            result["docx"] = ai_result.get("docx_report", b"")
        else:
            result["error"] = ai_result.get("error", "AI 报告生成失败")
    except Exception as e:
        result["error"] = str(e)
        traceback.print_exc()
    return result


# ================================================================
# 处理单个数据集
# ================================================================

def process_dataset(ds: dict, provider_config: dict, api_key: str, model: str) -> dict:
    out = {
        "dataset_id": ds["id"], "dataset_name": ds["name"],
        "start_time": datetime.now(timezone.utc).isoformat(),
        "steps": {}, "errors": [], "warnings": [],
    }
    _log(f"--- [{ds['id']}] {ds['name']} ---")

    # Step 1: 加载
    _log("  [1/8] Loading data...")
    df, var_dict, err = load_data(ds)
    if err or df is None:
        out["errors"].append(f"数据加载失败: {err}")
        _log(f"  FAIL: {err}")
        return out
    out["steps"]["load"] = f"OK - {df.shape[0]} rows x {df.shape[1]} cols"
    _log(f"  OK: {df.shape[0]}x{df.shape[1]}, var_dict={len(var_dict)}")

    # Step 2: Schema
    _log("  [2/8] Schema inference...")
    try:
        schema_df = _schema_infer(df, variable_dict_map=var_dict)
        tc = schema_df["inferred_type"].value_counts().to_dict()
        out["steps"]["schema"] = f"OK - {len(schema_df)} vars"
        out["steps"]["type_distribution"] = {str(k): int(v) for k, v in tc.items()}
        _log(f"  OK: types={dict(tc)}")
    except Exception as e:
        out["errors"].append(f"Schema失败: {e}")
        _log(f"  FAIL: {e}")
        return out

    # Step 3: Quality
    _log("  [3/8] Quality check...")
    quality = get_quality_report(df)
    out["steps"]["quality"] = quality
    _log(f"  OK: missing={quality['缺失率']}%, dup={quality['重复率']}%")

    # Step 4: Config
    _log("  [4/8] Analysis config...")
    AnalysisContext = _analysis_context
    ctx = AnalysisContext(
        mode="generic", dataset_name=ds["name"],
        data_file_name=os.path.basename(ds["data_path"]),
        df=df, file_type=ds["file_type"], variable_dict_map=var_dict,
    )
    ctx.variable_schema = schema_df
    ctx.build_type_maps()

    can_skip_bp = True  # whether we can skip AI-generated analysis plan

    if ds.get("use_preset") and ds.get("preset_key"):
        profile = _preset_profiles(ds["preset_key"])
        if profile:
            ctx.apply_preset_profile(profile)
            out["steps"]["preset"] = f"Loaded: {profile.get('profile_name')}"
            _log(f"  Preset: {profile.get('profile_name')}")
            can_skip_bp = True  # preset provides sufficient analysis plan
    else:
        out["steps"]["preset"] = "None (pure generic)"

    _auto_suggest_config(ctx)
    cfg = ctx.user_analysis_config
    _auto_pick_target(ctx)
    _auto_pick_groups(ctx)
    _auto_pick_explanatory(ctx)
    out["steps"]["config"] = {
        "target": cfg.get("target_variable", ""),
        "groups": cfg.get("group_variables", [])[:5],
        "explanatory": cfg.get("explanatory_variables", [])[:8],
    }
    _log(f"  Config: target={cfg.get('target_variable')}, groups={len(cfg.get('group_variables',[]))}, expl={len(cfg.get('explanatory_variables',[]))}")

    # Step 5: Analysis
    _log("  [5/8] Statistical analysis...")
    t0 = time.time()
    try:
        analysis_results = _generic_analysis(
            df=df, schema_df=schema_df, config=cfg, var_dict=var_dict,
        )
        elapsed = time.time() - t0
        n_uni = len(analysis_results.get("univariate", {}))
        n_biv_g = len(analysis_results.get("bivariate_group", {}))
        n_biv_c = len(analysis_results.get("bivariate_corr", {}))
        has_multi = analysis_results.get("multivariate") is not None
        _log(f"  OK ({elapsed:.1f}s): uni={n_uni}, biv_g={n_biv_g}, biv_c={n_biv_c}, multi={has_multi}")
        out["steps"]["analysis"] = f"uni:{n_uni} biv:{n_biv_g+n_biv_c} multi:{'Y' if has_multi else 'N'}"
        findings = _get_analysis_summary(analysis_results)
        if findings:
            out["steps"]["key_findings"] = findings[:3]
    except Exception as e:
        out["errors"].append(f"Analysis failed: {e}")
        _log(f"  FAIL: {e}")
        traceback.print_exc()
        analysis_results = {"univariate": {}, "bivariate_group": {}, "bivariate_corr": {}, "warnings": [str(e)]}

    # Step 6: AI Blueprint
    _log("  [6/8] AI Blueprint...")
    t0 = time.time()
    bp_result = call_ai_blueprint(
        df=df, schema_df=schema_df, quality=quality,
        var_dict=var_dict, ctx=ctx,
        provider_config=provider_config, api_key=api_key, model=model,
    )
    bp_elapsed = time.time() - t0
    if bp_result["success"]:
        bp = bp_result["blueprint"]
        out["steps"]["ai_blueprint"] = {
            "status": "OK", "elapsed": f"{bp_elapsed:.1f}s",
            "dataset_type": bp.get("dataset_understanding", {}).get("dataset_type", ""),
            "titles": bp.get("recommended_report_titles", [])[:2],
            "n_recipes": len(bp.get("analysis_recipes", [])),
        }
        _log(f"  OK ({bp_elapsed:.1f}s): {len(bp.get('analysis_recipes',[]))} recipes")

        msgs = ctx.apply_blueprint(bp, overwrite=False)
        cfg = ctx.user_analysis_config
        if msgs:
            out["steps"]["blueprint_applied"] = [m[:120] for m in msgs]
            _log(f"  Applied: {'; '.join(m[:80] for m in msgs[:3])}")

        if any("变量已设为" in str(m) for m in msgs):
            _log("  Re-running analysis with updated config...")
            try:
                analysis_results = _generic_analysis(
                    df=df, schema_df=schema_df, config=cfg, var_dict=var_dict,
                )
                n_uni2 = len(analysis_results.get("univariate", {}))
                n_biv2 = len(analysis_results.get("bivariate_group", {})) + len(analysis_results.get("bivariate_corr", {}))
                has_m2 = analysis_results.get("multivariate") is not None
                out["steps"]["analysis_updated"] = f"uni:{n_uni2} biv:{n_biv2} multi:{'Y' if has_m2 else 'N'}"
                f2 = _get_analysis_summary(analysis_results)
                if f2: out["steps"]["key_findings"] = f2[:3]
                _log(f"  Re-analysis OK: uni={n_uni2}, biv={n_biv2}, multi={has_m2}")
            except Exception as e:
                out["warnings"].append(f"Re-analysis failed: {e}")
    else:
        out["steps"]["ai_blueprint"] = {"status": "FAILED", "error": bp_result["error"][:200]}
        _log(f"  FAIL: {bp_result['error'][:200]}")

    # Step 7: AI Report
    _log("  [7/8] AI Report generation...")
    t0 = time.time()
    report_result = call_ai_report(
        df=df, schema_df=schema_df, config=cfg,
        analysis_results=analysis_results, quality=quality,
        provider_config=provider_config, api_key=api_key, model=model,
    )
    report_elapsed = time.time() - t0
    if report_result["success"]:
        out["steps"]["ai_report"] = {
            "status": "OK", "elapsed": f"{report_elapsed:.1f}s",
            "md_len": len(report_result["markdown"]),
            "html_len": len(report_result["html"]),
            "has_docx": bool(report_result["docx"]),
        }
        _log(f"  OK ({report_elapsed:.1f}s): MD={len(report_result['markdown'])} chars, HTML={len(report_result['html'])}, DOCX={'Y' if report_result['docx'] else 'N'}")
    else:
        out["steps"]["ai_report"] = {"status": "FAILED", "error": report_result["error"][:200]}
        _log(f"  FAIL: {report_result['error'][:200]}")

    # Step 8: Save
    _log("  [8/8] Saving output files...")
    ds_dir = TEST_RESULTS_DIR / ds["id"]
    ds_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    try:
        payload = _analysis_packager(
            df=df, schema_df=schema_df, config=cfg,
            analysis_results=analysis_results, quality=quality,
        )
        (ds_dir / "analysis_payload.json").write_text(_to_json_payload(payload), encoding="utf-8")
        saved.append("analysis_payload.json")
    except Exception as e:
        out["warnings"].append(f"Save payload: {e}")

    if bp_result["success"] and bp_result["blueprint"]:
        (ds_dir / "ai_blueprint.json").write_text(
            json.dumps(bp_result["blueprint"], ensure_ascii=False, indent=2), encoding="utf-8")
        saved.append("ai_blueprint.json")

    if report_result["success"]:
        if report_result["markdown"]:
            (ds_dir / "report.md").write_text(report_result["markdown"], encoding="utf-8")
            saved.append("report.md")
        if report_result["html"]:
            (ds_dir / "report.html").write_text(report_result["html"], encoding="utf-8")
            saved.append("report.html")
        if report_result["docx"]:
            (ds_dir / "report.docx").write_bytes(report_result["docx"])
            saved.append("report.docx")

    summary = {
        "dataset_id": ds["id"], "dataset_name": ds["name"],
        "rows": len(df), "cols": len(df.columns),
        "config": {k: v for k, v in cfg.items() if not k.startswith("_")},
        "quality": quality,
        "type_distribution": out["steps"].get("type_distribution", {}),
        "ai_blueprint_summary": out["steps"].get("ai_blueprint", {}),
        "ai_report_summary": out["steps"].get("ai_report", {}),
        "errors": out["errors"], "warnings": out["warnings"],
    }
    (ds_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    saved.append("summary.json")

    out["steps"]["saved"] = saved
    _log(f"  Saved {len(saved)} files: {', '.join(saved)}")
    out["end_time"] = datetime.now(timezone.utc).isoformat()
    return out


# ================================================================
# 测试报告
# ================================================================

def generate_test_report(all_results: List[dict]) -> str:
    lines = [
        "# 全数据集自动化测试报告",
        f"\n**生成时间**: {NOW_STR}",
        f"**数据集数量**: {len(all_results)}",
        f"**AI 厂商**: DeepSeek (deepseek-chat)\n",
    ]
    n_ok = sum(1 for r in all_results if not r.get("errors"))
    n_ai_bp = sum(1 for r in all_results if r.get("steps", {}).get("ai_blueprint", {}).get("status") == "OK")
    n_ai_rpt = sum(1 for r in all_results if r.get("steps", {}).get("ai_report", {}).get("status") == "OK")

    lines.extend([
        "## Summary",
        "",
        "| Metric | Result |",
        "|--------|--------|",
        f"| Total datasets | {len(all_results)} |",
        f"| Fully passed | {n_ok} |",
        f"| AI Blueprint OK | {n_ai_bp}/{len(all_results)} |",
        f"| AI Report OK | {n_ai_rpt}/{len(all_results)} |",
        "",
    ])

    lines.append("## Detailed Results\n")
    for i, r in enumerate(all_results):
        st = r.get("steps", {})
        errs = r.get("errors", [])
        lines.append(f"### {i+1}. {r['dataset_name']}")
        lines.append(f"\n**ID**: `{r['dataset_id']}`\n")
        status = "PASS" if not errs else ("PARTIAL" if all("AI" in e for e in errs) else "FAIL")
        lines.append(f"**Status**: {status}\n")

        lines.append("| Step | Result |")
        lines.append("|------|--------|")
        for sn in ["load", "schema", "preset", "config", "analysis", "ai_blueprint", "ai_report", "saved"]:
            v = st.get(sn, "")
            if isinstance(v, dict):
                if sn == "ai_blueprint":
                    v = f"{'OK' if v.get('status')=='OK' else 'FAIL'} ({v.get('elapsed','?')}) - {v.get('n_recipes','?')} recipes"
                elif sn == "ai_report":
                    v = f"{'OK' if v.get('status')=='OK' else 'FAIL'} ({v.get('elapsed','?')}) - {v.get('md_len','?')} chars"
                elif sn == "config":
                    v = f"target={v.get('target','?')}, groups={len(v.get('groups',[]))}"
                else:
                    v = json.dumps(v, ensure_ascii=False)[:100]
            lines.append(f"| {sn} | {str(v)[:120]} |")
        lines.append("")

        tc = st.get("type_distribution", {})
        if tc:
            lines.append(f"**Types**: {', '.join(f'{k}:{v}' for k,v in sorted(tc.items()))}\n")

        findings = st.get("key_findings", [])
        if findings:
            lines.append("**Key Findings**:")
            for f in findings:
                lines.append(f"- {str(f)[:150]}")
            lines.append("")

        saved = st.get("saved", [])
        if isinstance(saved, list) and saved:
            lines.append(f"**Outputs** ({len(saved)}):")
            for sf in saved:
                lines.append(f"- `test_results/{r['dataset_id']}/{sf}`")
            lines.append("")

        if errs:
            lines.append("**Errors**:")
            for e in errs:
                lines.append(f"- {str(e)[:200]}")
            lines.append("")

        lines.append("---\n")

    lines.append("## AI Call Statistics\n")
    lines.append("| Dataset | Blueprint | Time | Report | Time | Report Size |")
    lines.append("|---------|-----------|------|--------|------|-------------|")
    for r in all_results:
        st = r.get("steps", {})
        bp = st.get("ai_blueprint", {})
        rpt = st.get("ai_report", {})
        lines.append(
            f"| {r['dataset_name'][:25]} | "
            f"{'OK' if bp.get('status')=='OK' else 'FAIL'} | {bp.get('elapsed','-')} | "
            f"{'OK' if rpt.get('status')=='OK' else 'FAIL'} | {rpt.get('elapsed','-')} | "
            f"{rpt.get('md_len',0):,} |")
    lines.append("")

    lines.append("## Conclusions\n")
    if n_ok == len(all_results):
        lines.append("All datasets passed. The unified platform is working correctly.")
    else:
        lines.append(f"{n_ok}/{len(all_results)} datasets fully passed.")
        if n_ai_bp < len(all_results):
            lines.append(f"- {len(all_results)-n_ai_bp} AI blueprint failures. Check API quota or retry.")
        if n_ai_rpt < len(all_results):
            lines.append(f"- {len(all_results)-n_ai_rpt} AI report failures. Check API quota or retry.")
    lines.append(f"\nAll outputs: `test_results/` directory.")

    return "\n".join(lines)


# ================================================================
# main
# ================================================================

def main():
    _log("=== Importing modules ===")
    _import_modules()
    global _get_analysis_summary, _to_json_payload

    # Load settings
    user_settings = _user_settings()
    if not user_settings:
        _log("FATAL: No user_settings.json found")
        print("FATAL: No user_settings.json", flush=True)
        return
    provider_key = user_settings.get("provider_key", "deepseek")
    api_key = user_settings.get("api_key", "")
    model = user_settings.get("model", "deepseek-chat")
    if not api_key:
        _log("FATAL: API key is empty")
        return

    provider_config = _provider_config(provider_key)
    if not provider_config:
        _log(f"FATAL: Provider '{provider_key}' not found")
        return

    _log(f"AI: {provider_config.get('display_name', provider_key)} / {model}")
    _log(f"Datasets: {len(DATASETS)}")

    all_results = []
    total_start = time.time()

    for i, ds in enumerate(DATASETS):
        _log(f"\n[{i+1}/{len(DATASETS)}] Starting {ds['id']}...")
        try:
            result = process_dataset(ds, provider_config, api_key, model)
        except Exception as e:
            _log(f"FATAL: Dataset {ds['id']} crashed: {e}")
            traceback.print_exc()
            result = {
                "dataset_id": ds["id"], "dataset_name": ds["name"],
                "errors": [f"Crash: {e}"], "steps": {},
            }
        all_results.append(result)

    total_elapsed = time.time() - total_start

    # Generate test report
    _log("\n=== Generating test report ===")
    report_md = generate_test_report(all_results)
    report_path = TEST_RESULTS_DIR / f"TEST_REPORT_{NOW_STR}.md"
    report_path.write_text(report_md, encoding="utf-8")
    json_path = TEST_RESULTS_DIR / f"test_results_raw_{NOW_STR}.json"
    json_path.write_text(json.dumps(all_results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    n_ok = sum(1 for r in all_results if not r.get("errors"))
    n_ai_bp = sum(1 for r in all_results if r.get("steps", {}).get("ai_blueprint", {}).get("status") == "OK")
    n_ai_rpt = sum(1 for r in all_results if r.get("steps", {}).get("ai_report", {}).get("status") == "OK")

    _log(f"\n=== DONE ===")
    _log(f"Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
    _log(f"Passed: {n_ok}/{len(all_results)}")
    _log(f"AI Blueprint: {n_ai_bp}/{len(all_results)}")
    _log(f"AI Report: {n_ai_rpt}/{len(all_results)}")
    _log(f"Report: {report_path}")
    _log(f"Log: {LOG_PATH}")

    # Also print summary
    for line in [
        "",
        "=" * 60,
        f"  Test Complete!",
        f"  Time: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)",
        f"  Passed: {n_ok}/{len(all_results)}",
        f"  AI Blueprint: {n_ai_bp}/{len(all_results)}",
        f"  AI Report: {n_ai_rpt}/{len(all_results)}",
        f"  Output: {TEST_RESULTS_DIR}",
        f"  Report: {report_path}",
        "=" * 60,
    ]:
        try:
            print(line, flush=True)
        except:
            pass


if __name__ == "__main__":
    main()
