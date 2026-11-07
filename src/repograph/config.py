"""Host-owned configuration; repository files cannot change server policy."""

import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    root: Path
    database: Path
    max_file_bytes: int = Field(default=2_000_000, ge=1, le=50_000_000)
    max_files: int = Field(default=20_000, ge=1, le=1_000_000)
    max_total_bytes: int = Field(default=100_000_000, ge=1)

    @classmethod
    def load(cls, root: Path | None = None, database: Path | None = None) -> "Settings":
        root = (root or Path(os.environ.get("REPOGRAPH_ROOT", "."))).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Repository root must be a directory")
        database = database or Path(
            os.environ.get("REPOGRAPH_DATABASE", str(root / ".repograph" / "index.sqlite3"))
        )
        return cls(root=root, database=database.resolve())
