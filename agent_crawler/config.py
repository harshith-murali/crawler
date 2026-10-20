import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed_urls: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    url_prefixes: list[str] = Field(default_factory=list)
    denied_prefixes: list[str] = Field(default_factory=list)
    max_pages: int = Field(default=30, ge=1, le=10000)
    max_depth: int = Field(default=2, ge=0, le=20)
    max_discovered: int = Field(default=1000, ge=1, le=100000)
    request_timeout: float = Field(default=10, gt=0, le=60)
    delay_seconds: float = Field(default=1, ge=0, le=120)
    retries: int = Field(default=2, ge=0, le=5)
    max_response_bytes: int = Field(default=2000000, ge=1024, le=10000000)
    max_runtime_seconds: float = Field(default=120, gt=0, le=800)
    output_file: str = "output/agent_inventory.csv"
    user_agent: str = "AgentDiscoveryCrawler/0.1"
    search_queries: list[str] = Field(default_factory=list)
    search_max_results: int = Field(default=10, ge=1, le=20)
    llm_provider: str = "none"
    llm_endpoint: str = ""
    llm_model: str = ""

    @model_validator(mode="after")
    def validate_scope(self):
        self.allowed_domains = [d.lower().strip().rstrip(".") for d in self.allowed_domains]
        if any(not d or "/" in d or ":" in d or "*" in d for d in self.allowed_domains):
            raise ValueError(
                "allowed_domains must contain exact hostnames, without wildcards/ports"
            )
        if not self.allowed_domains:
            self.allowed_domains = sorted(
                {urlsplit(u).hostname for u in self.seed_urls if urlsplit(u).hostname}
            )
        if self.llm_provider not in {"none", "json-http"}:
            raise ValueError("llm_provider must be none or json-http")
        if self.llm_provider == "json-http" and not self.llm_endpoint.startswith("https://"):
            raise ValueError("json-http requires an HTTPS llm_endpoint")
        return self


def load_settings(path: str | None = None) -> Settings:
    data = json.loads(Path(path).read_text(encoding="utf-8")) if path else {}
    for name, field in Settings.model_fields.items():
        value = os.getenv(name.upper())
        if value is not None:
            data[name] = json.loads(value) if field.annotation == list[str] else value
    return Settings.model_validate(data)
