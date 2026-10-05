from datetime import datetime, timezone

import pytest
from sujie_gateway.contracts import CONTRACTS, load_json


@pytest.fixture
def fixture_document():
    def read(name):
        return load_json((CONTRACTS / "fixtures" / "valid" / f"{name}.json").read_text("utf-8"))

    return read


@pytest.fixture
def now():
    return datetime(2026, 9, 5, 9, 45, tzinfo=timezone.utc)
