"""
LangGraph workflow for Storage Detective.

Because this workflow has a genuine human-in-the-loop step (nothing
gets deleted without explicit approval), it's implemented as TWO
LangGraph graphs run in sequence by the UI, rather than one graph that
pauses mid-execution. This is a standard, honest way to model
human-approval gates in a Streamlit app (which re-runs top-to-bottom
on every interaction, unlike a long-lived backend process):

  Graph A (investigation_graph):
    scan -> classify -> investigate_large_items -> prioritize -> END
    (stops right before any destructive action; hands control back to
     the UI, which renders checkboxes for the user to approve items)

  Graph B (cleanup_graph):
    clean_approved -> verify -> END
    (only invoked after the UI collects explicit approved_paths)
"""

from langgraph.graph import StateGraph, END

from agents.storage_detective.state import StorageDetectiveState
from agents.storage_detective.tools import (
    scan_storage,
    classify_safety,
    clean_approved_items,
    verify_cleanup,
    find_virtualenvs,
    human_size,
)
from agents.storage_detective.rag import retrieve_docs
from utils.llm import get_llm

import json


# ---------------------------------------------------------------------------
# Graph A: Investigation (scan -> classify -> investigate -> prioritize)
# ---------------------------------------------------------------------------

def node_scan(state: StorageDetectiveState) -> StorageDetectiveState:
    results = scan_storage(state.get("scan_root"))
    return {
        "scan_results": [
            {
                "category": r.category,
                "path": r.path,
                "size_bytes": r.size_bytes,
                "exists": r.exists,
                "item_count": r.item_count,
            }
            for r in results
        ]
    }


def node_classify(state: StorageDetectiveState) -> StorageDetectiveState:
    classified = []
    for item in state["scan_results"]:
        if item["size_bytes"] == 0:
            continue
        has_manifest = None
        if item["category"] == "Old Python Virtual Environments":
            venvs = find_virtualenvs(state.get("scan_root") or None)
            has_manifest = all(v["has_manifest"] for v in venvs) if venvs else None
        safety = classify_safety(item["category"], has_manifest=has_manifest)
        classified.append({**item, **safety})
    return {"classified_items": classified}


def node_investigate_large_items(state: StorageDetectiveState) -> StorageDetectiveState:
    """
    For each significant item, retrieves grounded documentation (RAG)
    and asks the LLM to produce a short, specific explanation of why
    it is or isn't safe to clean — this is the "forensic" reasoning step.
    """
    llm = get_llm(temperature=0.2)
    notes = []
    # Only deep-investigate items above a noise threshold to keep this fast
    significant = [i for i in state["classified_items"] if i["size_bytes"] > 5 * 1024 * 1024]

    for item in significant:
        docs = retrieve_docs(item["category"], k=2)
        doc_context = "\n\n".join(f"[{d['source']}] {d['content']}" for d in docs) or "No documentation retrieved."

        prompt = (
            "You are Storage Detective, a forensic-toned but genuinely helpful "
            "disk-space investigator. Explain in 1-2 sentences why the item "
            "below is or isn't safe to clean, grounded in the documentation "
            "context. Be specific, not generic.\n\n"
            f"Category: {item['category']}\n"
            f"Path: {item['path']}\n"
            f"Size: {human_size(item['size_bytes'])}\n"
            f"Preliminary safety classification: {item['safety']}\n"
            f"Documentation context:\n{doc_context}\n\n"
            "Respond with ONLY the explanation sentence(s), no preamble."
        )
        result = llm.invoke(prompt)
        notes.append({
            "category": item["category"],
            "path": item["path"],
            "explanation": result.content.strip(),
            "sources": [d["source"] for d in docs],
        })
    return {"investigation_notes": notes}


def node_prioritize(state: StorageDetectiveState) -> StorageDetectiveState:
    """
    Ranks items by (safety tier, size) so the biggest genuinely-safe
    wins surface first — the "prioritize cleanup" step in the brief.
    """
    safety_rank = {"SAFE": 0, "CONDITIONAL": 1, "CAUTION": 2, "NEVER_AUTO": 3}
    notes_by_category = {n["category"]: n for n in state.get("investigation_notes", [])}

    items = []
    for item in state["classified_items"]:
        note = notes_by_category.get(item["category"])
        items.append({
            **item,
            "explanation": note["explanation"] if note else None,
            "sources": note["sources"] if note else [],
        })

    items.sort(key=lambda i: (safety_rank.get(i["safety"], 9), -i["size_bytes"]))

    recoverable = sum(i["size_bytes"] for i in items if i["safety"] in ("SAFE", "CONDITIONAL"))

    return {"prioritized_items": items, "total_recoverable_bytes": recoverable}


def build_investigation_graph():
    graph = StateGraph(StorageDetectiveState)
    graph.add_node("scan", node_scan)
    graph.add_node("classify", node_classify)
    graph.add_node("investigate_large_items", node_investigate_large_items)
    graph.add_node("prioritize", node_prioritize)

    graph.set_entry_point("scan")
    graph.add_edge("scan", "classify")
    graph.add_edge("classify", "investigate_large_items")
    graph.add_edge("investigate_large_items", "prioritize")
    graph.add_edge("prioritize", END)

    return graph.compile()


def run_investigation(scan_root: str | None = None) -> dict:
    app = build_investigation_graph()
    return app.invoke({"scan_root": scan_root})


# ---------------------------------------------------------------------------
# Graph B: Cleanup (clean_approved -> verify) — only runs post-approval
# ---------------------------------------------------------------------------

def node_clean_approved(state: StorageDetectiveState) -> StorageDetectiveState:
    approved = state.get("approved_paths", [])
    results = clean_approved_items(approved, dry_run=False)
    return {"clean_results": results}


def node_verify(state: StorageDetectiveState) -> StorageDetectiveState:
    approved = state.get("approved_paths", [])
    verification = verify_cleanup(approved)
    return {"verification": verification}


def build_cleanup_graph():
    graph = StateGraph(StorageDetectiveState)
    graph.add_node("clean_approved", node_clean_approved)
    graph.add_node("verify", node_verify)

    graph.set_entry_point("clean_approved")
    graph.add_edge("clean_approved", "verify")
    graph.add_edge("verify", END)

    return graph.compile()


def run_cleanup(approved_paths: list[str]) -> dict:
    if not approved_paths:
        return {"clean_results": {"deleted": [], "skipped": [], "errors": [], "freed_bytes": 0}, "verification": {"fully_cleared": True, "still_present": [], "cleared_count": 0}}
    app = build_cleanup_graph()
    return app.invoke({"approved_paths": approved_paths})
