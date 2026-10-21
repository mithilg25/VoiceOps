import json, re
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from src.config import EMBED_MODEL

KB_DIR = Path("kb")
OUT_DIR = Path("src/rag_index")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FM_RE  = re.compile(r"^---\n(.*?)\n---\n", re.S)
SEC_RE = re.compile(r"^## \[([A-Za-z0-9\-\.]+)\]\s*(.*)$", re.M)

def parse_doc(path: Path) -> list[dict]:
    text = path.read_text(encoding = "utf-8")
    m = FM_RE.match(text)
    fm, body_start = {}, 0
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.split()] = v.strip()
        body_start = m.end()
    body = text[body_start:]
    matches = list(SEC_RE.finditer(body))            
