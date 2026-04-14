from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .ocbs_sandbox import OCBSSandboxContract


SPEC_PATH = Path(__file__).resolve().parents[2] / "docs" / "ocbs_mock_sandbox_contract.json"


def load_ocbs_sandbox_spec() -> Dict[str, Any]:
    """Load the sample OCBS mock sandbox contract from disk."""
    with SPEC_PATH.open("r", encoding="utf-8") as spec_file:
        return json.load(spec_file)


class OCBSSandboxMock(OCBSSandboxContract):
    """Backward-compatible alias for the in-memory OCBS sandbox mock."""

    pass
