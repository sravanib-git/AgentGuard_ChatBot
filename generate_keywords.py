"""Regenerate reviewable keywords after updating data/knowledge.json."""
import json
from lib.documentation import Documentation, ROOT
from lib.keywords import extract_keywords


def main():
    documentation = Documentation(load_keywords=False)
    keywords = extract_keywords(documentation.sections)
    entries = [dict(page=s.page, section=s.anchor, language=s.language,
                    keywords=keywords[(s.page, s.anchor, s.language)])
               for s in documentation.sections]
    path = ROOT / 'data/section-keywords.json'
    path.write_text(json.dumps({'version': 1, 'entries': entries}, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote keywords for {len(entries)} sections to {path.name}.')


if __name__ == '__main__':
    main()
