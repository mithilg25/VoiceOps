import json, time
from pathlib import Path
from tools import lookup_order as _lo, create_ticket as _ct

LOG = Path("sample_outputs/tool_log.jsonl")

def _log(entry):
    LOG.parent.mkdir(parents = True, exist_ok = True)
    with LOG.open("a", encoding = "utf-8") as f:
        f.write(json.dumps(entry, default = str)+"\n")

def lookup_order(order_id, verification_value=None, tag=None):
    r = _lo(order_id, verification_value)
    _log({"t": time.time(), "tag": tag, "tool": "lookup_order",
          "args": {"order_id": order_id, "verified": bool(r.get("verified"))}})
    return r

def create_ticket(summary, order_id=None, reason=None, intent=None, tag=None):
    r = _ct(summary=summary, order_id=order_id, reason=reason, intent=intent)
    _log({"t": time.time(), "tag": tag, "tool": "create_ticket",
          "args": {"order_id": order_id, "created": bool(r.get("created"))}})
    return r




