"""
LangGraph workflow for CommandCheck.

Graph shape:

    parse_command
        -> understand_intent
            -> analyze_effects
                -> decide_retrieval (conditional edge)
                    -> retrieve_documentation -> risk_assessment
                    -> risk_assessment   (skipped retrieval)
                        -> find_safer_alternative
                            -> final_verdict -> END

Each node does one job and writes its result into shared state.
The LLM is invoked only in the nodes that genuinely need language
understanding (intent, effects, verdict). Risk scoring and doc
retrieval are grounded in real tools/RAG, not LLM guessing.
"""

import json
from langgraph.graph import StateGraph, END

from agents.commandcheck.state import CommandCheckState
from agents.commandcheck.tools import (
    parse_command,
    assess_risk_heuristics,
    lookup_safer_alternative,
    suggest_verification,
)
from agents.commandcheck.rag import retrieve_docs
from utils.llm import get_llm


# ---------------------------------------------------------------------------
# Node: Parse Command
# ---------------------------------------------------------------------------

def node_parse_command(state: CommandCheckState) -> CommandCheckState:
    parsed = parse_command(state["raw_command"])
    return {
        "parsed": {
            "base_command": parsed.base_command,
            "subcommand": parsed.subcommand,
            "flags": parsed.flags,
            "targets": parsed.targets,
            "shell_type": parsed.shell_type,
            "tokens": parsed.tokens,
        }
    }


# ---------------------------------------------------------------------------
# Node: Understand Intent
# ---------------------------------------------------------------------------

def node_understand_intent(state: CommandCheckState) -> CommandCheckState:
    llm = get_llm(temperature=0.1)
    parsed = state["parsed"]
    prompt = (
        "You are a terminal command intent classifier. In ONE short sentence, "
        "state what the user is trying to accomplish by running this command. "
        "Be specific about scope (what files/data/system are targeted).\n\n"
        f"Command: {state['raw_command']}\n"
        f"Parsed base command: {parsed['base_command']}\n"
        f"Subcommand: {parsed['subcommand']}\n"
        f"Flags: {parsed['flags']}\n"
        f"Targets: {parsed['targets']}\n\n"
        "Respond with only the one-sentence intent, no preamble."
    )
    result = llm.invoke(prompt)
    return {"intent": result.content.strip()}


# ---------------------------------------------------------------------------
# Node: Analyze Effects
# ---------------------------------------------------------------------------

def node_analyze_effects(state: CommandCheckState) -> CommandCheckState:
    llm = get_llm(temperature=0.1)
    prompt = (
        "List the concrete effects of running this command, as short bullet "
        "points (max 5). Focus on what files/data/processes/system state are "
        "actually changed. Respond ONLY with a JSON array of strings, no "
        "markdown fences, no other text.\n\n"
        f"Command: {state['raw_command']}\n"
        f"Intent: {state['intent']}"
    )
    result = llm.invoke(prompt)
    text = result.content.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        effects = json.loads(text)
        if not isinstance(effects, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        # Fall back to treating each line as a bullet if the model didn't
        # return clean JSON — keeps the node resilient rather than failing.
        effects = [line.strip("-• ").strip() for line in text.split("\n") if line.strip()]
    return {"effects": effects}


# ---------------------------------------------------------------------------
# Conditional: Decide whether retrieval is needed
# ---------------------------------------------------------------------------

def decide_retrieval(state: CommandCheckState) -> str:
    """
    The agent decides for itself whether documentation retrieval is
    warranted, rather than always retrieving. Purely read-only commands
    with an already-high-confidence heuristic match skip retrieval to
    save latency; anything else retrieves grounding documentation.
    """
    heuristics = assess_risk_heuristics(state["raw_command"])
    if heuristics["level"] == "SAFE" and heuristics["matched_rules"] > 0:
        return "skip_retrieval"
    return "retrieve"


def node_retrieve_documentation(state: CommandCheckState) -> CommandCheckState:
    query = f"{state['parsed']['base_command']} {state['parsed']['subcommand'] or ''} {' '.join(state['parsed']['flags'])}"
    docs = retrieve_docs(query.strip())
    return {"retrieved_docs": docs, "needs_retrieval": True}


def node_skip_retrieval(state: CommandCheckState) -> CommandCheckState:
    return {"retrieved_docs": [], "needs_retrieval": False}


# ---------------------------------------------------------------------------
# Node: Risk Assessment
# ---------------------------------------------------------------------------

def node_risk_assessment(state: CommandCheckState) -> CommandCheckState:
    heuristics = assess_risk_heuristics(state["raw_command"])
    doc_context = "\n\n".join(
        f"[{d['source']}] {d['content']}" for d in state.get("retrieved_docs", [])
    ) or "No retrieved documentation for this command."

    llm = get_llm(temperature=0.1)
    prompt = (
        "You are assessing the risk level of a terminal command. Use the "
        "deterministic heuristic scan and retrieved documentation below as "
        "grounding — do not contradict the heuristic level unless the "
        "documentation clearly justifies a different level; if you do, briefly "
        "explain why in your reasons.\n\n"
        f"Command: {state['raw_command']}\n"
        f"Effects: {state['effects']}\n"
        f"Heuristic risk level: {heuristics['level']}\n"
        f"Heuristic tags matched: {heuristics['tags']}\n\n"
        f"Retrieved documentation:\n{doc_context}\n\n"
        "Respond ONLY with a JSON object of the form:\n"
        '{"risk_level": "SAFE|LOW|MEDIUM|HIGH|DESTRUCTIVE", "reasons": ["reason1", "reason2"]}\n'
        "No markdown fences, no other text."
    )
    result = llm.invoke(prompt)
    text = result.content.strip().replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(text)
        risk_level = parsed.get("risk_level", heuristics["level"])
        reasons = parsed.get("reasons", [])
    except json.JSONDecodeError:
        risk_level = heuristics["level"] if heuristics["level"] != "UNKNOWN" else "MEDIUM"
        reasons = [f"Matched heuristic pattern(s): {', '.join(heuristics['tags'])}"] if heuristics["tags"] else ["Unable to fully parse model output; defaulted to a cautious estimate."]

    return {"risk_level": risk_level, "risk_reasons": reasons}


# ---------------------------------------------------------------------------
# Node: Find Safer Alternative
# ---------------------------------------------------------------------------

def node_find_safer_alternative(state: CommandCheckState) -> CommandCheckState:
    heuristics = assess_risk_heuristics(state["raw_command"])
    alt = lookup_safer_alternative(heuristics["tags"])
    verification = suggest_verification(state["parsed"]["shell_type"])
    return {"safer_alternative": alt, "verification_command": verification}


# ---------------------------------------------------------------------------
# Node: Final Verdict
# ---------------------------------------------------------------------------

def node_final_verdict(state: CommandCheckState) -> CommandCheckState:
    llm = get_llm(temperature=0.3)
    doc_context = "\n\n".join(
        f"[{d['source']}] {d['content']}" for d in state.get("retrieved_docs", [])
    ) or "No additional documentation was retrieved for this command."

    prompt = (
        "Write the final verdict for a developer tool called CommandCheck that "
        "explains terminal commands before people run them. Tone: direct, "
        "slightly playful, respectful of the reader's intelligence — never "
        "condescending. Use plain language, not corporate hedge-speak.\n\n"
        f"Command: {state['raw_command']}\n"
        f"Intent: {state['intent']}\n"
        f"Effects: {state['effects']}\n"
        f"Risk level: {state['risk_level']}\n"
        f"Risk reasons: {state['risk_reasons']}\n"
        f"Safer alternative: {state.get('safer_alternative') or 'None needed'}\n"
        f"Documentation context:\n{doc_context}\n\n"
        "Respond ONLY with a JSON object:\n"
        "{\n"
        '  "verdict_summary": "one punchy sentence",\n'
        '  "verdict_explanation": "2-4 sentences on what it actually does and why that risk level",\n'
        '  "appropriate_when": "1-2 sentences on when it is actually fine to run this"\n'
        "}\nNo markdown fences, no other text."
    )
    result = llm.invoke(prompt)
    text = result.content.strip().replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {
            "verdict_summary": f"{state['risk_level']} risk command.",
            "verdict_explanation": " ".join(state["effects"]) if state["effects"] else "See risk reasons above.",
            "appropriate_when": "Review the risk reasons above before proceeding.",
        }

    return {
        "verdict_summary": parsed.get("verdict_summary", ""),
        "verdict_explanation": parsed.get("verdict_explanation", ""),
        "appropriate_when": parsed.get("appropriate_when", ""),
    }


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(CommandCheckState)

    graph.add_node("parse_command", node_parse_command)
    graph.add_node("understand_intent", node_understand_intent)
    graph.add_node("analyze_effects", node_analyze_effects)
    graph.add_node("retrieve_documentation", node_retrieve_documentation)
    graph.add_node("skip_retrieval", node_skip_retrieval)
    graph.add_node("risk_assessment", node_risk_assessment)
    graph.add_node("find_safer_alternative", node_find_safer_alternative)
    graph.add_node("final_verdict", node_final_verdict)

    graph.set_entry_point("parse_command")
    graph.add_edge("parse_command", "understand_intent")
    graph.add_edge("understand_intent", "analyze_effects")

    graph.add_conditional_edges(
        "analyze_effects",
        decide_retrieval,
        {
            "retrieve": "retrieve_documentation",
            "skip_retrieval": "skip_retrieval",
        },
    )

    graph.add_edge("retrieve_documentation", "risk_assessment")
    graph.add_edge("skip_retrieval", "risk_assessment")
    graph.add_edge("risk_assessment", "find_safer_alternative")
    graph.add_edge("find_safer_alternative", "final_verdict")
    graph.add_edge("final_verdict", END)

    return graph.compile()


def run_commandcheck(command: str) -> dict:
    """Entry point used by the Streamlit UI."""
    app = build_graph()
    final_state = app.invoke({"raw_command": command})
    return final_state
