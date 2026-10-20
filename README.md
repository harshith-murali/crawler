# AWS AI Agent Discovery Crawler

Build a CSV mapping publicly documented named AI agents to their stated business tasks.
Public documentation is evidence of what a source says; it does **not** establish which
agents a bank uses internally, audit private deployments, or discover the entire web.
No real-world findings or seed URLs are invented. The default configuration has no seeds
and produces a header-only inventory. `config.public.json` supplies 15 reviewed official
source URLs; its live run produced 20 evidence-backed records, including 15 financial-services
relationships across nine organizations (12 deployments, two pilots, one capability). The fictional examples live
only in `examples/`. See [source selection and live results](SOURCES.md).

## Install and run

Requires Python 3.11+ (AWS template uses Python 3.12).

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp examples/config.json config.json
# Edit config.json: supply authorized public seed_urls and allowed_domains.
python -m agent_crawler --config config.json
```

The CLI also installs as `agent-crawler`. `--output path.csv` overrides the output location.
No API keys or AWS account are needed locally. An empty configuration can be run as a
smoke check: `python -m agent_crawler`. It intentionally returns zero findings.

Before enabling a domain, review its website terms and your authorization to crawl it.
Use a descriptive `user_agent` with an operator contact URL. The crawler honors robots.txt,
never signs in or solves access challenges, does not render JavaScript, and skips failures.
Operators must remove sources whose terms prohibit crawling; robots.txt is not a license.

## Run the reviewed public sources

```sh
.venv/bin/python scripts/run_public_crawl.py
.venv/bin/python scripts/check_inventory_evidence.py
.venv/bin/python scripts/export_finance_views.py
```

This uses `config.public.json`, the production crawler and reviewed official source
profiles, prioritizing banks and financial services. It writes `output/agent_inventory.csv`, the crawl summary, and exact source snapshots
with timestamps/hashes under `output/sources/` for local review. A normal CLI run using
`--config config.public.json` produces the same inventory without keeping snapshots.
No provider credentials are required. The main inventory has 13 documented deployments, five capabilities and two pilots. The
finance-only deployment view has 12 rows. Statuses describe source disclosures, not an
independent audit of continued current use. See [SOURCES.md](SOURCES.md) for the source URLs and limits.
Running the default empty/example configuration overwrites the inventory with a header-only
file; use the public configuration to reproduce real findings.

## Architecture and scope

1. Normalize supplied seeds and optional Brave search results into a bounded BFS queue.
2. Permit exact allowed hostnames, optional URL path prefixes, and exclude denied prefixes/assets.
3. Check public IP resolution and robots.txt; fetch bounded HTML with timeouts, delays and retries.
4. Parse title, readable text, links and tables with BeautifulSoup. Crawl internal in-scope
   links up to the depth limit. All in-scope HTML links are eligible; use path prefixes to
   prioritize technology, product documentation, official catalogues and case studies.
5. Extract explicit named agent/task statements; validate evidence and deduplicate.
6. Write a UTF-8 CSV and JSON summary. Lambda uploads both to a private S3 run directory.

Exact hostnames include subdomains only when explicitly configured. Without allowed_domains,
seed hostnames define scope; search results never expand it. URL prefixes match full path
segments, not lookalike paths. Redirect destinations undergo scope and robots checks before
fetching. Tracking parameters/fragments are removed; other query parameters are retained and
sorted. Trailing slashes and encoded slashes are preserved because servers may distinguish them.

Requests have no ambient netrc authentication, proxy credentials or persistent server cookies.
Robots rules and request delays are cached per origin/host. A missing robots.txt (404) allows
crawling; other non-200 statuses and robots redirects fail closed. Robots Crawl-delay and
Request-rate can increase the configured request spacing. 429/500/502/503/504 and network
connection errors/timeouts receive bounded retries; Retry-After seconds are honored up to
120 seconds and within the runtime budget. HTTP-date Retry-After falls back to backoff.

## Configuration

Use a JSON file and/or `.env` (see `.env.example`). Environment variables override JSON;
CLI `--output` overrides both. Arrays must be JSON arrays, not comma-separated strings.
Each JSON key has the uppercase environment equivalent. Unknown JSON keys are rejected.

| JSON setting | Default | Meaning |
|---|---|---|
| seed_urls | [] | Public starting URLs |
| allowed_domains | seed hostnames | Exact allowed hostnames |
| url_prefixes / denied_prefixes | [] / [] | Absolute URL prefixes to include/exclude |
| max_pages | 30 | Maximum attempted page fetches, including failures |
| max_depth | 2 | Seed depth is zero |
| max_discovered | 1000 | Maximum unique queued URLs, including seeds |
| request_timeout | 10 | Per-request network timeout in seconds |
| delay_seconds | 1 | Minimum spacing between requests per host |
| retries | 2 | Additional attempts after transient failures |
| max_response_bytes | 2000000 | Decompressed HTML/robots body size limit |
| max_runtime_seconds | 120 | Cooperative crawl runtime budget |
| output_file | output/agent_inventory.csv | Output CSV; sibling .summary.json is also written |
| user_agent | AgentDiscoveryCrawler/0.1 | Crawler identification |
| search_queries | [] | Optional search terms |
| search_max_results | 10 | Results per query, maximum 20 |
| llm_provider | none | `none` or `json-http` |
| llm_endpoint / llm_model | empty | Configured HTTPS extraction gateway and model |

Choose reviewed official sources rather than relying on a broad query alone. Search snippets
are never treated as evidence: returned URLs must be fetched and pass the same checks.

### Optional search

Set `BRAVE_SEARCH_API_KEY` and `SEARCH_QUERIES` (JSON list). The adapter uses the
[Brave Web Search API](https://api-dashboard.search.brave.com/documentation/services/web-search).
Also set allowed_domains; search discovery remains within that allowlist. Missing credentials
or API errors fall back to seeds. The adapter requests one result page per query and makes
no completeness claim. Keys are read from the environment and are not logged.

### Optional LLM extraction

No model is needed for the deterministic path. `LLM_PROVIDER=json-http` enables an
**operator-provided extraction gateway**, not a direct adapter for a particular model vendor.
Set `LLM_ENDPOINT` (HTTPS), `LLM_MODEL`, and `LLM_API_KEY`. The gateway receives an HTTP POST
with Bearer authentication and JSON fields `model`, `instructions`, `document` (`source_url`,
`text`, limited to 40,000 characters), and `response_schema` (generated JSON Schema).
It must return HTTP 200 and a plain JSON object `{"records": [...]}` conforming to that schema;
chat-completion wrappers, tools and arbitrary extra properties are rejected.

The page is untrusted data. No page instruction, code or tool call is executed. Records must
copy the organization, name, task and optional department into supporting source excerpts.
The source URL must equal the fetched page URL. The strict schema rejects incomplete/generic
records and invalid statuses; evidence checks reject text missing from the source. LLM results
are always labelled `documented_use_case`, regardless of the provider's deployment claim.
Human review is still required: literal quotation validation cannot prove semantic correctness.
Malformed responses or missing keys fall back to deterministic extraction. Review provider
retention/pricing policies before sending public source text to your configured gateway.

## Extraction and evidence

The conservative deterministic extractor supports:

- Tables with `organization`, `agent_name` (or `agent`), and `task_or_purpose` (or `task` /
  `purpose`) headers. Optional `department`, `business_function`, `status` and `type` are
  supported. A name must identify an Agent/Assistant/Copilot, or the row type must say AI agent.
- Explicit English sentences such as the **fictional syntax example**:
  `Illustrative Bank uses its Research Assistant to summarize public reports.`
  Verbs supported: uses, deploys, pilots, tests, proposes, plans to deploy. Agents must be
  explicitly named with an Agent/Assistant/Copilot suffix. Organization is never guessed
  from a domain, page title, vendor name, or logo.

Both generic paths require explicit AI-agent context on the page. Additionally, reviewed
official-page profiles in `source_profiles.py` and `finance_profiles.py` recognize specific
document formats with explicit agent/assistant context and source-backed organization
attribution. Finance profiles require source-specific usage, rollout, or pilot statements.
Short ordered quotations can use ` […] ` to mark omissions; every fragment must exist in
the source in the same order. Named chatbots, assistants and RL systems are not all assumed
to be autonomous GenAI agents. This is a high-precision baseline:
unfamiliar prose, unnamed agents, ambiguous deployments and many real pages yield no records.
Extend `extraction.py` or configure the optional gateway for more source formats. Sources
can make inaccurate claims; evidence status describes the documentation, not independent verification.

| evidence_status | Meaning |
|---|---|
| documented_use_case | Source states a named agent and task; deployment is unspecified |
| documented_deployed | Deterministic explicit uses/deploys statement or deployed table status |
| documented_experimental | Explicit pilot/test/experimental status |
| documented_proposed | Explicit proposed/planned status |

The CSV columns, in order, are:

```text
organization,task_or_purpose,agent_name,department_or_business_function,source_url,supporting_evidence,evidence_status
```

Each row is one supported agent-purpose relationship; CSV uses Python's CSV writer and UTF-8
with proper comma, quote and multiline escaping. A valid header is written even with no findings.
Deduplication compares organization, agent name, task and department using whitespace
normalization and case folding. Similar purposes never combine distinct named agents. For an
identical relationship, the first source and its status are retained; this is not an exhaustive citation archive.
Page content hashes prevent repeated extraction of identical readable text.

`output/agent_inventory.summary.json` includes discovered, attempted, fetched, failed, skipped,
duplicate pages, extracted records, errors, timestamps and stop reason. Discovered pages may
exceed fetched pages because of limits. Robots-denied/unsupported pages are skipped, HTTP
failures are failed. Fetched counts successful HTML requests, including redirected duplicates.
The runtime limit is cooperative; socket/DNS/provider operations can overrun it briefly.
Logs go to stderr locally and CloudWatch in Lambda. Review artifacts before external sharing;
source URLs can contain query strings and source excerpts are untrusted text. CSV is raw data;
spreadsheet software may interpret formula-like source cells—import cells as text.

## Tests and illustrative data

```sh
pytest -q
ruff check agent_crawler tests
cfn-lint template.yaml
python -m examples.demo
```

Tests use local fixtures and mocked HTTP, with no external requests or credentials. Coverage
includes parsing, URL canonicalization, scope, BFS limits, duplicate pages/records, structured
and sentence extraction, record validation, CSV encoding/escaping, robots and redirects,
retry/error/timeout handling, provider fallback/validation and Lambda S3 upload behavior.

`examples/illustrative_input.html` and `examples/illustrative_agent_inventory.csv` are synthetic.
`python -m examples.demo` regenerates only the illustrative CSV. It never writes fictional rows
into `output/agent_inventory.csv`. The original smoke run produced a header-only output; the subsequent expanded live run using
`config.public.json` produced 20 real records. See `SOURCES.md`.

## AWS deployment

Install/configure the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
and [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html).
Use an authorized deployment role; never put credentials in the repository.

```sh
sam validate --lint
sam build --use-container
sam deploy --guided --capabilities CAPABILITY_IAM
```

During guided deployment set `SeedUrls`, `AllowedDomains`, `UrlPrefixes`, and `DeniedPrefixes`
as JSON arrays. Configure the reviewed source list before enabling the schedule. Set
`ScheduleEnabled=true` only when recurring crawling is wanted; it defaults to false.
`ScheduleExpression` defaults to `rate(1 day)`. Bounded invocation also works manually:

```sh
aws cloudformation describe-stacks --stack-name YOUR_STACK --query 'Stacks[0].Outputs'
aws lambda invoke --function-name YOUR_FUNCTION --cli-binary-format raw-in-base64-out --payload '{}' response.json
# Use bucket and csv_key from response.json:
aws s3 cp s3://YOUR_BUCKET/runs/YOUR_RUN_ID/agent_inventory.csv output/agent_inventory.csv
```

A custom SAM Makefile build packages only runtime dependencies and `agent_crawler/`; local
`.env`, outputs, test fixtures and example data are excluded from the deployment ZIP.
Docker is needed for the documented container build.

The [SAM function](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-resource-function.html)
uses 512 MB, Python 3.12 and a 300-second timeout. The crawler stops at 240 seconds or at least
30 seconds before the invocation deadline to leave time for output upload. AWS Lambda's
[maximum timeout is 900 seconds](https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html).
Every run writes `/tmp/<run-id>/agent_inventory.csv` and its summary, uploads them to
`s3://<private-bucket>/runs/<run-id>/`, then removes temporary artifacts. Unique keys avoid
concurrent-run overwrites. A failed upload raises a Lambda error; it is never reported as success.
An empty event cannot broaden the configured scope. The function needs public internet egress;
the supplied template does not place it inside a VPC.

The template creates an encrypted, versioned, private S3 bucket retained on stack deletion,
a 14-day CloudWatch log group, a Lambda Errors alarm, and an optional EventBridge schedule.
The execution role grants only `s3:PutObject` within that bucket's `runs/` prefix and log stream
creation/writes in that log group. It cannot read/list/delete S3 objects. Operator downloads
need a separate `s3:GetObject` permission. Partial crawl failures appear in summaries/logs;
the Lambda alarm reports invocation failures, not individual page failures. Add an SNS alarm
action or summary-based monitoring for your operational needs.

Deployment permissions belong to the operator, separate from the Lambda role: CloudFormation
stack management, SAM packaging bucket upload, creating/updating these Lambda/S3/IAM/Logs/
CloudWatch/EventBridge resources, and `iam:PassRole` for the specific function role. Have your
AWS administrator scope deployment permissions to your stack, region and packaging bucket.
SAM guided deployment may create/manage its packaging bucket. No deployment is performed by
this repository's tests. Retained S3 data must be deleted separately if no longer needed.

Optional APIs are disabled in the baseline stack. To enable them in AWS, extend the template
with your provider settings and Secrets Manager dynamic references for keys; give the deployment
role access to the specific secret as required. Do not pass plaintext API keys on command lines
or commit them in SAM config files. The runtime does not require Secrets Manager permissions
when values are resolved by CloudFormation. The keys use `BRAVE_SEARCH_API_KEY` / `LLM_API_KEY`,
as locally. No broad model-access IAM policy is required for the HTTP gateway.

## Limits, cost and next steps

There is no guarantee of completeness or truth beyond the quoted documentation. No JavaScript
rendering, PDF parsing, private data, login, CAPTCHA bypass, multilingual extraction or distributed
crawl state is included. Source HTML/title are parsed transiently; only evidence excerpts and
summaries persist. A public-IP DNS check is defense in depth, not a hardened DNS-rebinding
sandbox. Use controlled egress/DNS filtering when operating against hostile sources.

HTML bodies/queues are capped; parser overhead and very large seed/query configuration can
still consume resources. Search and LLM calls use network timeouts but do not have crawl-style
retry handling. Set small query/page/depth/runtime limits. Lambda duration, S3 objects/versions,
CloudWatch logs, optional search and LLM requests can incur costs; consult your account's
current pricing and use budgets. No numeric pricing assumptions are baked in.

For longer crawls use ECS Fargate plus SQS with durable URL deduplication, checkpoints,
per-domain scheduling and dead-letter queues. Further improvements include source-specific
extractors, citation archives, human review, monitoring, and extraction quality evaluation on
labelled real public sources.
