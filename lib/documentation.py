"""Load original documentation and validate source identities and links."""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from .security import contains_secret

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = 'https://ag-dev.actaclad.com/docs/'


@dataclass(frozen=True)
class Section:
    id: int
    page: str
    anchor: str
    title: str
    url: str
    language: str
    text: str


class Documentation:
    def __init__(self, path=None, questions_path=None):
        path = Path(path) if path else ROOT / 'data/knowledge.json'
        value = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(value, dict) or value.get('schemaVersion') != 1 or value.get('demo') is not False:
            raise ValueError('Unsupported documentation format.')
        if value.get('provenance', {}).get('complete') is False:
            raise ValueError('Documentation export is incomplete.')
        pages = value.get('pages')
        if not isinstance(pages, list) or not pages:
            raise ValueError('Documentation must contain pages.')
        self.sections = []
        seen = set()
        self.excluded_sections = 0
        section_id = 0
        for page in pages:
            slug = page.get('slug')
            if not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9-]+', slug) or slug in seen:
                raise ValueError('Invalid or repeated page slug.')
            seen.add(slug)
            if page.get('url') != BASE_URL + slug:
                raise ValueError('Unapproved documentation link.')
            if not isinstance(page.get('title'), str) or not page['title'].strip():
                raise ValueError('Documentation title is missing.')
            sections = page.get('sections')
            if sections is None:
                sections = [{'id': '', 'title': page['title'], 'language': 'all', 'text': page.get('text')}]
            if not isinstance(sections, list) or not sections:
                raise ValueError('A page must contain sections.')
            identities = set()
            for section in sections:
                anchor, language, text = section.get('id'), section.get('language'), section.get('text')
                if not isinstance(anchor, str) or not re.fullmatch(r'[a-z0-9-]*', anchor) or language not in ('all', 'py', 'node'):
                    raise ValueError('Invalid section identity.')
                if (anchor, language) in identities:
                    raise ValueError('Repeated section and SDK variant.')
                identities.add((anchor, language))
                if not isinstance(text, str) or not text.strip() or len(text) > 100000:
                    raise ValueError('Invalid documentation section text.')
                heading = section.get('title', page['title'])
                if not isinstance(heading, str):
                    raise ValueError('Invalid section title.')
                section_id += 1
                if contains_secret(text) or contains_secret(heading) or contains_secret(page['title']):
                    self.excluded_sections += 1
                    continue
                title = page['title'] if heading == page['title'] else page['title'] + ' / ' + heading
                self.sections.append(Section(section_id, slug, anchor, title, page['url'] + ('#' + anchor if anchor else ''), language, text))
        self.page_count = len(pages)
        questions_path = Path(questions_path) if questions_path else ROOT / 'data/hypothetical-questions.json'
        metadata = json.loads(questions_path.read_text(encoding='utf-8-sig'))
        self.questions = {}
        valid = {(s.page, s.anchor) for s in self.sections}
        for entry in metadata.get('entries', []):
            key = (entry.get('page'), entry.get('section'))
            questions = entry.get('questions')
            if not isinstance(questions, list) or any(not isinstance(q, str) for q in questions):
                raise ValueError('Invalid search-question metadata.')
            if key in valid:
                self.questions.setdefault(key, []).extend(q for q in questions if not contains_secret(q))
