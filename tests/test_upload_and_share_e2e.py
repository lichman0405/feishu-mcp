"""
Manual E2E test: upload_file_and_share -> send_message
"""
import os
import tempfile

from feishu_mcp.tools.documents import upload_file_and_share
from feishu_mcp.tools.messages import send_message

CHAT_ID = "oc_2ed2973a91574e4033c7eac08ffe8c6e"


def main():
    # Step 1: Create a local test file
    tmp = tempfile.NamedTemporaryFile(
        suffix=".txt", delete=False, mode="w", encoding="utf-8"
    )
    tmp.write("feishu-miqroera-mcp upload_file_and_share E2E test file\nTimestamp: 2026-02-27")
    tmp.close()

    print("=== Step 1: upload_file_and_share ===")
    result = upload_file_and_share(tmp.name, "mcp_e2e_test.txt")
    os.unlink(tmp.name)
    print("file_token:", result["file_token"])
    print("file_name :", result["file_name"])
    print("share_url :", result["share_url"])

    print()
    print("=== Step 2: Send share link to group ===")
    import json
    share_url = result["share_url"]
    content = json.dumps({"text": f"[MCP e2e test] File uploaded, share link:\n{share_url}"})
    send_result = send_message("chat_id", CHAT_ID, content)
    print("send result:", send_result)


if __name__ == "__main__":
    main()