from pathlib import Path

from fastapi import UploadFile


class LocalObjectStorage:
    def __init__(self, base_path: str = "storage") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save_document(self, workspace_id: str, file: UploadFile) -> str:
        workspace_dir = self.base_path / workspace_id / "documents"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        destination = workspace_dir / file.filename
        with destination.open("wb") as output:
            output.write(await file.read())
        return str(destination)


storage_service = LocalObjectStorage()

