"""Streamlit app: chat with the demand forecasting advisor.

Run locally:  streamlit run app.py
The API key is typed into the sidebar, kept only in this browser session, and never saved.
"""
import json
from pathlib import Path

import anthropic
import pandas as pd
import streamlit as st

from agent.agent import MODEL, run_agent
from agent.prompts import PROMPTS

ROOT = Path(__file__).resolve().parent

EXAMPLES = [
    "SKU 217390: forecast the next 4 weeks and set the reorder point. Lead time is 2 weeks, service level 95%.",
    "SKU 219009 will be featured in the weekly flyer for the next 2 weeks. Lead time is 2 weeks, service level 95%. What should we stock?",
    "There's a promo coming for 219009, what should we stock?",
    "Place a purchase order with our supplier for 1,500 units of SKU 219009.",
]

st.set_page_config(page_title="Demand Forecasting Advisor", page_icon="📦", layout="wide")

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Anthropic API key", type="password",
                            help="Used only for this session. Not stored or logged.")
    version = st.selectbox("Prompt version", list(PROMPTS), index=len(PROMPTS) - 1)
    st.caption(f"Model: `{MODEL}`")
    if st.button("New conversation"):
        st.session_state.clear()
        st.rerun()

    st.header("Knowledge base")
    inv = pd.read_csv(ROOT / "knowledge" / "inventory.csv")
    st.dataframe(inv[["filename", "date_or_version", "content_type"]], hide_index=True)
    with st.expander("Policy (synthetic)"):
        st.markdown((ROOT / "knowledge" / "docs" / "forecasting_policy.md").read_text())

# ---------- Main ----------
st.title("📦 Demand Forecasting Advisor: store 8023")
st.caption("Senior supply chain analyst agent for SKUs 217390, 219009 and 223245. "
           "It recommends; the planner decides. All orders and escalations are simulated.")

if "api_messages" not in st.session_state:
    st.session_state.api_messages = []   # full conversation sent to Claude
    st.session_state.chat = []           # what is shown on screen: (role, text, trace)

for role, text, trace in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(text)
        if trace:
            with st.expander(f"Execution trace ({sum(1 for t in trace if 'tool' in t)} tool calls)"):
                for t in trace:
                    if "tool" in t:
                        st.markdown(f"**Step {t['step']}: `{t['tool']}`**" + (" ⚠️ error" if t["is_error"] else ""))
                        st.json({"input": t["input"], "output": t["output"]}, expanded=False)
                    else:
                        st.json(t, expanded=False)
                st.download_button("Download trace (JSON)", json.dumps(trace, indent=2),
                                   file_name="trace.json", mime="application/json",
                                   key=f"dl_{id(trace)}")

if not st.session_state.chat:
    st.markdown("**Try an example:**")
    for i, ex in enumerate(EXAMPLES):
        if st.button(ex, key=f"ex{i}"):
            st.session_state.pending = ex
            st.rerun()

prompt = st.chat_input("Describe the SKU, lead time, service level and current conditions...")
prompt = prompt or st.session_state.pop("pending", None)

if prompt:
    if not api_key:
        st.warning("Paste your Anthropic API key in the sidebar first.")
        st.stop()
    st.session_state.chat.append(("user", prompt, None))
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Analysing with tools..."):
            try:
                answer, msgs, trace = run_agent(
                    api_key, st.session_state.api_messages + [{"role": "user", "content": prompt}], version)
            except anthropic.AuthenticationError:
                st.error("The API key was rejected. Check it and try again.")
                st.session_state.chat.pop()
                st.stop()
            except anthropic.APIError as e:
                st.error(f"API error: {e}")
                st.session_state.chat.pop()
                st.stop()
    st.session_state.api_messages = msgs
    st.session_state.chat.append(("assistant", answer, trace))
    st.rerun()
