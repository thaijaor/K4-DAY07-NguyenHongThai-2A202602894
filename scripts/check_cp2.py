import csv
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

D = Path("data/ecommerce")
REQ = ["doc_id", "title", "source_url", "retrieved_at", "document_version", "audience"]
mds = sorted(D.glob("*.md"))
rows = list(csv.DictReader(open(D / "sources.csv", encoding="utf-8"))) if (D / "sources.csv").exists() else []
ids, auds = [], {}

print(f"{'FILE NAME':45} {'STATUS':15} {'AUDIENCE':10} {'DOC_ID'}")
print("-" * 80)
for p in mds:
    content = p.read_text(encoding="utf-8")
    frontmatter = content.split("---")[1] if "---" in content else ""
    fm = {}
    for line in frontmatter.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'").split("#")[0].strip()
    
    doc_id = fm.get("doc_id")
    ids.append(doc_id)
    aud = fm.get("audience")
    auds[aud] = auds.get(aud, 0) + 1
    
    missing = [k for k in REQ if k not in fm]
    id_match = (doc_id == p.stem)
    if not missing and id_match:
        status = "OK"
    else:
        status = f"ERR (missing: {missing}, id_match: {id_match})"
    
    print(f"{p.name:45} {status:15} {str(aud):10} {str(doc_id)}")

print("-" * 80)
print("Số file .md      :", len(mds), "(yêu cầu: 5-10)")
csv_ids = sorted([r["doc_id"] for r in rows])
file_ids = sorted([i for i in ids if i])
is_khop = (csv_ids == file_ids)
print("sources.csv      :", "KHỚP" if is_khop else f"LỆCH (CSV có {len(csv_ids)}, files có {len(file_ids)})")
if not is_khop:
    print("  + Có trong CSV nhưng không có trong file:", set(csv_ids) - set(file_ids))
    print("  + Có trong file nhưng không có trong CSV:", set(file_ids) - set(csv_ids))
print("Phân bố audience :", auds)
