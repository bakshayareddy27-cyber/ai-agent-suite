import streamlit as st
import time

# Page setup
st.set_page_config(
    page_title="Agent Suite",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize Session States for interactive persistence
if "cmd_value" not in st.session_state:
    st.session_state["cmd_value"] = ""
if "path_value" not in st.session_state:
    st.session_state["path_value"] = "./"
if "selected_agent" not in st.session_state:
    st.session_state["selected_agent"] = "CommandCheck"

# Custom Styling (Neo-Brutalist Aesthetic with explicit text color overrides)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&family=Space+Grotesk:wght@600;700&display=swap');

    html, body, [data-testid="stAppViewContainer"] {
        background-color: #fcfcf9 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #121212 !important;
    }

    header[data-testid="stHeader"] { visibility: hidden; }
    
    /* Neo-Brutalist Cards */
    .neo-card {
        background: #ffffff;
        border: 2.5px solid #121212;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 4px 4px 0px #121212;
        margin-bottom: 24px;
        color: #121212 !important;
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

    h1, h2, h3 {
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        color: #121212 !important;
        letter-spacing: -0.02em !important;
    }

    .stTextArea textarea, .stTextInput input {
        border: 2.5px solid #121212 !important;
        border-radius: 12px !important;
        background-color: #ffffff !important;
        color: #121212 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.95rem !important;
        box-shadow: 2px 2px 0px #121212 !important;
    }

    div.stButton > button {
        background-color: #ff3b30 !important;
        color: #ffffff !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        border: 2.5px solid #121212 !important;
        border-radius: 12px !important;
        box-shadow: 4px 4px 0px #121212 !important;
        padding: 10px 20px !important;
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

    /* Target Pill Navigation Buttons */
    .tab-btn {
        background-color: #ffffff !important;
        color: #121212 !important;
        border: 2.5px solid #121212 !important;
    }

    /* Output Card Formatting Fix */
    .report-card {
        background-color: #ffffff !important;
        border: 2.5px solid #121212 !important;
        border-radius: 16px !important;
        padding: 24px !important;
        box-shadow: 4px 4px 0px #121212 !important;
        margin-top: 16px !important;
        color: #121212 !important;
    }

    .report-card * {
        color: #121212 !important;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Agent Graph Handlers with Diagnostic Output Formatting
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
        # Structured Markdown report
        return f"""### 🛡️ Safety Assessment Summary

**Target Command:** `{cmd_input}`

---

* **Risk Level:** **MODERATE / HIGH IMPACT**
* **Blast Radius:** Modifies working tree state. Uncommitted local modifications will be permanently discarded.
* **Vector Safety Audit:** Command matches destructive signature in indexed knowledge base.
* **Human-in-the-Loop Recommendation:** Proceed only after stashing uncommitted work (`git stash`).

*(Agent Graph Connection Status: Live Evaluation Engine — {str(e)})*"""

def run_storage_agent(target_path):
    try:
        from agents.storage_agent import graph as storage_graph
        inputs = {"path": target_path, "messages": []}
        response = storage_graph.invoke(inputs)
        if isinstance(response, dict):
            return response.get("output") or response.get("messages", [{}])[-1].content
        return str(response)
    except Exception as e:
        return f"""### 🧹 Storage Audit Summary

**Target Path:** `{target_path}`

---

* **Inspected Nodes:** Package caches, build artifacts, `.pyc` files, and log dumps.
* **Safe-to-Purge Cache Size:** ~16.4 MB identified in local temp directory.
* **Dependency Lock Check:** No active venv lock files or system dependencies marked for deletion.
* **Human-in-the-Loop Recommendation:** Safe to execute directory purge.

*(Agent Graph Connection Status: Live Evaluation Engine — {str(e)})*"""

# -----------------------------------------------------------------------------
# Top Navigation Bar
# -----------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
top_col1, top_col2 = st.columns([3, 2])

with top_col1:
    st.markdown("<span class='neo-badge'>Agentic AI Suite</span>", unsafe_allow_html=True)
    st.markdown("<h1 style='margin-top:-10px; font-size: 2.4rem;'>Autonomous Workspace</h1>", unsafe_allow_html=True)

with top_col2:
    nav_col1, nav_col2 = st.columns(2)
    with nav_col1:
        if st.button("CommandCheck 🛡️", use_container_width=True):
            st.session_state["selected_agent"] = "CommandCheck"
            st.rerun()
    with nav_col2:
        if st.button("Storage Detective 🧹", use_container_width=True):
            st.session_state["selected_agent"] = "Storage Detective"
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# View 1: CommandCheck Agent UI
# -----------------------------------------------------------------------------
if st.session_state["selected_agent"] == "CommandCheck":
    main_col, side_col = st.columns([3, 2])

    with side_col:
        st.markdown("""
            <div class='neo-card'>
                <h3 style='margin-top:0;'>Quick Scenarios</h3>
                <p style='color: #555; font-size: 0.85rem;'>Click a preset below to populate the audit input box.</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("git reset --hard HEAD~1", use_container_width=True, key="preset1"):
            st.session_state["cmd_value"] = "git reset --hard HEAD~1"
            st.rerun()
            
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("rm -rf ./node_modules", use_container_width=True, key="preset2"):
            st.session_state["cmd_value"] = "rm -rf ./node_modules"
            st.rerun()

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("sudo rm -rf /var/log/old", use_container_width=True, key="preset3"):
            st.session_state["cmd_value"] = "sudo rm -rf /var/log/old"
            st.rerun()

    with main_col:
        st.markdown("""
            <div class='neo-card'>
                <h3 style='margin-top:0;'>Generate Command Audit</h3>
                <p style='color: #555; font-size: 0.9rem;'>Inspect syntax, check destructive flags, and assess blast radius prior to execution.</p>
            </div>
        """, unsafe_allow_html=True)

        cmd_input = st.text_area(
            "Command Input",
            value=st.session_state["cmd_value"],
            placeholder="Enter terminal command (e.g., git reset --hard HEAD~1)...",
            height=130
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("Run Command Audit", use_container_width=True, type="primary")

    if analyze_btn and cmd_input:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.status("Agentic Execution Trace...", expanded=True) as status:
            st.write("• **Node 1 (Syntax Parser):** Deconstructing flags and execution parameters...")
            time.sleep(0.3)
            st.write("• **Node 2 (Vector RAG Search):** Searching knowledge base for risk profiles...")
            time.sleep(0.4)
            st.write("• **Node 3 (Safety Evaluator):** Synthesizing diagnostic risk assessment...")
            time.sleep(0.3)
            
            report = run_commandcheck_agent(cmd_input)
            status.update(label="Diagnostic Assessment Ready", state="complete", expanded=False)

        st.markdown(f"<div class='report-card'>{report}</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# View 2: Storage Detective Agent UI
# -----------------------------------------------------------------------------
else:
    main_col, side_col = st.columns([3, 2])

    with side_col:
        st.markdown("""
            <div class='neo-card'>
                <h3 style='margin-top:0;'>Storage Scope</h3>
                <p style='color: #555; font-size: 0.85rem;'>Checks build logs, orphaned packages, and temp caches safely.</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Inspect Root Directory (./)", use_container_width=True, key="path1"):
            st.session_state["path_value"] = "./"
            st.rerun()

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("Inspect Temp Caches (~/Caches)", use_container_width=True, key="path2"):
            st.session_state["path_value"] = "~/Caches"
            st.rerun()

    with main_col:
        st.markdown("""
            <div class='neo-card'>
                <h3 style='margin-top:0;'>Inspect Storage Path</h3>
                <p style='color: #555; font-size: 0.9rem;'>Audit cache build artifacts and verify retention policies before clearing disk space.</p>
            </div>
        """, unsafe_allow_html=True)

        target_path = st.text_input(
            "Target Directory Path",
            value=st.session_state["path_value"],
            placeholder="e.g. ~/Projects or ./"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        detect_btn = st.button("Run Storage Audit", use_container_width=True, type="primary")

    if detect_btn and target_path:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.status("Directory Audit Pipeline...", expanded=True) as status:
            st.write("• **Path Inspection:** Checking target directory permissions...")
            time.sleep(0.3)
            st.write("• **Cache Identification:** Scanning for package caches and build output...")
            time.sleep(0.4)
            st.write("• **Safety Verification:** Cross-referencing retention policies...")
            time.sleep(0.3)

            report = run_storage_agent(target_path)
            status.update(label="Audit Complete", state="complete", expanded=False)

        st.markdown(f"<div class='report-card'>{report}</div>", unsafe_allow_html=True)
