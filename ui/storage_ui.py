import streamlit as st
import time

def render_storage_ui(agent_graph):
    # Minimalist CSS styling
    st.markdown("""
        <style>
        .stTextInput input {
            font-family: 'SF Mono', 'Fira Code', 'Roboto Mono', monospace !important;
            border-radius: 8px !important;
        }
        .step-label {
            font-weight: 600;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            font-size: 0.75rem;
            color: #888;
        }
        </style>
    """, unsafe_allow_html=True)

    head_col1, head_col2 = st.columns([4, 1])
    with head_col1:
        st.caption("Disk & Cache Inspector")
        st.title("Storage Detective")
    with head_col2:
        st.write("")
        st.toggle("Cozy Mode", key="storage_theme")

    st.write("Locate deep cache build artifacts and verify retention dependencies before freeing space.")
    st.markdown("<br>", unsafe_allow_html=True)

    target_path = st.text_input("Target Directory Path", value="./", placeholder="e.g. ~/Projects or ./")
    detect_btn = st.button("Inspect Directory", type="primary", use_container_width=True)

    if detect_btn:
        st.markdown("---")

        with st.status("Analyzing directory tree...", expanded=True) as status:
            st.write("• **Directory Inspection:** Verifying file tree structure and permissions")
            time.sleep(0.3)
            st.write("• **Cache Identification:** Scanning for package caches and build output folders")
            time.sleep(0.4)
            st.write("• **Safety Verification:** Cross-referencing active environment configurations")
            time.sleep(0.3)

            try:
                inputs = {"path": target_path, "messages": []}
                response = agent_graph.invoke(inputs)
                status.update(label="Inspection Complete", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Inspection Failed", state="error")
                st.error(f"Error: {str(e)}")
                return

        st.markdown("<span class='step-label'>Storage Report</span>", unsafe_allow_html=True)
        
        if isinstance(response, dict):
            output_text = response.get("output") or response.get("messages", [{}])[-1].content
        else:
            output_text = str(response)

        st.markdown(output_text)
