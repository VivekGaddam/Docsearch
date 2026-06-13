RETRIEVAL_PIPELINE = {
    "steps": [
        "Embed query for dense retrieval against Qdrant",
        "Run BM25 sparse retrieval over workspace chunk corpus",
        "Merge and deduplicate candidates by chunk_id",
        "Cross-encoder rerank top candidates",
        "Assemble context window with citations",
        "Return answer only if citations are present",
    ],
    "qdrant": {
        "collection_strategy": "one logical collection with workspace_id metadata filter",
        "payload": [
            "workspace_id",
            "document_id",
            "filename",
            "page_number",
            "chunk_id",
            "source_type",
            "upload_time",
        ],
    },
}

