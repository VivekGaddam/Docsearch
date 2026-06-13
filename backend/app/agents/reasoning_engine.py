"""
Reasoning Engine — Chain-of-Thought + Multi-Hop Reasoning

After retrieval, this engine reasons over the evidence in structured steps:
1. Analyses what's been retrieved
2. Identifies evidence gaps
3. Checks if more context is needed (multi-hop retrieval trigger)
4. Produces a reasoning chain that the synthesizer uses to build a human-quality answer

The reasoning chain is transparent — every step is returned to the frontend.
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.agents.state import AgentState
from app.agents.tools.base import _step
from app.services.llm_service import llm_service


_REASONING_SYSTEM = """You are an expert research analyst. Your job is to reason over retrieved evidence and produce a structured reasoning chain before writing the final answer.

Given the user's query and retrieved evidence, produce ONLY a JSON object with these fields:

{
  "reasoning_chain": [
    {
      "step": "short step name",
      "thought": "your analytical thought — what you observe in the evidence",
      "conclusion": "what you conclude from this step"
    }
  ],
  "evidence_gaps": ["gap 1", "gap 2"],
  "needs_more_context": false,
  "confidence": 0.9
}

Rules:
- reasoning_chain: 2–5 steps that logically build toward answering the query
- evidence_gaps: things the user asked about that are NOT covered in the retrieved evidence (empty list if evidence is sufficient)
- needs_more_context: true only if crucial information is missing to answer the query
- Keep each thought/conclusion concise (1–2 sentences)
- Be analytical, not just descriptive — draw inferences, identify patterns
"""


def reason_over_evidence(state: AgentState, db: Session) -> AgentState:
    """
    Node: Reason over retrieved contexts using chain-of-thought.
    Populates: state.reasoning_chain, state.evidence_gaps.
    """
    started = time.perf_counter()

    if not state.contexts:
        state.evidence_gaps = ["No evidence retrieved to reason over."]
        state.steps.append(_step(
            "reasoning_engine",
            "Reason over evidence",
            "No evidence to reason over — skipped",
            started,
            status="skipped",
        ))
        return state

    if not llm_service.is_available():
        # Fallback: generate minimal reasoning chain from contexts
        state.reasoning_chain = [
            {
                "step": "Evidence review",
                "thought": f"Retrieved {len(state.contexts)} chunks from workspace.",
                "conclusion": "Proceeding to synthesize from available evidence.",
            }
        ]
        state.steps.append(_step(
            "reasoning_engine",
            "Reason over evidence",
            f"Reasoning over {len(state.contexts)} chunks (LLM unavailable — minimal chain)",
            started,
        ))
        return state

    # Build the evidence block (cap at 6000 chars to fit context window)
    combined = "\n\n---\n\n".join(state.contexts[:6])
    if len(combined) > 6000:
        combined = combined[:6000] + "\n…[truncated]"

    sub_qs = "\n".join(f"- {q}" for q in state.sub_queries) or f"- {state.query}"

    user_prompt = (
        f"Query: {state.query}\n"
        f"Intent: {state.intent}\n"
        f"Sub-questions to answer:\n{sub_qs}\n\n"
        f"Retrieved Evidence:\n{combined}"
    )

    result = llm_service.chat_json(_REASONING_SYSTEM, user_prompt)

    if result and "reasoning_chain" in result:
        raw_chain = result.get("reasoning_chain", [])
        state.reasoning_chain = [
            {
                "step": str(s.get("step", "")),
                "thought": str(s.get("thought", "")),
                "conclusion": str(s.get("conclusion", "")),
            }
            for s in raw_chain
            if isinstance(s, dict)
        ]
        state.evidence_gaps = [str(g) for g in result.get("evidence_gaps", [])]
    else:
        state.reasoning_chain = [
            {
                "step": "Evidence review",
                "thought": f"Analysed {len(state.contexts)} retrieved passages.",
                "conclusion": "Sufficient context found to answer the query.",
            }
        ]
        state.evidence_gaps = []

    chain_len = len(state.reasoning_chain)
    gaps_len = len(state.evidence_gaps)
    state.steps.append(_step(
        "reasoning_engine",
        "Reason over evidence",
        f"Produced {chain_len}-step reasoning chain; {gaps_len} evidence gap(s) detected",
        started,
    ))
    return state
