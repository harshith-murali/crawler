# Official sources and inventory qualifications

Reviewed and crawled on 2026-10-20. The current `config.public.json` run fetched **15 official
pages**, with no failed/skipped pages, and produced **20 agent-purpose records**. It preserves
all five original findings and adds **15 financial-services records across nine organizations**.
No search API key, LLM or AWS account was used for the run.

## Financial-services results

| Organization | Named system(s) | Source-supported classification |
|---|---|---|
| Bank of America | Erica; Erica for Employees | Documented deployments: customer money management; employee IT service desk support |
| Wells Fargo | Fargo | Documented deployment: banking transactions and account insights |
| Wells Fargo | AI Teammate | Announced product capability: advisor resource search/summarization; source does not establish actual adoption |
| Citi | Citi Assist | Documented internal rollout: policies and procedures assistance |
| DBS | DBS-GPT | Documented employee availability: content generation and writing |
| DBS | CSO Assistant | Pilot in the July 2024 disclosure, with broader rollout planned; not classified as fully deployed from that announcement |
| OCBC | OCBC GPT; OCBC Buddy | Documented deployments: employee writing/research; internal-policy questions |
| NatWest | Ask Archie+; Fraud Triage Agent | Documented deployments: employee queries; suspicious credit-card transactions |
| NatWest | Cora, agentic spending questions | Explicitly described as a trial; this task is not promoted to a full deployment |
| RBC Capital Markets | Aiden | Documented use of an RL order-execution system; not a GenAI chatbot |
| Capital One Auto | Chat Concierge | Agentic sales assistance supported by reported real customer-conversion results |
| bunq | Finn | Documented GenAI banking support usage |

Financial-services totals: **12 documented deployments, 2 experimental/pilot relationships,
1 product-capability relationship**. The remaining five rows are the original Microsoft,
Salesforce, IBM and Camping World findings: four product capabilities and one historical
deployment. Overall totals are 13 deployments, 5 capabilities and 2 pilots.

Named assistants and chatbots remain within the original project scope. Their inclusion does
not establish autonomous or agentic behavior: that terminology is used only where the source
supports it. For example, Aiden uses reinforcement learning, while Chat Concierge is explicitly
agentic; several bank systems are described simply as AI assistants or chatbots. An announced
capability or future availability is not treated as evidence of organization-wide adoption.

## Reviewed financial source URLs

| Source | Date/context and what the evidence establishes |
|---|---|
| [Bank of America: Erica milestones](https://newsroom.bankofamerica.com/content/newsroom/press-releases/2025/08/a-decade-of-ai-innovation--bofa-s-virtual-assistant-erica-surpas.html) | August 2025 disclosure; includes actual usage/embedded status for both named systems |
| [Wells Fargo: Digital milestones](https://newsroom.wf.com/news-releases/news-details/2026/Wells-Fargo-Reaches-Major-Digital-Milestones/default.aspx) | 2026 disclosure; explicitly AI-powered Fargo, more than a billion interactions and concrete banking tasks |
| [Wells Fargo: AI Teammate](https://newsroom.wf.com/news-releases/news-details/2026/Wells-Fargo-introduces-AI-Teammate-bringing--AI-powered-support-to-the-advisor-experience/default.aspx) | 2026 launch/capability announcement; broader channel availability is expressed in the future tense, so no adoption claim is made |
| [Citi: Australia/New Zealand expansion](https://www.citigroup.com/global/news/press-release/2025/citi-expands-generative-ai-capabilities-to-australia-and-new-zealand) | September 17, 2025; colleagues have access through an internal rollout, with an explicit Citi Assist description |
| [DBS: CSO Assistant and DBS-GPT](https://www.dbs.com/newsroom/DBS_empowers_its_Customer_Service_Officers_with_Gen_AI_powered_virtual_assistant_to_reduce_toil_and_enhance_customer_experience) | July 18, 2024; CSO Assistant pilots began in October 2023, with full deployment still expected; DBS-GPT was already available to more than 25,000 employees |
| [OCBC: Creating value through AI](https://www.ocbc.com/group/investors/annual-reports/2024-annual-report/creating-value-through-ai.page) | 2024 annual-report context; explicit rollout of OCBC GPT and an implemented-use-case section naming OCBC Buddy |
| [NatWest: AI collaboration](https://www.natwestgroup.com/news-and-insights/news-room/press-releases/ai-and-data/2025/mar/natwest-open-ai-collaborate-to-accelerate-cutting-edge-ai-transf.html) | March 20, 2025; footer identifies Ask Archie+ as the bank's 24/7 employee chatbot already using GenAI |
| [RBC Borealis: Aiden](https://rbcborealis.com/applications/aiden/) | Undated live page: describes how RBC Capital Markets uses Aiden and how its agent executes orders; includes historical product launches |
| [Capital One Auto: Innovation awards](https://www.capitalone.com/about/newsroom/capital-one-auto-wins-two-2026-big-innovation-awards/) | March 12, 2026; task description plus Q1 2025 customer-conversion results support actual use, rather than an award alone |
| [bunq: Finn upgrade](https://press.bunq.com/258930-bunq-launches-smarter-more-powerful-upgrade-to-genai-financial-assistant/) | December 16, 2025; states user queries already answered and concrete support usage |
| [NatWest: Future of customer relationships](https://www.natwestgroup.com/who-we-are/about-natwest-group/tech-data-and-AI/natwest-ai-adoption-report/how-we-use-AI-for-the-future-of-customer-relationships.html) | Live page retrieved October 20, 2026: says Fraud Triage Agent is now live, but spending questions are a trial. Its publication date is not established; an old template metadata date is not used as the report date |

## Original sources retained

- [Microsoft Adoption: Agents in Microsoft 365](https://adoption.microsoft.com/en-us/ai-agents/agents-in-microsoft-365/): Researcher and Analyst product capabilities.
- [Salesforce Trailhead: Sales Coach](https://trailhead.salesforce.com/content/learn/modules/agentforce-for-sales-coaching-setup-and-customization/get-to-know-agentforce-sales-coach): product capability; no internal Salesforce deployment claim.
- [IBM: AI assistants](https://www.ibm.com/solutions/ai-assistants): IBM watsonx Code Assistant product capability.
- [IBM: Camping World case study](https://www.ibm.com/case-studies/camping-world): Arvee deployment, with historical implementation/metrics as of March 2022. This does not establish continued current use.

## Evidence, reproducibility and limits

The seven-column primary CSV remains `output/agent_inventory.csv`. Every row includes a source
URL, exact supporting text and an evidence status. Some excerpts use the explicit ` […] `
omission marker to retain a short task quote plus a separate lifecycle/context statement. Every
fragment must appear verbatim in the saved source, in the same order. Organization and agent
names are read from the quoted source text, not guessed from a domain. Departments are blank
where an explicit department assignment would require interpretation.

`documented_deployed` means the source reports usage, rollout, or a live service; it is not an
independent audit and does not establish that a system remains active today. The CSV uses the
source's organization/brand/division labels (e.g., Citi, NatWest, Capital One Auto). Sources may
contain vendor claims or historical figures. Source dates/qualifications above must travel with
any interpretation of the inventory, especially DBS's historical pilot.

Narrow reviewed parsers in `source_profiles.py` and `finance_profiles.py` extract the actual
fetched text. Changed, missing, proposed or negated deployment statements do not emit stored
findings. All 20 records have passed schema, source-quote, saved HTML hash, and deterministic
record/status reproduction checks. These checks establish traceability, not independent truth.
The evidence report also records the CSV hash so exports cannot use an older audit merely
because it has the same row count.

Reproduce from the repository root:

```sh
.venv/bin/python scripts/run_public_crawl.py
.venv/bin/python scripts/check_inventory_evidence.py
.venv/bin/python scripts/export_finance_views.py
```

`config.public.json` prioritizes the 11 financial source URLs and retains the four original
pages. `config.finance.json` is a finance-only configuration. Requests use the production
robots/scope policy, two-second spacing (or longer site guidance), size/time limits and retries.
The narrowly scoped run exhausted its queue after the 15 seeds; it did not discover the whole
web. A normal CLI crawl with the same configuration produces the primary CSV without snapshots.

Generated artifacts:

- `output/agent_inventory.csv`: all 20 relationships.
- `output/financial_services_inventory.csv`: 15 finance relationships, all statuses.
- `output/financial_services_deployments.csv`: 12 finance deployments only.
- `output/financial_services_pilots.csv`: two historical/trial relationships.
- `output/product_capabilities.csv`: five capabilities, including Wells Fargo AI Teammate.
- `output/inventory_breakdown.json`: counts and financial organization list.
- `output/agent_inventory.summary.json`: live crawl statistics/timestamps.
- `output/agent_inventory.evidence_check.json`: per-row evidence/status checks and CSV hash.
- `output/sources/manifest.json`, `*.html`, `*.txt`: exact local review snapshots and fetch timestamps/hashes.
- `output/archive/initial-five-records/`: preserved prior inventory and its snapshots.

Views are derived from the audited primary CSV, not separate crawl results. None contain the
fictional examples under `examples/`. The crawl/extraction used no external model provider.

## Candidates not promoted into findings

The research files under `output/research*` are separate from production snapshots:

- Morgan Stanley's Debrief announcement repeatedly timed out. No record was inserted from a search snippet or browser summary.
- Lemonade's robots endpoint returned HTTP 403; the crawler failed closed and did not fetch the article or invent an insurance deployment.
- Two newer DBS pages returned article shells without their substantive body in static HTML. Their rendered/search text was not used to claim a newer rollout of CSO Assistant.
- A broader Citi overview did not supply a distinct agent/task relationship under the reviewed extraction rules. Generic document tools or unnamed future AI initiatives were not converted into agents.
- Older NatWest plans for Cora fraud support were not treated as deployed. The retained Fraud Triage Agent row relies on a separate, explicit live-service statement.

All source content is untrusted data; no page instructions are executed. Public snapshots are
local review artifacts excluded from source control; do not redistribute full website copies.
Terms, access and robots policies can change. No login, CAPTCHA or other access restriction
was bypassed. No AWS deployment was performed during this local expansion.
