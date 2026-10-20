"""Reviewed bank disclosure grammars. Names/tasks and lifecycle evidence come from live text.

A profile is tied to one reviewed official URL. Optional context/lifecycle matches provide
short, ordered source excerpts, separated by an explicit omission marker. These are named
AI assistants/chatbots as well as agentic systems, not claims that all systems are autonomous.
"""

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from pydantic import ValidationError

from .models import Record, supported


@dataclass(frozen=True)
class Profile:
    host: str
    path: str
    pattern: str
    status: str
    context: str = ""
    lifecycle: str = ""


BOFA = "/content/newsroom/press-releases/2025/08/a-decade-of-ai-innovation--bofa-s-virtual-assistant-erica-surpas.html"
CITI = "/global/news/press-release/2025/citi-expands-generative-ai-capabilities-to-australia-and-new-zealand"
DBS = "/newsroom/DBS_empowers_its_Customer_Service_Officers_with_Gen_AI_powered_virtual_assistant_to_reduce_toil_and_enhance_customer_experience"
OCBC = "/group/investors/annual-reports/2024-annual-report/creating-value-through-ai.page"
NATWEST = "/news-and-insights/news-room/press-releases/ai-and-data/2025/mar/natwest-open-ai-collaborate-to-accelerate-cutting-edge-ai-transf.html"
CAPITAL_ONE = "/about/newsroom/capital-one-auto-wins-two-2026-big-innovation-awards/"
BUNQ = "/258930-bunq-launches-smarter-more-powerful-upgrade-to-genai-financial-assistant/"

PROFILES = [
    Profile(
        "newsroom.bankofamerica.com",
        BOFA,
        r"Our clients appreciate (?P<agent_name>Erica)’s ability to help them "
        r"(?P<task_or_purpose>manage their spending, improve budgeting and increase savings)"
        r",[”\"] said Nikki Katz, head of digital at (?P<organization>Bank of America)",
        "documented_deployed",
        lifecycle=r"Erica is embedded today across the enterprise, assisting clients and employees",
    ),
    Profile(
        "newsroom.bankofamerica.com",
        BOFA,
        r"(?P<agent_name>Erica for Employees) is used today by [^.]{1,70}? "
        r"(?P<organization>Bank of America) employees, with the virtual assistant having "
        r"(?P<task_or_purpose>reduced calls into the I T IT service desk) by [^.]{1,40}",
        "documented_deployed",
    ),
    Profile(
        "newsroom.wf.com",
        "/news-releases/news-details/2026/Wells-Fargo-Reaches-Major-Digital-Milestones/default.aspx",
        r"Since its debut in 2023, (?P<agent_name>Fargo) has become a central part of that experience, "
        r"helping customers complete common banking tasks such as "
        r"(?P<task_or_purpose>sending money with Zelle®, paying bills, locating routing numbers, "
        r"and gaining insights into spending and account balances)\.",
        "documented_deployed",
        context=r"(?P<organization>Wells Fargo) today announced significant milestones in its digital transformation, "
        r"underscoring growing customer adoption of its mobile banking platform and AI[‑-]powered virtual assistant, Fargo®\.",
        lifecycle=r"Fargo has now supported customers through more than 1 billion interactions",
    ),
    Profile(
        "newsroom.wf.com",
        "/news-releases/news-details/2026/Wells-Fargo-introduces-AI-Teammate-bringing--AI-powered-support-to-the-advisor-experience/default.aspx",
        r"In its initial phase, (?P<agent_name>AI Teammate) helps teams "
        r"(?P<task_or_purpose>search and summarize information from WFA’s core resource center)",
        "documented_use_case",
        context=r"(?P<organization>Wells Fargo) today announced the launch of AI Teammate",
    ),
    Profile(
        "www.citigroup.com",
        CITI,
        r"(?P<agent_name>(?P<organization>Citi) Assist): A desktop assistant that "
        r"(?P<task_or_purpose>helps colleagues navigate Citi's policies and procedures)\.",
        "documented_deployed",
        lifecycle=r"Through the rollout, colleagues have access to three Gen AI tools that make it easier and simpler for to get work done\.",
    ),
    Profile(
        "www.dbs.com",
        DBS,
        r"Another use case which has been benefiting (?P<organization>DBS) employees is "
        r"(?P<agent_name>DBS-GPT), a Gen AI program similar to ChatGPT which the bank developed "
        r"to help its employees with (?P<task_or_purpose>content generation and writing tasks in a secure environment)\. "
        r"DBS-GPT is currently available to over 25,000 employees across the bank\.",
        "documented_deployed",
    ),
    Profile(
        "www.dbs.com",
        DBS,
        r"(?P<agent_name>CSO Assistant) (?P<task_or_purpose>transcribes customer queries in real-time "
        r"and does ‘live’ searches on the bank’s knowledge base to quickly retrieve query-specific information)",
        "documented_experimental",
        context=r"Nimish Panchmatia, Chief Data and Transformation Officer, (?P<organization>DBS)",
        lifecycle=r"Based on data collected since pilots began in October 2023, CSO Assistant has demonstrated "
        r"transcription and solutioning accuracy of nearly 100%, and when fully deployed, is expected to reduce call handling time by up to 20%\.",
    ),
    Profile(
        "www.ocbc.com",
        OCBC,
        r"In November 2023, we became the first to roll out a GenAI chatbot, "
        r"(?P<agent_name>(?P<organization>OCBC) GPT), which supports our 30,000 employees "
        r"worldwide in (?P<task_or_purpose>writing, research and ideation)\.",
        "documented_deployed",
    ),
    Profile(
        "www.ocbc.com",
        OCBC,
        r"(?P<agent_name>(?P<organization>OCBC) Buddy) An in-house GenAI knowledge assistant "
        r"that can (?P<task_or_purpose>answer employees' questions on internal policies, from parental leave to expense application)\.",
        "documented_deployed",
        lifecycle=r"Here are some of the ways we have implemented AI and the benefits we have gained\.",
    ),
    Profile(
        "www.natwestgroup.com",
        NATWEST,
        r"(?P<agent_name>Ask Archie\+) is (?P<organization>NatWest)’s 24/7 AI chatbot for colleagues, "
        r"covering (?P<task_or_purpose>Technology, HR, Property, Bookings and Purchasing queries), "
        r"which now uses Gen AI to simplify colleague experiences",
        "documented_deployed",
    ),
    Profile(
        "rbcborealis.com",
        "/applications/aiden/",
        r"As a reinforcement learning \(RL\) algorithm, (?P<agent_name>Aiden) "
        r"(?P<task_or_purpose>develops an order execution strategy dynamically, by adapting to constantly shifting "
        r"market conditions and by balancing long-term goals against short-term opportunities)\.",
        "documented_deployed",
        context=r"Please read more about the research behind Aiden and about how we use Aiden "
        r"and Aiden Arrival in (?P<organization>RBC Capital Markets)\.",
    ),
    Profile(
        "www.capitalone.com",
        CAPITAL_ONE,
        r"(?P<agent_name>Chat Concierge) uses proprietary agentic AI technology to put customers in the driver's seat "
        r"of their car buying experience by (?P<task_or_purpose>connecting them with the dealer, helping them find the "
        r"right car, requesting a test drive),",
        "documented_deployed",
        context=r"(?P<organization>Capital One Auto)’s Chat Concierge and ProtectID have been recognized as Innovative Product Winners",
        lifecycle=r"Based on Q1 2025 results alone, Chat Concierge was found to be 55% more successful at converting leads "
        r"into buyers than a leading competitor\.",
    ),
    Profile(
        "press.bunq.com",
        BUNQ,
        r"As their GenAI Assistant, users most frequently rely on (?P<agent_name>Finn) for "
        r"(?P<task_or_purpose>everyday banking support, especially questions related to card services, payments, and savings)\.",
        "documented_deployed",
        context=r"A true financial assistant for (?P<organization>bunq) users, Finn has answered millions of user queries "
        r"since its launch two years ago\.",
    ),
    Profile(
        "www.natwestgroup.com",
        "/who-we-are/about-natwest-group/tech-data-and-AI/natwest-ai-adoption-report/how-we-use-AI-for-the-future-of-customer-relationships.html",
        r"The (?P<agent_name>Fraud Triage Agent) is now live in Cora for credit card customers "
        r"across all (?P<organization>NatWest) brands, helping them "
        r"(?P<task_or_purpose>understand suspicious credit card transactions and what steps to take next)\.",
        "documented_deployed",
    ),
    Profile(
        "www.natwestgroup.com",
        "/who-we-are/about-natwest-group/tech-data-and-AI/natwest-ai-adoption-report/how-we-use-AI-for-the-future-of-customer-relationships.html",
        r"With our AI assistant, (?P<agent_name>Cora), customers have been trialling an agentic "
        r"financial assistant for (?P<task_or_purpose>asking simple questions such as: "
        r"\"What did I spend last month\?\" or \"How does my spending compare to this time last year\?\") "
        r"and receiving immediate, personalised responses\.",
        "documented_experimental",
        context=r"In our research, 57% of (?P<organization>NatWest) Group customers said their use of AI "
        r"had grown rapidly in the previous six months",
    ),
]


def _excerpts(text, matches):
    spans = sorted((match.start(), match.end()) for match in matches)
    merged = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return " […] ".join(text[start:end] for start, end in merged)


def extract_finance_records(page):
    parsed = urlsplit(page.url)
    records = []
    for profile in PROFILES:
        if parsed.hostname != profile.host or parsed.path.rstrip("/") != profile.path.rstrip("/"):
            continue
        match = re.search(profile.pattern, page.text)
        if not match:
            continue
        matches = [match]
        data = match.groupdict()
        for pattern in (profile.context, profile.lifecycle):
            if not pattern:
                continue
            extra = re.search(pattern, page.text)
            if not extra:
                break
            matches.append(extra)
            data.update(extra.groupdict())
        else:
            try:
                record = Record.model_validate(
                    data
                    | {
                        "source_url": page.url,
                        "supporting_evidence": _excerpts(page.text, matches),
                        "evidence_status": profile.status,
                    }
                )
                if supported(record, page.text, page.url):
                    records.append(record)
            except ValidationError:
                # Changed or oversized source text cannot become a stale/pre-filled finding.
                continue
    return records
