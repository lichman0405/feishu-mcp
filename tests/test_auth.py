"""
tests/test_auth.py — unit tests for the auth module
"""
import pytest
from unittest.mock import patch, MagicMock
import os


def test_get_app_id_raises_without_env():
    """Should raise EnvironmentError when FEISHU_APP_ID is not configured."""
    with patch.dict(os.environ, {"FEISHU_APP_ID": ""}):
        from feishu_mcp import auth
        # Reset cache
        import importlib
        importlib.reload(auth)
        with pytest.raises(EnvironmentError):
            auth.get_app_id()


def test_get_tenant_access_token_caches(monkeypatch):
    """tenant_access_token should be cached; second call should not trigger an HTTP request."""
    import feishu_mcp.auth as auth
    import importlib
    importlib.reload(auth)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "code": 0,
        "tenant_access_token": "t-test-token-12345",
        "expire": 7200,
    }
    mock_response.raise_for_status = MagicMock()

    call_count = 0

    def fake_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_response

    monkeypatch.setenv("FEISHU_APP_ID", "cli_test")
    monkeypatch.setenv("FEISHU_APP_SECRET", "secret_test")

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post = fake_post
        token1 = auth.get_tenant_access_token()
        token2 = auth.get_tenant_access_token()

    assert token1 == "t-test-token-12345"
    assert token1 == token2
    assert call_count == 1, "Cache is valid; HTTP request should only be sent once"