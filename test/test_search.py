import copy
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from lib.documentation import Documentation, Section, ROOT
from lib.keywords import extract_keywords
from lib.search import SearchIndex, query_context
from lib.security import validate_request
from lib.service import SupportService


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documentation = Documentation()
        cls.service = SupportService(cls.documentation)

    def test_documentation_snapshot(self):
        self.assertEqual(self.documentation.page_count, 9)
        self.assertEqual(len(self.documentation.sections), 72)

    def test_keywords_cover_every_sdk_section_and_are_reproducible(self):
        generated = extract_keywords(self.documentation.sections)
        self.assertEqual(generated, extract_keywords(self.documentation.sections))
        self.assertEqual(len(self.documentation.keywords), 72)
        for section in self.documentation.sections:
            key = (section.page, section.anchor, section.language)
            self.assertTrue(self.documentation.keywords[key])
            self.assertTrue(generated[key])
        self.assertIn('python', generated[('onboarding', 'quickstart', 'py')])
        self.assertIn('npm', generated[('onboarding', 'quickstart', 'node')])

    def test_metadata_matches_precede_body_and_preserve_evidence(self):
        body = Section(1, 'body', '', 'Body', 'https://ag-dev.actaclad.com/docs/body', 'all', 'cobalt ' * 100)
        keyword = Section(2, 'keyword', '', 'Keyword', 'https://ag-dev.actaclad.com/docs/keyword', 'all', 'Original keyword section.')
        hypothetical = Section(3, 'question', '', 'Question', 'https://ag-dev.actaclad.com/docs/question', 'all', 'Original question section.')
        docs = type('Docs', (), {'sections': [body, keyword, hypothetical],
                                'keywords': {('keyword', '', 'all'): ['cobalt']},
                                'questions': {('question', ''): ['Where is cobalt?']}})()
        index = SearchIndex(docs)
        matches = index.search('cobalt', [])
        self.assertEqual({s.id for s in matches[:2]}, {2, 3})
        self.assertEqual(matches[-1], body)
        self.assertNotIn('cobalt', keyword.text)
        self.assertEqual(index.search('original', []), [keyword, hypothetical])

    def test_keyword_loader_rejects_invalid_and_missing_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'keywords.json'
            for metadata in ({'version': 1, 'entries': []},
                             {'version': 1, 'entries': [{'page': 'introduction', 'section': '', 'language': 'all', 'keywords': 'invalid'}]},
                             {'version': 1, 'entries': [{'page': 'introduction', 'section': '', 'language': 'all', 'keywords': ['password=' + 'a' * 25]}]}):
                path.write_text(json.dumps(metadata), encoding='utf-8')
                with self.assertRaises(ValueError):
                    Documentation(keywords_path=path)

    def test_expected_sections(self):
        cases = [('Install Python SDK', 'onboarding#quickstart'), ('Where do I set environment variables for Python?', 'onboarding#detailed'), ('Where can I inspect model call latency and token usage?', 'observability#traces'), ('How do I see an entire conversation?', 'observability#sessions'), ('How do I invite someone and assign a project role?', 'rbac#assigning'), ('Where can I export compliance evidence?', 'governance#compliance'), ('How do I revoke login sessions?', 'auth#logout'), ('How do I test an agent for vulnerabilities?', 'security#red-teaming'), ('How do I create a test set?', 'ai-quality#datasets')]
        for question, expected in cases:
            with self.subTest(question=question):
                result = self.service.answer({'question': question})
                self.assertTrue(any(s['url'].endswith(expected) for s in result['sources']))
                self.assertLessEqual(len(result['sources']), 5)
                self.assertLessEqual(sum(len(s['excerpt']) for s in result['sources']), 30000)

    def test_results_are_original_and_offline(self):
        def denied(*args, **kwargs):
            raise AssertionError('Search must not access the network')
        with patch.object(socket.socket, 'connect', denied):
            result = self.service.answer({'question': 'Install Python SDK'})
        for section in result['sources']:
            original = next(s for s in self.documentation.sections if s.id == section['id'])
            self.assertEqual(section['excerpt'], original.text)
            self.assertEqual(section['url'], original.url)
        self.assertNotIn('model', self.service.status())

    def test_question_metadata_stays_out_of_evidence(self):
        original = self.documentation.sections[0]
        fake = type('Docs', (), {'sections': [original], 'questions': {(original.page, original.anchor): ['zephyrcobaltmarker']}})()
        matches = SearchIndex(fake).search('zephyrcobaltmarker', [])
        self.assertEqual(matches, [original])
        self.assertNotIn('zephyrcobaltmarker', matches[0].text)

    def test_followup_and_topic_change(self):
        history = [{'role': 'user', 'content': 'Install Python SDK'}, {'role': 'assistant', 'content': 'Node words must not choose the SDK.'}]
        before = copy.deepcopy(history)
        result = self.service.answer({'question': 'How do I configure it?', 'history': history})
        self.assertTrue(result['sources'])
        self.assertTrue(all(s['language'] != 'node' for s in result['sources']))
        self.assertEqual(query_context('Assign project roles', history)[1], 'all')
        self.assertEqual(query_context('Install Node SDK', history)[1], 'node')
        self.assertEqual(history, before)
        self.assertFalse(hasattr(self.service, 'history'))

    def test_no_match_and_greetings(self):
        for question, status in [('xyzzyprefix teleportation', 'insufficient'), ('hello', 'conversational'), ('thanks', 'conversational')]:
            self.assertEqual(self.service.answer({'question': question})['status'], status)

    def test_secret_inputs_and_history(self):
        self.assertEqual(self.service.answer({'question': 'key sk-or-v1-' + 'a'*40})['status'], 'blocked')
        history = [{'role': 'user', 'content': 'password=' + 'b'*25}, {'role': 'assistant', 'content': 'Okay'}]
        self.assertEqual(self.service.answer({'question': 'Configure Python SDK', 'history': history})['status'], 'blocked')

    def test_guardrail_conflicts_and_budget(self):
        matches = self.service.index.search('Where do guardrails run?', [])
        self.assertTrue(any(s.url.endswith('onboarding#guardrail-config') for s in matches))
        self.assertTrue(any(s.url.endswith('security#guardrails') for s in matches))
        self.assertEqual(self.service.index.search('Install Python SDK', [], max_characters=1), [])

    def test_invalid_requests(self):
        for value in [None, {}, {'question': ''}, {'question': 'x'*2001}, {'question': 'hi', 'language': 'hi'}, {'question': 'hi', 'history': [{'role': 'user', 'content': 'x'}]}, {'question': 'hi', 'history': [{'role': 'system', 'content': 'x'}, {'role': 'assistant', 'content': 'x'}]}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_request(value)

    def test_loader_rejects_links_and_hides_secrets(self):
        original = json.loads((ROOT / 'data/knowledge.json').read_text(encoding='utf-8-sig'))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'docs.json'
            invalid = copy.deepcopy(original)
            invalid['pages'][0]['url'] = 'https://evil.test/docs/introduction'
            path.write_text(json.dumps(invalid), encoding='utf-8')
            with self.assertRaises(ValueError): Documentation(path)
            original['pages'][0]['sections'][0]['text'] += ' password=' + 'a'*25
            path.write_text(json.dumps(original), encoding='utf-8')
            docs = Documentation(path)
            self.assertEqual(docs.excluded_sections, 1)
            self.assertEqual(len(docs.sections), 71)
