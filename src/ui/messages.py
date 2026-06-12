"""Centralized user-facing messages for the Streamlit app.

All user-visible error messages, hints, and prompts are centralized here
to ensure consistency across tabs and make future updates easier.

None of these functions contain business logic — they only return strings.
They are safe to call from any module without importing Streamlit.
"""

from __future__ import annotations

from typing import List

from src.ui.theme import (
    COLORS,
    RADIUS,
    SPACING,
    CARD_STYLE,
    PIPELINE_STATUS_BG,
    PIPELINE_STATUS_COLORS,
)


# ================================================================
# No API Key messages
# ================================================================


def get_no_api_key_message(api_key_env: str = "") -> str:
    """Message shown when the user has not configured an API Key.

    Args:
        api_key_env: The environment variable name for this provider's API key.
    """
    lines = [
        "💡 **当前未配置 API Key。**",
        "",
        "你仍然可以继续使用以下功能：",
        "- 📁 数据上传与变量管理",
        "- 📊 描述统计、交叉分析、相关分析、回归分析",
        "- 📈 可视化图表",
        "- 📄 模板报告生成（HTML / DOCX）",
        "",
        "如需生成 **AI 分析报告**，请在左侧或当前页面配置模型厂商和 API Key：",
    ]
    if api_key_env:
        lines.append(f"  - 在上方输入框中填入 API Key")
        lines.append(f"  - 或设置环境变量 `{api_key_env}`")
    else:
        lines.append("  - 在上方输入框中填入 API Key")
    return "\n".join(lines)


def get_no_api_key_short_message() -> str:
    """One-line hint when no API Key is present."""
    return (
        "💡 未配置 API Key。统计分析功能不受影响；"
        "如需 AI 报告，请在当前页面配置 API Key。"
    )


# ================================================================
# Literature search messages
# ================================================================


def get_literature_empty_message(keywords: str = "") -> str:
    """Message shown when literature search returns zero results.

    Args:
        keywords: The search keywords that were used.
    """
    lines = [
        "⚠️ **未检索到合适文献。**",
        "",
        "可能的原因与建议：",
        "1. 当前免费文献 API（Semantic Scholar / OpenAlex / CrossRef）以 **英文数据库** 为主，中文关键词命中较少",
    ]
    if keywords and any("一" <= c <= "鿿" for c in keywords):
        lines.append(
            "2. 你的关键词为中文，可以尝试补充英文关键词，例如：\n"
            "   - `government service satisfaction`\n"
            "   - `public service quality`\n"
            "   - `citizen satisfaction survey`\n"
            "   - `policy evaluation`"
        )
    else:
        lines.append("2. 可以尝试更宽泛的关键词，减少专业术语限定")
    lines.append("3. 文献综述是辅助材料，**不影响基础统计分析**")
    lines.append("4. 可以跳过文献检索，直接生成报告")
    return "\n".join(lines)


def get_literature_error_message(error: str = "") -> str:
    """Message shown when literature search fails with an exception.

    Args:
        error: The error message (may be technical).
    """
    lines = [
        "⚠️ **文献检索请求失败。**",
        "",
        "可能的原因：",
        "- 网络连接不稳定，无法访问学术 API",
        "- 请求频率过高，被暂时限流",
        "- API 服务暂时不可用",
        "",
        "建议：",
        "- 稍后重试",
        "- 减少文献来源数",
        "- 文献综述是辅助材料，可以跳过直接生成报告",
    ]
    if error:
        lines.append(f"\n技术信息：`{error[:200]}`")
    return "\n".join(lines)


def get_literature_keywords_hint() -> str:
    """Hint about keyword language for literature search."""
    return (
        "💡 提示：免费文献 API 以英文数据库为主。中文关键词命中率可能较低，"
        "建议尝试 `government service satisfaction`、`public service quality` 等英文关键词。"
    )


# ================================================================
# AI Report error messages
# ================================================================


def format_user_friendly_error(exc_or_message: object, context: str = "") -> str:
    """Convert any exception or error string into a user-friendly Chinese message.

    This classifies common error patterns and returns an appropriate
    Chinese message with actionable suggestions.  Falls back to the
    original message if no pattern matches.

    Args:
        exc_or_message: An Exception object or error string.
        context: Optional context, e.g. "AI 报告生成" or "文献检索".

    Returns:
        A user-friendly Chinese error message string.
    """
    msg = ""
    if isinstance(exc_or_message, Exception):
        msg = str(exc_or_message)
    elif isinstance(exc_or_message, str):
        msg = exc_or_message
    else:
        msg = str(exc_or_message)

    msg_lower = msg.lower()
    ctx_prefix = f"**{context}** 失败" if context else "操作失败"

    # 1. API Key 缺失 / 未授权
    if any(kw in msg_lower for kw in ("unauthorized", "401", "invalid api key", "incorrect api key",
                                        "authentication failed", "invalid x-api-key", "no api key",
                                        "api key not provided", "missing api key")):
        return (
            f"{ctx_prefix}：**API Key 无效或缺失。**\n\n"
            "请检查：\n"
            "1. API Key 是否正确填写（注意前后空格）\n"
            "2. API Key 是否仍然有效（未过期、未删除）\n"
            "3. 该 Key 是否有权限访问所选模型\n\n"
            "💡 你仍然可以使用数据上传、统计分析和模板报告功能。"
        )

    # 2. API Key 错误 / 禁止访问
    if any(kw in msg_lower for kw in ("forbidden", "403", "access denied", "not allowed",
                                        "insufficient permissions", "billing", "quota")):
        return (
            f"{ctx_prefix}：**API 访问被拒绝。**\n\n"
            "可能的原因：\n"
            "1. API Key 无权访问该模型\n"
            "2. 账户余额不足或配额已用完\n"
            "3. 该模型需要单独开通\n\n"
            "建议：检查 API 厂商后台的账户状态和额度。"
        )

    # 3. 网络连接失败
    if any(kw in msg_lower for kw in ("connection", "timeout", "timed out", "network",
                                        "resolve", "dns", "refused", "unreachable",
                                        "econnrefused", "econnreset", "enotfound")):
        return (
            f"{ctx_prefix}：**网络连接失败。**\n\n"
            "可能的原因：\n"
            "1. 网络不稳定或断开\n"
            "2. API 地址无法访问（是否需要代理/VPN？）\n"
            "3. 防火墙阻止了外部请求\n\n"
            "建议：检查网络连接，或稍后重试。"
        )

    # 4. 模型名称错误
    if any(kw in msg_lower for kw in ("model not found", "invalid model", "unknown model",
                                        "model does not exist", "404", "not available")):
        return (
            f"{ctx_prefix}：**模型名称错误或模型不可用。**\n\n"
            "建议：\n"
            "1. 检查模型名称拼写\n"
            "2. 尝试「联网获取模型列表」获取可用模型\n"
            "3. 确认该模型在所选厂商中可用"
        )

    # 5. 返回内容为空
    if any(kw in msg_lower for kw in ("empty response", "no content", "empty content",
                                        "null response", "返回内容为空")):
        return (
            f"{ctx_prefix}：**模型返回内容为空。**\n\n"
            "可能的原因：\n"
            "1. 模型对输入内容未产生有效回复\n"
            "2. 请求被内容安全过滤\n\n"
            "建议：尝试调整报告参数或更换模型。"
        )

    # 6. 请求超时
    if any(kw in msg_lower for kw in ("timeout", "timed out", "超时")):
        return (
            f"{ctx_prefix}：**请求超时。**\n\n"
            "建议：\n"
            "1. 减小「最大文献来源数」或报告篇幅\n"
            "2. 检查网络连接质量\n"
            "3. 稍后重试"
        )

    # 7. Payload 为空 / 缺少分析结果
    if any(kw in msg_lower for kw in ("payload", "分析结果为空", "缺少分析结果",
                                        "no analysis results", "empty payload")):
        return (
            f"{ctx_prefix}：**分析结果不完整。**\n\n"
            "建议：\n"
            "1. 先在「8. 生成 Analysis Payload」中生成分析结果\n"
            "2. 确认已在「分析方案」中设置了目标变量\n"
            "3. 确认数据加载正常"
        )

    # 8. Server error (5xx)
    if any(kw in msg_lower for kw in ("500", "502", "503", "server error", "internal server",
                                        "service unavailable", "overloaded")):
        return (
            f"{ctx_prefix}：**API 服务端错误。**\n\n"
            "API 服务暂时不可用，请稍后重试。如果持续出现，可检查厂商服务状态页面。"
        )

    # 9. Rate limit
    if any(kw in msg_lower for kw in ("rate limit", "too many requests", "429")):
        return (
            f"{ctx_prefix}：**请求频率过高，被暂时限流。**\n\n"
            "请稍等片刻后重试。"
        )

    # Fallback: return original message with a note
    return (
        f"{ctx_prefix}：{msg}\n\n"
        "💡 如需帮助，请检查 API Key、网络连接和模型名是否正确。\n"
        "统计分析功能不受影响，你仍然可以查看所有图表和分析结果。"
    )


def get_ai_report_error_message(error: str = "", context: str = "AI 报告生成") -> str:
    """Get a user-friendly AI report generation error message.

    This is a convenience wrapper around :func:`format_user_friendly_error`
    for the specific context of AI report generation.

    Args:
        error: The error string or exception message.
        context: Context label (default: "AI 报告生成").
    """
    return format_user_friendly_error(error, context=context)


# ================================================================
# Privacy & sensitive field messages
# ================================================================


def get_privacy_warning_message(high_risk_count: int = 0, medium_risk_count: int = 0) -> str:
    """Privacy warning shown before AI report generation.

    Args:
        high_risk_count: Number of high-risk variables detected.
        medium_risk_count: Number of medium-risk variables detected.
    """
    if high_risk_count > 0:
        lines = [
            "🔒 **隐私提醒：建议不要将高风险字段送入 AI。**",
            "",
            f"系统检测到 **{high_risk_count}** 个高风险变量"
        ]
        if medium_risk_count > 0:
            lines[2] += f"和 **{medium_risk_count}** 个中风险变量"
        lines[2] += "。"
        lines += [
            "",
            "高风险字段可能包含：",
            "- 📱 手机号、身份证号等直接身份标识",
            "- 📧 邮箱、地址等联系方式",
            "- 💬 自由文本（可能包含未脱敏的个人信息）",
            "- 💰 金融账户等敏感信息",
            "",
            "默认情况下，高风险变量 **仅用于本地统计，不会发送给 AI**。",
            "你可以在下方「7. 隐私与变量使用设置」中逐变量调整发送策略。",
        ]
        return "\n".join(lines)

    if medium_risk_count > 0:
        return (
            "🔒 **隐私提醒：** 检测到 {medium_risk_count} 个中风险变量。"
            "这些变量默认以聚合统计形式发送给 AI。"
            "你可以在下方「7. 隐私与变量使用设置」中调整发送策略。"
        ).format(medium_risk_count=medium_risk_count)

    return (
        "✅ 未检测到中高风险变量。所有变量的统计结果将以聚合形式发送给 AI。"
        "你仍然可以在下方「7. 隐私与变量使用设置」中调整变量使用方式。"
    )


def get_sensitive_field_explanations() -> dict:
    """Return a mapping from privacy category codes to Chinese explanations."""
    return {
        "direct_identifier": "🚫 **直接身份标识** — 如姓名、身份证号、手机号。**强烈建议不发送给 AI。**",
        "contact_info": "📧 **联系方式** — 如电话、邮箱、地址。建议仅用于本地分组统计。",
        "free_text": "💬 **自由文本** — 可能包含未脱敏的个人信息。建议仅发送聚合统计。",
        "financial": "💰 **金融信息** — 如收入、账户号。建议不发送给 AI。",
        "location_info": "📍 **地理位置** — 如详细地址。建议仅发送到区/县级别的聚合统计。",
        "demographic_attribute": "👤 **人口统计属性** — 如年龄、性别。通常风险较低，可以聚合发送。",
        "sensitive_attribute": "⚠️ **敏感属性** — 如健康状况、政治观点。建议不发送给 AI。",
        "unknown": "❓ **未分类** — 请确认该变量是否包含敏感信息后再决定发送方式。",
    }


def get_sensitive_field_data_explanation(category: str) -> str:
    """Get the explanation for a specific privacy category.

    Args:
        category: Privacy category code (e.g. 'direct_identifier', 'free_text').
    """
    explanations = get_sensitive_field_explanations()
    return explanations.get(category, explanations.get("unknown", ""))


# ================================================================
# Export messages
# ================================================================


def get_export_success_message(formats: List[str]) -> str:
    """Message shown when report export succeeds.

    Args:
        formats: List of exported format names, e.g. ["HTML", "DOCX"].
    """
    fmt_str = "、".join(formats)
    lines = [
        f"✅ **报告生成完成！已生成 {fmt_str} 格式。**",
        "",
        "请点击下方下载按钮保存文件。",
        "- 📥 下载按钮在报告预览下方",
        "- 📂 文件保存在浏览器的默认下载目录",
        "",
        "💡 提示：统计关联不等于因果关系，报告内容建议人工审阅后使用。",
    ]
    return "\n".join(lines)


def get_export_error_message(fmt: str = "", reason: str = "") -> str:
    """Message shown when report export fails.

    Args:
        fmt: The format that failed, e.g. "DOCX" or "HTML".
        reason: Known reason for the failure, if any.
    """
    fmt_label = f"**{fmt}** " if fmt else ""
    lines = [f"❌ {fmt_label}报告导出失败。"]

    if reason:
        lines.append(f"\n原因：{reason}")

    lines += [
        "",
        "可能的原因与建议：",
        "1. **outputs 目录权限不足** — 检查 outputs/ 目录是否存在且可写",
        "2. **文件被占用** — 关闭可能正在使用该文件的程序（如 Word）",
        "3. **磁盘空间不足** — 检查磁盘剩余空间",
        "4. **python-docx 未安装** — 运行 `pip install python-docx`",
        "",
        "💡 建议：尝试切换导出格式，或重新生成报告。",
    ]
    return "\n".join(lines)


def get_export_directory_hint() -> str:
    """Hint about where exported files are saved."""
    return (
        "📂 导出的文件默认保存在 `outputs/` 目录下。"
        "如果该目录不存在，系统会自动创建。"
    )


# ================================================================
# Beginner / flow guide messages
# ================================================================


def _landing_shared_constants():
    """Return (C, R, card_css, steps) for landing page functions."""
    C = COLORS
    R = RADIUS
    card_css = (
        f"background:{C.surface};border:1px solid {C.border};"
        f"border-radius:{R['md']};padding:20px;"
        f"box-shadow:0 1px 3px rgba(16,24,40,0.06);"
    )
    steps = [
        ("数据与变量", "上传数据、预览与变量管理"),
        ("分析方案", "手动配置或 AI 推荐"),
        ("统计分析", "单/双/多变量分析"),
        ("可视化仪表盘", "自动生成图表"),
        ("报告工作台", "报告生成、预览、导出"),
    ]
    return C, R, card_css, steps


def get_landing_hero() -> str:
    """Render the landing page hero area (two-column: brand + 5-step overview).

    Does NOT include CTA buttons — those are rendered as st.button() in app.py.
    """
    C, R, card_css, steps = _landing_shared_constants()

    step_items = []
    for i, (name, hint) in enumerate(steps, 1):
        step_items.append(
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'padding:9px 0;border-bottom:1px solid {C.divider};">'
            f'<div style="width:24px;height:24px;border-radius:50%;'
            f'background:{C.surface_subtle};color:{C.text_muted};'
            f'text-align:center;line-height:24px;font-size:11px;'
            f'font-weight:600;flex-shrink:0;">{i}</div>'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-size:13px;font-weight:600;color:{C.text};'
            f'line-height:1.3;">{name}</div>'
            f'<div style="font-size:11px;color:{C.text_muted};'
            f'line-height:1.3;">{hint}</div>'
            f'</div></div>'
        )

    return (
        f'<div style="display:flex;gap:28px;flex-wrap:wrap;'
        f'align-items:stretch;margin-bottom:8px;">'
        # ── Left: brand ──
        f'<div style="flex:1;min-width:300px;">'
        f'<div style="font-size:32px;font-weight:700;color:{C.text_strong};'
        f'line-height:1.2;margin-bottom:6px;">CivicSurvey Studio</div>'
        f'<div style="font-size:14px;color:{C.primary};font-weight:500;'
        f'margin-bottom:14px;">'
        f'问策 Insight &middot; AI 辅助问卷统计分析与报告生成工作台</div>'
        f'<div style="font-size:13px;color:{C.text_muted};'
        f'line-height:1.65;margin-bottom:18px;max-width:480px;">'
        f'上传问卷数据，自动识别变量类型，完成统计分析、可视化与报告生成。</div>'
        # disclaimer
        f'<div style="font-size:11px;color:{C.text_subtle};'
        f'line-height:1.55;max-width:480px;">'
        f'统计关联不等于因果关系，分析结果需结合实际情况进行人工判断。'
        f'AI 仅作为辅助分析和报告草稿工具，最终结论仍需人工复核。</div>'
        f'</div>'
        # ── Right: 5-step overview card ──
        f'<div style="flex:1;min-width:260px;{card_css}">'
        f'<div style="font-size:11px;color:{C.text_muted};'
        f'text-transform:uppercase;letter-spacing:0.5px;'
        f'margin-bottom:10px;">工作流概览</div>'
        f'{"".join(step_items)}'
        f'</div>'
        f'</div>'
    )


def get_landing_cards() -> str:
    """Render the getting-started cards and workflow step cards."""
    C, R, card_css, steps = _landing_shared_constants()

    # ── Three getting-started cards ──
    cards = (
        f'<div style="display:flex;gap:14px;margin-bottom:22px;flex-wrap:wrap;">'
        f'<div style="flex:1;min-width:200px;{card_css}">'
        f'<div style="font-size:14px;font-weight:600;color:{C.text};margin-bottom:6px;">'
        f'上传问卷数据</div>'
        f'<div style="font-size:12px;color:{C.text_muted};line-height:1.6;">'
        f'支持 CSV / Excel 格式，上传后自动完成数据质量检查和变量类型识别。'
        f'在左侧边栏上传文件即可开始。</div></div>'
        f'<div style="flex:1;min-width:200px;{card_css}">'
        f'<div style="font-size:14px;font-weight:600;color:{C.text};margin-bottom:6px;">'
        f'加载示例数据</div>'
        f'<div style="font-size:12px;color:{C.text_muted};line-height:1.6;">'
        f'无数据时可使用内置模拟数据快速体验完整分析流程。'
        f'所有示例均为模拟数据，不含真实个人信息。</div></div>'
        f'<div style="flex:1;min-width:200px;{card_css}">'
        f'<div style="font-size:14px;font-weight:600;color:{C.text};margin-bottom:6px;">'
        f'配置 AI 报告</div>'
        f'<div style="font-size:12px;color:{C.text_muted};line-height:1.6;">'
        f'仅在需要 AI 生成报告时配置 API Key。'
        f'本地统计分析无需 API Key。在左侧边栏 AI 设置区配置。</div></div>'
        f'</div>'
    )

    # ── Five workflow step cards ──
    pending_bg = PIPELINE_STATUS_BG["pending"]
    step_cards_html = []
    for i, (name, hint) in enumerate(steps, 1):
        step_cards_html.append(
            f'<div style="flex:1;min-width:130px;background:{C.surface};'
            f'border:1px solid {C.border};border-radius:{R["md"]};'
            f'padding:14px 10px;text-align:center;'
            f'box-shadow:0 1px 2px rgba(16,24,40,0.04);">'
            f'<div style="width:24px;height:24px;border-radius:50%;'
            f'background:{pending_bg};margin:0 auto 8px;'
            f'line-height:24px;font-size:11px;font-weight:600;'
            f'color:{C.text_muted};">{i}</div>'
            f'<div style="font-size:13px;font-weight:600;color:{C.text};'
            f'margin-bottom:3px;">{name}</div>'
            f'<div style="font-size:11px;color:{C.text_muted};'
            f'line-height:1.4;">{hint}</div>'
            f'</div>'
        )

    steps_row = (
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;'
        f'margin-bottom:20px;">'
        f'{"".join(step_cards_html)}'
        f'</div>'
    )

    return cards + steps_row


def get_beginner_flow_guide() -> str:
    """Render the full landing page (hero + cards) as a single HTML block.

    For cases where CTA buttons aren't needed inline.
    """
    action_hint = (
        f'<div style="text-align:center;font-size:11px;color:{COLORS.text_subtle};'
        f'margin-bottom:8px;margin-top:6px;">'
        f'推荐操作：加载内置示例数据或上传你自己的问卷数据开始分析</div>'
    )
    return get_landing_hero() + action_hint + get_landing_cards()


def get_example_data_loaded_message(dataset_name: str = "政府服务满意度示例数据") -> str:
    """Message shown when example data has been loaded.

    Args:
        dataset_name: The display name of the loaded dataset.
    """
    return (
        f"✅ **已加载「{dataset_name}」**\n\n"
        "- 该数据为 **模拟数据**，不包含真实个人信息\n"
        "- 包含满意度、分类变量、数值变量和少量缺失值\n"
        "- 可继续前往「数据与变量」和「分析方案」完成后续步骤\n"
        "- 配套变量说明表已自动加载"
    )


def get_example_data_not_found_message() -> str:
    """Message shown when example data files are missing."""
    return (
        "⚠️ **示例数据文件未找到。**\n\n"
        "请确保以下文件存在于 `examples/` 目录：\n"
        "- `examples/government_service_satisfaction_sample.csv`\n"
        "- `examples/variable_dictionary_sample.csv`\n\n"
        "你仍然可以上传自己的数据文件进行分析。"
    )
