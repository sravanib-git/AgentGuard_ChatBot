"""Input intent and clarification regressions for the standalone prototype."""
import unittest
from unittest.mock import patch
from lib.search import query_context
from lib.service import SupportService


class QueryHandlingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = SupportService()

    def test_blank_requests_are_rejected(self):
        for question in ('', ' ', '\t\n'):
            with self.subTest(question=question), self.assertRaises(ValueError):
                self.service.answer({'question': question})

    def test_ambiguous_questions_ask_before_searching(self):
        for question in ('How do I configure...', 'configure', 'How do I configure it?',
                         'Can you explain it?', 'What about that?', 'How do I set it up?'):
            with self.subTest(question=question):
                with patch.object(self.service.index, 'search', side_effect=AssertionError('Do not search without a topic')):
                    result = self.service.answer({'question': question})
                self.assertEqual(result['status'], 'clarification')
                self.assertFalse(result['sources'])
                self.assertIn('?', result['answer'])

    def test_low_information_questions_request_a_topic(self):
        for question in ('how', 'the', 'please help', '???', 'please tell me how to use'):
            with self.subTest(question=question):
                result = self.service.answer({'question': question})
                self.assertEqual(result['status'], 'clarification')
                self.assertIn('feature or topic', result['answer'])
                self.assertFalse(result['sources'])

    def test_fragments_with_a_subject_search_normally(self):
        for question in ('Python SDK setup', 'Python SDK', 'SDK', 'trace latency', 'project roles'):
            with self.subTest(question=question):
                result = self.service.answer({'question': question})
                self.assertEqual(result['status'], 'results')
                self.assertTrue(result['sources'])
                if 'Python' in question:
                    self.assertTrue(all(s['language'] != 'node' for s in result['sources']))

    def test_followups_keep_the_current_user_topic(self):
        history = [{'role': 'user', 'content': 'Python SDK setup'},
                   {'role': 'assistant', 'content': 'Matching documentation.'}]
        for question in ('How do I configure it?', 'configure', 'Can you explain it?', 'How do I set it up?'):
            with self.subTest(question=question):
                result = self.service.answer({'question': question, 'history': history})
                self.assertEqual(result['status'], 'results')
                self.assertTrue(all(s['language'] != 'node' for s in result['sources']))
                self.assertIn('Python SDK', query_context(question, history)[0])

    def test_greetings_and_clarification_do_not_invent_a_topic(self):
        for previous in ('hello', 'How do I configure...', 'thanks'):
            history = [{'role': 'user', 'content': previous},
                       {'role': 'assistant', 'content': 'Try Python SDK or guardrails.'}]
            result = self.service.answer({'question': 'How do I configure it?', 'history': history})
            self.assertEqual(result['status'], 'clarification')
            self.assertFalse(result['sources'])

    def test_explicit_topic_change_does_not_borrow_previous_sdk(self):
        history = [{'role': 'user', 'content': 'Python SDK setup'},
                   {'role': 'assistant', 'content': 'Matching documentation.'}]
        query, language = query_context('How do I configure this guardrail?', history)
        self.assertNotIn('Python', query)
        self.assertEqual(language, 'all')

    def test_short_answer_can_complete_a_clarification(self):
        history = [{'role': 'user', 'content': 'How do I configure...'},
                   {'role': 'assistant', 'content': 'What would you like to configure?'}]
        query, language = query_context('Python SDK', history)
        self.assertIn('configure', query)
        self.assertEqual(language, 'py')
        self.assertEqual(self.service.answer({'question': 'Python SDK', 'history': history})['status'], 'results')

    def test_latest_subject_prevents_reviving_an_older_topic(self):
        history = [{'role': 'user', 'content': 'Python SDK setup'},
                   {'role': 'assistant', 'content': 'Matching documentation.'},
                   {'role': 'user', 'content': 'project roles'},
                   {'role': 'assistant', 'content': 'Matching documentation.'}]
        query, language = query_context('How do I configure it?', history)
        self.assertIn('project roles', query)
        self.assertNotIn('Python', query)
        self.assertEqual(language, 'all')

    def test_no_match_wording_does_not_claim_documentation_is_absent(self):
        result = self.service.answer({'question': 'xyzzyprefix teleportation'})
        self.assertEqual(result['status'], 'insufficient')
        self.assertIn("couldn't find", result['answer'])
        self.assertFalse(result['sources'])

    def test_safeguards_run_before_clarification(self):
        result = self.service.answer({'question': 'password=' + 'a' * 25})
        self.assertEqual(result['status'], 'blocked')