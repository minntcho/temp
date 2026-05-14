from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


def write_csv_chunks(
    *,
    out_dir: Path,
    file_stem: str,
    headers: list[str],
    rows: Iterable[dict[str, object]],
    chunk_size: int,
) -> list[Path]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    current_rows: list[dict[str, object]] = []

    for row in rows:
        current_rows.append(row)
        if len(current_rows) == chunk_size:
            written.append(write_chunk(out_dir, file_stem, headers, current_rows, len(written) + 1))
            current_rows = []

    if current_rows or not written:
        written.append(write_chunk(out_dir, file_stem, headers, current_rows, len(written) + 1))

    return written


def write_chunk(
    out_dir: Path,
    file_stem: str,
    headers: list[str],
    rows: list[dict[str, object]],
    index: int,
) -> Path:
    path = out_dir / f"{file_stem}_part_{index:04d}.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    return path
