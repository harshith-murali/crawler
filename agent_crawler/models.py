import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .urls import normalize_url

FIELDS = [
    "organization",
    "task_or_purpose",
    "agent_name",
    "department_or_business_function",
    "source_url",
    "supporting_evidence",
    "evidence_status",
]


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    organization: str = Field(min_length=1, max_length=300)
    task_or_purpose: str = Field(min_length=1, max_length=2000)
    agent_name: str = Field(min_length=1, max_length=300)
    department_or_business_function: str = Field(default="", max_length=300)
    source_url: str
    supporting_evidence: str = Field(min_length=1, max_length=4000)
    evidence_status: Literal[
        "documented_use_case",
        "documented_deployed",
        "documented_experimental",
        "documented_proposed",
    ]

    @field_validator("organization", "task_or_purpose", "agent_name", "supporting_evidence")
    @classmethod
    def nonempty(cls, value):
        value = compact(value)
        if not value or value.lower() in {
            "unknown",
            "n/a",
            "none",
            "null",
            "ai",
            "agent",
            "ai agent",
            "agents",
        }:
            raise ValueError("missing or generic required field")
        return value

    @field_validator("source_url")
    @classmethod
    def source(cls, value):
        normalized = normalize_url(value)
        if not normalized:
            raise ValueError("invalid source URL")
        return normalized


class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    records: list[Record] = Field(max_length=100)


def evidence_in_source(evidence: str, text: str) -> bool:
    """Allow explicitly marked omissions; every quoted fragment must occur in source order."""
    text = compact(text)
    evidence = compact(evidence)
    if evidence in text:
        return True
    fragments = evidence.split(" […] ")
    if len(fragments) < 2 or any(not fragment.strip() for fragment in fragments):
        return False
    position = 0
    for fragment in fragments:
        start = text.find(fragment, position)
        if start < 0:
            return False
        position = start + len(fragment)
    return True


def supported(record: Record, text: str, url: str) -> bool:
    evidence = compact(record.supporting_evidence)
    return (
        record.source_url == url
        and evidence_in_source(evidence, text)
        and all(
            compact(value).casefold() in evidence.casefold()
            for value in (record.agent_name, record.organization, record.task_or_purpose)
        )
        and (
            not record.department_or_business_function
            or compact(record.department_or_business_function).casefold() in evidence.casefold()
        )
    )


def deduplicate(records: list[Record]) -> list[Record]:
    # Keep distinct named agents separate. Preserve the first supported source and status.
    result, seen = [], set()
    for record in records:
        key = tuple(
            compact(getattr(record, k)).casefold()
            for k in (
                "organization",
                "agent_name",
                "task_or_purpose",
                "department_or_business_function",
            )
        )
        if key not in seen:
            seen.add(key)
            result.append(record)
    return result
