from sqlalchemy.orm import Session

from app.agents.orchestrator import research_agent
from app.agents.planner import greeting_response, is_greeting
from app.models.agent_run import AgentRun
from app.models.citation import Citation
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResultResponse
from app.services.workspace_service import get_workspace_for_user


class AgentService:
    def answer_query(self, payload: SearchRequest, user: User, db: Session) -> SearchResultResponse:
        get_workspace_for_user(payload.workspace_id, user, db)

        # Fast path for greetings — no agent run overhead
        if is_greeting(payload.query):
            run = self._create_run(payload, user, db, run_type="chat", plan="Greeting — no tools")
            answer = greeting_response(payload.query)
            run.response = answer
            run.status = "completed"
            db.commit()
            return SearchResultResponse(
                answer=answer,
                citations=[],
                run_id=run.id,
                plan=["Detect greeting", "Respond without tools"],
                steps=[],
                mode="chat",
            )

        run = self._create_run(payload, user, db, run_type="agent", plan="Planning…")
        result = research_agent.run(payload, user, db)

        run.response = result.answer
        run.status = "completed"
        run.plan = f"intent={result.intent} confidence={result.confidence:.2f}\n" + "\n".join(result.plan)
        db.commit()
        self._persist_citations(run.id, result.citations, db)

        result.run_id = run.id
        return result

    def _create_run(
        self,
        payload: SearchRequest,
        user: User,
        db: Session,
        run_type: str,
        plan: str,
    ) -> AgentRun:
        run = AgentRun(
            workspace_id=payload.workspace_id,
            user_id=user.id,
            run_type=run_type,
            query=payload.query,
            status="running",
            plan=plan,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    def _persist_citations(self, run_id: str, citations, db: Session) -> None:
        for citation in citations:
            if citation.source_type != "document":
                continue
            db.add(Citation(
                agent_run_id=run_id,
                chunk_id=citation.chunk_id or citation.chunk_reference,
                document_name=citation.document_name,
                page_number=citation.page_number,
                reference_text=citation.chunk_reference,
            ))
        db.commit()


agent_service = AgentService()
