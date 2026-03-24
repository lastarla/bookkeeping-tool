from __future__ import annotations

from pathlib import Path

from server.bookkeeping.models import FileMeta


SUPPORTED_TYPES = {
    ".csv": "csv",
    ".xlsx": "xlsx",
}


def parse_file_meta(file_path: str | Path) -> FileMeta:
    path = Path(file_path)
    source_type = SUPPORTED_TYPES.get(path.suffix.lower())
    if not source_type:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    stem = path.stem
    parts = stem.split("_") if stem else []
    owner = parts[0].strip() if parts else ""
    if not owner:
        raise ValueError(f"Cannot parse owner from file name: {path.name}")

    platform = parts[1].strip() if len(parts) >= 2 and parts[1].strip() else None
    return FileMeta(
        owner=owner,
        platform=platform,
        source_type=source_type,
        source_file=str(path),
        file_name=path.name,
    )
