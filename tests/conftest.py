import os

import pytest

os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("OPENAI_API_KEY", "")


@pytest.fixture
def api_key() -> str:
    return os.environ["API_KEY"]
