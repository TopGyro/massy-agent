"""
Massy Agent Loop — OpenAI tool-calling agent for supply chain queries.
"""

import os
import json
import logging
from openai import OpenAI

import sys
sys.path.insert(0, "/app")
from tools.massy_tools import TOOLS
from tools.schemas import TOOL_SCHEMAS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("massy.agent")

MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_STEPS = 8

SYSTEM_PROMPT = """You are the Massy Supply Chain Intelligence Agent serving operations
managers across Massy Group's Caribbean network — Trinidad, Tobago, Barbados, Guyana, and St. Lucia.

You have seven tools for inventory, demand forecasting, warehouse optimisation, route planning,
sustainability, network graph analysis, and shipping compliance.

Chain tools logically:
- Reorder questions: inventory then demand forecast then routes then sustainability
- Warehouse questions: warehouse optimizer then sustainability
- Cross-border shipments: always run shipping compliance
- Network risk questions: analyze supply network

Always quantify in TTD, km, and kg CO2. Be specific to the Caribbean context.
After gathering tool results, give a clear, structured recommendation."""

# Convert tool schemas to OpenAI tools format
def _to_openai_tools(schemas):
    return [{"type": "function", "function": s["function"]} for s in schemas]

OPENAI_TOOLS = _to_openai_tools(TOOL_SCHEMAS)


class MassyAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = MODEL

    def run(self, user_query: str, trace_callback=None):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ]
        tool_trace = []

        for step in range(MAX_STEPS):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=OPENAI_TOOLS,
                tool_choice="auto"
            )
            msg = response.choices[0].message
            messages.append(msg)

            if not msg.tool_calls:
                final = msg.content or ""
                if trace_callback:
                    trace_callback("final", final)
                return final, tool_trace

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                logger.info("Tool call: %s(%s)", fn_name, fn_args)
                if trace_callback:
                    trace_callback("tool_call", {"name": fn_name, "args": fn_args})

                fn = TOOLS.get(fn_name)
                if fn is None:
                    result = {"error": f"unknown tool {fn_name}"}
                else:
                    try:
                        result = fn(**fn_args)
                    except Exception as e:
                        logger.exception("Tool %s failed", fn_name)
                        result = {"error": str(e)}

                tool_trace.append({"tool": fn_name, "args": fn_args, "result": result})
                if trace_callback:
                    trace_callback("tool_result", {"name": fn_name, "result": result})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str)
                })

        final = "Reached maximum reasoning steps."
        if trace_callback:
            trace_callback("final", final)
        return final, tool_trace


if __name__ == "__main__":
    import sys
    agent = MassyAgent()
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else \
        "What is the single point of failure in our Caribbean logistics network?"

    def printer(event_type, data):
        if event_type == "tool_call":
            print(f"\n[TOOL] {data['name']}({data['args']})")
        elif event_type == "tool_result":
            print(f"[RESULT] {json.dumps(data['result'], default=str)[:200]}...")
        elif event_type == "final":
            print(f"\n{'='*60}\nFINAL ANSWER:\n{'='*60}\n{data}")

    answer, trace = agent.run(query, trace_callback=printer)
    print(f"\nTools called: {[t['tool'] for t in trace]}")