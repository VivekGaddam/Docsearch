from app.schemas.search import CitationResponse


class WebSearchService:
    def search(self, query: str) -> tuple[list[str], list[CitationResponse]]:
        summary = (
            f"External web research placeholder for '{query}'. "
            "Integrate Tavily, Exa, SerpAPI, or an internal search gateway in production."
        )
        citation = CitationResponse(
            document_name="Web Search",
            chunk_reference="web:placeholder",
            chunk_id=None,
            source_type="web",
            url="https://example.com/search-integration",
        )
        return [summary], [citation]


web_search_service = WebSearchService()
