"""Small excerpts from the reviewed official documents, used only for parser regression tests."""

from agent_crawler.extraction import extract_records
from agent_crawler.models import supported
from agent_crawler.parsing import parse_html

MICROSOFT = "https://adoption.microsoft.com/en-us/ai-agents/agents-in-microsoft-365/"
SALESFORCE = "https://trailhead.salesforce.com/content/learn/modules/agentforce-for-sales-coaching-setup-and-customization/get-to-know-agentforce-sales-coach"
IBM = "https://www.ibm.com/solutions/ai-assistants"
CASE_STUDY = "https://www.ibm.com/case-studies/camping-world"


def test_microsoft_product_context_and_purpose():
    text = (
        "The Analyst agent works within Microsoft 365 Copilot Chat to transform complex "
        "data into clear insights and visualizations, enabling you and your team to "
        "make informed decisions quickly and efficiently. Generally available."
    )
    page = parse_html(f"<p>{text}</p>", MICROSOFT)
    records = extract_records(page)
    assert len(records) == 1
    assert records[0].agent_name == "Analyst"
    assert records[0].organization == "Microsoft"
    assert records[0].evidence_status == "documented_use_case"
    assert supported(records[0], page.text, page.url)
    # Identical prose on an unreviewed third-party page does not activate this parser.
    assert extract_records(parse_html(f"<p>{text}</p>", "https://third-party.example/")) == []


def test_salesforce_product_is_not_customer_deployment():
    text = (
        "Good news: Salesforce now offers a solution that helps managers and sales reps "
        "alike. Agentforce Sales Coach provides deal-specific, personalized feedback "
        "to sellers on their messaging and customer communication."
    )
    records = extract_records(parse_html(f"<p>{text}</p>", SALESFORCE))
    assert len(records) == 1
    assert records[0].organization == "Salesforce"
    assert records[0].agent_name == "Agentforce Sales Coach"
    assert records[0].evidence_status == "documented_use_case"
    assert extract_records(parse_html(text.replace("provides", "might provide"), SALESFORCE)) == []


def test_ibm_named_coding_assistant():
    text = (
        "IBM watsonx™ Code Assistant AI coding assistants for enterprise developers "
        "Accelerate developer productivity and onboarding, support application "
        "modernization and IT automation."
    )
    records = extract_records(parse_html(text, IBM))
    assert len(records) == 1
    assert records[0].agent_name == "IBM watsonx™ Code Assistant"
    assert records[0].organization == "IBM"
    assert extract_records(parse_html(text.replace("Code Assistant", "Orchestrate"), IBM)) == []


def test_case_study_requires_explicit_deployment():
    text = (
        "The solution, powered by IBM watsonx Assistant, seamlessly integrates LivePerson "
        "a conversational cloud platform, and was deployed across all the web properties, "
        "increasing the coverage of questions and telephone capabilities. It connects "
        "Camping World customers with a virtual agent, enabling live agents to take over "
        "more complex conversations. Named Arvee, the virtual agent ensures faster and "
        "more efficient response times with dynamic routing and capacity management capabilities."
    )
    page = parse_html(f"<p>{text}</p>", CASE_STUDY)
    records = extract_records(page)
    assert len(records) == 1
    assert records[0].organization == "Camping World"  # Not technology supplier IBM.
    assert records[0].agent_name == "Arvee"
    assert records[0].evidence_status == "documented_deployed"
    assert supported(records[0], page.text, page.url)
    assert (
        extract_records(parse_html(text.replace("was deployed", "may be deployed"), CASE_STUDY))
        == []
    )
    assert (
        extract_records(parse_html(text.replace("was deployed", "was not deployed"), CASE_STUDY))
        == []
    )


def test_changed_source_yields_no_stale_findings():
    for url in (MICROSOFT, SALESFORCE, IBM, CASE_STUDY):
        assert (
            extract_records(parse_html("<p>Documentation temporarily unavailable.</p>", url)) == []
        )
