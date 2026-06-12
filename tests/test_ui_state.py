"""Tests for src/ui/state.py — session state initialization."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# We avoid importing streamlit here — instead we mock st.session_state
# and test the _set_default helper and init_session_state logic directly.

class TestSetDefault:
    """Test the _set_default helper function."""

    def test_set_when_key_missing(self):
        """Should set the key when it does not exist."""
        from src.ui.state import _set_default

        state = {}
        # Mock st.session_state
        import src.ui.state as mod
        original = getattr(mod, 'st', None)
        try:
            class MockSt:
                session_state = state
            mod.st = MockSt()
            _set_default("my_key", 42)
            assert state["my_key"] == 42
        finally:
            if original is not None:
                mod.st = original

    def test_no_overwrite_when_key_exists(self):
        """Should NOT overwrite an existing key."""
        from src.ui.state import _set_default

        state = {"my_key": "original"}
        import src.ui.state as mod
        original = getattr(mod, 'st', None)
        try:
            class MockSt:
                session_state = state
            mod.st = MockSt()
            _set_default("my_key", "should_not_overwrite")
            assert state["my_key"] == "original"
        finally:
            if original is not None:
                mod.st = original


class TestInitSessionState:
    """Test init_session_state() via mocking."""

    @pytest.fixture
    def mock_st(self, monkeypatch):
        """Provide a fresh mock session_state."""
        state = {}

        class MockSt:
            session_state = state

        monkeypatch.setattr("src.ui.state.st", MockSt())
        # Also mock load_user_settings to return empty
        monkeypatch.setattr("src.ui.state.load_user_settings", lambda: {})
        return state

    def test_generic_config_defaults(self, mock_st):
        """init_session_state should set generic_config with correct defaults."""
        from src.ui.state import init_session_state
        init_session_state()
        cfg = mock_st["generic_config"]
        assert cfg["report_title"] == "问卷数据分析报告"
        assert cfg["target_variable"] == ""
        assert cfg["group_variables"] == []
        assert cfg["explanatory_variables"] == []

    def test_saved_settings_without_file(self, mock_st):
        """Without saved settings, _saved_* keys should be empty/default."""
        from src.ui.state import init_session_state
        init_session_state()
        assert mock_st["_saved_provider_key"] == ""
        assert mock_st["_saved_api_key"] == ""
        assert mock_st["_saved_model"] == ""
        assert mock_st["_saved_remember"] is False

    def test_saved_settings_with_file(self, monkeypatch):
        """With saved settings, _saved_* keys should reflect saved values."""
        saved = {
            "provider_key": "deepseek",
            "api_key": "sk-saved",
            "model": "saved-model",
            "remember": True,
        }
        monkeypatch.setattr("src.ui.state.load_user_settings", lambda: saved)

        state = {}
        class MockSt:
            session_state = state
        monkeypatch.setattr("src.ui.state.st", MockSt())

        from src.ui.state import init_session_state
        init_session_state()
        assert state["_saved_provider_key"] == "deepseek"
        assert state["_saved_api_key"] == "sk-saved"
        assert state["_saved_model"] == "saved-model"
        assert state["_saved_remember"] is True

    def test_ai_model_default_from_saved(self, monkeypatch):
        """_ai_model should default to _saved_model when available."""
        saved = {
            "provider_key": "openai",
            "api_key": "sk",
            "model": "gpt-4",
            "remember": True,
        }
        monkeypatch.setattr("src.ui.state.load_user_settings", lambda: saved)

        state = {}
        class MockSt:
            session_state = state
        monkeypatch.setattr("src.ui.state.st", MockSt())

        from src.ui.state import init_session_state
        init_session_state()
        assert state["_ai_model"] == "gpt-4"

    def test_ai_models_init_defaults(self, mock_st):
        """ai_models_* keys should have correct defaults."""
        from src.ui.state import init_session_state
        init_session_state()
        assert mock_st["ai_models_fetched"] is False
        assert mock_st["ai_available_models"] == []
        assert mock_st["ai_models_source"] == ""
        assert mock_st["ai_models_updated_at"] is None
        assert mock_st["ai_models_error"] == ""

    def test_idempotent(self, mock_st):
        """Calling init_session_state twice should not overwrite user changes."""
        from src.ui.state import init_session_state
        init_session_state()
        # User changes a value
        mock_st["generic_config"]["report_title"] = "自定义标题"
        mock_st["_ai_model"] = "user-selected-model"
        # Call again
        init_session_state()
        # Should preserve user changes
        assert mock_st["generic_config"]["report_title"] == "自定义标题"
        assert mock_st["_ai_model"] == "user-selected-model"
