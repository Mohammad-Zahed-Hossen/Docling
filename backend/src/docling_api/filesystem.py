import re
import shutil
import time
from pathlib import Path
from uuid import uuid4


def safe_stem(filename: str | None) -> str:
    raw_stem = Path(filename or "document").stem
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_stem).strip("._-")
    return normalized[:80] or "document"


class ResultStore:
    def __init__(self, root: Path, ttl_minutes: int) -> None:
        self.jobs_root = root / "jobs"
        self.results_root = root / "results"
        self.ttl_seconds = ttl_minutes * 60
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        self.results_root.mkdir(parents=True, exist_ok=True)

    def create_job(self) -> tuple[str, Path, Path]:
        result_id = uuid4().hex
        job_dir = self.jobs_root / result_id
        result_dir = self.results_root / result_id
        job_dir.mkdir()
        result_dir.mkdir()
        return result_id, job_dir, result_dir

    def cleanup_job(self, job_dir: Path) -> None:
        shutil.rmtree(job_dir, ignore_errors=True)

    def cleanup_result(self, result_dir: Path) -> None:
        shutil.rmtree(result_dir, ignore_errors=True)

    def resolve_result(self, result_id: str, filename: str) -> Path | None:
        if not re.fullmatch(r"[0-9a-f]{32}", result_id):
            return None
        result_dir = self.results_root / result_id
        candidate = result_dir / filename
        if candidate.is_file() and candidate.parent == result_dir:
            return candidate
        return None

    def prune_expired(self) -> None:
        cutoff = time.time() - self.ttl_seconds
        for directory in self.results_root.iterdir():
            try:
                if directory.is_dir() and directory.stat().st_mtime < cutoff:
                    shutil.rmtree(directory, ignore_errors=True)
            except OSError:
                continue
