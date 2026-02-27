"""
scripts/start_webhook.py
One-click startup for the Webhook server + display ngrok public URL

Usage:
  python scripts/start_webhook.py

Prerequisites:
  1. ngrok installed (https://ngrok.com/download) and available on PATH
     OR: pip install pyngrok
  2. FEISHU_VERIFICATION_TOKEN set in .env (optional; signature verification is skipped if absent)

After startup:
  - Copy the printed ngrok URL
  - In the Feishu developer console, go to Events & Callbacks → Event Config
    and enter <ngrok_url>/webhook/feishu
  - Feishu will send a URL Challenge, which is verified automatically
"""

import subprocess
import sys
import time
import threading
import os

WEBHOOK_PORT = 8080
WEBHOOK_PATH = "/webhook/feishu"


def start_uvicorn():
    """Start the uvicorn FastAPI server as a background process."""
    cmd = [
        sys.executable, "-m", "uvicorn",
        "feishu_mcp.webhook.handler:app",
        "--host", "0.0.0.0",
        "--port", str(WEBHOOK_PORT),
        "--log-level", "info",
    ]
    proc = subprocess.Popen(cmd, cwd=os.path.join(os.path.dirname(__file__), ".."))
    return proc


def get_ngrok_url():
    """Retrieve the public URL of the current ngrok tunnel."""
    try:
        import httpx
        # ngrok local management API
        r = httpx.get("http://127.0.0.1:4040/api/tunnels", timeout=5)
        tunnels = r.json().get("tunnels", [])
        for t in tunnels:
            if t.get("proto") == "https":
                return t["public_url"]
        for t in tunnels:
            return t.get("public_url", "")
    except Exception:
        return None


def start_ngrok_pyngrok():
    """Start an ngrok tunnel using pyngrok."""
    try:
        from pyngrok import ngrok
        tunnel = ngrok.connect(WEBHOOK_PORT, "http")
        return tunnel.public_url.replace("http://", "https://")
    except ImportError:
        return None


def main():
    print("=" * 60)
    print("  Feishu MCP Webhook Service Launcher")
    print("=" * 60)

    # Switch to project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    sys.path.insert(0, "src")

    # 1. Start uvicorn
    print("\n[1] Starting FastAPI Webhook server (port:", WEBHOOK_PORT, ")...")
    server_proc = start_uvicorn()
    time.sleep(2)  # Wait for server to be ready

    # 2. Start ngrok
    print("[2] Starting ngrok tunnel...")
    public_url = start_ngrok_pyngrok()

    if not public_url:
        # Try calling the ngrok command directly
        ngrok_proc = subprocess.Popen(
            ["ngrok", "http", str(WEBHOOK_PORT), "--log=stdout"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("    Waiting for ngrok to establish tunnel...")
        time.sleep(3)
        public_url = get_ngrok_url()

    if not public_url:
        print("\n  ⚠️  ngrok not detected. Please obtain a public URL manually:")
        print("  Option 1: pip install pyngrok && re-run this script")
        print("  Option 2: Download ngrok (https://ngrok.com/download), run: ngrok http 8080")
        print(f"\n  Webhook server is running locally: http://localhost:{WEBHOOK_PORT}{WEBHOOK_PATH}")
        print("\n  Press Ctrl+C to stop")
        try:
            server_proc.wait()
        except KeyboardInterrupt:
            server_proc.terminate()
        return

    callback_url = f"{public_url}{WEBHOOK_PATH}"

    print("\n" + "=" * 60)
    print("  ✅ Service started successfully!")
    print("=" * 60)
    print(f"\n  📍 Local address: http://localhost:{WEBHOOK_PORT}{WEBHOOK_PATH}")
    print(f"  🌐 Public address (paste into Feishu console):")
    print(f"\n     {callback_url}\n")
    print("=" * 60)
    print("\n  Steps:")
    print("  1. Copy the public address above")
    print("  2. Go to Feishu Open Platform → Events & Callbacks → Event Config")
    print("  3. Paste the URL into the 'Request URL' field")
    print("  4. Click 'Save' — Feishu will auto-complete the URL Challenge verification")
    print("  5. Under 'Subscribed Events' add: im.message.receive_v1")
    print("  6. Publish the app version")
    print("\n  ✅ After configuration, @mention the bot to trigger events!")
    print("\n  Press Ctrl+C to stop\n")

    try:
        server_proc.wait()
    except KeyboardInterrupt:
        print("\n  Stopping service...")
        server_proc.terminate()


if __name__ == "__main__":
    main()
