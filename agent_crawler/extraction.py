import logging
import re

from pydantic import ValidationError

from .finance_profiles import extract_finance_records
from .models import Record, supported
from .source_profiles import extract_profile_records

log = logging.getLogger(__name__)
# Full explicit relationship only; no organization inferred from host or branding.
RELATION = re.compile(
    r"^(?P<organization>[A-Z][\w &.,'-]{1,100}?) "
    r"(?P<verb>deploys|uses|pilots|tests|proposes|plans to deploy) "
    r"(?:an? AI agent (?:named|called) |(?:its |the )?)"
    r"(?P<agent_name>[A-Z][\w &'’-]{1,100}?(?:Agent|Assistant|Copilot)) "
    r"to (?P<task_or_purpose>[^.!?]{3,1000})[.!?]?$"
)


def status_from_text(text: str) -> str:
    # Lifecycle labels are exact explicit values, not keyword guesses (e.g. "not deployed").
    text = text.strip().casefold()
    if text in {"proposes", "proposed", "plans to deploy", "planned", "not yet deployed"}:
        return "documented_proposed"
    if text in {"pilots", "pilot", "experimental", "prototype", "tests", "test", "testing"}:
        return "documented_experimental"
    if text in {"deployed", "deploys", "in production", "uses", "operational"}:
        return "documented_deployed"
    return "documented_use_case"


def extract_records(page) -> list[Record]:
    profile_records = extract_profile_records(page) + extract_finance_records(page)
    # Agent/assistant can also mean a human or physical system: require explicit AI context.
    if not re.search(r"\b(?:AI|artificial intelligence)[ -]+agents?\b", page.text, re.IGNORECASE):
        return profile_records
    candidates = []
    aliases = {
        "task": "task_or_purpose",
        "purpose": "task_or_purpose",
        "agent": "agent_name",
        "department": "department_or_business_function",
        "business_function": "department_or_business_function",
    }
    for table in page.tables:
        for row in table:
            data = {aliases.get(k, k): v for k, v in row.items()}
            if not all(k in data for k in ("organization", "task_or_purpose", "agent_name")):
                continue
            evidence = " ".join(row.values())
            # A generic AI product table must explicitly identify an agent/assistant/copilot.
            if not re.search(
                r"\b(agent|assistant|copilot)\b", data["agent_name"], re.IGNORECASE
            ) and not re.search(r"\bAI agent\b", data.get("type", ""), re.IGNORECASE):
                continue
            candidates.append(
                {k: data[k] for k in ("organization", "task_or_purpose", "agent_name")}
                | {
                    "department_or_business_function": data.get(
                        "department_or_business_function", ""
                    ),
                    "supporting_evidence": evidence,
                    # Infer lifecycle only from an explicit status column.
                    "evidence_status": status_from_text(data.get("status", "")),
                }
            )
    for block in page.blocks:
        match = RELATION.fullmatch(block)
        if match:
            data = match.groupdict()
            verb = data.pop("verb")
            candidates.append(
                data | {"supporting_evidence": block, "evidence_status": status_from_text(verb)}
            )
    records = list(profile_records)
    for data in candidates:
        try:
            record = Record.model_validate(data | {"source_url": page.url})
            if supported(record, page.text, page.url):
                records.append(record)
        except ValidationError:
            log.debug("Rejected incomplete candidate at %s", page.url)
    return records
