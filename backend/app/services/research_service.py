from sqlalchemy.orm import Session

from app.models.report import Report
from app.models.research_session import ResearchSession
from app.models.user import User
from app.schemas.research import ResearchReportResponse, ResearchRequest
from app.schemas.search import SearchRequest
from app.services.agent_service import agent_service
from app.services.workspace_service import get_workspace_for_user


class ResearchService:
    def run_research(
        self,
        payload: ResearchRequest,
        user: User,
        db: Session,
    ) -> ResearchReportResponse:
        get_workspace_for_user(payload.workspace_id, user, db)

        session = ResearchSession(
            workspace_id=payload.workspace_id,
            user_id=user.id,
            title=payload.session_title,
            query=payload.query,
            status="running",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        agent_result = agent_service.answer_query(
            SearchRequest(
                workspace_id=payload.workspace_id,
                query=payload.query,
                top_k=8,
                include_web=True,
            ),
            user,
            db,
        )
        session.summary = agent_result.answer
        session.status = "completed"

        report_markdown = self._render_report(payload.query, agent_result.answer, agent_result.citations)
        report = Report(
            workspace_id=payload.workspace_id,
            research_session_id=session.id,
            title=f"Research Report - {payload.session_title}",
            format="markdown",
            content=report_markdown,
        )
        db.add(report)
        db.commit()
        db.refresh(session)

        return ResearchReportResponse(
            session=session,
            report_markdown=report_markdown,
            citations=agent_result.citations,
        )

    def _render_report(self, query: str, answer: str, citations) -> str:
        references = "\n".join(
            f"- {citation.document_name} ({citation.chunk_reference})"
            for citation in citations
        )
        return (
            f"# Executive Summary\n\n{answer}\n\n"
            f"# Key Findings\n\n- Research query: {query}\n"
            f"- Evidence synthesized from internal and external sources\n\n"
            f"# Technical Analysis\n\n{answer}\n\n"
            f"# Recommendations\n\n- Validate findings with domain SMEs\n"
            f"- Expand ingestion connectors for broader coverage\n\n"
            f"# References\n\n{references}"
        )


research_service = ResearchService()

