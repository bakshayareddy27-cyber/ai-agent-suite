import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Agent Suite — CommandCheck × Storage Detective",
    page_icon="🛰️",
    layout="wide",
)

DARK_CSS = """
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; }
    section[data-testid="stSidebar"] { background-color: #0a0e14; }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        border: 1px solid #2d333b;
    }
    div[data-testid="stTextArea"] textarea, div[data-testid="stTextInput"] input {
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        background-color: #161b22;
        border: 1px solid #30363d;
        color: #e6edf3;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 8px 8px 0 0;
        padding: 10px 18px;
        font-family: 'JetBrains Mono', monospace;
    }
    div[data-testid="stMetric"] { background-color: #161b22; padding: 10px; border-radius: 10px; }
    code { color: #7fd858 !important; }
</style>
"""
st.markdown(DARK_CSS, unsafe_allow_html=True)

if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
    st.error(
        "No LLM API key found. Set `ANTHROPIC_API_KEY` (recommended) or "
        "`OPENAI_API_KEY` as an environment variable, or add it to a `.env` "
        "file in the project root (see `.env.example`)."
    )
    st.stop()

tab1, tab2 = st.tabs(["🚨  CommandCheck", "🕵️  Storage Detective"])

with tab1:
    from ui import commandcheck_ui
    commandcheck_ui.render()

with tab2:
    from ui import storage_ui
    storage_ui.render()

st.sidebar.markdown("### 🛰️ Agent Suite")
st.sidebar.caption(
    "Two independent LangGraph agents, each with real tool calling and "
    "retrieval-augmented generation over a dedicated knowledge base."
)
st.sidebar.markdown("---")
st.sidebar.markdown("**CommandCheck**")
st.sidebar.caption("Explains and risk-rates terminal commands before you run them.")
st.sidebar.markdown("**Storage Detective**")
st.sidebar.caption("Investigates disk usage and cleans only what you approve.")
