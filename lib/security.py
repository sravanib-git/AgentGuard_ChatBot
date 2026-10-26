"""Input limits and recognizable secret patterns for local search."""
import re


def contains_secret(value):
    patterns = (
        r'\b(?:sk-(?:or-v1-|proj-)?[\w-]{20,}|(?:pk|sk)-lf-[\w-]{20,}|AKIA[A-Z0-9]{16})\b',
        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        r'''\b(?:api[_ -]?key|secret[_ -]?key|password)\s*[:=]\s*["']?[\w+/-]{20,}''',
    )
    return any(re.search(pattern, value, re.I) for pattern in patterns)


def validate_request(value):
    if not isinstance(value, dict):
        raise ValueError('Send a JSON object.')
    question = value.get('question')
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError('Enter a question between 1 and 2,000 characters.')
    if value.get('language', 'en') != 'en':
        raise ValueError('Only English documentation is supported.')
    history = value.get('history', [])
    if not isinstance(history, list) or len(history) > 6 or len(history) % 2:
        raise ValueError('History must contain up to three complete exchanges.')
    copied = []
    for index, message in enumerate(history):
        role = 'assistant' if index % 2 else 'user'
        if not isinstance(message, dict) or message.get('role') != role:
            raise ValueError('History must alternate user and assistant messages.')
        content = message.get('content')
        if not isinstance(content, str) or not content.strip() or len(content) > 12000:
            raise ValueError('Invalid history message.')
        copied.append({'role': role, 'content': content})
    if sum(len(message['content']) for message in copied) > 18000:
        raise ValueError('History is too long. Start a new chat.')
    return {'question': question.strip(), 'history': copied}


def blocked_message(value):
    if any(contains_secret(text) for text in [value['question'], *[m['content'] for m in value['history']]]):
        return 'Remove API keys, passwords or private keys before searching.'
    # Direct override phrases receive a fixed reply; no model interprets this input.
    if re.search(r'\b(ignore|override|disregard)\b.{0,50}\b(previous|system|developer|all)\b.{0,30}\b(instructions|rules|prompts?)\b', value['question'], re.I):
        return 'Please search for an AgentGuard feature or documentation topic.'
    return None
