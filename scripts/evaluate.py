#!/usr/bin/env python3
import argparse, json, re, sys, time
from pathlib import Path
import pandas as pd

# 1. Fix Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.agent import Agent
from src.tools_wrapper import LOG

def _score(reply: str, must_in: str, must_not: str) -> bool:
    r = reply.lower()
    ok_in = all(any(alt.strip().lower() in r for alt in fact.split("/"))
                for fact in re.split(r"\s*;\s*", must_in) if fact.strip())
    ok_not = not any(bad.strip().lower() in r for bad in re.split(r"\s*;\s*", must_not) if bad.strip())
    return ok_in and ok_not

def run_questions(col: str, out_csv: str):
    # 2. Use absolute paths for data
    df = pd.read_csv(ROOT_DIR / "practice/questions.csv", dtype=str, keep_default_na=False)
    rows, correct = [], 0
    for _, r in df.iterrows():
        agent = Agent(tag=f"q_{r['id']}")
        reply, meta = agent.respond(r[col])
        time.sleep(4)
        ok = _score(reply, r["must_include"], r["must_not_include"])
        correct += ok
        rows.append({"id": r["id"], "ok": ok, "reply": reply, "sources": meta.get("sources", [])})
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print(f"[{col}]  {correct}/{len(df)} = {correct/len(df):.1%}")

def run_conversations(out_json: str):
    df = pd.read_csv(ROOT_DIR / "practice/conversations.csv", dtype=str, keep_default_na=False)
    per_conv, ok_convs = {}, 0
    
    for cid, grp in df.groupby("conversation_id", sort=False):
        tag = f"conv_{cid}"
        agent = Agent(tag=tag)
        grp = grp.sort_values("turn", key=lambda s: s.astype(int))
        turns = []
        for _, r in grp.iterrows():
            reply, meta = agent.respond(r["customer_message"])
            time.sleep(4)
            ok = _score(reply, r["must_include"], r["must_not_include"])
            turns.append({"turn": int(r["turn"]), "ok": ok, "reply": reply, "sources": meta.get("sources", [])})

        calls = []
        if LOG.exists():
            for line in LOG.read_text(encoding="utf-8").splitlines():
                e = json.loads(line)
                if e.get("tag") == tag: calls.append(e["tool"])

        all_ok = all(t["ok"] for t in turns)
        if all_ok: ok_convs += 1
        
        per_conv[cid] = {
            "turns": turns, "all_ok": all_ok,
            "expected_tool_calls": [c for c in grp["expected_tool_calls"] if c],
            "actual_tool_calls": calls,
        }

    print(f"[conversations]  {ok_convs}/{len(per_conv)} fully correct")
    Path(out_json).write_text(json.dumps(per_conv, indent=2, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["all", "question", "asr", "conv"], default="all")
    a = ap.parse_args()
    
    out_dir = ROOT_DIR / "sample_outputs"
    out_dir.mkdir(exist_ok=True)
    
    if a.mode in ("all", "question"): run_questions("question", out_dir / "eval_questions.csv")
    if a.mode in ("all", "asr"):      run_questions("asr_text", out_dir / "eval_asr.csv")
    if a.mode in ("all", "conv"):     run_conversations(out_dir / "eval_conversations.json")