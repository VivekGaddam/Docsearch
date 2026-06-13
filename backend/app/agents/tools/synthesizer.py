from __future__ import annotations

import re
import time
from collections import defaultdict

from sqlalchemy.orm import Session

from app.agents.state import AgentState
from app.agents.tools.base import _step
from app.schemas.search import CitationResponse
from app.services.llm_service import llm_service


# ── Intent-specific LLM system prompts ─────────────────────────────────────

_SYSTEM_PROMPTS: dict[str, str] = {
    "summarize": (
        "You are an expert research analyst. Read the provided document evidence and produce a "
        "comprehensive, SYNTHESIZED summary — do NOT copy-paste raw text. Analyse, condense, and "
        "reorganise the content into these sections:\n"
        "## Executive Summary (2-3 sentences)\n"
        "## Key Highlights (bullet list of 5-8 most important points)\n"
        "## Detailed Findings (organised by theme)\n"
        "## Conclusion\n"
        "Be analytical, not descriptive. Paraphrase, don't quote verbatim."
    ),
    "compare": (
        "You are an expert analyst specialising in comparative analysis. "
        "SYNTHESIZE a comparison — do NOT repeat raw content. "
        "Use: ## Overview, ## Similarities, ## Key Differences (table if applicable), "
        "## Recommendation. Be direct about which is better and why."
    ),
    "extract": (
        "You are a data extraction expert. Extract and ORGANISE information — do NOT dump raw text. "
        "Present: ## Extracted Items (grouped by category), ## Key Facts, ## Summary. "
        "Use bullet lists and tables, not paragraphs."
    ),
    "research": (
        "You are a senior research analyst. SYNTHESIZE the evidence into an insightful brief — "
        "draw connections, identify patterns, and provide analysis beyond what's literally written. "
        "Use: ## Research Summary, ## Key Findings (with analysis), ## Insights & Implications, "
        "## Conclusion. Show reasoning, not just facts."
    ),
    "qa": (
        "You are a precise assistant. Answer the SPECIFIC question asked — give a direct answer first, "
        "then supporting evidence. Do NOT copy-paste document content. "
        "If the question asks about suitability (e.g. 'what companies can X apply for'), "
        "reason from the skills and experience to give specific, actionable recommendations. "
        "Format: ## Direct Answer, ## Supporting Evidence, ## Recommendations (if applicable)."
    ),
    "explain": (
        "You are a knowledgeable explainer. Make the topic clear and accessible. "
        "Use: ## What It Is, ## How It Works, ## Why It Matters, ## Key Takeaways. "
        "Use analogies and examples. Synthesize — don't quote raw text."
    ),
    "general": (
        "You are a helpful research assistant. Answer the question by SYNTHESIZING the evidence — "
        "do NOT reproduce raw document text verbatim. Draw insights, connect ideas, and produce "
        "a clear, well-structured answer in markdown. End with ## Sources."
    ),
}

_BASE_INSTRUCTION = (
    "\n\nCRITICAL RULES:\n"
    "1. SYNTHESIZE — do not copy-paste raw document text. Analyse and reorganise it.\n"
    "2. Answer the SPECIFIC question asked. Stay focused.\n"
    "3. Use markdown formatting with clear sections.\n"
    "4. End with ## Sources listing all citations.\n"
    "5. If you cannot answer from the evidence, say so honestly."
)


class SynthesizerTool:
    name = "synthesizer"
    label = "Synthesize answer"

    def run(self, state: AgentState, db: Session) -> AgentState:
        started = time.perf_counter()

        if not state.contexts:
            if state.document_scoped:
                state.answer = (
                    "No document content is available in this workspace. "
                    "Upload PDF, DOCX, or other supported files, then ask again."
                )
            else:
                state.answer = (
                    "I couldn't find relevant evidence in your workspace or external sources. "
                    "Try uploading documents or rephrasing your question."
                )
            state.citations = state.citations or [CitationResponse(
                document_name="No source available",
                chunk_reference="unavailable",
                source_type="system",
            )]
            state.steps.append(_step(self.name, self.label, "No evidence to synthesize", started, status="failed"))
            return state

        # Deduplicate contexts before synthesis
        state.contexts, state.citations = self._dedup(state.contexts, state.citations)

        state.answer = self._synthesize(state)
        if not state.citations:
            state.citations = [CitationResponse(
                document_name="No source available",
                chunk_reference="unavailable",
                source_type="system",
            )]

        doc_count = sum(1 for c in state.citations if c.source_type == "document")
        web_count = sum(1 for c in state.citations if c.source_type == "web")
        state.steps.append(_step(
            self.name,
            self.label,
            f"Synthesized {state.intent} answer from {doc_count} doc + {web_count} web source(s)",
            started,
        ))
        return state

    # ── Deduplication ────────────────────────────────────────────────────────

    def _dedup(
        self, contexts: list[str], citations: list[CitationResponse]
    ) -> tuple[list[str], list[CitationResponse]]:
        seen: set[str] = set()
        out_ctx: list[str] = []
        out_cit: list[CitationResponse] = []
        for ctx, cit in zip(contexts, citations):
            fp = ctx[:120].strip().lower()
            if fp not in seen:
                seen.add(fp)
                out_ctx.append(ctx)
                out_cit.append(cit)
        return out_ctx, out_cit

    # ── LLM synthesis ────────────────────────────────────────────────────────

    def _build_sources_block(self, state: AgentState) -> str:
        lines = []
        seen: set[str] = set()
        for c in state.citations[:12]:
            key = f"{c.document_name}:{c.page_number}"
            if key in seen:
                continue
            seen.add(key)
            if c.source_type == "document":
                page = f" p.{c.page_number}" if c.page_number else ""
                lines.append(f"- 📄 {c.document_name}{page}")
            elif c.url:
                lines.append(f"- 🌐 [{c.document_name}]({c.url})")
            else:
                lines.append(f"- {c.document_name}")
        return "\n".join(lines)

    def _synthesize(self, state: AgentState) -> str:
        combined = "\n\n---\n\n".join(state.contexts[:8])
        if len(combined) > 9000:
            combined = combined[:9000] + "\n…[truncated]"

        sources_block = self._build_sources_block(state)
        system_prompt = _SYSTEM_PROMPTS.get(state.intent, _SYSTEM_PROMPTS["general"]) + _BASE_INSTRUCTION

        sub_qs_block = ""
        if state.sub_queries and state.sub_queries != [state.query]:
            sub_qs_block = "Sub-questions to address:\n" + "\n".join(f"- {q}" for q in state.sub_queries) + "\n\n"

        reasoning_block = ""
        if state.reasoning_chain:
            lines = ["Reasoning steps:\n"]
            for s in state.reasoning_chain:
                lines.append(f"- {s.get('step', '')}: {s.get('conclusion', '')}")
            reasoning_block = "\n".join(lines) + "\n\n"

        user_prompt = (
            f"Question: {state.query}\n"
            f"Intent: {state.intent}\n\n"
            f"{sub_qs_block}"
            f"{reasoning_block}"
            f"Evidence from documents:\n{combined}\n\n"
            f"Sources:\n{sources_block}"
        )

        if llm_service.is_available():
            answer = llm_service.chat(system_prompt, user_prompt, temperature=0.25)
            if answer:
                return answer

        # ── Smart fallback (no LLM) ──────────────────────────────────────────
        return self._smart_fallback(state, sources_block)

    # ── Smart fallback — no LLM ──────────────────────────────────────────────

    def _smart_fallback(self, state: AgentState, sources_block: str) -> str:
        """
        Intent-aware structured fallback when no LLM is available.
        Organises chunks intelligently instead of dumping raw text.
        """
        intent = state.intent
        query = state.query
        contexts = state.contexts[:6]

        if intent == "summarize":
            return self._fallback_summarize(contexts, sources_block)
        elif intent == "qa":
            return self._fallback_qa(query, contexts, sources_block)
        elif intent == "extract":
            return self._fallback_extract(query, contexts, sources_block)
        elif intent == "compare":
            return self._fallback_compare(contexts, sources_block)
        else:
            return self._fallback_general(query, contexts, sources_block)

    def _extract_bullets(self, text: str) -> list[str]:
        """Extract bullet-point-like lines from chunk text."""
        bullets = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith(("•", "-", "*", "·")):
                bullets.append(line.lstrip("•-*· ").strip())
            elif re.match(r"^\d+[\.\)]\s", line):
                bullets.append(re.sub(r"^\d+[\.\)]\s+", "", line).strip())
            elif len(line) > 30 and line[0].isupper() and not line.endswith(":"):
                bullets.append(line)
        return [b for b in bullets if len(b) > 10][:5]

    def _extract_section_heading(self, text: str) -> str:
        """Try to find a section heading in the chunk."""
        for line in text.split("\n")[:4]:
            line = line.strip()
            if line and len(line) < 60 and line[0].isupper() and not line.endswith("."):
                return line
        return ""

    def _fallback_summarize(self, contexts: list[str], sources_block: str) -> str:
        lines = ["## Document Summary\n"]
        lines.append("*Here are the key points extracted from your document(s):*\n")

        all_bullets: list[str] = []
        section_content: dict[str, list[str]] = defaultdict(list)

        for ctx in contexts:
            heading = self._extract_section_heading(ctx)
            bullets = self._extract_bullets(ctx)
            if heading and bullets:
                section_content[heading].extend(bullets[:3])
            else:
                all_bullets.extend(bullets[:3])

        if section_content:
            lines.append("## Key Sections\n")
            for heading, points in list(section_content.items())[:5]:
                lines.append(f"### {heading}")
                for p in points[:3]:
                    lines.append(f"- {p}")
                lines.append("")

        if all_bullets:
            lines.append("## Additional Key Points\n")
            for b in all_bullets[:8]:
                lines.append(f"- {b}")
            lines.append("")

        if not section_content and not all_bullets:
            # Last resort: first 800 chars of first chunk, cleanly formatted
            snippet = contexts[0][:800].strip() if contexts else ""
            lines.append(f"\n{snippet}\n")

        lines.append(f"\n## Sources\n\n{sources_block}")
        lines.append("\n\n> 💡 **Tip**: Configure an OpenAI-compatible API key for richer, synthesized summaries.")
        return "\n".join(lines)

    def _fallback_qa(self, query: str, contexts: list[str], sources_block: str) -> str:
        lines = [f"## Answer: {query}\n"]

        # For company/role suitability questions, look for skills/experience
        is_suitability = any(kw in query.lower() for kw in [
            "compan", "apply", "job", "role", "position", "hire", "suitable", "qualify", "fit"
        ])

        if is_suitability:
            lines.append("*Based on the document content, here is the relevant information:*\n")
            skills_found: list[str] = []
            exp_found: list[str] = []

            for ctx in contexts:
                ctx_lower = ctx.lower()
                bullets = self._extract_bullets(ctx)
                if any(kw in ctx_lower for kw in ["skill", "language", "framework", "technolog", "tool"]):
                    skills_found.extend(bullets[:4])
                if any(kw in ctx_lower for kw in ["experience", "engineer", "developer", "worked", "built", "delivered"]):
                    exp_found.extend(bullets[:4])

            if skills_found:
                lines.append("### Technical Skills & Expertise")
                for s in skills_found[:6]:
                    lines.append(f"- {s}")
                lines.append("")

            if exp_found:
                lines.append("### Experience Highlights")
                for e in exp_found[:6]:
                    lines.append(f"- {e}")
                lines.append("")

            lines.append(
                "### To get a full analysis\n"
                "Configure an AI API key to get specific company/role recommendations "
                "based on these skills and experience."
            )
        else:
            # Generic QA: find the most relevant passage
            most_relevant = contexts[0] if contexts else ""
            # Extract the most relevant paragraph
            paragraphs = [p.strip() for p in most_relevant.split("\n\n") if len(p.strip()) > 40]
            if paragraphs:
                lines.append("*Most relevant passage from your documents:*\n")
                lines.append(f"> {paragraphs[0][:500]}")
                if len(paragraphs) > 1:
                    lines.append(f"\n> {paragraphs[1][:300]}")
            else:
                lines.append(most_relevant[:600])

        lines.append(f"\n## Sources\n\n{sources_block}")
        lines.append("\n\n> 💡 **Tip**: Configure an OpenAI-compatible API key for direct, synthesized answers.")
        return "\n".join(lines)

    def _fallback_extract(self, query: str, contexts: list[str], sources_block: str) -> str:
        lines = [f"## Extracted Information: {query}\n"]

        all_items: list[str] = []
        for ctx in contexts:
            items = self._extract_bullets(ctx)
            all_items.extend(items[:5])

        if all_items:
            lines.append("### Found Items\n")
            # Deduplicate
            seen: set[str] = set()
            for item in all_items:
                fp = item[:50].lower()
                if fp not in seen:
                    seen.add(fp)
                    lines.append(f"- {item}")
        else:
            lines.append(f"{contexts[0][:800] if contexts else 'No content found.'}")

        lines.append(f"\n## Sources\n\n{sources_block}")
        return "\n".join(lines)

    def _fallback_compare(self, contexts: list[str], sources_block: str) -> str:
        lines = ["## Comparison\n"]
        lines.append("*Content from your workspace documents:*\n")
        for i, ctx in enumerate(contexts[:3], 1):
            heading = self._extract_section_heading(ctx) or f"Section {i}"
            bullets = self._extract_bullets(ctx)
            lines.append(f"### {heading}")
            for b in bullets[:4]:
                lines.append(f"- {b}")
            lines.append("")
        lines.append(f"\n## Sources\n\n{sources_block}")
        lines.append("\n\n> 💡 **Tip**: Configure an API key for a structured comparison table.")
        return "\n".join(lines)

    def _fallback_general(self, query: str, contexts: list[str], sources_block: str) -> str:
        lines = [f"## Response to: {query}\n"]
        lines.append("*Relevant excerpts from your documents:*\n")

        for i, ctx in enumerate(contexts[:4], 1):
            heading = self._extract_section_heading(ctx) or f"Excerpt {i}"
            bullets = self._extract_bullets(ctx)
            lines.append(f"### {heading}")
            if bullets:
                for b in bullets[:4]:
                    lines.append(f"- {b}")
            else:
                lines.append(ctx[:400].strip())
            lines.append("")

        lines.append(f"\n## Sources\n\n{sources_block}")
        lines.append("\n\n> 💡 **Tip**: Configure an OpenAI-compatible API key for synthesized, intelligent answers.")
        return "\n".join(lines)


synthesizer_tool = SynthesizerTool()
