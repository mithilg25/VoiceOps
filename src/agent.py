import json, re
from .llm import chat
from .rag import retrieve, format_context
from .data import get_product, search_products, check_pincode, add_business_days, business_days_between
from . import tools_wrapper

SYSTEM_BASE = """You are ZentroMart's AI support assistant.

TODAY = 2026-10-20. Use this date for every calculation; ignore your own clock.
BUSINESS DAYS = Monday–Saturday, skipping the dates in data/holidays.csv.
Return windows count in CALENDAR days from delivery. Refund timelines count in BUSINESS days from initiation.

HARD RULES
1. In your first reply, introduce yourself as an AI assistant.
2. Reply in the customer's language. Keep replies to 2–3 short sentences. Ask one question at a time.
3. Ground every answer in the RETRIEVED DOCUMENTS (below) or in tool results. If neither covers the question, say you don't know and offer to connect a colleague. NEVER invent policies, dates, or amounts.
4. Precedence: current policy > agent_guide > help > FAQ > marketing. Superseded documents apply ONLY to the case their successor names.
5. NEVER share order details until identity is verified. Ask for the order ID, then ONE of: phone last-4 OR delivery pincode. Max ONE retry. If both attempts fail, refuse order details.
6. Escalate when ANY of these is true: (a) damaged/defective/wrong item worth > ₹10,000; (b) suspected fraud; (c) legal action; (d) contacts_last_7_days >= 2; (e) refund more than 3 business days past its max timeline; (f) customer asks for a human; (g) safety risk. Before escalating, call create_ticket().
7. Never claim an action you did not take. There is NO cancel tool — guide the customer to My Orders.

CRITICAL FORMATTING RULES:
- When quoting a date, use the format "27 October 2026". You may include the ISO date in brackets if helpful.
- If you mention a number or currency, you MUST use digits (e.g., 79, ₹49, 48).
- For refund timelines: Check [REF-2], find the number of days, and use the `add_business_days` tool to calculate the exact date. You MUST include this exact date in your reply.
"""

SYSTEM_VOICE = """
VOICE CHANNEL — reply will be spoken. Spell dates with the month name ("the 27th of October").
Group order IDs in fours ("six nine five two, zero eight six seven"). Say amounts in rupees.
Keep to two or three short sentences.
"""

TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "lookup_order",
        "description": "Look up a synthetic ZentroMart order. Without verification_value, returns only a verification prompt. Pass a 4-digit phone suffix OR a 6-digit delivery pincode to unlock details.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": ["string", "null"]},
            "verification_value": {"type": "string", "description": "4-digit phone suffix OR 6-digit pincode. Omit on first call."}
        }, "required": ["order_id"]}
    }},
    {"type": "function", "function": {
        "name": "create_ticket",
        "description": "Create a human-handover ticket. Include the issue, intent, order ID, what was checked, and the escalation reason.",
        "parameters": {"type": "object", "properties": {
            "summary": {"type": "string"}, "order_id": {"type": "string"},
            "reason": {"type": "string"}, "intent": {"type": "string"}
        }, "required": ["summary"]}
    }},
    {"type": "function", "function": {
        "name": "get_product",
        "description": "Look up a specific SKU in the catalog.",
        "parameters": {"type": "object", "properties": {"sku": {"type": "string"}}, "required": ["sku"]}
    }},
    {"type": "function", "function": {
        "name": "search_products",
        "description": "Search the catalog by product title or brand.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    }},
    {"type": "function", "function": {
        "name": "check_pincode",
        "description": "Check if a pincode is serviceable and whether COD / Express are available.",
        "parameters": {"type": "object", "properties": {"pincode": {"type": "string"}}, "required": ["pincode"]}
    }},
    {"type": "function", "function": {
        "name": "add_business_days",
        "description": "Return the date n business days after a given ISO date. Use this to calculate exact refund dates.",
        "parameters": {"type": "object", "properties": {"start_iso": {"type": "string"}, "n": {"type": "integer"}}, "required": ["start_iso", "n"]}
    }},
    {"type": "function", "function": {
        "name": "business_days_between",
        "description": "Count business days between two ISO dates (start excluded, end included). Use for overdue checks.",
        "parameters": {"type": "object", "properties": {"start_iso": {"type": "string"}, "end_iso": {"type": "string"}}, "required": ["start_iso", "end_iso"]}
    }},
]

class Agent:
    def __init__(self, voice: bool = False, tag: str | None = None):
        self.voice = voice
        self.tag   = tag or "default"
        system = SYSTEM_BASE + (SYSTEM_VOICE if voice else "")
        self.history = [{"role": "system", "content": system}]
        self.verified_orders   = {}
        self.verify_attempts   = {}  # FIXED: was self.verified_attempts
        self.last_sources      = []

    def _query(self) -> str:
        # IMPROVEMENT: Weight the current message higher. Only use history for short follow-ups.
        user_msgs = [m["content"] for m in self.history if m["role"] == "user"]
        if not user_msgs: return ""
        last_msg = user_msgs[-1]
        
        if len(last_msg.split()) < 5 and len(user_msgs) > 1:
            return user_msgs[-2] + " " + last_msg
        return last_msg

    def _retrieve(self) -> tuple[str, list[str]]:
        hits = list(retrieve(self._query(), k=6))
        chunks = [c for c, _ in hits]
        self.last_sources = [c["section_id"] for c in chunks]
        return format_context(chunks), self.last_sources

    def respond(self, user_msg: str):
        # FIXED: Append the user message FIRST, so retrieval actually sees it.
        self.history.append({"role": "user", "content": user_msg})
        
        ctx_text, source_ids = self._retrieve()

        turn_messages = self.history + [{
            "role": "system",
            "content": f"RETRIEVED DOCUMENTS for this turn:\n\n{ctx_text}"
        }]

        for _ in range(8):
            resp = chat(turn_messages, tools=TOOLS_SCHEMA)
            msg = resp.choices[0].message
            turn_messages.append(msg)

            if not msg.tool_calls:
                self.history.append({"role": "assistant", "content": msg.content})
                return msg.content, {"sources": source_ids}

            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments or "{}")
                result = self._dispatch(name, args)
                turn_messages.append({
                    "role": "tool", "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str)
                })

        fallback = "Sorry, I'm having trouble with that. Let me connect you to a colleague."
        self.history.append({"role": "assistant", "content": fallback})
        return fallback, {"sources": source_ids}

    def _dispatch(self, name: str, args: dict):
        if name == "lookup_order":
            oid = re.sub(r"\D", "", args.get("order_id", ""))
            vv  = args.get("verification_value")
            if vv is None or str(vv).strip() == "":
                return tools_wrapper.lookup_order(oid, tag=self.tag)

            used = self.verify_attempts.get(oid, 0)
            if used >= 2:
                return {"verified": False, "message": "Verification already failed twice. Do not share order details."}
            
            result = tools_wrapper.lookup_order(oid, verification_value=str(vv), tag=self.tag)
            if not result.get("verified"):
                self.verify_attempts[oid] = used + 1
            else:
                self.verified_orders[oid] = result
                self.history.append({"role": "system", "content": f"Order {oid} is now VERIFIED. You may share its details."})
            return result

        # FIXED: Removed the accidental leading space in "create_ticket"
        if name == "create_ticket":
            # FIXED: Re-wrote the broken parentheses
            return tools_wrapper.create_ticket(
                summary=args.get("summary", ""),
                order_id=args.get("order_id"),
                reason=args.get("reason"),
                intent=args.get("intent"),
                tag=self.tag
            )
            
        if name == "get_product":         return get_product(args.get("sku", ""))
        if name == "search_products":     return search_products(args.get("query", ""))
        if name == "check_pincode":       return check_pincode(args.get("pincode", ""))
        if name == "add_business_days":
            return {"date": add_business_days(args.get("start_iso", ""), int(args.get("n", 0)))}
        if name == "business_days_between":
            return {"days": business_days_between(args.get("start_iso", ""), args.get("end_iso", ""))}

        return {"error": f"unknown tool {name}"}  





                                        
