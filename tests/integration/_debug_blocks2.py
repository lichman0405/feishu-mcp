import sys, os
sys.path.insert(0, 'src')
os.environ['PYTHONIOENCODING'] = 'utf-8'
import httpx, json
from feishu_mcp.auth import get_auth_headers
from feishu_mcp.tools.documents import create_document, _markdown_to_blocks

doc = create_document('Block Debug 3')
doc_id = doc['document_id']
print('doc_id:', doc_id)

MD = """# Heading

## Level 2

Plain paragraph.

1. Ordered one
2. Ordered two

- Unordered

```python
code
```

---

End
"""
blocks = _markdown_to_blocks(MD)
print(f'Total {len(blocks)} blocks')

errs = []
for i, blk in enumerate(blocks):
    r = httpx.post(
        f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children',
        headers=get_auth_headers(),
        json={'children': [blk], 'index': -1}
    )
    d = r.json()
    if d.get('code') == 0:
        print(f'Block {i} type={blk["block_type"]} OK')
    else:
        print(f'Block {i} type={blk["block_type"]} FAIL code={d["code"]} msg={d.get("msg")}')
        print('  Body:', json.dumps(blk, ensure_ascii=False))
        errs.append((i, blk, d))

if not errs:
    print('\nAll individual blocks OK; now test batch...')
    doc2 = create_document('Block Batch Test')
    doc_id2 = doc2['document_id']
    r2 = httpx.post(
        f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id2}/blocks/{doc_id2}/children',
        headers=get_auth_headers(),
        json={'children': blocks, 'index': -1}
    )
    d2 = r2.json()
    print('Batch result:', d2.get('code'), d2.get('msg'))
    if d2.get('code') == 0:
        print('Batch OK')