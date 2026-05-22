from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Document:
    document_id: str
    source_path: Path
    source_type: str
    raw_text: str
    normalized_text: str
