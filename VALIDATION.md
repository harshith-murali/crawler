# Validation — 2026-10-20

Executed in this workspace with Python 3.14.4 after installing `.[dev]` in `.venv`:

| Check | Result |
|---|---|
| `pytest -q` | 47 passed |
| `ruff check agent_crawler tests examples` | Passed |
| `ruff format --check agent_crawler tests examples` | Passed |
| `cfn-lint template.yaml` | Passed, including SAM transformation |
| `python -m compileall -q agent_crawler` | Passed |
| `python -m agent_crawler --config examples/config.json` | Passed; header-only CSV and summary |
| `python -m examples.demo` | Passed; 4 clearly fictional rows in examples only |

Tests use mocked HTTP/local fixture pages and mocked S3, including crawl discovery and
extraction together. They do not establish extraction quality on arbitrary real websites.
No live seed URLs were supplied. `output/agent_inventory.csv` therefore contains the required
seven-column header and zero findings. Its JSON summary records zero discovered/fetched/failed
pages and zero records. All illustrative data remains in `examples/` and `tests/fixtures/`.

AWS SAM CLI is not installed here. `sam build`, container packaging and AWS deployment were
not executed; cfn-lint validated the infrastructure configuration. AWS runtime is configured
for Python 3.12; runtime behavior was tested locally on Python 3.14, not inside Lambda.

Before a production run, configure reviewed public seeds/scope and install AWS SAM/Docker
for the documented container build. Local deterministic crawling needs no credentials.
Optional Brave discovery needs `BRAVE_SEARCH_API_KEY`. Optional JSON HTTP LLM extraction
needs an operator-provided gateway and `LLM_API_KEY`. AWS deployment requires an authorized
AWS identity and the stack permissions described in README.md. No real-world inventory or
external-provider correctness is claimed by these offline checks.


## Subsequent live-source validation

A follow-up request authorized selecting official sources and running a live crawl. Added
four source-specific parsers and `config.public.json`; all **52 offline tests now pass**.
Ruff and cfn-lint also pass after the changes. The snapshot runner fetched four official pages,
with zero failures/skips, and extracted five records. All records passed the strict Record
schema and their complete supporting excerpts and fields matched the actual saved source text.
See `SOURCES.md`, `output/agent_inventory.summary.json`, and `output/sources/manifest.json`.
The earlier zero-findings statements above refer only to the initial empty-config smoke run.
No search/LLM credentials or AWS deployment were used for this live run.


## Financial-services expansion

The expanded run on 2026-10-20 fetched 15 official pages, with zero failures or skips, and
produced 20 records. It preserved the first five findings and added 15 financial-services
relationships across nine organizations: 12 deployments, two pilots and one capability.
All 20 records pass schema, ordered excerpt, snapshot hash and source/status reproduction
checks. A CSV hash binds the evidence report to the exact inventory used by derived views.

The offline suite now has **100 passing tests**, including real-source parser regressions,
negated/future lifecycle rejection, omitted-quote order, pilot/deployment separation, manual
pilot-status promotion rejection and stale-audit rejection. Ruff and cfn-lint pass. Source
qualification and excluded research candidates are documented in SOURCES.md. No AWS
build/deployment or external LLM calls were performed during the expansion.
