WORKER_TASKS = [
    "document_ingestion",
    "embedding_generation",
    "sparse_index_refresh",
    "report_export",
    "connector_sync",
]


def main() -> None:
    for task in WORKER_TASKS:
        print(f"registered task: {task}")


if __name__ == "__main__":
    main()
