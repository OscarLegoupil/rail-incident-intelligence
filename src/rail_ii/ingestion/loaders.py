from __future__ import annotations

from pathlib import Path

from .document import Document
from .text_normalizer import normalize_text


class TxtLoader:
    """Loader for plain text incident reports."""

    source_type = "txt"

    @classmethod
    def load(cls, source_path: Path | str) -> Document:
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"TXT source path does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"TXT source path must point to a file: {path}")

        raw_text = path.read_text(encoding="utf-8")
        document_id = path.stem
        normalized_text = normalize_text(raw_text)

        return Document(
            document_id=document_id,
            source_path=path,
            source_type=cls.source_type,
            raw_text=raw_text,
            normalized_text=normalized_text,
        )
