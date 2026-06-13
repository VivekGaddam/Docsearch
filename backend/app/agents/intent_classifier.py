"""
Intent Classifier — Query Understanding Layer

Transforms a raw user query into a structured intent object:
  { intent, task_type, sub_queries, confidence, reasoning }

When the LLM is available, uses a structured JSON prompt.
Falls back to fast regex heuristics when no API key is configured.

Intent taxonomy:
  summarize   — "summarize", "overview", "tldr", "brief", "key points"
  compare     — "compare", "vs", "difference between", "contrast"
  extract     — "list all", "extract", "find all", "what entities", "enumerate"
  research    — "research", "latest", "trends", "how does X work", "find information"
  explain     — "explain", "what is", "how does", "define"
  qa          — factoid questions: "who", "when", "where", "how many", "which companies",
                "can he apply", "is he qualified", "what role"
  greeting    — hi, hello, thanks, bye
  general     — anything else
"""
from __future__ import annotations

import re
import time

from app.agents.state import AgentState
from app.agents.tools.base import _step
from app.services.llm_service import llm_service


# ── Fast regex fallbacks ────────────────────────────────────────────────────
# Ordered by specificity — most specific first

_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    # Greeting — always check first
    ("greeting", [
        r"^(hi|hello|hey|thanks?|thank\s+you|bye|goodbye|ok(?:ay)?|cool|yo)\b",
    ]),

    # Compare — strong signals
    ("compare", [
        r"\bcompare\b", r"\bvs\.?\b", r"\bversus\b",
        r"\bdiff(?:erence)?s?\b", r"\bcontrast\b",
        r"\bbetter\s+(?:than|or)\b", r"\bwhich\s+is\s+(?:better|best|worse)\b",
    ]),

    # Summarize — strong signals
    ("summarize", [
        r"\bsummar(?:ize|y|ise)\b", r"\boverview\b", r"\btldr?\b",
        r"\bbrief(?:ly)?\b", r"\boutline\b", r"\bkey\s+points?\b",
        r"\bmain\s+points?\b", r"\bgist\b", r"\brecap\b",
        r"\bwhat(?:'s|\s+is)\s+(?:in|inside|covered|included)\b",
        r"\bsummarise\b",
    ]),

    # Extract — structured data retrieval
    ("extract", [
        r"\bextract\b", r"\blist\s+all\b", r"\bfind\s+all\b",
        r"\bentit(?:y|ies)\b", r"\benumerat\b", r"\bpull\s+out\b",
        r"\bidentif(?:y|ies)\b.{0,20}\b(?:all|every|each)\b",
        r"\bwhat\s+(?:are\s+(?:all|the)|skills|technologies|tools|languages|frameworks)\b",
        r"\blist\b.{0,20}\b(?:skill|technolog|experience|project|certif)\b",
    ]),

    # QA — factoid / inference questions (BEFORE research to catch "what companies")
    ("qa", [
        # Direct fact questions
        r"\bwho\s+(?:is|was|are|wrote|created|built|made)\b",
        r"\bwhen\s+(?:did|was|is|were|will)\b",
        r"\bwhere\s+(?:is|was|does|did|can)\b",
        r"\bhow\s+many\b", r"\bhow\s+much\b", r"\bhow\s+long\b",
        # Suitability / eligibility / fit questions
        r"\b(?:what|which)\s+compan(?:y|ies)\b",
        r"\b(?:can|could|should|would)\s+(?:he|she|they|this\s+person|candidate)\b",
        r"\bappl(?:y|ied|ying)\s+(?:for|to)\b",
        r"\bsuitable\s+(?:for|to)\b", r"\bqualif(?:ied|ication)\b",
        r"\bfit\s+(?:for|to)\b", r"\bgood\s+(?:for|at|candidate)\b",
        r"\belig(?:ible|ibility)\b",
        r"\bwhat\s+(?:role|position|job|title)\b",
        r"\bhire(?:d|able)?\b", r"\brecruit\b",
        # Profile inference questions
        r"\bstrength\b", r"\bweakness\b", r"\bexpertise\b",
        r"\bspeciali[sz]e\b", r"\bbackground\b",
        r"\bhe\s+(?:has|is|was|can|knows|worked|built|has\s+worked)\b",
        r"\bshe\s+(?:has|is|was|can|knows|worked|built|has\s+worked)\b",
        r"\bcandidate\s+(?:has|is|can|should)\b",
    ]),

    # Explain — concept explanation
    ("explain", [
        r"\bexplain\b", r"\bwhat\s+is\b", r"\bwhat\s+are\b",
        r"\bhow\s+does\b", r"\bhow\s+do\b", r"\bhow\s+to\b",
        r"\bdefine\b", r"\bdescribe\b", r"\bmeaning\s+of\b",
        r"\bwhat\s+does\s+.{1,30}\s+mean\b",
    ]),

    # Research — external/synthesis knowledge
    ("research", [
        r"\bresearch\b", r"\blatest\b", r"\bnews\b",
        r"\btrends?\b", r"\bmarket\b", r"\bmcp\b",
        r"\bstate\s+of\s+the\s+art\b", r"\bcurrent\b",
        r"\binformation\s+(?:about|on)\b", r"\bfind\s+(?:information|info|details)\b",
        r"\btell\s+me\s+about\b", r"\blearn\s+about\b",
    ]),
]


def _regex_classify(query: str) -> dict:
    lowered = query.lower().strip()
    for intent, patterns in _INTENT_PATTERNS:
        for p in patterns:
            if re.search(p, lowered):
                return {
                    "intent": intent,
                    "task_type": intent,
                    "sub_queries": _decompose(query, intent),
                    "confidence": 0.75,
                    "reasoning": f"Regex matched pattern for intent={intent}",
                }
    return {
        "intent": "general",
        "task_type": "general",
        "sub_queries": [query],
        "confidence": 0.5,
        "reasoning": "No strong signal — classified as general",
    }


def _decompose(query: str, intent: str) -> list[str]:
    """Generate useful sub-queries based on intent type."""
    if intent == "summarize":
        return [
            "What are the main topics and sections in the document?",
            "What are the key findings or conclusions?",
            "What is the overall purpose and structure?",
        ]
    if intent == "qa":
        return [query, f"Evidence and context relevant to: {query}"]
    if intent == "extract":
        return [query, f"All items related to: {query}"]
    if intent == "compare":
        return [query, "Key similarities between documents", "Key differences between documents"]
    return [query]


# ── LLM classifier ──────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an expert query intent classifier for a document research assistant.
Analyse the user's query and return ONLY a JSON object (no markdown, no commentary) with these fields:

{
  "intent": "<one of: summarize|compare|extract|research|explain|qa|greeting|general>",
  "task_type": "<same as intent>",
  "sub_queries": ["<sub-question 1>", "<sub-question 2>"],
  "confidence": <float 0–1>,
  "reasoning": "<one sentence explaining the classification>"
}

Intent definitions:
- summarize  → user wants a summary, overview, or key points of document(s)
- compare    → user wants to compare/contrast two or more things
- extract    → user wants a list of entities, facts, skills, or structured data
- research   → user wants external/contextual knowledge or multi-source synthesis
- explain    → user wants a concept explained or defined
- qa         → factoid or inference question — includes "what companies can X apply for",
               "is X qualified for Y", "which roles suit this candidate", "can he/she apply"
- greeting   → social message (hi, thanks, bye)
- general    → does not fit any above category

Sub-queries: decompose the query into 1–3 specific retrieval sub-questions.
Confidence: how certain you are of the intent (1.0 = very certain).

IMPORTANT: Questions about what jobs/companies/roles a person is suitable for → intent=qa
"""


def classify_intent(state: AgentState) -> AgentState:
    """
    Node: classify user intent via LLM (with regex fallback).
    Populates: state.intent, state.task_type, state.sub_queries, state.confidence.
    """
    started = time.perf_counter()

    if not llm_service.is_available():
        result = _regex_classify(state.query)
        _apply(state, result)
        state.steps.append(_step(
            "intent_classifier",
            "Classify query intent",
            f"Intent: {state.intent} (regex, confidence={state.confidence:.0%})",
            started,
        ))
        return state

    result = llm_service.chat_json(_SYSTEM_PROMPT, f"Query: {state.query}")

    if not result or "intent" not in result:
        result = _regex_classify(state.query)

    _apply(state, result)
    state.steps.append(_step(
        "intent_classifier",
        "Classify query intent",
        f"Intent: {state.intent} | Confidence: {state.confidence:.0%}",
        started,
    ))
    return state


def _apply(state: AgentState, result: dict) -> None:
    valid_intents = {"summarize", "compare", "extract", "research", "explain", "qa", "greeting", "general"}
    state.intent = result.get("intent", "general")
    if state.intent not in valid_intents:
        state.intent = "general"
    state.task_type = result.get("task_type", state.intent)
    raw_sub = result.get("sub_queries", [state.query])
    state.sub_queries = [q for q in raw_sub if isinstance(q, str)][:3] or [state.query]
    state.confidence = max(0.0, min(1.0, float(result.get("confidence", 0.75))))
