from __future__ import annotations

import re

from app.agents.state import AgentState


GREETING_PATTERN = re.compile(
    r"^\s*(hi|hello|hey|howdy|yo|sup|good\s+(morning|afternoon|evening|night)"
    r"|thanks?|thank\s+you|bye|goodbye|ok(?:ay)?|cool|nice)[\s!.?,]*$",
    re.I,
)

# Queries about uploaded/workspace content — never route to web as fallback
DOCUMENT_SCOPED_PATTERNS = [
    r"\bthis\s+(document|file|pdf|resume|cv|report|paper)\b",
    r"\buploaded\b",
    r"\bin\s+(?:my|the|this)\s+workspace\b",
    r"\bthe\s+(document|file|pdf|resume|cv)\b",
    r"\bwhat(?:'s|\s+is)\s+there\b",
    r"\bwhat\s+is\s+in\b",
    r"\bcontents?\s+of\b",
    r"\bsummarize\s+(?:this|the|my)\b",
    r"\bexplain\s+(?:this|the|my)\b",
]

# Signals that external/web knowledge is useful
WEB_SIGNAL_PATTERNS = [
    r"\blatest\b",
    r"\bnews\b",
    r"\bcurrent events\b",
    r"\btoday\b",
    r"\bsearch the web\b",
    r"\bon the internet\b",
    r"\bwhat is\b",
    r"\bwho is\b",
    r"\bhow does\b",
    r"\bexplain\b(?!\s+(?:this|the|my))",
    r"\bresearch\b",
    r"\bmodel context protocol\b",
    r"\bmcp\b",
    r"\btrends?\b",
    r"\bmarket\b",
]

COMPARISON_PATTERNS = [
    r"\bcompare\b",
    r"\bdiff(?:erence)?\b",
    r"\bcontrast\b",
    r"\bvs\.?\b",
    r"\bversus\b",
]

OVERVIEW_PATTERNS = [
    r"\bexplain\b",
    r"\bwhat(?:'s|\s+is)\s+there\b",
    r"\bwhat\s+is\s+in\b",
    r"\bsummarize\b",
    r"\boverview\b",
    r"\bdescribe\b",
]


def is_greeting(query: str) -> bool:
    return bool(GREETING_PATTERN.match(query.strip()))


def is_document_scoped(query: str) -> bool:
    lowered = query.lower()
    return any(re.search(p, lowered) for p in DOCUMENT_SCOPED_PATTERNS)


def suggests_web_search(query: str) -> bool:
    lowered = query.lower()
    return any(re.search(p, lowered) for p in WEB_SIGNAL_PATTERNS)


def suggests_comparison(query: str) -> bool:
    lowered = query.lower()
    return any(re.search(p, lowered) for p in COMPARISON_PATTERNS)


def is_overview_query(query: str) -> bool:
    lowered = query.lower()
    return any(re.search(p, lowered) for p in OVERVIEW_PATTERNS)


def greeting_response(query: str) -> str:
    lowered = query.strip().lower()
    if re.match(r"thanks?|thank\s+you", lowered):
        return "You're welcome! Ask me anything about your workspace documents or external research topics."
    if re.match(r"bye|goodbye", lowered):
        return "Goodbye! Your research sessions and documents are saved in this workspace."
    return (
        "Hello! I'm your research assistant. I can search your workspace documents, "
        "search the web, compare files, and generate cited research answers."
    )


def plan_agent(state: AgentState) -> AgentState:
    """General-purpose planner: selects tools based on query type, not topic."""
    query = state.query

    if is_greeting(query):
        state.is_greeting = True
        state.mode = "chat"
        state.plan = ["Detect greeting", "Respond without tools"]
        return state

    state.document_scoped = is_document_scoped(query)
    state.use_comparison = suggests_comparison(query)
    state.use_web = state.include_web and suggests_web_search(query) and not state.document_scoped

    plan_steps = ["Analyze query and plan tool usage", "Search workspace documents"]

    if state.use_comparison:
        plan_steps.append("Compare workspace documents")
    if state.use_web:
        plan_steps.append("Search external web sources")
    plan_steps.extend(["Evaluate evidence coverage", "Synthesize cited answer"])

    state.plan = plan_steps
    state.mode = "agent"
    return state


def should_run_web_after_workspace(state: AgentState) -> bool:
    """Reflection: only add web if workspace evidence is insufficient AND query needs external knowledge."""
    if not state.include_web or state.document_scoped:
        return False
    if state.use_web:
        return True
    if not state.contexts and suggests_web_search(state.query):
        return True
    return False
