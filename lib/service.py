"""Request-local documentation support service."""
import re
from .documentation import Documentation
from .search import SearchIndex, clarification_message
from .security import blocked_message, validate_request


def response(text, status, sections=()):
    return {'answer': text, 'status': status, 'mode': 'search', 'sources': [{'id': s.id, 'title': s.title, 'url': s.url, 'language': s.language, 'excerpt': s.text} for s in sections]}


class SupportService:
    def __init__(self, documentation=None):
        self.documentation = documentation or Documentation()
        self.index = SearchIndex(self.documentation)

    def status(self):
        return {'application': 'agentguard-documentation-final', 'mode': 'search', 'pages': self.documentation.page_count, 'sections': len(self.documentation.sections), 'excludedSections': self.documentation.excluded_sections}

    def answer(self, raw):
        value = validate_request(raw)
        blocked = blocked_message(value)
        if blocked:
            return response(blocked, 'blocked')
        social = re.sub(r'[.!?]+$', '', value['question'].lower()).strip()
        if social in ('hi', 'hello', 'hey'):
            return response('Hello. Which AgentGuard feature would you like to find documentation for?', 'conversational')
        if social in ('thanks', 'thank you', 'thx'):
            return response("You're welcome.", 'conversational')
        if social in ('ok', 'okay', 'understood', 'got it'):
            return response('Search for another AgentGuard feature whenever you need it.', 'conversational')
        clarification = clarification_message(value['question'], value['history'])
        if clarification:
            return response(clarification, 'clarification')
        sections = self.index.search(value['question'], value['history'])
        if not sections:
            return response("I couldn't find a relevant section in the available documentation. Try rephrasing your question or browse the documentation.", 'insufficient')
        return response('Here are matching original documentation sections. Open a source link for the full guide.', 'results', sections)
