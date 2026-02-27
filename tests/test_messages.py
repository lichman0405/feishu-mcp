"""
tests/test_messages.py — unit tests for the messages tool
"""
import json
import pytest
from unittest.mock import patch, MagicMock


def _mock_feishu_response(data: dict):
    """Build a mock Feishu API response."""
    mock = MagicMock()
    mock.json.return_value = {"code": 0, "msg": "success", "data": data}
    mock.raise_for_status = MagicMock()
    return mock


def test_send_message_text(monkeypatch):
    """send_message should correctly build the request and return message_id."""
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test")
    monkeypatch.setenv("FEISHU_APP_SECRET", "secret_test")

    import feishu_mcp.auth as auth
    import importlib
    importlib.reload(auth)
    auth._tenant_token = "t-fake-token"
    auth._tenant_token_expire = 9999999999.0

    from feishu_mcp.tools.messages import send_message

    mock_resp = _mock_feishu_response({"message_id": "om_test_123"})
    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
        result = send_message("chat_id", "oc_test", '{"text": "hello"}', "text")

    assert result["message_id"] == "om_test_123"


def test_build_text_with_at():
    """build_text_with_at should correctly generate text content with @user mention."""
    from feishu_mcp.tools.messages import build_text_with_at

    content = build_text_with_at("Please review", at_open_ids=["ou_abc123"])
    parsed = json.loads(content)
    assert "ou_abc123" in parsed["text"]
    assert "Please review" in parsed["text"]