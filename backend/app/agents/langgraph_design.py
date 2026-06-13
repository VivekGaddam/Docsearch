"""
LangGraph-compatible agent design — v2: Query Understanding + Reasoning Layer.

Runtime orchestrator: app.agents.orchestrator.ResearchAgentOrchestrator
Implements a 7-node pipeline. LangGraph will formalise conditional edges
once dependency versions align.

Flow:
  User Query
  → IntentClassifier   (LLM-based, regex fallback)
  → Greeting?          → FinalAnswer (no tools)
  → LegacyPlanner      (sets document_scoped / use_comparison flags)
  → TaskRouter         (picks specialist agent)
  → SpecialistAgent    (summarize | compare | research | qa | extract | general)
  → EvaluateEvidence   (should we add web search?)
  → WebSearch          (conditional — only when workspace evidence is thin)
  → ReasoningEngine    (chain-of-thought + evidence gap detection)
  → Synthesizer        (intent-specific template, cites reasoning chain)
  → FinalAnswer
"""

LANGGRAPH_DESIGN = {
    "version": "2.0",
    "nodes": [
        "intent_classifier",
        "planner",
        "task_router",
        # specialist agents (selected dynamically by task_router)
        "summarize_agent",
        "compare_agent",
        "research_agent",
        "qa_agent",
        "extract_agent",
        "general_search",
        # shared nodes
        "evaluate_evidence",
        "web_search_tool",
        "reasoning_engine",
        "synthesizer",
        "final_answer",
    ],
    "edges": [
        ["START", "intent_classifier"],
        ["intent_classifier", "final_answer"],          # greeting
        ["intent_classifier", "planner"],               # all research queries
        ["planner", "task_router"],
        ["task_router", "summarize_agent"],             # intent=summarize
        ["task_router", "compare_agent"],               # intent=compare
        ["task_router", "research_agent"],              # intent=research
        ["task_router", "qa_agent"],                    # intent=qa
        ["task_router", "extract_agent"],               # intent=extract
        ["task_router", "general_search"],              # intent=explain|general
        ["summarize_agent", "evaluate_evidence"],
        ["compare_agent", "evaluate_evidence"],
        ["research_agent", "evaluate_evidence"],
        ["qa_agent", "evaluate_evidence"],
        ["extract_agent", "evaluate_evidence"],
        ["general_search", "evaluate_evidence"],
        ["evaluate_evidence", "web_search_tool"],       # conditional
        ["evaluate_evidence", "reasoning_engine"],
        ["web_search_tool", "reasoning_engine"],
        ["reasoning_engine", "synthesizer"],
        ["synthesizer", "final_answer"],
        ["final_answer", "END"],
    ],
    "tool_registry": [
        "workspace_search",
        "web_search",
        "document_comparison",
        "synthesizer",
        # MCP tools
        "mcp.search_workspace",
        "mcp.classify_intent",
        "mcp.synthesize_answer",
        "mcp.compare_documents",
    ],
    "specialist_registry": {
        "summarize": "SummarizeAgent",
        "compare":   "CompareAgent",
        "research":  "ResearchSpecialistAgent",
        "qa":        "QAAgent",
        "extract":   "ExtractAgent",
    },
    "principles": [
        "Intent-first: LLM classifies query intent before any retrieval",
        "Task-specific agents: each intent routes to an optimised specialist",
        "Multi-hop retrieval: ResearchAgent runs searches per sub-query",
        "Chain-of-thought: ReasoningEngine produces transparent reasoning steps",
        "Evidence gap disclosure: gaps reported in answer and UI",
        "Intent-specific synthesis: each task type uses a tailored output template",
        "Backward-compatible: regex fallback when no LLM key is set",
        "MCP-ready: all core capabilities exposed as MCP tools",
        "Every answer must include citations",
    ],
}
