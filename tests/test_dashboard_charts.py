"""Tests for dashboard chart generation with binary variables.

Verifies that the fix for binary-type targets in generate_dashboard_charts
produces adequate chart counts without hardcoding.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

from src.generic_charts import (
    auto_univariate_chart,
    auto_bivariate_chart,
    generate_dashboard_charts,
)


class TestBinaryVariableCharts:
    """Verify binary variables produce charts (not None) in bivariate contexts."""

    def test_univariate_binary_produces_chart(self):
        """Binary variable should produce a univariate bar chart."""
        df = pd.DataFrame({
            "converted": [0, 1, 0, 1, 0, 0, 1, 1, 0, 0],
        })
        fig = auto_univariate_chart(df, "converted", "binary", "是否转化")
        assert fig is not None, "Binary univariate chart should not be None"

    def test_bivariate_categorical_x_binary_produces_chart(self):
        """categorical × binary should produce a stacked bar chart."""
        df = pd.DataFrame({
            "region": ["A", "B", "A", "B", "A", "B", "A", "B", "A", "A"],
            "converted": [0, 1, 0, 1, 0, 0, 1, 1, 0, 0],
        })
        fig = auto_bivariate_chart(
            df, "region", "converted",
            "categorical", "binary", "区域", "是否转化",
        )
        assert fig is not None, "categorical × binary bivariate chart should not be None"

    def test_bivariate_numeric_x_binary_produces_chart(self):
        """numeric × binary should produce a box plot."""
        df = pd.DataFrame({
            "age": [25, 30, 35, 40, 28, 33, 45, 50, 22, 27],
            "converted": [0, 1, 0, 1, 0, 0, 1, 1, 0, 0],
        })
        fig = auto_bivariate_chart(
            df, "age", "converted",
            "numeric", "binary", "年龄", "是否转化",
        )
        assert fig is not None, "numeric × binary bivariate chart should not be None"

    def test_binary_x_binary_produces_chart(self):
        """binary × binary should produce a stacked bar chart."""
        df = pd.DataFrame({
            "coupon_used": [0, 1, 0, 1, 0, 0, 1, 0, 1, 0],
            "converted":  [1, 0, 0, 1, 0, 1, 1, 0, 1, 0],
        })
        fig = auto_bivariate_chart(
            df, "coupon_used", "converted",
            "binary", "binary", "优惠券使用", "是否转化",
        )
        assert fig is not None, "binary × binary bivariate chart should not be None"


class TestDashboardWithBinaryTarget:
    """Full dashboard generation with a binary target variable."""

    def test_dashboard_binary_target_produces_minimum_charts(self):
        """Dashboard with binary target should produce ≥5 valid charts.

        This is the test_run4.py scenario: config B with converted as target.
        The fix adds 'binary' to the cat_type set so binary targets participate
        in bivariate chart pairings (as categorical variables with 2 levels).
        """
        np.random.seed(42)
        n = 250
        df = pd.DataFrame({
            "user_id": [f"U{i:06d}" for i in range(n)],
            "region": np.random.choice(["华东", "华北", "华南", "西南", "西北", "东北"], n),
            "device": np.random.choice(["Android", "PC", "iOS", "小程序"], n),
            "membership_level": np.random.choice(["普通", "银卡", "金卡", "钻石"], n),
            "age": np.random.randint(18, 65, n).astype(float),
            "page_views": np.random.randint(1, 200, n).astype(float),
            "session_minutes": np.random.uniform(1, 60, n).round(2),
            "service_rating": np.random.randint(1, 6, n).astype(float),
            "price_sensitivity": np.random.randint(1, 6, n).astype(float),
            "coupon_used": np.random.randint(0, 2, n).astype(float),
            "purchase_amount": np.random.uniform(0, 500, n).round(2),
            "converted": np.random.randint(0, 2, n).astype(float),
        })

        schema_df = pd.DataFrame([
            {"column": "user_id", "inferred_type": "id", "display_name": "用户ID"},
            {"column": "region", "inferred_type": "categorical", "display_name": "地区"},
            {"column": "device", "inferred_type": "categorical", "display_name": "设备"},
            {"column": "membership_level", "inferred_type": "categorical", "display_name": "会员等级"},
            {"column": "age", "inferred_type": "numeric", "display_name": "年龄"},
            {"column": "page_views", "inferred_type": "numeric", "display_name": "页面浏览量"},
            {"column": "session_minutes", "inferred_type": "numeric", "display_name": "会话时长"},
            {"column": "service_rating", "inferred_type": "ordinal", "display_name": "服务评分"},
            {"column": "price_sensitivity", "inferred_type": "ordinal", "display_name": "价格敏感度"},
            {"column": "coupon_used", "inferred_type": "binary", "display_name": "使用优惠券"},
            {"column": "purchase_amount", "inferred_type": "numeric", "display_name": "购买金额"},
            {"column": "converted", "inferred_type": "binary", "display_name": "是否转化"},
        ])

        config_b = {
            "report_title": "电商用户转化行为分析报告",
            "target_variable": "converted",
            "group_variables": ["region", "device", "membership_level", "coupon_used"],
            "explanatory_variables": ["age", "page_views", "session_minutes", "service_rating", "price_sensitivity"],
        }

        dashboard = generate_dashboard_charts(df, schema_df, config_b)
        valid = [(k, t, f) for k, t, f in dashboard if f is not None]

        # Should have at least:
        # - 1 target univariate chart
        # - 4 group×target bivariate charts (region, device, membership, coupon × converted)
        # - 5 expl×target bivariate charts (age, pages, session, rating, sensitivity × converted)
        # - 1 correlation heatmap
        # = 11 potential charts
        assert len(valid) >= 5, (
            f"Expected ≥5 valid charts with binary target, got {len(valid)}. "
            f"Valid keys: {[k for k, t, f in valid]}"
        )

    def test_dashboard_binary_target_not_hardcoded(self):
        """Verify the chart generation is driven by data, not hardcoded counts.

        A dashboard with fewer variables should produce fewer (but still valid) charts.
        """
        df = pd.DataFrame({
            "region": ["A", "B", "A", "B", "A", "B", "A", "B", "A", "A"],
            "converted": [0, 1, 0, 1, 0, 0, 1, 0, 1, 0],
        })
        schema_df = pd.DataFrame([
            {"column": "region", "inferred_type": "categorical", "display_name": "区域"},
            {"column": "converted", "inferred_type": "binary", "display_name": "是否转化"},
        ])
        config = {
            "target_variable": "converted",
            "group_variables": ["region"],
            "explanatory_variables": [],
        }

        dashboard = generate_dashboard_charts(df, schema_df, config)
        valid = [(k, t, f) for k, t, f in dashboard if f is not None]

        # With minimal variables:
        # - 1 target univariate
        # - 1 group×target (region × converted)
        # - 0 expl×target (no explanatory vars)
        # - 0 heatmap (< 2 numeric vars)
        # = 2 charts
        assert len(valid) == 2, (
            f"Expected exactly 2 valid charts with minimal config, got {len(valid)}"
        )
