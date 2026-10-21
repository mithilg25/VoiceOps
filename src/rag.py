import json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from .config import EMBED_MODEL

_DIR = Path(__file__).resolve().parent / "rag_index"
_chunks = json.loads((_DIR / "chunks.json").read_text(encoding="utf-8"))
_embs   = np.load(_DIR / "embeddings.npy")
_model  = SentenceTransformer(EMBED_MODEL)

PRECEDENCE = {"policy": 4, "agent_guide": 3, "help": 2, "faq": 1, "marketing": 0, "meta": 0}

def retrieve(query: str, k: int = 6):
    q = _model.encode([query], normalize_embeddings=True)[0]
    sims = _embs @ q
    adj = sims.copy()
    for i, c in enumerate(_chunks):
        if c["status"] == "superseded":
            adj[i] *= 0.7
        adj[i] += 0.02 * PRECEDENCE.get(c["doc_type"], 0)
    for i in np.argsort(-adj)[:k]:
        yield _chunks[i], float(adj[i])

def format_context(chunk_list) -> str:
    parts = []
    for c in chunk_list:
        parts.append(f"[{c['section_id']}] ({c['doc_type']}, {c['status']}, from {c['effective_from']})\n{c['text']}")
    return "\n\n---\n\n".join(parts)
