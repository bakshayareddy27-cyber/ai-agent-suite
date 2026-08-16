"""
LangGraph state schema for CommandCheck.

Every node reads from and writes to this shared state. Using a
TypedDict (LangGraph's standard pattern) makes the data flow between
nodes explicit and inspectable — useful both for correctness and for
demoing exactly how the agent "thinks" step by step.
"""

from typing import TypedDict, Optional, List, Dict, Any


class CommandCheckState(TypedDict, total=False):
    raw_command: str

    # Parse Command node output
    parsed: Dict[str, Any]

    # Understand Intent node output
    intent: str

    # Analyze Effects node output
    effects: List[str]

    # Retrieve Documentation node output
    retrieved_docs: List[Dict[str, str]]
    needs_retrieval: bool

    # Risk Assessment node output
    risk_level: str          # SAFE | LOW | MEDIUM | HIGH | DESTRUCTIVE
    risk_reasons: List[str]

    # Find Safer Alternative node output
    safer_alternative: Optional[str]

    # Verification suggestion
    verification_command: Optional[str]

    # Final Verdict node output
    verdict_summary: str
    verdict_explanation: str
    appropriate_when: str
