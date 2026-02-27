"""
auth.py — Feishu token management

Supports:
- tenant_access_token (app identity, auto-cached, refreshed 5 min before expiry)
- user_access_token (user identity, read from .env, used by calendar and other user-scoped APIs)
"""

import logging
import time
from typing import Optional

import httpx
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)

FEISHU_BASE_URL = "https://open.feishu.cn"

# ——— In-memory token cache ———
_tenant_token: Optional[str] = None
_tenant_token_expire: float = 0.0  # Unix timestamp


def get_app_id() -> str:
    v = os.getenv("FEISHU_APP_ID", "")
    if not v or v.startswith("cli_xxx"):
        raise EnvironmentError(
            "FEISHU_APP_ID is not configured. Copy .env.example to .env and fill in real credentials."
        )
    return v


def get_app_secret() -> str:
    v = os.getenv("FEISHU_APP_SECRET", "")
    if not v or v.startswith("xxx"):
        raise EnvironmentError(
            "FEISHU_APP_SECRET is not configured. Copy .env.example to .env and fill in real credentials."
        )
    return v


def get_tenant_access_token() -> str:
    """Retrieve tenant_access_token with automatic caching and refresh 5 minutes before expiry."""
    global _tenant_token, _tenant_token_expire

    now = time.time()
    if _tenant_token and now < _tenant_token_expire - 300:
        return _tenant_token

    url = f"{FEISHU_BASE_URL}/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": get_app_id(),
        "app_secret": get_app_secret(),
    }

    with httpx.Client(timeout=10) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(
            f"Failed to get tenant_access_token: code={data.get('code')}, msg={data.get('msg')}"
        )

    _tenant_token = data["tenant_access_token"]
    _tenant_token_expire = now + data.get("expire", 7200)
    logger.debug("tenant_access_token refreshed, expires in %s seconds", data.get("expire"))
    return _tenant_token


def get_user_access_token() -> Optional[str]:
    """
    Read user_access_token from environment variable.

    Note: user_access_token expires in ~2 hours; refresh via refresh_token when expired.
    Current implementation reads directly from env; can be extended to auto-refresh.
    """
    token = os.getenv("FEISHU_USER_ACCESS_TOKEN", "").strip()
    return token if token else None


def get_auth_headers(use_user_token: bool = False) -> dict:
    """
    Return authentication headers required for Feishu API calls.

    Args:
        use_user_token: If True, prefer user_access_token (e.g. for calendar);
                        falls back to tenant_access_token if user token is unavailable.
    """
    if use_user_token:
        token = get_user_access_token()
        if token:
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }
        logger.warning(
            "use_user_token=True but FEISHU_USER_ACCESS_TOKEN is not set; "
            "falling back to tenant_access_token (calendar organizer will be the Bot)"
        )

    return {
        "Authorization": f"Bearer {get_tenant_access_token()}",
        "Content-Type": "application/json; charset=utf-8",
    }


if __name__ == "__main__":
    # Quick verification: python -m feishu_mcp.auth
    logging.basicConfig(level=logging.DEBUG)
    try:
        token = get_tenant_access_token()
        print(f"✅ tenant_access_token obtained: {token[:12]}...")
    except Exception as e:
        print(f"❌ Failed: {e}")
