"""PHTA Streamlit UI — clean medical aesthetic chat interface.

Production-grade web UI for the Personal Health Triaging Agent.
Features: chat-based triage conversation, medical disclaimer banner,
triage result cards with color coding, session persistence, accessibility.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from agent.orchestrator import handle_user_input
from agent.session_manager import session_manager

st.set_page_config(
    page_title="PHTA — Personal Health Triaging Agent",
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TRIAGE_COLORS = {
    1: {"name": "EMERGENCY", "color": "red", "bg": "#fff5f5", "border": "#e53e3e"},
    2: {"name": "URGENT", "color": "orange", "bg": "#fffaf0", "border": "#ed8936"},
    3: {"name": "SEMI-URGENT", "color": "#d69e2e", "bg": "#fffff0", "border": "#ecc94b"},
    4: {"name": "NON-URGENT", "color": "green", "bg": "#f0fff4", "border": "#38a169"},
}

CSS = """
<style>
.main .block-container { max-width: 800px; padding-top: 1rem; }
.disclaimer-banner {
    background: #fefcbf; border: 1px solid #ecc94b; border-radius: 8px;
    padding: 10px 16px; margin-bottom: 16px; font-size: 0.88rem; color: #744210;
}
.disclaimer-banner strong { color: #c05621; }
.triage-card {
    border-radius: 12px; padding: 20px 24px; margin: 16px 0;
}
.triage-card h2 { margin-top: 0; font-size: 1.4rem; }
.triage-card .action { font-weight: 600; margin: 8px 0; }
.emergency-msg {
    background: #fff5f5; border: 2px solid #e53e3e; border-radius: 12px;
    padding: 20px 24px; margin: 12px 0; color: #9b2c2c;
}
.emergency-msg h2 { color: #e53e3e; margin-top: 0; }
.stChatMessage { padding: 8px 12px; }
</style>
"""


def init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "phta_session_id" not in st.session_state:
        st.session_state.phta_session_id = None
    if "triage_complete" not in st.session_state:
        st.session_state.triage_complete = False
    if "triage_result" not in st.session_state:
        st.session_state.triage_result = None


def render_disclaimer() -> None:
    st.markdown(
        '<div class="disclaimer-banner">'
        "<strong>⚕️ THIS IS NOT A MEDICAL DIAGNOSIS.</strong> "
        "PHTA is a triage screening tool only. "
        "Always consult a qualified healthcare professional. "
        "If this is a medical emergency, call <strong>115</strong> immediately."
        "</div>",
        unsafe_allow_html=True,
    )


def render_triage_card(result: dict) -> None:
    level = result.get("triage_level", 4)
    tc = TRIAGE_COLORS.get(level, TRIAGE_COLORS[4])
    detail = result.get("triage_detail", {})

    if level == 1:
        st.markdown(
            f'<div class="emergency-msg"><h2>🚨 EMERGENCY</h2>'
            f"<p>{result.get('message', '')}</p></div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<div class="triage-card" style="background:{tc["bg"]};border:2px solid {tc["border"]}">'
        f'<h2 style="color:{tc["color"]}">{tc["name"]}</h2>'
        f'<p><strong>Confidence:</strong> {detail.get("confidence", 0):.0%}</p>'
        f'<p>{detail.get("primary_concern", "")}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_monitoring_plan(message: str) -> None:
    st.markdown(
        f'<div class="triage-card" style="background:#f0fff4;border:2px solid #38a169">'
        f"{message.replace(chr(10), '<br>')}"
        f"</div>",
        unsafe_allow_html=True,
    )


def on_send(user_input: str) -> None:
    if not user_input.strip():
        return

    st.session_state.messages.append({"role": "user", "content": user_input})

    result = handle_user_input(
        user_input,
        session_id=st.session_state.phta_session_id,
    )
    st.session_state.phta_session_id = result.get("session_id")

    st.session_state.messages.append({"role": "assistant", "content": result.get("message", "")})

    if result.get("is_complete"):
        st.session_state.triage_complete = True
        if result.get("triage_detail"):
            st.session_state.triage_result = result.get("triage_detail", {})
            st.session_state.triage_result["message"] = result.get("message", "")
            st.session_state.triage_result["triage_level"] = result.get("triage_level", 4)


def start_new_session() -> None:
    if st.session_state.phta_session_id:
        session_manager.delete(st.session_state.phta_session_id)
    st.session_state.messages = []
    st.session_state.phta_session_id = None
    st.session_state.triage_complete = False
    st.session_state.triage_result = None


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    init_session()

    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("⚕️ Personal Health Triaging Agent")
    with col2:
        if st.button("New Session", use_container_width=True):
            start_new_session()
            st.rerun()

    render_disclaimer()

    if not st.session_state.messages:
        with st.chat_message("assistant"):
            st.markdown(
                "Welcome to the Personal Health Triaging Agent (PHTA).\n\n"
                "I'm here to help you understand your symptoms and provide "
                "guidance on whether and how urgently to seek medical care.\n\n"
                "**Describe your symptoms in your own words.** "
                "I'll ask a few questions and then give you a triage recommendation.\n\n"
                "*English and Vietnamese supported. Voice input available in the CLI version.*"
            )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if st.session_state.triage_complete and st.session_state.triage_result:
        result = st.session_state.triage_result
        if result.get("triage_level") == 1:
            with st.chat_message("assistant"):
                render_triage_card({"triage_level": 1, "message": result.get("message", "")})
        elif result.get("triage_level", 4) <= 2:
            with st.chat_message("assistant"):
                render_triage_card({"triage_level": result["triage_level"], "triage_detail": result})

    if not st.session_state.triage_complete:
        user_input = st.chat_input("Describe your symptoms...")
        if user_input:
            on_send(user_input)
            st.rerun()

    st.markdown("---")
    st.caption(
        "PHTA v1.0.0 | Local-first, encrypted | "
        "[Privacy Policy](/) | [Medical Disclaimer](/)"
    )


if __name__ == "__main__":
    main()
