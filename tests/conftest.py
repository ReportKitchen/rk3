import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rk3.documents import list_documents  # noqa: E402
from rk3.pipeline import convert  # noqa: E402


@pytest.fixture(scope="session")
def corpus():
    """Convert every source document once per test session. Stage
    fingerprints make this cheap when nothing changed."""
    results = {}
    for d in list_documents():
        results[d["slug"]] = convert(d["slug"])
    return results
