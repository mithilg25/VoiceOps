
import json, re, sys
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer


ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.config import EMBED_MODEL

# 2. Use absolute paths
KB_DIR  = ROOT_DIR / "kb"
OUT_DIR = ROOT_DIR / "src" / "rag_index"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FM_RE  = re.compile(r"^---\n(.*?)\n---\n", re.S)
SEC_RE = re.compile(r"^## \[([A-Za-z0-9\-\.]+)\]\s*(.*)$", re.M)

def parse_doc(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    fm, body_start = {}, 0
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
        body_start = m.end()
    body = text[body_start:]
    matches = list(SEC_RE.finditer(body))
    chunks = []
    for i, sm in enumerate(matches):
        start = sm.start()
        end   = matches[i+1].start() if i+1 < len(matches) else len(body)
        chunks.append({
            "doc_id": fm.get("doc_id", ""), "doc_type": fm.get("doc_type", ""),
            "status": fm.get("status", ""), "effective_from": fm.get("effective_from", ""),
            "section_id": sm.group(1), "title": sm.group(2).strip(),
            "text": body[start:end].strip(), "source": path.name,
        })
    return chunks

def main():
    all_chunks = []
    for p in sorted(KB_DIR.glob("*.md")):
        all_chunks += parse_doc(p)
    print(f"{len(all_chunks)} chunks from {len(list(KB_DIR.glob('*.md')))} docs")

    model = SentenceTransformer(EMBED_MODEL)
    texts = [f"[{c['section_id']}] {c['title']}\n{c['text']}" for c in all_chunks]
    embs  = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    np.save(OUT_DIR / "embeddings.npy", embs)
    (OUT_DIR / "chunks.json").write_text(json.dumps(all_chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote index files to {OUT_DIR}")

if __name__ == "__main__":
    main()