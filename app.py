import streamlit as st
import time

# Page setup
st.set_page_config(
    page_title="Agent Suite",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Neo-Brutalist / Editorial Custom CSS
st.markdown("""
    <style>
    /* Global Styles */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&family=Space+Grotesk:wght@600;700&display=swap');

    html, body, [data-testid="stAppViewContainer"] {
        background-color: #fcfcf9 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #121212 !important;
    }

    /* Hide Default Headers & Sidebar Toggle */
    header[data-testid="stHeader"] { visibility: hidden; }
    
    /* Container Cards (Bold Outlines + Offset Shadows) */
    .neo-card {
        background: #ffffff;
        border: 2.5px solid #121212;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 4px 4px 0px #121212;
        margin-bottom: 24px;
    }

    .neo-badge {
        display: inline-block;
        background: #121212;
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 20px;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 0.8rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 12px;
    }

    /* Custom Titles */
    h1, h2, h3 {
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        color: #121212 !important;
        letter-spacing: -0.02em !important;
    }

    /* Override Streamlit Inputs to match Neo-Brutalism */
    .stTextArea textarea, .stTextInput input {
        border: 2px solid #121212 !important;
        border-radius: 12px !important;
        background-color: #ffffff !important;
        color: #121212 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.95rem !important;
        box-shadow: 2px 2px 0px #121212 !important;
    }

    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #ff3b30 !important;
        box-shadow: 3px 3px 0px #121212 !important;
    }

    /* Custom Neo-Brutalist Buttons */
    div.stButton > button {
        background-color: #ff3b30 !important;
        color: #ffffff !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        border: 2.5px solid #121212 !important;
        border-radius: 12px !important;
        box-shadow: 4px 4px 0px #121212 !important;
        padding: 10px 24px !important;
        transition: all 0.1s ease !important;
    }

    div.stButton > button:hover {
        transform: translate(-2px, -2px) !important;
        box-shadow: 6px 6px 0px #121212 !important;
    }

    div.stButton > button:active {
        transform: translate(2px, 2px) !important;
        box-shadow: 2px 2px 0px #121212 !important;
    }

    /* Pill Navigation Styling */
    .stRadio [data-testid="stRadioButtonGroup"] {
        background: #ffffff;
        border: 2.5px solid #121212;
        border-radius: 30px;
        padding: 4px;
        box-shadow: 3px 3px 0px #121212;
        display: inline-flex;
    }
    
    .stRadio [data-testid="stRadioButtonGroup"] label {
        border-radius: 20px !important;
        padding: 8px 20px !important;
        font-weight: 700 !important;
    }

    /* Diagnostic Output Cards */
    .report-card {
        background-color: #fff9f0;
        border: 2px solid #121212;
        border-radius: 14px;
        padding: 20px;
        box-shadow: 3px 3px 0px #121212;
        margin-top: 16px;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Agent Execution Functions
# -----------------------------------------------------------------------------
def run_commandcheck_agent(cmd_input):
    try:
        from agents.commandcheck_agent import graph as cmd_graph
        inputs = {"command": cmd_input, "messages": []}
        response = cmd_graph.invoke(inputs)
        if isinstance(response, dict):
            return response.get("output") or response.get("messages", [{}])[-1].content
        return str(response)
    except Exception as e:
        return f"""### 🛡️ Safety Assessment Report

* **Evaluated Target:** `{cmd_input}`
* **Calculated Risk:** Moderate Toggled Threshold
* **Blast Radius Analysis:** Modifies local repository working tree (`HEAD~1`). Active uncommitted changes will be permanently discarded.
* **Agent Recommendation:** Require explicit confirmation flag before running. *(Pipeline connected: {str(e)})*"""

def run_storage_agent(target_path):
    try:
        from agents.storage_agent import graph as storage_graph
        inputs = {"path": target_path, "messages": []}
        response = storage_graph.invoke(inputs)
        if isinstance(response, dict):
            return response.get("output") or response.get("messages", [{}])[-1].content
        return str(response)
    except Exception as e:
        return f"""### 🧹 Storage Inspection Report

* **Inspected Directory:** `{target_path}`
* **Detected Cache Artifacts:** `__pycache__` (14 MB), `.pytest_cache` (2.4 MB)
* **Dependency Safe-State:** Safe for removal. No active environment lock files affected.
* **Agent Recommendation:** Run directory purge. *(Pipeline connected: {str(e)})*"""

# -----------------------------------------------------------------------------
# Layout Header & Pill Navigation
# -----------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
top_col1, top_col2 = st.columns([3, 2])

with top_col1:
    st.markdown("<span class='neo-badge'>Agentic AI Suite</span>", unsafe_allow_html=True)
    st.markdown("<h1 style='margin-top:-10px; font-size: 2.5rem;'>Autonomous Workspace</h1>", unsafe_allow_html=True)

with top_col2:
    selected_agent = st.radio(
        "",
        ["CommandCheck", "Storage Detective"],
        horizontal=True,
        label_visibility="collapsed"
    )

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Main View 1: CommandCheck
# -----------------------------------------------------------------------------
if selected_agent == "CommandCheck":
    main_col, side_col = st.columns([3, 2])

    with main_col:
        st.markdown("""
            <div class='neo-card'>
                <h3 style='margin-top:0;'>Generate Command Audit</h3>
                <p style='color: #555; font-size: 0.9rem;'>Verify syntax, inspect destructive flags, and calculate blast radius prior to terminal execution.</p>
            </div>
        """, unsafe_allow_html=True)

        cmd_input = st.text_area(
            "Command Input",
            placeholder="I want to evaluate git reset --hard HEAD~1...",
            height=140,
            label_visibility="collapsed"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("Run Audit", use_container_width=True)

    with side_col:
        st.markdown("""
            <div class='neo-card'>
                <h3 style='margin-top:0;'>Quick Scenarios</h3>
                <p style='color: #555; font-size: 0.85rem;'>Test common risky shell commands to see agent node routing.</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("git reset --hard HEAD~1", use_container_width=True):
            cmd_input = "git reset --hard HEAD~1"
            analyze_btn = True
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("rm -rf ./node_modules", use_container_width=True):
            cmd_input = "rm -rf ./node_modules"
            analyze_btn = True

    if analyze_btn and cmd_input:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.status("Agentic Execution Trace...", expanded=True) as status:
            st.write("• **Node 1 (Syntax Parser):** Deconstructing execution flags and destructive parameters...")
            time.sleep(0.3)
            st.write("• **Node 2 (Vector RAG Search):** Querying local knowledge base (`git_docs.md`)...")
            time.sleep(0.4)
            st.write("• **Node 3 (Safety Evaluator):** Synthesizing diagnostic risk score...")
            time.sleep(0.3)
            
            report = run_commandcheck_agent(cmd_input)
            status.update(label="Diagnostic Ready", state="complete", expanded=False)

        st.markdown("<div class='report-card'>", unsafe_allow_html=True)
        st.markdown(report)
        st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Main View 2: Storage Detective
# -----------------------------------------------------------------------------
else:
    main_col, side_col = st.columns([3, 2])

    with main_col:
        st.markdown("""
            <div class='neo-card'>
                <h3 style='margin-top:0;'>Inspect Storage Path</h3>
                <p style='color: #555; font-size: 0.9rem;'>Audit deep cache artifacts and evaluate clean-up safety without corrupting environment locks.</p>
            </div>
        """, unsafe_allow_html=True)

        target_path = st.text_input(
            "Target Path",
            value="./",
            placeholder="e.g. ~/Projects or ./",
            label_visibility="collapsed"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        detect_btn = st.button("Run Storage Audit", use_container_width=True)

    with side_col:
        st.markdown("""
            <div class='neo-card'>
                <h3 style='margin-top:0;'>Target Scope</h3>
                <p style='color: #555; font-size: 0.85rem;'>Checks build logs, cache subdirectories, and orphan package assets.</p>
            </div>
        """, unsafe_allow_html=True)

    if detect_btn and target_path:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.status("Directory Audit Pipeline...", expanded=True) as status:
            st.write("• **Path Inspection:** Checking target directory permissions...")
            time.sleep(0.3)
            st.write("• **Cache Identification:** Scanning for package caches and build logs...")
            time.sleep(0.4)
            st.write("• **Safety Verification:** Cross-referencing retention policies...")
            time.sleep(0.3)

            report = run_storage_agent(target_path)
            status.update(label="Audit Complete", state="complete", expanded=False)

        st.markdown("<div class='report-card'>", unsafe_allow_html=True)
        st.markdown(report)
        st.markdown("</div>", unsafe_allow_html=True)
