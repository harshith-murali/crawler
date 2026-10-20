from pathlib import Path

import pytest

from agent_crawler.config import Settings
from agent_crawler.http import Fetcher


@pytest.fixture
def html():
    return (Path(__file__).parent / "fixtures/agents.html").read_text(encoding="utf-8")


@pytest.fixture
def settings(tmp_path):
    return Settings(
        seed_urls=["https://docs.example/"],
        delay_seconds=0,
        retries=0,
        output_file=str(tmp_path / "agent_inventory.csv"),
    )


@pytest.fixture
def fetcher(settings):
    # Tests mock every request; no private-destination bypass exists in the CLI.
    f = Fetcher(settings, public_check=lambda _: None)
    yield f
    f.close()
