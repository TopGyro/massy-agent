"""
Massy Supply Chain Agent — Streamlit UI
"""

import os
import sys
import json
import uuid

import streamlit as st

from massy_agent import MassyAgent

st.set_page_config(page_title="Massy Supply Chain Agent", page_icon="⚓", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    .agent-header {
        background: linear-gradient(135deg, #0d1f0f 0%, #0a1628 100%);
        border: 1px solid #1e3a1f; border-radius: 8px; padding: 20px 28px; margin-bottom: 20px;
    }
    .agent-title { font-family: 'IBM Plex Mono', monospace; font-size: 18px; color: #4ade80; margin: 0; }
    .agent-subtitle { font-size: 13px; color: #6b7280; margin: 4px 0 0; }
    .tool-badge {
        display: inline-block; background: #0f1923; border-left: 3px solid #38bdf8;
        padding: 8px 12px; margin: 4px 0; font-family: 'IBM Plex Mono', monospace;
        font-size: 12px; color: #38bdf8; border-radius: 0 4px 4px 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="agent-header">
    <p class="agent-title">// MASSY SUPPLY CHAIN INTELLIGENCE AGENT</p>
    <p class="agent-subtitle">OpenAI · AWS DynamoDB · Caribbean Distribution Network</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚓ Massy Agent")
    st.caption(f"Model: {os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}")
    st.caption("OpenAI · AWS DynamoDB")
    st.divider()
    st.markdown("**7 Tools**")
    for t in ["Inventory Status", "Demand Forecast", "Warehouse Optimizer",
              "Route Planner", "Sustainability", "Graph Analysis", "Shipping Compliance"]:
        st.caption(f"• {t}")
    st.divider()
    st.markdown("**Try asking:**")
    examples = [
        "What is the single point of failure in our Caribbean logistics network?",
        "What should we reorder for Port of Spain this week?",
        "Optimise the warehouse pick sequence for WH-POS-001",
        "Generate a customs declaration for shipping rice and chicken from Trinidad to Barbados",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=ex):
            st.session_state.pending = ex

if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_resource
def get_agent():
    return MassyAgent()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("tools"):
            for t in msg["tools"]:
                st.markdown(f'<div class="tool-badge">→ {t}</div>', unsafe_allow_html=True)
        st.markdown(msg["content"])

pending = st.session_state.pop("pending", None)
user_input = st.chat_input("Ask about inventory, routes, warehouse, sustainability, or shipping...")
query = pending or user_input

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        tools_used = []
        status = st.status("Agent reasoning...", expanded=True)

        def trace_cb(event_type, data):
            if event_type == "tool_call":
                tools_used.append(data["name"])
                status.write(f"🔧 Calling **{data['name']}**")
            elif event_type == "tool_result":
                preview = json.dumps(data["result"], default=str)[:150]
                status.write(f"✓ {data['name']} returned data")

        agent = get_agent()
        try:
            answer, trace = agent.run(query, trace_callback=trace_cb)
            status.update(label=f"Done — {len(tools_used)} tools called", state="complete", expanded=False)
        except Exception as e:
            answer = f"Error: {e}\n\nCheck your OPENAI_API_KEY and AWS credentials in .env."
            trace = []
            status.update(label="Error", state="error")

        for t in tools_used:
            st.markdown(f'<div class="tool-badge">→ {t}</div>', unsafe_allow_html=True)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer, "tools": tools_used})