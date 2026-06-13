from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.agents.intent_classifier import classify_intent
from app.agents.planner import greeting_response, plan_agent, should_run_web_after_workspace
from app.agents.reasoning_engine import reason_over_evidence
from app.agents.state import AgentState
from app.agents.task_router import task_router
from app.agents.tools import synthesizer_tool, web_search_tool
from app.agents.tools.base import _step
from app.models.user import User
from app.schemas.search import AgentStepResponse, ReasoningStep, SearchRequest, SearchResultResponse


class ResearchAgentOrchestrator:
    """
    Multi-agent research orchestrator.

    New Flow:
      Query
      → Intent Classification (LLM-based, regex fallback)
      → Task Router         (selects specialist agent)
      → Specialist Agent    (summarize | compare | research | qa | extract | general)
      → Reasoning Engine    (chain-of-thought + evidence gap detection)
      → Synthesizer         (intent-specific, human-quality answer)

    Backward-compatible: if no LLM key, gracefully falls back to the
    original planner → workspace_search → synthesize pipeline.
    """

    def run(self, payload: SearchRequest, user: User, db: Session) -> SearchResultResponse:
        state = AgentState(
            query=payload.query,
            workspace_id=payload.workspace_id,
            include_web=payload.include_web,
            top_k=payload.top_k,
        )
        state._user = user

        # ── Node 1: Intent Classification ──────────────────────────────────
        state = classify_intent(state)

        # ── Node 2: Greeting shortcut ──────────────────────────────────────
        if state.intent == "greeting":
            state.is_greeting = True
            state.mode = "chat"
            state.answer = greeting_response(state.query)
            state.plan = ["Detect greeting", "Respond without tools"]
            return self._to_response(state, run_type="chat")

        # ── Node 3: Legacy planner (sets document_scoped, use_comparison, etc.) ──
        # Run for backward compat flags — intent classifier already set intent
        started_plan = time.perf_counter()
        state = plan_agent(state)
        state.steps.append(_step(
            "planner",
            "Plan research workflow",
            f"Plan: {' → '.join(state.plan)}",
            started_plan,
        ))

        # ── Node 4: Task Router → Specialist Agent ─────────────────────────
        state = task_router.route(state, db)

        # ── Node 5: Evaluate — maybe add web search ────────────────────────
        eval_started = time.perf_counter()
        run_web = should_run_web_after_workspace(state)
        state.steps.append(_step(
            "evaluate",
            "Evaluate evidence coverage",
            "Web search added" if run_web else "Workspace evidence sufficient",
            eval_started,
        ))
        if run_web:
            state = web_search_tool.run(state, db)

        # ── Node 6: Reasoning Engine ───────────────────────────────────────
        state = reason_over_evidence(state, db)

        # ── Node 7: Synthesizer ────────────────────────────────────────────
        state = synthesizer_tool.run(state, db)

        return self._to_response(state, run_type="agent")

    def _to_response(self, state: AgentState, run_type: str) -> SearchResultResponse:
        # Convert reasoning chain dicts → ReasoningStep pydantic models
        reasoning_steps = [
            ReasoningStep(
                step=s.get("step", ""),
                thought=s.get("thought", ""),
                conclusion=s.get("conclusion", ""),
            )
            for s in state.reasoning_chain
        ]

        return SearchResultResponse(
            answer=state.answer,
            citations=state.citations,
            run_id="",  # filled by agent_service
            plan=state.plan,
            steps=state.steps,
            mode=state.mode if state.mode != "agent" else run_type,
            # New reasoning/intent fields
            intent=state.intent,
            task_type=state.task_type,
            confidence=state.confidence,
            reasoning_chain=reasoning_steps,
            evidence_gaps=state.evidence_gaps,
            sub_queries=state.sub_queries,
        )


research_agent = ResearchAgentOrchestrator()
