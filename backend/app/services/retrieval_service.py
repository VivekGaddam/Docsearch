from collections import Counter
from math import log

from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.document import Document
from app.schemas.search import CitationResponse


class RetrievalService:
    def __init__(self) -> None:
        self.index: dict[str, list[dict[str, str | int | None]]] = {}

    def index_chunk(self, chunk: Chunk, document_name: str) -> None:
        workspace_chunks = self.index.setdefault(chunk.workspace_id, [])
        workspace_chunks.append(
            {
                "id": chunk.id,
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "document_name": document_name,
                "page_number": chunk.page_number,
                "content": chunk.content,
            }
        )

    def ensure_workspace_index(self, workspace_id: str, db: Session) -> int:
        """Rebuild in-memory index from DB when empty (e.g. after server restart)."""
        if self.index.get(workspace_id):
            return len(self.index[workspace_id])

        rows = (
            db.query(Chunk, Document.filename)
            .join(Document, Chunk.document_id == Document.id)
            .filter(Chunk.workspace_id == workspace_id)
            .all()
        )
        for chunk, filename in rows:
            self.index_chunk(chunk, filename)
        return len(rows)

    def _dedup_chunks(
        self,
        chunks: list[dict],
        citations: list[CitationResponse],
    ) -> tuple[list[str], list[CitationResponse]]:
        """Remove duplicate chunks by content fingerprint."""
        seen_content: set[str] = set()
        seen_ids: set[str] = set()
        out_chunks: list[str] = []
        out_citations: list[CitationResponse] = []
        for chunk, citation in zip(chunks, citations):
            chunk_id = str(citation.chunk_id or citation.chunk_reference)
            # Fingerprint: first 120 chars of content (catches same chunk indexed twice)
            content_fp = str(chunk)[:120].strip().lower()
            if chunk_id in seen_ids or content_fp in seen_content:
                continue
            seen_ids.add(chunk_id)
            seen_content.add(content_fp)
            out_chunks.append(chunk)
            out_citations.append(citation)
        return out_chunks, out_citations

    def get_workspace_overview(
        self,
        workspace_id: str,
        top_k: int = 12,
    ) -> tuple[list[str], list[CitationResponse]]:
        """Return diverse chunks spread across all documents — for overview/summarize queries."""
        chunks = self.index.get(workspace_id, [])
        if not chunks:
            return [], []

        # Group by document_id and interleave to get spread coverage
        doc_buckets: dict[str, list[dict]] = {}
        for c in chunks:
            doc_id = str(c["document_id"])
            doc_buckets.setdefault(doc_id, []).append(c)

        # Round-robin across documents to pick diverse chunks
        selected: list[dict] = []
        bucket_lists = list(doc_buckets.values())
        idx = 0
        while len(selected) < top_k:
            added_any = False
            for bl in bucket_lists:
                if idx < len(bl):
                    selected.append(bl[idx])
                    added_any = True
                    if len(selected) >= top_k:
                        break
            if not added_any:
                break
            idx += 1

        raw_citations = [
            CitationResponse(
                document_name=str(c["document_name"]),
                page_number=c["page_number"] if isinstance(c["page_number"], int) else None,
                chunk_reference=str(c["chunk_id"]),
                chunk_id=str(c["id"]),
            )
            for c in selected
        ]
        raw_contents = [str(c["content"]) for c in selected]
        return self._dedup_chunks(raw_contents, raw_citations)

    def _sparse_score(self, query: str, text: str) -> float:
        terms = query.lower().split()
        if not terms:
            return 0.0
        counts = Counter(text.lower().split())
        return sum((1 + log(counts[term])) for term in terms if term in counts)

    def _dense_score(self, query: str, text: str) -> float:
        query_terms = set(query.lower().split())
        text_terms = set(text.lower().split())
        if not query_terms or not text_terms:
            return 0.0
        overlap = len(query_terms & text_terms)
        union = len(query_terms | text_terms)
        return overlap / union

    def search(self, workspace_id: str, query: str, top_k: int = 5) -> tuple[list[str], list[CitationResponse]]:
        chunks = self.index.get(workspace_id, [])
        scored: list[tuple[float, dict[str, str | int | None]]] = []
        for chunk in chunks:
            dense = self._dense_score(query, str(chunk["content"]))
            sparse = self._sparse_score(query, str(chunk["content"]))
            rerank = dense * 0.5 + sparse * 0.5
            scored.append((rerank, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)

        # Take top_k * 2 candidates then dedup to get top_k unique
        candidates = scored[: top_k * 2]
        top_chunks = [chunk for score, chunk in candidates if score > 0]
        if not top_chunks:
            top_chunks = [chunk for _, chunk in candidates]

        raw_citations = [
            CitationResponse(
                document_name=str(c["document_name"]),
                page_number=c["page_number"] if isinstance(c["page_number"], int) else None,
                chunk_reference=str(c["chunk_id"]),
                chunk_id=str(c["id"]),
            )
            for c in top_chunks
        ]
        raw_contents = [str(c["content"]) for c in top_chunks]

        # Dedup then trim to top_k
        deduped_contents, deduped_citations = self._dedup_chunks(raw_contents, raw_citations)
        return deduped_contents[:top_k], deduped_citations[:top_k]


retrieval_service = RetrievalService()
