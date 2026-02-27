"""
tests/test_documents.py — unit tests for the cloud document tool
"""
import pytest
from feishu_mcp.tools.documents import _markdown_to_blocks


def test_markdown_heading():
    """# Heading should be converted to HeadingBlock (block_type=3)."""
    blocks = _markdown_to_blocks("# Level 1 Heading")
    assert len(blocks) == 1
    assert blocks[0]["block_type"] == 3  # H1


def test_markdown_paragraph():
    """Plain paragraph should be converted to TextBlock (block_type=2)."""
    blocks = _markdown_to_blocks("This is a plain paragraph")
    assert blocks[0]["block_type"] == 2


def test_markdown_bullet_list():
    """Unordered list should be converted to BulletBlock (block_type=12)."""
    blocks = _markdown_to_blocks("- Item A\n- Item B")
    assert all(b["block_type"] == 12 for b in blocks)
    assert len(blocks) == 2


def test_markdown_ordered_list():
    """Ordered list should be converted to OrderedBlock (block_type=13)."""
    blocks = _markdown_to_blocks("1. First item\n2. Second item")
    assert all(b["block_type"] == 13 for b in blocks)


def test_markdown_code_block():
    """Code block should be converted to CodeBlock (block_type=14)."""
    md = "```python\nprint('hello')\n```"
    blocks = _markdown_to_blocks(md)
    assert blocks[0]["block_type"] == 14
    assert "print" in blocks[0]["code"]["elements"][0]["text_run"]["content"]


def test_markdown_divider():
    """--- should be converted to DividerBlock (block_type=22)."""
    blocks = _markdown_to_blocks("---")
    assert blocks[0]["block_type"] == 22


def test_markdown_link():
    """Markdown link should be extracted as a text_run with link style."""
    blocks = _markdown_to_blocks("[Feishu Official](https://feishu.cn)")
    elem = blocks[0]["text"]["elements"][0]
    assert elem["text_run"]["text_element_style"]["link"]["url"] == "https://feishu.cn"
    assert elem["text_run"]["content"] == "Feishu Official"


def test_markdown_mixed():
    """Mixed Markdown should correctly parse all element types."""
    md = """# Report Title

This is a summary paragraph.

## References

- [Paper One](https://example.com/paper1)
- [Paper Two](https://example.com/paper2)

---

```python
result = 42
```
"""
    blocks = _markdown_to_blocks(md)
    types = [b["block_type"] for b in blocks]
    assert 3 in types   # H1
    assert 4 in types   # H2
    assert 2 in types   # paragraph
    assert 12 in types  # bullet
    assert 22 in types  # divider
    assert 14 in types  # code