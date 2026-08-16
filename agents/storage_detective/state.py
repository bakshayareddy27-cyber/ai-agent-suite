"""
LangGraph state schema for Storage Detective.

Mirrors the SCAN -> CLASSIFY -> INVESTIGATE -> DETERMINE SAFETY ->
PRIORITIZE -> ASK APPROVAL -> CLEAN -> VERIFY workflow described in
the assignment brief. The graph pauses before any deletion — CLEAN
only ever runs on items the UI has recorded as explicitly approved.
"""

from typing import TypedDict, Optional, List, Dict, Any


class StorageDetectiveState(TypedDict, total=False):
    scan_root: Optional[str]

    # SCAN node output
    scan_results: List[Dict[str, Any]]

    # CLASSIFY node output
    classified_items: List[Dict[str, Any]]

    # INVESTIGATE large items node output (RAG-grounded explanation)
    investigation_notes: List[Dict[str, Any]]

    # PRIORITIZE node output
    prioritized_items: List[Dict[str, Any]]
    total_recoverable_bytes: int

    # ASK APPROVAL — filled in by the UI after user interaction, not the graph
    approved_paths: List[str]

    # CLEAN node output (only runs once approved_paths is non-empty)
    clean_results: Dict[str, Any]

    # VERIFY node output
    verification: Dict[str, Any]

    report_markdown: str
