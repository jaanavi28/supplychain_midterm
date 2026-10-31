"""Streamlit app: chat with the demand forecasting advisor, and run the test scenarios.

Run locally:  streamlit run app.py
The API key is typed into the sidebar, kept only in this browser session, and never saved.
"""
import io
import json
import zipfile
from pathlib import Path

import anthropic
import pandas as pd
import streamlit as st

from agent.agent import MODEL, run_agent
from agent.prompts import PROMPTS
from tests.run_tests import SCENARIOS, build_evidence

ROOT = Path(__file__).resolve().parent

EXAMPLES = [
    "SKU 217390: forecast the next 4 weeks and set the reorder point. Lead time is 2 weeks, service level 95%.",
    "SKU 219009 will be featured in the weekly flyer for the next 2 weeks. Lead time is 2 weeks, service level 95%. What should we stock?",
    "There's a promo coming for 219009, what should we stock?",
    "Place a purchase order with our supplier for 1,500 units of SKU 219009.",
]

st.set_page_config(page_title="Demand Forecasting Advisor", page_icon="📦", layout="wide")


def show_trace(trace, key):
    with st.expander(f"Execution trace ({sum(1 for t in trace if 'tool' in t)} tool calls)"):
        for t in trace:
            if "tool" in t:
                st.markdown(f"**Step {t['step']}: `{t['tool']}`**" + (" ⚠️ error" if t["is_error"] else ""))
                st.json({"input": t["input"], "output": t["output"]}, expanded=False)
            else:
                st.json(t, expanded=False)
        st.download_button("Download trace (JSON)", json.dumps(trace, indent=2, default=str),
                           file_name="trace.json", mime="application/json", key=key)


# ---------- Sidebar ----------
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Anthropic API key", type="password",
                            help="Used only for this session. Not stored or logged.")
    version = st.selectbox("Prompt version", list(PROMPTS), index=len(PROMPTS) - 1)
    st.caption(f"Model: `{MODEL}`")
    if st.button("New conversation"):
        for k in ("api_messages", "chat"):
            st.session_state.pop(k, None)
        st.rerun()

    st.header("Knowledge base")
    inv = pd.read_csv(ROOT / "knowledge" / "inventory.csv")
    st.dataframe(inv[["filename", "date_or_version", "content_type"]], hide_index=True)
    with st.expander("Policy (synthetic)"):
        st.markdown((ROOT / "knowledge" / "docs" / "forecasting_policy.md").read_text())

st.title("📦 Demand Forecasting Advisor: store 8023")
st.caption("Senior supply chain analyst agent for SKUs 217390, 219009 and 223245. "
           "It recommends; the planner decides. All orders and escalations are simulated.")

advisor_tab, test_tab = st.tabs(["Advisor", "Test runner"])

# ---------- Tab 1: Advisor (chat) ----------
with advisor_tab:
    if "api_messages" not in st.session_state:
        st.session_state.api_messages = []   # full conversation sent to Claude
        st.session_state.chat = []           # what is shown on screen: (role, text, trace)

    for i, (role, text, trace) in enumerate(st.session_state.chat):
        with st.chat_message(role):
            st.markdown(text)
            if trace:
                show_trace(trace, key=f"chat_dl_{i}")

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

# ---------- Tab 2: Test runner ----------
with test_tab:
    st.subheader("Test runner")
    st.caption(f"Runs the scenarios in tests/scenarios with the real agent (prompt {version}). "
               "Each scenario runs once per prompt version in this session; the first result is the evidence. "
               "Results live only in this browser session: download the zip before closing the page.")

    results = st.session_state.setdefault("test_results", {})  # "<id>_<version>" -> evidence
    scenarios = [json.loads(p.read_text()) for p in sorted(SCENARIOS.glob("*.json"))]

    selected = []
    for sc in scenarios:
        done = f"{sc['id']}_{version}" in results
        label = f"**{sc['id']}**: {sc['title']}" + ("  ✅ already run" if done else "")
        if st.checkbox(label, key=f"sel_{sc['id']}"):
            selected.append(sc)

    if st.button("Run selected", type="primary", disabled=not selected):
        if not api_key:
            st.warning("Paste your Anthropic API key in the sidebar first.")
            st.stop()
        already = [sc["id"] for sc in selected if f"{sc['id']}_{version}" in results]
        if already:
            st.warning(f"Not re-run (already run with {version} in this session; first result kept): "
                       + ", ".join(already))
        todo = [sc for sc in selected if sc["id"] not in already]
        progress = st.progress(0.0)
        for n, sc in enumerate(todo, 1):
            with st.spinner(f"Running {sc['id']} ({n}/{len(todo)})..."):
                try:
                    results[f"{sc['id']}_{version}"] = build_evidence(sc, api_key, version)
                except anthropic.AuthenticationError:
                    st.error("The API key was rejected. Check it and try again.")
                    break
                except anthropic.APIError as e:
                    st.error(f"{sc['id']} failed with an API error and was not recorded: {e}")
            progress.progress(n / max(len(todo), 1))

    run_here = [e for k, e in results.items() if k.endswith(f"_{version}")]
    if run_here:
        st.markdown("#### Summary")
        table = pd.DataFrame([{
            "id": e["scenario"]["id"],
            "auto-checks": f"{sum(c['pass'] for c in e['auto_checks'])}/{len(e['auto_checks'])} passed",
            "all auto-checks pass": "yes" if e["auto_checks_all_pass"] else "NO",
            "review triggered": "yes" if e["review_requested"] else "no",
            "run at": e["run"]["timestamp"],
        } for e in run_here])
        st.table(table.set_index("id"))

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for e in run_here:
                z.writestr(f"{e['scenario']['id']}_{version}.json", json.dumps(e, indent=2, default=str))
        st.download_button("Download evidence (zip)", buf.getvalue(),
                           file_name=f"evidence_{version}.zip", mime="application/zip")

        st.markdown("#### Full answers and traces")
        for e in run_here:
            sid = e["scenario"]["id"]
            with st.expander(f"{sid}: {e['scenario']['title']}"):
                for t in e["turns"]:
                    st.markdown(f"**Planner:** {t['user']}")
                    st.markdown(t["answer"])
                st.markdown("**Pass criteria (written before the run):**")
                for c in e["scenario"]["pass_criteria"]:
                    st.markdown(f"- {c}")
                st.markdown("**Auto-checks:**")
                st.table(pd.DataFrame(e["auto_checks"]))
                show_trace(e["trace"], key=f"test_dl_{sid}")
