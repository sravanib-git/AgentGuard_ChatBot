"""Lexical BM25 search with user-topic and SDK hints; no generation."""
import math
import re
from collections import Counter

STOP = set('a an the is are was were be do does did how what where when why who which can could would should i me my we our you your it its this that these those to for of on in and or with from by about please agentguard use using explain simpler simply understand again'.split())
ALIASES = {'configuration': 'configure', 'configuring': 'configure', 'setup': 'configure', 'installation': 'install', 'installing': 'install', 'initialization': 'init', 'initialize': 'init', 'traces': 'trace', 'tracing': 'trace', 'logging': 'trace', 'logs': 'trace', 'sessions': 'session', 'credentials': 'key', 'keys': 'key', 'roles': 'role', 'permissions': 'permission', 'guardrails': 'guardrail'}


def terms(text):
    return [ALIASES.get(word, word) for word in re.findall(r'[a-z0-9]+', text.lower()) if len(word) > 1 and word not in STOP]


def sdk(text):
    python = bool(re.search(r'\b(python|pip)\b', text, re.I))
    node = bool(re.search(r'\bnode(?:\.js)?\b|\bnpm\b', text, re.I))
    return 'py' if python and not node else 'node' if node and not python else None


# These words describe an action or a conversational fragment, not its subject.
# Keep SDK/language names as searchable subjects even in a two-word question.
GENERIC = set('configure config set up install init start enable disable turn on off get find view create add delete remove update change do make work works working fix run help tell show want need know learn explain understand simpler simply again more details detail information info something anything thing things question answer yes no hello hi hey thanks thank thx okay ok understood got going about also then next now'.split())
ACTIONS = re.compile(r'\b(configur\w*|setup|set\s+(?:it\s+)?up|install\w*|initializ\w*|enable|disable|create|delete|remove|update|change|find|view|run|use)\b', re.I)


def subjects(text):
    """Lexical subject hints, not a claim that a question is answerable."""
    found = set(terms(text)) - GENERIC
    if re.search(r'\bagentguard\b', text, re.I):
        found.add('agentguard')
    return found


def dependent(text):
    if subjects(text):
        return False
    return bool(re.search(r'\b(it|that|this|those|them|simpler|simply|understand|again|explain|more)\b', text, re.I) or ACTIONS.search(text))


def query_context(question, history):
    users = [m['content'] for m in history if m['role'] == 'user'][-3:]
    previous = []
    if dependent(question):
        # Assistant suggestions never establish a topic. Use the newest user
        # subject, with any intervening incomplete follow-ups, within this chat.
        for index in range(len(users) - 1, -1, -1):
            if subjects(users[index]):
                previous = users[index:]
                break
    elif subjects(question) and users and not subjects(users[-1]) and ACTIONS.search(users[-1]):
        # A short answer such as "Python SDK" can complete "configure what?".
        previous = users[-1:]
    language = sdk(question) or next((sdk(t) for t in reversed(previous) if sdk(t)), 'all')
    return ' '.join([question, *previous]), language


def clarification_message(question, history):
    if subjects(question):
        return None
    if dependent(question) and subjects(query_context(question, history)[0]):
        return None
    if re.search(r'\b(configur\w*|setup|set\s+(?:it\s+)?up)\b', question, re.I):
        return 'What would you like to configure—for example, the Python SDK or a guardrail?'
    if re.search(r'\binstall\w*\b', question, re.I):
        return 'What would you like to install—for example, the Python SDK or the Node.js SDK?'
    if dependent(question):
        return 'Which AgentGuard feature or topic do you mean—for example, SDK setup, traces or project roles?'
    return 'Please add a feature or topic so I can search the documentation—for example, Python SDK setup or project roles.'


class SearchIndex:
    def __init__(self, documentation):
        self.sections = tuple(documentation.sections)
        self.frequencies = []
        for section in self.sections:
            extra = documentation.questions.get((section.page, section.anchor), [])
            self.frequencies.append(Counter(terms(' '.join([section.title, section.title, section.text, *extra]))))
        self.lengths = [sum(counts.values()) for counts in self.frequencies]
        self.average = sum(self.lengths) / max(1, len(self.lengths)) or 1
        self.df = Counter(term for counts in self.frequencies for term in counts)

    def search(self, question, history, max_sections=5, max_characters=30000):
        query, language = query_context(question, history)
        keywords = set(terms(query))
        if not keywords and re.search(r'\bagentguard\b', query, re.I):
            keywords.update(('platform', 'overview'))
        eligible, ranked = [], []
        for section, counts, length in zip(self.sections, self.frequencies, self.lengths):
            if language != 'all' and section.language not in ('all', language):
                continue
            eligible.append(section)
            score = 0
            for term in keywords:
                frequency = counts[term]
                idf = math.log(1 + (len(self.sections) - self.df[term] + .5) / (self.df[term] + .5))
                score += idf * frequency * 2.2 / (frequency + 1.2 * (.25 + .75 * length / self.average))
            if score > 0:
                ranked.append((score, section))
        ranked.sort(key=lambda item: (-item[0], item[1].id))
        selected, used, seen = [], 0, set()

        def add(section):
            nonlocal used
            if section and section.id not in seen and len(selected) < max_sections and used + len(section.text) <= max_characters:
                selected.append(section)
                seen.add(section.id)
                used += len(section.text)

        for _, section in ranked[:2]:
            add(section)
        companions = []
        if selected and selected[0].page == 'onboarding' and selected[0].anchor in ('quickstart', 'detailed', 'faq'):
            companions.extend((('onboarding', 'quickstart'), ('onboarding', 'detailed')))
        if 'guardrail' in keywords:
            companions.extend((('onboarding', 'guardrail-config'), ('security', 'guardrails')))
        for page, anchor in companions:
            add(next((s for s in eligible if s.page == page and s.anchor == anchor), None))
        for score, section in ranked:
            if score < ranked[0][0] * .3:
                break
            add(section)
        return selected
