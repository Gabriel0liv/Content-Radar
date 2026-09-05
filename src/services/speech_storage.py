from __future__ import annotations

from pathlib import Path
from typing import Iterable


class SpeechStorage:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_filename(filename: str) -> str:
        if not filename or Path(filename).name != filename or "/" in filename or "\\" in filename:
            raise ValueError("Nome de arquivo inválido")
        return filename

    def job_dir(self, job_id: int) -> Path:
        path = self.root / "jobs" / str(job_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def input_dir(self, job_id: int) -> Path:
        path = self.job_dir(job_id) / "input"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def work_dir(self, job_id: int) -> Path:
        path = self.job_dir(job_id) / "work"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def artifacts_dir(self, job_id: int) -> Path:
        path = self.job_dir(job_id) / "artifacts"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def logs_dir(self, job_id: int) -> Path:
        path = self.job_dir(job_id) / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def artifact_path(self, job_id: int, filename: str) -> Path:
        return self.artifacts_dir(job_id) / self._validate_filename(filename)

    def save_input(self, job_id: int, filename: str, chunks: Iterable[bytes]) -> Path:
        safe_name = self._validate_filename(filename)
        destination = self.input_dir(job_id) / safe_name
        with destination.open("wb") as handle:
            for chunk in chunks:
                if chunk:
                    handle.write(chunk)
        return destination

    def safe_storage_key(self, path: Path) -> str:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Caminho fora do armazenamento gerenciado") from exc
        return relative.as_posix()
