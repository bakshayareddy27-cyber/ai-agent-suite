import streamlit as st
import time

def render_commandcheck_ui(agent_graph):
    # Minimalist, non-robotic CSS styling
    st.markdown("""
        <style>
        /* Base typography & container tweaks */
        .stTextArea textarea {
            font-family: 'SF Mono', 'Fira Code', 'Roboto Mono', monospace !important;
            font-size: 0.9rem !important;
            border-radius: 8px !important;
        }
        
        /* Subtle execution steps card */
        .execution-box {
            background-color: rgba(125, 125, 125, 0.05);
            border: 1px solid rgba(125, 125, 125, 0.15);
            border-radius: 10px;
            padding: 16px;
            margin: 16px 0;
            font-size: 0.9rem;
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

    # Header section
    head_col1, head_col2 = st.columns([4, 1])
    with head_col1:
        st.caption("Terminal Security Guardrail")
        st.title("CommandCheck")
    with head_col2:
        st.write("")
        st.toggle("Cozy Mode", key="cmd_theme")

    st.write("Inspect syntax, flag destructive flags, and evaluate risk tiers before executing shell commands.")
    st.markdown("<br>", unsafe_allow_html=True)

    col_input, col_preset = st.columns([3, 2])

    with col_input:
        cmd_input = st.text_area(
            "Command Input",
            placeholder="git reset --hard HEAD~1",
            height=130
        )
        analyze_btn = st.button("Evaluate Command", use_container_width=True, type="primary")

    with col_preset:
        st.caption("Common Scenarios")
        if st.button("git reset --hard HEAD~1", use_container_width=True):
            cmd_input = "git reset --hard HEAD~1"
            analyze_btn = True
        if st.button("rm -rf ./node_modules", use_container_width=True):
            cmd_input = "rm -rf ./node_modules"
            analyze_btn = True
        if st.button("sudo rm -rf /var/log/old", use_container_width=True):
            cmd_input = "sudo rm -rf /var/log/old"
            analyze_btn = True

    if analyze_btn and cmd_input:
        st.markdown("---")
        
        # Humanized step-by-step trace
        with st.status("Running analysis pipeline...", expanded=True) as status:
            st.write("• **Parsing Command:** Deconstructing syntax, arguments, and execution flags")
            time.sleep(0.3)
            st.write("• **Querying Knowledge Base:** Searching indexed vector store for safety guidelines")
            time.sleep(0.4)
            st.write("• **Assessing Blast Radius:** Evaluating system state impact and recovery potential")
            time.sleep(0.3)
            
            try:
                inputs = {"command": cmd_input, "messages": []}
                response = agent_graph.invoke(inputs)
                status.update(label="Analysis Complete", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Pipeline Execution Failed", state="error")
                st.error(f"Error: {str(e)}")
                return

        # Render structured diagnostic report
        st.markdown("<span class='step-label'>Diagnostic Summary</span>", unsafe_allow_html=True)
        
        if isinstance(response, dict):
            output_text = response.get("output") or response.get("messages", [{}])[-1].content
        else:
            output_text = str(response)

        st.markdown(output_text)
