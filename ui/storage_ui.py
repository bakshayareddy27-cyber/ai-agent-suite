import streamlit as st
from agents.storage_detective.graph import run_investigation, run_cleanup
from agents.storage_detective.tools import human_size

SAFETY_STYLES = {
    "SAFE":        {"emoji": "🟢", "color": "#2ecc71", "label": "Safe to clean"},
    "CONDITIONAL": {"emoji": "🟡", "color": "#f1c40f", "label": "Probably safe — review"},
    "CAUTION":     {"emoji": "🟠", "color": "#e67e22", "label": "Caution — check first"},
    "NEVER_AUTO":  {"emoji": "🔴", "color": "#e74c3c", "label": "Never auto-clean"},
}


def render():
    st.markdown(
        """
        <div style="padding: 4px 0 18px 0;">
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 13px;
                  letter-spacing: 2px; color: #7f8fa6; text-transform: uppercase;">
                Forensic Disk Analysis
            </span>
            <h1 style="margin: 4px 0 0 0; font-size: 34px;">Storage Detective</h1>
            <p style="color: #9aa5b1; margin-top: 2px;">Where TF Did My Storage Go?</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "Scans real cache/temp locations on the machine this app is running on. "
        "Nothing is ever deleted without your explicit per-item approval below."
    )

    scan_root = st.text_input(
        "Optional: folder to search for old virtual environments (defaults to your home directory)",
        value="",
        placeholder="e.g. /home/you/projects",
    )

    if st.button("🔍 Scan My Storage", type="primary", use_container_width=True):
        with st.spinner("Scanning → classifying → investigating large items → prioritizing..."):
            try:
                result = run_investigation(scan_root.strip() or None)
            except Exception as e:
                st.error(f"Scan failed: {e}")
                return
        st.session_state["sd_result"] = result
        st.session_state.pop("sd_clean_result", None)

    if "sd_result" in st.session_state:
        _render_investigation(st.session_state["sd_result"])

    if "sd_clean_result" in st.session_state:
        _render_cleanup_result(st.session_state["sd_clean_result"])


def _render_investigation(result: dict):
    items = [i for i in result.get("prioritized_items", []) if i["size_bytes"] > 0]
    recoverable = result.get("total_recoverable_bytes", 0)

    st.markdown("### 🕵️ Your Storage Crime Scene")

    st.markdown(
        f"""
        <div style="border: 1px solid #7fd85855; background: #7fd85814; border-radius: 12px;
             padding: 16px 22px; margin: 12px 0;">
            <div style="font-size: 14px; color: #9aa5b1;">Potentially recoverable</div>
            <div style="font-size: 28px; font-weight: 700; color: #7fd858;">{human_size(recoverable)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    approved = []
    for item in items:
        style = SAFETY_STYLES.get(item["safety"], SAFETY_STYLES["CAUTION"])
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1.2, 1])
            with c1:
                st.markdown(f"**{item['category']}**")
                st.caption(item["path"])
                if item.get("explanation"):
                    st.write(item["explanation"])
                    if item.get("sources"):
                        st.caption("Source: " + ", ".join(set(item["sources"])))
            with c2:
                st.markdown(
                    f"<span style='color:{style['color']}; font-weight:600;'>{style['emoji']} {style['label']}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{human_size(item['size_bytes'])}**")
            with c3:
                default_checked = item["safety"] == "SAFE"
                checked = st.checkbox(
                    "Approve",
                    value=default_checked,
                    key=f"approve_{item['path']}",
                    disabled=item["safety"] == "NEVER_AUTO",
                )
                if checked and item["safety"] != "NEVER_AUTO":
                    approved.append(item["path"])

    st.divider()
    st.caption(f"{len(approved)} item(s) approved for cleanup.")
    confirm = st.checkbox("I understand approved items will be permanently deleted.")
    if st.button("🧹 Clean Approved Items", disabled=not (approved and confirm), use_container_width=True):
        with st.spinner("Cleaning approved items → verifying result..."):
            clean_result = run_cleanup(approved)
        st.session_state["sd_clean_result"] = clean_result
        st.rerun()


def _render_cleanup_result(result: dict):
    clean = result.get("clean_results", {})
    verify = result.get("verification", {})

    st.markdown("### ✅ Cleanup Report")
    st.success(f"Freed approximately {human_size(clean.get('freed_bytes', 0))}.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Deleted**")
        for p in clean.get("deleted", []):
            st.caption(f"✓ {p}")
    with col2:
        if clean.get("errors"):
            st.markdown("**Errors**")
            for e in clean["errors"]:
                st.caption(f"✗ {e['path']} — {e['error']}")

    if verify.get("fully_cleared"):
        st.info("Verification passed: all approved paths are confirmed cleared.")
    else:
        st.warning(f"{len(verify.get('still_present', []))} path(s) still present after cleanup — may require elevated permissions.")
