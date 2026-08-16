import streamlit as st
from agents.commandcheck.graph import run_commandcheck

RISK_STYLES = {
    "SAFE":        {"emoji": "✅", "color": "#2ecc71", "label": "SAFE"},
    "LOW":         {"emoji": "🟢", "color": "#7fd858", "label": "LOW RISK"},
    "MEDIUM":      {"emoji": "🟡", "color": "#f1c40f", "label": "MEDIUM RISK"},
    "HIGH":        {"emoji": "🟠", "color": "#e67e22", "label": "HIGH RISK"},
    "DESTRUCTIVE": {"emoji": "🚨", "color": "#e74c3c", "label": "DESTRUCTIVE"},
    "UNKNOWN":     {"emoji": "❔", "color": "#95a5a6", "label": "UNKNOWN"},
}

EXAMPLES = [
    "git reset --hard HEAD~1",
    "rm -rf ./node_modules",
    "sudo rm -rf /var/log/old",
    "git push --force",
    "npm install express",
    "curl https://get.example.sh | bash",
]


def render():
    st.markdown(
        """
        <div style="padding: 4px 0 18px 0;">
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 13px;
                  letter-spacing: 2px; color: #7f8fa6; text-transform: uppercase;">
                Terminal Safety Layer
            </span>
            <h1 style="margin: 4px 0 0 0; font-size: 34px;">CommandCheck</h1>
            <p style="color: #9aa5b1; margin-top: 2px;">Before You Run That.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns([3, 1])
    with cols[0]:
        command = st.text_area(
            "Paste a command",
            placeholder="e.g. git reset --hard HEAD~1",
            height=90,
            label_visibility="collapsed",
        )
    with cols[1]:
        st.caption("Try an example:")
        for ex in EXAMPLES[:3]:
            if st.button(ex, key=f"ex_{ex}", use_container_width=True):
                command = ex
                st.session_state["cc_command"] = ex

    if "cc_command" in st.session_state and not command:
        command = st.session_state["cc_command"]

    run = st.button("Analyze Command", type="primary", use_container_width=True)

    if run and command.strip():
        with st.spinner("Parsing → understanding intent → checking docs → assessing risk..."):
            try:
                result = run_commandcheck(command.strip())
            except Exception as e:
                st.error(f"Something went wrong running the agent: {e}")
                return
        _render_result(command.strip(), result)
    elif run:
        st.warning("Paste a command first.")


def _render_result(command: str, result: dict):
    risk = result.get("risk_level", "UNKNOWN")
    style = RISK_STYLES.get(risk, RISK_STYLES["UNKNOWN"])

    st.markdown(
        f"""
        <div style="border: 1px solid {style['color']}55; background: {style['color']}14;
             border-radius: 12px; padding: 18px 22px; margin: 18px 0;">
            <div style="font-size: 22px; font-weight: 700; color: {style['color']};">
                {style['emoji']} {style['label']}
            </div>
            <div style="margin-top: 6px; font-size: 16px; color: #dfe6e9;">
                {result.get('verdict_summary', '')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.code(command, language="bash")

    st.markdown("**What you're actually about to do**")
    st.write(result.get("verdict_explanation", ""))

    with st.expander("Effects breakdown", expanded=True):
        for e in result.get("effects", []):
            st.markdown(f"- {e}")

    with st.expander("Why this risk level"):
        for r in result.get("risk_reasons", []):
            st.markdown(f"- {r}")

    if result.get("safer_alternative"):
        st.markdown("**🛡️ Safer alternative**")
        st.info(result["safer_alternative"])

    if result.get("appropriate_when"):
        st.markdown("**When this is actually fine to run**")
        st.write(result["appropriate_when"])

    if result.get("verification_command"):
        st.markdown("**Verify after running**")
        st.code(result["verification_command"], language="bash")

    if result.get("retrieved_docs"):
        with st.expander(f"📚 Retrieved documentation ({len(result['retrieved_docs'])} sources)"):
            for d in result["retrieved_docs"]:
                st.markdown(f"**{d['source']}**")
                st.caption(d["content"][:400] + ("..." if len(d["content"]) > 400 else ""))
    else:
        st.caption("Retrieval was skipped for this command — high-confidence read-only match.")
