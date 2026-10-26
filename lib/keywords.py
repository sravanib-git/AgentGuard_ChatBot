"""Extract reproducible section keywords from local documentation only."""
import math
import re
from collections import Counter
from .search import terms, STOP, GENERIC

FILLER = STOP | GENERIC | set('not no only all each every any both also has have had will there here than then into out one two three first same other such through before after example examples default true false none const import return await string name value set code page section console application'.split())

# Domain vocabulary is selected only when it occurs in that section's text.
# These phrases keep the important concepts ahead of statistical word choices.
TOPICS = '''observability|security|governance|quality|trust|AI agents|LLM|runtime guardrails|auditability|traces|spans|sessions|latency|tokens|cost|prompt injection|PII|redaction|secrets|credentials|API keys|public key|secret key|host URL|project ID|environment variables|SDK|Python|Node.js|OpenAI|Anthropic|Bedrock|Gemini|LangGraph|LangChain|MCP|instrumentation|init|flush|withPolicy|policy|metadata|tenant|userId|sessionId|feature|guardrails|kill switch|observe|onBlock|capture content|prompt|response|streaming|polling|rate limit|token limit|budget|allowed model|output schema|hallucination|execution limit|excessive agency|tool calls|trust profile|dimensions|dashboards|widgets|coverage|scores|evaluation|LLM Evals|decision models|human review|test sets|datasets|experiments|judge|rubrics|groundedness|OWASP|red teaming|vulnerabilities|incidents|compliance|evidence|frameworks|covered|partial|gap|out of scope|not assessed|evidence pack|policy as code|YAML|AI bill of materials|inventory|ownership|risk tier|data governance|residency|regions|no-train|audit trail|hash|integrity|RBAC|roles|scopes|permissions|Owner|Admin|Member|Viewer|custom roles|entitlements|read|CUD|export|project settings|organization|members|invite|Auditor|authentication|sign-in|SSO|OIDC|NextAuth|JWT|cookies|session lifecycle|idle|expiry|refresh|logout|revocation|denylist|Redis|sid|rotation|password|magic link|Google|GitHub|Azure|Okta|Auth0|Keycloak'''.split('|')


def extract_keywords(sections):
    """Rank meaningful words by TF-IDF; include headings and technical names."""
    sections = tuple(sections)
    counts = [Counter(t for t in terms(s.text) if t not in FILLER and not t.isdigit()) for s in sections]
    frequency = Counter(t for count in counts for t in count)
    result = {}
    for section, count in zip(sections, counts):
        prose = re.sub(r'```.*?```', '', section.text, flags=re.S)
        headings = re.findall(r'^#{1,6}\s+(.+)$', prose, re.M)
        phrases = [section.title.split(' / ')[-1], *headings]
        heading_phrases = {p.strip().lower() for p in phrases}
        topics = [t for t in [*TOPICS, 'npm', 'pip'] if re.search(r'(?<!\w)' + re.escape(t) + r'(?!\w)', section.text, re.I)]
        # Preserve option/environment names as written in the source.
        identifiers = re.findall(r'\b(?:[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+|[a-z]+(?:[A-Z][a-z0-9]+)+)\b', section.text)
        ranked = sorted(count, key=lambda t: (-(1 + math.log(count[t])) * math.log(1 + len(sections) / frequency[t]), t))
        keywords, seen = [], set()
        for phrase in [*phrases, *topics, *identifiers, *ranked[:12]]:
            phrase = phrase.strip().lower()
            if phrase and phrase not in seen and (phrase in heading_phrases or any(t not in FILLER for t in terms(phrase))):
                seen.add(phrase)
                keywords.append(phrase)
        result[(section.page, section.anchor, section.language)] = keywords
    return result
