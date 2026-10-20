"""Small, reviewed parsers for official prose formats; all values come from fetched text.

These identify product capabilities, not enterprise adoption. Only the case-study rule
can identify deployment, and it requires an explicit deployment statement in its evidence.
No stored finding is emitted when a source's URL or prose no longer matches.
"""

import re
from urllib.parse import urlsplit

from .models import Record, supported

# Each pattern captures both organization and named agent in the same source excerpt.
# The rules describe document grammar, not an inventory of manually supplied facts.
PROFILES = [
    (
        "adoption.microsoft.com",
        "/en-us/ai-agents/agents-in-microsoft-365/",
        (
            r"The (?P<agent_name>[A-Z][A-Za-z ]+?) agent works within "
            r"(?P<organization>Microsoft) 365 Copilot Chat to "
            r"(?P<task_or_purpose>[^.]{5,350}?), enabling"
        ),
        "documented_use_case",
    ),
    (
        "trailhead.salesforce.com",
        "/content/learn/modules/agentforce-for-sales-coaching-setup-and-customization/get-to-know-agentforce-sales-coach",
        (
            r"Good news: (?P<organization>Salesforce) now offers a solution that helps managers "
            r"and sales reps alike\. (?P<agent_name>Agentforce [A-Z][A-Za-z ]+?) provides "
            r"(?P<task_or_purpose>[^.]{5,350})\."
        ),
        "documented_use_case",
    ),
    (
        "www.ibm.com",
        "/solutions/ai-assistants",
        (
            r"(?P<agent_name>(?P<organization>IBM) watsonx[™®]? Code Assistant) "
            r"AI coding assistants for enterprise developers "
            r"(?P<task_or_purpose>[^.]{5,350})\."
        ),
        "documented_use_case",
    ),
    (
        "www.ibm.com",
        "/case-studies/camping-world",
        (
            r"The solution, powered by IBM watsonx Assistant, [^.]{5,250} was deployed "
            r"across all the web properties, [^.]{5,250}\. It connects "
            r"(?P<organization>[A-Z][A-Za-z ]+?) customers with a virtual agent, "
            r"enabling live agents to take over more complex conversations\. Named "
            r"(?P<agent_name>[A-Z][A-Za-z]+), the virtual agent ensures "
            r"(?P<task_or_purpose>[^.]{5,350})\."
        ),
        "documented_deployed",
    ),
]


def extract_profile_records(page):
    parsed = urlsplit(page.url)
    records = []
    for host, path, pattern, status in PROFILES:
        if parsed.hostname != host or parsed.path.rstrip("/") != path.rstrip("/"):
            continue
        for match in re.finditer(pattern, page.text):
            record = Record.model_validate(
                match.groupdict()
                | {
                    "source_url": page.url,
                    "supporting_evidence": match.group(0),
                    "evidence_status": status,
                }
            )
            if supported(record, page.text, page.url):
                records.append(record)
    return records
