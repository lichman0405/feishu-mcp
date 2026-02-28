"""
tools/documents.py — Cloud Document Tools

Provides:
- create_folder: Create a folder in Drive
- create_document: Create a document in Drive
- write_document_markdown: Write Markdown content to a document (converts to Feishu Blocks)
- upload_file: Upload a file to Drive
- insert_file_block: Insert a downloadable file block at the end of a document
- set_doc_permission: Set member permissions for documents/files (supports users and groups)
- set_doc_public_access: Set the external link access level of a document
- get_share_link: Get the share link of a document
- grant_permission_request: Handle permission requests and grant access to the requester

Feishu Block API reference:
https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document-block/batch_create
"""

import logging
import mimetypes
import os
from pathlib import Path
from typing import Optional

import httpx

from feishu_mcp.auth import get_auth_headers, get_tenant_access_token

logger = logging.getLogger(__name__)
FEISHU_BASE_URL = "https://open.feishu.cn"


# ─────────────────────────────────────────
# Internal HTTP helpers
# ─────────────────────────────────────────

def _post(path: str, payload: dict, params: dict | None = None) -> dict:
    url = f"{FEISHU_BASE_URL}{path}"
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, headers=get_auth_headers(), json=payload, params=params or {})
    # Read body first so Feishu error details are not lost on HTTP 4xx/5xx
    try:
        data = resp.json()
    except Exception:
        resp.raise_for_status()
        raise RuntimeError(f"Feishu API [{path}]: HTTP {resp.status_code}, non-JSON body")
    if data.get("code") != 0:
        raise RuntimeError(
            f"Feishu API error [{path}]: code={data.get('code')}, msg={data.get('msg')}"
        )
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Feishu API [{path}]: HTTP {resp.status_code}, body={data}"
        )
    return data


def _patch(path: str, payload: dict) -> dict:
    url = f"{FEISHU_BASE_URL}{path}"
    with httpx.Client(timeout=15) as client:
        resp = client.patch(url, headers=get_auth_headers(), json=payload)
    try:
        data = resp.json()
    except Exception:
        resp.raise_for_status()
        raise RuntimeError(f"Feishu API [{path}]: HTTP {resp.status_code}, non-JSON body")
    if data.get("code") != 0:
        raise RuntimeError(
            f"Feishu API error [{path}]: code={data.get('code')}, msg={data.get('msg')}"
        )
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Feishu API [{path}]: HTTP {resp.status_code}, body={data}"
        )
    return data
    return data


def _get(path: str, params: dict | None = None) -> dict:
    url = f"{FEISHU_BASE_URL}{path}"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, headers=get_auth_headers(), params=params or {})
    try:
        data = resp.json()
    except Exception:
        resp.raise_for_status()
        raise RuntimeError(f"Feishu API [{path}]: HTTP {resp.status_code}, non-JSON body")
    if data.get("code") != 0:
        raise RuntimeError(
            f"Feishu API error [{path}]: code={data.get('code')}, msg={data.get('msg')}"
        )
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Feishu API [{path}]: HTTP {resp.status_code}, body={data}"
        )
    return data


# ─────────────────────────────────────────
# Document creation & content writing
# ─────────────────────────────────────────

def create_folder(name: str, folder_token: str = "") -> dict:
    """
    Create an empty folder in Drive.

    Args:
        name: Folder name (1–256 bytes)
        folder_token: Parent folder token; empty string means create in the root folder.
                      Can be retrieved from get_root_folder or list_folder.

    Returns:
        dict: {"token": "fldXxx...", "url": "https://feishu.cn/drive/folder/..."
    """
    payload = {
        "name": name,
        "folder_token": folder_token,
    }
    data = _post("/open-apis/drive/v1/files/create_folder", payload)
    result = data.get("data", {})
    logger.info("Folder '%s' created successfully, token=%s", name, result.get("token"))
    return result


def create_document(title: str, folder_token: Optional[str] = None) -> dict:
    """
    Create a document in Drive.

    Args:
        title: Document title (plain text, max 800 characters)
        folder_token: Target folder token; omit to place in the root folder

    Returns:
        dict containing document_id, title, etc.
    """
    payload: dict = {"title": title}
    if folder_token:
        payload["folder_token"] = folder_token

    data = _post("/open-apis/docx/v1/documents", payload)
    doc = data["data"]["document"]
    logger.info("Document created: document_id=%s, title=%s", doc["document_id"], title)
    return doc


def write_document_markdown(document_id: str, markdown_content: str) -> dict:
    """
    Convert Markdown content to Feishu Blocks and write them into a document.

    Supported Markdown elements:
    - # ## ### Headings (→ HeadingBlock)
    - Plain paragraphs (→ TextBlock with paragraph)
    - - * Unordered lists (→ BulletBlock)
    - 1. Ordered lists (→ OrderedBlock)
    - [link text](url) (→ TextBlock with hyperlink)
    - ```code block``` (→ CodeBlock)
    - **bold** (→ bold style)
    - --- (→ DividerBlock)

    Args:
        document_id: Document ID
        markdown_content: Markdown string

    Returns:
        dict containing the list of written blocks
    """
    blocks = _markdown_to_blocks(markdown_content)
    if not blocks:
        logger.warning("write_document_markdown: parsed block list is empty, skipping write")
        return {}

    # Feishu API limits: max 50 children per request, max 3 edits/sec per document.
    # Split into batches of 50 blocks.
    import time as _time

    BATCH_SIZE = 50
    total_created = 0
    last_data: dict = {}
    api_path = f"/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children"

    for batch_start in range(0, len(blocks), BATCH_SIZE):
        batch = blocks[batch_start : batch_start + BATCH_SIZE]
        payload = {
            "children": batch,
            "index": -1,  # append to end of document
        }
        last_data = _post(api_path, payload)
        total_created += len(batch)
        logger.info(
            "Wrote batch %d–%d (%d blocks) to document %s",
            batch_start, batch_start + len(batch), len(batch), document_id,
        )
        # Respect the 3 edits/sec rate limit if more batches remain
        if batch_start + BATCH_SIZE < len(blocks):
            _time.sleep(0.4)

    logger.info("Total %d blocks written to document %s", total_created, document_id)
    return {"blocks_created": total_created, **last_data.get("data", {})}


def _markdown_to_blocks(md: str) -> list[dict]:
    """
    Lightweight Markdown → Feishu Block JSON converter.
    Feishu Block structure reference:
    https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document-block/block-overview
    """
    import re

    blocks = []
    lines = md.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Divider line
        if re.match(r"^-{3,}$", line.strip()):
            blocks.append({"block_type": 22, "divider": {}})  # DividerBlock
            i += 1
            continue

        # Code block
        if line.startswith("```"):
            code_lines = []
            language = line[3:].strip() or "plaintext"
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append({
                "block_type": 14,  # CodeBlock
                "code": {
                    "language": language,
                    "elements": [{"text_run": {"content": "\n".join(code_lines)}}],
                },
            })
            i += 1
            continue

        # Headings H1-H5
        heading_match = re.match(r"^(#{1,5})\s+(.*)", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            # block_type: 3=H1, 4=H2, 5=H3, 6=H4, 7=H5
            block_type = min(level + 2, 7)
            blocks.append({
                "block_type": block_type,
                f"heading{level}": {
                    "elements": [_text_element(text)],
                    "style": {},
                },
            })
            i += 1
            continue

        # Unordered list
        if re.match(r"^[\-\*\+]\s+", line):
            text = re.sub(r"^[\-\*\+]\s+", "", line).strip()
            blocks.append({
                "block_type": 12,  # BulletBlock
                "bullet": {"elements": [_text_element(text)], "style": {}},
            })
            i += 1
            continue

        # Ordered list
        if re.match(r"^\d+\.\s+", line):
            text = re.sub(r"^\d+\.\s+", "", line).strip()
            blocks.append({
                "block_type": 13,  # OrderedBlock
                "ordered": {"elements": [_text_element(text)], "style": {}},
            })
            i += 1
            continue

        # Skip blank lines
        if line.strip() == "":
            i += 1
            continue

        # Plain paragraph
        blocks.append({
            "block_type": 2,  # TextBlock (paragraph)
            "text": {
                "elements": [_text_element(line)],
                "style": {},
            },
        })
        i += 1

    return blocks


def _text_element(text: str) -> dict:
    """
    Convert text containing **bold** and [link](url) markup into a Feishu TextElement.
    Simplified: the entire text is handled as a single text_run (with link extraction).
    """
    import re

    # Link: [text](url)
    link_match = re.search(r"\[([^\]]+)\]\(([^)]+)\)", text)
    if link_match:
        link_text = link_match.group(1)
        link_url = link_match.group(2)
        return {
            "text_run": {
                "content": link_text,
                "text_element_style": {
                    "link": {"url": link_url},
                },
            }
        }

    # Bold: **text**
    bold_match = re.fullmatch(r"\*\*(.+)\*\*", text.strip())
    if bold_match:
        return {
            "text_run": {
                "content": bold_match.group(1),
                "text_element_style": {"bold": True},
            }
        }

    return {"text_run": {"content": text}}


# ─────────────────────────────────────────
# File upload
# ─────────────────────────────────────────

def upload_file(
    file_path: str,
    file_name: Optional[str] = None,
    parent_token: Optional[str] = None,
    parent_type: str = "explorer",
) -> dict:
    """
    Upload a file to Feishu Drive (≤20 MB uses simple upload; >20 MB uses multipart upload).

    Args:
        file_path: Local file path
        file_name: Display name in Drive; defaults to the local filename
        parent_token: Target folder token; omit to place in the root folder
        parent_type: "explorer" (My Drive, default) | "wiki_node" | ...

    Returns:
        dict containing file_token
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    name = file_name or path.name
    size = path.stat().st_size
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"

    if size <= 20 * 1024 * 1024:
        return _upload_simple(path, name, size, mime, parent_token, parent_type)
    else:
        return _upload_multipart(path, name, size, mime, parent_token, parent_type)


def _upload_simple(
    path: Path, name: str, size: int, mime: str,
    parent_token: Optional[str], parent_type: str
) -> dict:
    """Simple upload for files ≤20 MB."""
    token = get_tenant_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    form_data = {
        "file_name": name,
        "parent_type": parent_type,
        "size": str(size),
    }
    if parent_token:
        form_data["parent_node"] = parent_token

    with open(path, "rb") as f:
        files = {"file": (name, f, mime)}
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{FEISHU_BASE_URL}/open-apis/drive/v1/files/upload_all",
                headers=headers,
                data=form_data,
                files=files,
            )
            resp.raise_for_status()

    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"File upload failed: code={data['code']}, msg={data.get('msg')}")

    file_token = data["data"]["file_token"]
    logger.info("File uploaded successfully: %s → file_token=%s", name, file_token)
    return data["data"]


def _upload_multipart(
    path: Path, name: str, size: int, mime: str,
    parent_token: Optional[str], parent_type: str
) -> dict:
    """Multipart upload for files >20 MB (prepare → upload parts → finish)."""
    token = get_tenant_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    # Step 1: prepare
    prepare_payload: dict = {
        "file_name": name,
        "parent_type": parent_type,
        "size": size,
    }
    if parent_token:
        prepare_payload["parent_node"] = parent_token

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{FEISHU_BASE_URL}/open-apis/drive/v1/files/upload_prepare",
            headers=headers,
            json=prepare_payload,
        )
        resp.raise_for_status()
    prep_data = resp.json()
    if prep_data.get("code") != 0:
        raise RuntimeError(f"upload_prepare failed: {prep_data}")

    upload_id = prep_data["data"]["upload_id"]
    block_size = prep_data["data"]["block_size"]
    block_num = prep_data["data"]["block_num"]

    # Step 2: upload parts
    upload_headers = {"Authorization": f"Bearer {token}"}
    with open(path, "rb") as f:
        for seq in range(block_num):
            chunk = f.read(block_size)
            with httpx.Client(timeout=120) as client:
                resp = client.post(
                    f"{FEISHU_BASE_URL}/open-apis/drive/v1/files/upload_part",
                    headers=upload_headers,
                    data={
                        "upload_id": upload_id,
                        "seq": str(seq),
                        "size": str(len(chunk)),
                    },
                    files={"file": (name, chunk, mime)},
                )
                resp.raise_for_status()
            logger.debug("Uploaded part %d/%d", seq + 1, block_num)

    # Step 3: finish
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{FEISHU_BASE_URL}/open-apis/drive/v1/files/upload_finish",
            headers=headers,
            json={"upload_id": upload_id, "block_num": block_num},
        )
        resp.raise_for_status()
    finish_data = resp.json()
    if finish_data.get("code") != 0:
        raise RuntimeError(f"upload_finish failed: {finish_data}")

    file_token = finish_data["data"]["file_token"]
    logger.info("Multipart upload complete: %s → file_token=%s", name, file_token)
    return finish_data["data"]


def upload_file_and_share(
    file_path: str,
    file_name: Optional[str] = None,
    parent_token: Optional[str] = None,
) -> dict:
    """
    Upload a local file to Feishu Drive, automatically set organization-wide read permission,
    and return a directly shareable URL.

    Use case: After an Agent downloads a file locally, complete upload → set permission → get link
    in one step, then call send_message to share the link in a group.

    Args:
        file_path: Absolute path to the local file
        file_name: Display name in Drive; defaults to the local filename
        parent_token: Target folder token (optional)

    Returns:
        dict: {
            "file_token": "...",   # Drive file token
            "file_name": "...",    # Actual filename
            "share_url": "...",    # Shareable URL accessible within the organization
        }
    """
    # 1. Upload
    result = upload_file(file_path, file_name, parent_token)
    file_token = result["file_token"]
    actual_name = file_name or Path(file_path).name

    # 2. Grant organization-wide read access
    set_doc_public_access(file_token, "file", "tenant_readable")

    # 3. Get share link
    share_url = get_share_link(file_token, "file")

    logger.info("File uploaded and shared: %s → %s", actual_name, share_url)
    return {
        "file_token": file_token,
        "file_name": actual_name,
        "share_url": share_url,
    }


# ─────────────────────────────────────────
# File block insertion
# ─────────────────────────────────────────

def insert_file_block(
    document_id: str,
    file_token: str,
    file_name: str,
) -> dict:
    """
    Insert a downloadable file block at the end of a document.

    Args:
        document_id: Document ID
        file_token: Token of the already-uploaded file
        file_name: Display name of the file in the document

    Returns:
        dict containing the written block information
    """
    payload = {
        "children": [
            {
                "block_type": 23,  # FileBlock
                "file": {
                    "token": file_token,
                    "name": file_name,
                },
            }
        ],
        "index": -1,
    }
    data = _post(
        f"/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children",
        payload,
    )
    logger.info("File block inserted: document_id=%s, file=%s", document_id, file_name)
    return data.get("data", {})


# ─────────────────────────────────────────
# Permission management
# ─────────────────────────────────────────

def set_doc_permission(
    file_token: str,
    file_type: str,
    member_open_ids: list[str] | None = None,
    chat_ids: list[str] | None = None,
    perm_type: str = "view",
) -> list[dict]:
    """
    Batch-add member permissions to a document/file, supporting users (openid) and groups (openchat).

    Args:
        file_token: Token of the document/file (document_id or file_token)
        file_type: "doc" | "docx" | "file" | "bitable" | "sheet"
        member_open_ids: List of user open_ids to authorize (can be used together with chat_ids)
        chat_ids: List of group chat_ids to authorize (starting with oc_)
                  Note: when using tenant_access_token, the bot must already be in the group,
                  otherwise the API returns error 1063003.
        perm_type: "view" (read-only) | "edit" (editable) | "full_access" (full control)

    Returns:
        list of authorization results
    """
    results = []

    def _add_member(member_type: str, member_id: str) -> None:
        payload = {
            "member_type": member_type,
            "member_id": member_id,
            "perm": perm_type,
        }
        data = _post(
            f"/open-apis/drive/v1/permissions/{file_token}/members",
            payload,
            params={"type": file_type},
        )
        results.append(data.get("data", {}))

    for uid in (member_open_ids or []):
        _add_member("openid", uid)

    for cid in (chat_ids or []):
        _add_member("openchat", cid)

    logger.info(
        "Document %s granted %s permission: %d user(s), %d group(s)",
        file_token, perm_type,
        len(member_open_ids or []), len(chat_ids or []),
    )
    return results


def set_doc_public_access(
    file_token: str,
    file_type: str,
    access_level: str = "tenant_readable",
) -> dict:
    """
    Set the public access level of a document for tenant members or external users.

    Args:
        file_token: Document token
        file_type: "doc" | "docx" | "file" etc.
        access_level:
          - "off": Disable link sharing
          - "tenant_readable": Anyone in the organization with the link can view (recommended for group sharing)
          - "tenant_editable": Anyone in the organization with the link can edit
          - "anyone_readable": Anyone on the internet with the link can view
          - "anyone_editable": Anyone on the internet with the link can edit

    Returns:
        dict with the updated public access settings
    """
    payload = {
        "link_share_entity": access_level,
        "external_access_entity": "open" if access_level.startswith("anyone") else "closed",
    }
    data = _patch(
        f"/open-apis/drive/v1/permissions/{file_token}/public?type={file_type}",
        payload,
    )
    logger.info("Document %s public access set to: %s", file_token, access_level)
    return data.get("data", {})


def get_share_link(file_token: str, file_type: str) -> str:
    """
    Get the share link for a document or file.

    Args:
        file_token: Document/file token
        file_type: "doc" | "docx" | "file" etc.

    Returns:
        Shareable URL string
    """
    # Try to get share link via API
    try:
        data = _post(
            f"/open-apis/drive/v1/permissions/{file_token}/public_permission_meta",
            payload={},
            params={"type": file_type},
        )
        url = data.get("data", {}).get("url", "")
        if url:
            logger.info("Document %s share link: %s", file_token, url)
            return url
    except Exception:
        pass

    # Fallback: construct standard link
    type_path = {"docx": "docx", "doc": "docs", "sheet": "sheets", "bitable": "base", "file": "file"}.get(file_type, "docx")
    url = f"https://feishu.cn/{type_path}/{file_token}"
    logger.info("Document %s share link (constructed): %s", file_token, url)
    return url


def grant_permission_request(
    file_token: str,
    file_type: str,
    user_open_id: str,
    perm_type: str = "view",
) -> dict:
    """
    Handle a permission request event: grant the specified permission to the requester.
    Typically called from a Webhook event handler.

    Args:
        file_token: Document/file token
        file_type: File type
        user_open_id: open_id of the requester
        perm_type: Permission type to grant; default is "view" (read-only)

    Returns:
        Authorization result
    """
    results = set_doc_permission(file_token, file_type, [user_open_id], perm_type)
    return results[0] if results else {}
