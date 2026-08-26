"""Bonus: thin demo UI for both tasks. Run with: streamlit run ui/streamlit_app.py

TODO(you): wire the two tabs below to app.triage.classify_ticket and
app.account_brief.summarize_account once those are implemented. Kept
deliberately thin — this is a demo surface for the Loom video, not a second
place to put business logic.
"""
import json
import sys
from pathlib import Path

# streamlit run only puts this script's own directory on sys.path, not the
# repo root, so the `app` package isn't importable regardless of cwd unless
# we add it explicitly here.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app.account_brief import summarize_account
from app.config import ACCOUNTS_PATH
from app.schemas import TicketIn
from app.triage import classify_ticket

st.set_page_config(page_title="AI Technical Support Agent", layout="wide")
st.title("AI Technical Support Agent — Demo")

tab1, tab2 = st.tabs(["Ticket Triage", "Account Health Brief"])

with tab1:
    subject = st.text_input("Subject")
    body = st.text_area("Body", height=200)
    if st.button("Classify ticket", type="primary"):
        try:
            result = classify_ticket(TicketIn(subject=subject, body=body))
            st.json(result.model_dump())
        except NotImplementedError:
            st.warning("classify_ticket isn't implemented yet — see app/triage.py")

with tab2:
    accounts = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
    account_id = st.selectbox(
        "Account",
        options=[a["account_id"] for a in accounts],
        format_func=lambda aid: f"{aid} — {next(a['company'] for a in accounts if a['account_id'] == aid)}",
    )
    if st.button("Generate brief", type="primary"):
        try:
            brief = summarize_account(account_id)
            st.subheader("Executive summary")
            st.write(brief.executive_summary)
            st.subheader("Risks")
            if brief.risks:
                for risk in brief.risks:
                    st.markdown(f"- **{risk.issue}** — *\"{risk.quote}\"* ({risk.ticket_id})")
            else:
                st.success("No churn risk or escalation signals detected in the last 90 days.")
            st.subheader("Talking points")
            for point in brief.talking_points:
                st.markdown(f"- {point}")
        except NotImplementedError:
            st.warning("summarize_account isn't implemented yet — see app/account_brief.py")
