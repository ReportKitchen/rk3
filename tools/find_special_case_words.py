#!/usr/bin/env python3
"""Find per-document case-sensitive terms in converted PDF HTML.

This is a spike tool for discovering words/phrases that should be protected
when later converting all-caps headings or TOC entries to title/sentence case.

It reads output/pdfium/*/index.html and writes a sibling
special-case-words.json. Evidence comes only from mixed-case document text:
all-caps blocks are skipped because they cannot tell us the intended casing.

Usage:
  python tools/find_special_case_words.py --all
  python tools/find_special_case_words.py 02--foia-basics-for-activists-may-2019
  python tools/find_special_case_words.py output/pdfium/02--foia-basics-for-activists-may-2019/index.html
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, Pattern


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "pdfium"

BLOCK_TAGS = {
    "blockquote",
    "caption",
    "dd",
    "dt",
    "figcaption",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "p",
    "td",
    "th",
}
SKIP_TAGS = {"head", "script", "style", "svg", "nav"}

ACRONYM_RE = re.compile(
    r"(?<![\w])("
    r"(?:[A-Z]\.){2,}[A-Z]?\.?"
    r"|[A-Z]{2,}(?:[/-][A-Z0-9]{1,})*"
    r"|[A-Z]+[0-9]+[A-Z0-9-]*"
    r")(['\u2019]s)?(?![\w])"
)

MIXED_CASE_RE = re.compile(
    r"(?<![\w])("
    r"[a-z]+[A-Z][A-Za-z0-9]*"
    r"|[A-Z][a-z]+[A-Z][A-Za-z0-9]*"
    r")(['\u2019]s)?(?![\w])"
)

TOKEN_RE = re.compile(
    r"[a-z]+[A-Z][A-Za-z0-9]*"
    r"|[A-Z][a-z]+[A-Z][A-Za-z0-9]*"
    r"|(?:[A-Z]\.){2,}[A-Z]?\.?"
    r"|[A-Z]{2,}(?:[/-][A-Z0-9]{1,})*"
    r"|[A-Z]+[0-9]+[A-Z0-9-]*"
    r"|[A-Z][a-z]+(?:[-'\u2019][A-Za-z0-9]+)*"
    r"|&"
    r"|[a-z]+"
    r"|[^\w\s]"
)

CONNECTORS = {
    "&",
    "and",
    "at",
    "by",
    "de",
    "del",
    "du",
    "for",
    "from",
    "in",
    "la",
    "le",
    "of",
    "on",
    "the",
    "to",
    "van",
    "von",
    "with",
}

LEADING_NAME_WORDS = {"A", "An", "The"}
TRAILING_STRIP = ".,;:!?)]}\u201d\u2019\"'"

ACRONYM_DENYLIST = {
    "A.M.",
    "ALL",
    "AM",
    "APPENDIX",
    "CHAPTER",
    "EXAMPLE",
    "FAQ",
    "FIGURE",
    "NO",
    "P.M.",
    "PART",
    "PM",
    "SECTION",
    "TABLE",
    "YES",
}

SINGLE_WORD_DENYLIST = {
    "About",
    "After",
    "All",
    "Also",
    "Although",
    "And",
    "Another",
    "As",
    "At",
    "Before",
    "Below",
    "Between",
    "Both",
    "But",
    "By",
    "Can",
    "Chapter",
    "Data",
    "Do",
    "Does",
    "During",
    "Each",
    "Even",
    "Every",
    "Example",
    "Figure",
    "Finally",
    "First",
    "For",
    "From",
    "Here",
    "How",
    "However",
    "If",
    "In",
    "Introduction",
    "It",
    "Key",
    "Many",
    "More",
    "Most",
    "Next",
    "No",
    "Note",
    "Now",
    "Once",
    "One",
    "Only",
    "Or",
    "Other",
    "Our",
    "Part",
    "Please",
    "Report",
    "Requester",
    "Requesters",
    "Section",
    "Sec",
    "See",
    "Since",
    "So",
    "Some",
    "Table",
    "That",
    "The",
    "Then",
    "There",
    "These",
    "This",
    "Those",
    "Through",
    "To",
    "Use",
    "Using",
    "We",
    "What",
    "When",
    "Where",
    "While",
    "Why",
    "Will",
    "With",
    "Yes",
    "Yet",
    "You",
    "Your",
}


@dataclass
class TextBlock:
    tag: str
    text: str
    page: int | None = None


@dataclass
class TermStats:
    variants: Counter = field(default_factory=Counter)
    pages: set[int] = field(default_factory=set)
    examples: list[str] = field(default_factory=list)

    def add(self, text: str, block: TextBlock) -> None:
        text = clean_term(text)
        if not text:
            return
        self.variants[text] += 1
        if block.page is not None:
            self.pages.add(block.page)
        example = excerpt(block.text, text)
        if example and example not in self.examples and len(self.examples) < 3:
            self.examples.append(example)

    @property
    def count(self) -> int:
        return sum(self.variants.values())

    @property
    def canonical(self) -> str:
        return self.variants.most_common(1)[0][0]

    def to_json(self) -> dict:
        variants = dict(sorted(self.variants.items(), key=lambda item: (-item[1], item[0])))
        return {
            "text": self.canonical,
            "count": self.count,
            "variants": variants,
            "pages": sorted(self.pages),
            "examples": self.examples,
        }


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[TextBlock] = []
        self._stack: list[dict] = []
        self._skip_depth = 0
        self._current_page: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = dict(attrs)
        page = parse_page(attr.get("data-page"))
        if page is not None:
            self._current_page = page
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "br" and self._stack:
            self._stack[-1]["parts"].append("\n")
            return
        if tag in BLOCK_TAGS:
            self._stack.append(
                {
                    "tag": tag,
                    "page": page if page is not None else self._current_page,
                    "parts": [],
                }
            )

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._skip_depth and tag in SKIP_TAGS:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag not in BLOCK_TAGS or not self._stack:
            return
        block = self._stack.pop()
        text = normalize_space(" ".join(block["parts"]))
        if text:
            self.blocks.append(TextBlock(tag=block["tag"], text=text, page=block["page"]))
        if self._stack and text:
            self._stack[-1]["parts"].append(text)

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not self._stack:
            return
        self._stack[-1]["parts"].append(data)


def parse_page(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def clean_term(text: str) -> str:
    text = normalize_space(text).strip(TRAILING_STRIP)
    text = re.sub(r"^(The|A|An)\s+", "", text)
    return text.strip(TRAILING_STRIP)


def is_all_caps_block(text: str) -> bool:
    letters = [ch for ch in text if ch.isalpha()]
    return bool(letters) and all(ch.isupper() for ch in letters)


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z][A-Za-z'\u2019-]*", text))


def repeated_heading_key(text: str) -> str:
    text = normalize_space(text)
    text = re.sub(r"\s+\d{1,4}$", "", text)
    return text.strip()


def is_repeated_heading_candidate(text: str) -> bool:
    text = repeated_heading_key(text)
    if not text or any(ch in ".!?" for ch in text):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'\u2019-]*", text)
    if not 3 <= len(words) <= 12:
        return False
    cap_words = [word for word in words if word[:1].isupper()]
    return len(cap_words) >= 2 and len(cap_words) >= len(words) / 2


def strip_repeated_heading_prefix(block: TextBlock, headings: set[str]) -> TextBlock:
    text = block.text
    for heading in sorted(headings, key=len, reverse=True):
        if text == heading:
            return TextBlock(tag=block.tag, text="", page=block.page)
        if text.startswith(heading + " "):
            rest = text[len(heading) :].strip()
            rest = re.sub(r"^\d{1,4}\b\s*", "", rest)
            return TextBlock(tag=block.tag, text=rest, page=block.page)
    return block


def remove_repeated_heading_noise(blocks: list[TextBlock]) -> list[TextBlock]:
    counts = Counter(
        repeated_heading_key(block.text)
        for block in blocks
        if is_repeated_heading_candidate(block.text)
    )
    headings = {text for text, count in counts.items() if count >= 3}
    if not headings:
        return blocks
    cleaned = [strip_repeated_heading_prefix(block, headings) for block in blocks]
    return [block for block in cleaned if block.text]


def is_acronym_token(token: str) -> bool:
    token = token.strip(TRAILING_STRIP)
    if not token or token in ACRONYM_DENYLIST:
        return False
    letters = [ch for ch in token if ch.isalpha()]
    return len(letters) >= 2 and all(ch.isupper() for ch in letters)


def is_mixed_case_token(token: str) -> bool:
    token = token.strip(TRAILING_STRIP)
    if not token:
        return False
    return bool(MIXED_CASE_RE.fullmatch(token))


def is_capitalized_token(token: str) -> bool:
    if not token or token == "&":
        return False
    if is_mixed_case_token(token):
        return False
    if is_acronym_token(token):
        return True
    return bool(re.match(r"^[A-Z][a-z]+(?:[-'\u2019][A-Za-z0-9]+)*$", token))


def is_connector(token: str) -> bool:
    return token == "&" or token.lower() in CONNECTORS


def likely_sentence_boundary(prev_token: str | None) -> bool:
    return prev_token is None or prev_token in {".", "!", "?", "\u2026", ";", ":"}


def extract_blocks(html: str) -> list[TextBlock]:
    parser = VisibleTextParser()
    parser.feed(html)
    parser.close()
    return parser.blocks


def excerpt(text: str, term: str, width: int = 180) -> str:
    text = normalize_space(text)
    pos = text.lower().find(term.lower())
    if pos < 0:
        return text[:width] + ("..." if len(text) > width else "")
    start = max(0, pos - width // 2)
    end = min(len(text), pos + len(term) + width // 2)
    snippet = text[start:end].strip()
    if start:
        snippet = "..." + snippet
    if end < len(text):
        snippet += "..."
    return snippet


def acronym_key(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def case_sensitive_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def name_key(text: str) -> str:
    return re.sub(r"\s+", " ", clean_term(text).lower())


def iter_acronyms(block: TextBlock) -> Iterable[str]:
    for match in ACRONYM_RE.finditer(block.text):
        token = match.group(1).strip(TRAILING_STRIP)
        if is_acronym_token(token) and not is_structural_label(match):
            yield token


def iter_case_sensitive_terms(block: TextBlock) -> Iterable[str]:
    for match in MIXED_CASE_RE.finditer(block.text):
        token = match.group(1).strip(TRAILING_STRIP)
        if token and not is_bad_case_sensitive_term(token):
            yield token


def is_structural_label(match: re.Match) -> bool:
    token = match.group(1).strip(TRAILING_STRIP).upper()
    if token not in {"APPENDIX", "CHAPTER", "FIGURE", "PART", "SECTION", "TABLE"}:
        return False
    tail = match.string[match.end() : match.end() + 16]
    return bool(re.match(r"\s+(?:[0-9]+|[IVXLCDM]+|[A-Z])\b\s*[:.)-]?", tail))


def is_bad_case_sensitive_term(token: str) -> bool:
    if len(token) < 3:
        return True
    # CamelCase prose compounds tend to be real case-sensitive names/brands;
    # two-letter chunks are usually fragments from a bad split.
    letters = [ch for ch in token if ch.isalpha()]
    return len(letters) < 3


def is_likely_citation_block(block: TextBlock) -> bool:
    text = block.text
    if block.tag not in {"li", "p"}:
        return False
    has_year = bool(re.search(r"\b(?:19|20)\d{2}\b", text))
    if not has_year:
        return False
    has_quoted_title = bool(re.search(r"[\"“][^\"”]{12,}[\"”]", text))
    has_citation_commas = text.count(",") >= 2
    return has_quoted_title and has_citation_commas


def is_prose_evidence_block(block: TextBlock) -> bool:
    if block.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        return False
    words = word_count(block.text)
    if words < 8:
        return False
    if not any(ch in ".!?" for ch in block.text):
        return words >= 18
    return True


def iter_proper_names(block: TextBlock) -> Iterable[str]:
    tokens = TOKEN_RE.findall(block.text)
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if not is_capitalized_token(token):
            i += 1
            continue

        parts = [token]
        atoms = 1
        j = i + 1
        while j < len(tokens):
            current = tokens[j]
            if is_capitalized_token(current):
                parts.append(current)
                atoms += 1
                j += 1
                continue
            if (
                is_connector(current)
                and j + 1 < len(tokens)
                and is_capitalized_token(tokens[j + 1])
            ):
                parts.append(current)
                parts.append(tokens[j + 1])
                atoms += 1
                j += 2
                continue
            break

        if atoms >= 2:
            candidate = clean_term(" ".join(parts))
            if candidate and not is_bad_name(candidate):
                yield candidate
            i = j
        else:
            i += 1


def is_bad_name(candidate: str) -> bool:
    words = candidate.split()
    if not words:
        return True
    if len(words) == 1:
        return True
    if all(is_acronym_token(word) or is_connector(word) for word in words):
        return True
    if words[0] in SINGLE_WORD_DENYLIST and len(words) == 2:
        return True
    return False


def analyze_html(html: str) -> dict:
    blocks = remove_repeated_heading_noise(
        [block for block in extract_blocks(html) if not is_all_caps_block(block.text)]
    )

    acronyms: dict[str, TermStats] = defaultdict(TermStats)
    case_sensitive_terms: dict[str, TermStats] = defaultdict(TermStats)
    proper_names: dict[str, TermStats] = defaultdict(TermStats)

    for block in blocks:
        for acronym in iter_acronyms(block):
            acronyms[acronym_key(acronym)].add(acronym, block)
        for term in iter_case_sensitive_terms(block):
            case_sensitive_terms[case_sensitive_key(term)].add(term, block)
        if is_prose_evidence_block(block) and not is_likely_citation_block(block):
            for name in iter_proper_names(block):
                proper_names[name_key(name)].add(name, block)

    return {
        "summary": {
            "evidence_blocks": len(blocks),
            "acronyms": len(acronyms),
            "case_sensitive_terms": len(case_sensitive_terms),
            "proper_names": len(proper_names),
            "proper_words": 0,
        },
        "acronyms": sorted_terms(acronyms.values()),
        "case_sensitive_terms": sorted_terms(case_sensitive_terms.values()),
        "proper_names": sorted_terms(proper_names.values()),
        "proper_words": [],
    }


def header_key(text: str) -> str:
    return normalize_space(text).casefold()


def unique_headers(html: str) -> list[dict]:
    seen: dict[str, dict] = {}
    for block in extract_blocks(html):
        if block.tag not in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            continue
        key = header_key(block.text)
        if key not in seen:
            seen[key] = {
                "text": block.text,
                "levels": set(),
                "pages": set(),
                "count": 0,
            }
        seen[key]["levels"].add(block.tag)
        if block.page is not None:
            seen[key]["pages"].add(block.page)
        seen[key]["count"] += 1

    headers = []
    for item in seen.values():
        headers.append(
            {
                "text": item["text"],
                "levels": sorted(item["levels"]),
                "pages": sorted(item["pages"]),
                "count": item["count"],
            }
        )
    return headers


def protected_terms(data: dict) -> list[str]:
    terms = []
    for bucket in ("proper_names", "case_sensitive_terms", "acronyms", "proper_words"):
        for item in data.get(bucket, []):
            text = item.get("text")
            if text:
                terms.append(text)
    return sorted(set(terms), key=lambda text: (-len(text.split()), -len(text), text.casefold()))


def protected_term_occurrences(data: dict) -> int:
    total = 0
    for bucket in ("proper_names", "case_sensitive_terms", "acronyms", "proper_words"):
        for item in data.get(bucket, []):
            total += int(item.get("count", 0))
    return total


def term_pattern(term: str) -> Pattern:
    prefix = r"(?<![A-Za-z0-9])" if term[:1].isalnum() else ""
    suffix = r"(?![A-Za-z0-9])" if term[-1:].isalnum() else ""
    return re.compile(prefix + re.escape(term) + suffix, re.IGNORECASE)


def build_protection_patterns(terms: list[str]) -> list[tuple[str, Pattern]]:
    return [(term, term_pattern(term)) for term in terms]


def sentence_case(text: str, patterns: list[tuple[str, Pattern]]) -> tuple[str, list[str]]:
    lowered = text.lower()
    found: list[str] = []
    replacements: list[tuple[int, int, str]] = []

    occupied: list[tuple[int, int]] = []
    for term, pattern in patterns:
        for match in pattern.finditer(text):
            start, end = match.span()
            if any(start < used_end and end > used_start for used_start, used_end in occupied):
                continue
            occupied.append((start, end))
            replacements.append((start, end, term))
            found.append(term)

    out = lowered
    for start, end, term in sorted(replacements, reverse=True):
        out = out[:start] + term + out[end:]

    def cap_first(match: re.Match) -> str:
        return match.group(0).upper()

    out = re.sub(r"[A-Za-z]", cap_first, out, count=1)
    out = re.sub(r"\bi\b", "I", out)
    return out, found


def build_examples(html: str, special_cases: dict) -> dict:
    terms = protected_terms(special_cases)
    patterns = build_protection_patterns(terms)
    headers = []
    header_terms = Counter()
    header_term_occurrences = 0

    for header in unique_headers(html):
        cased, found = sentence_case(header["text"], patterns)
        for term in found:
            header_terms[term] += 1
        header_term_occurrences += len(found)
        headers.append(
            {
                "as_found": header["text"],
                "sentence_case": cased,
                "protected_terms": sorted(set(found), key=str.casefold),
                "protected_term_occurrences": len(found),
                "levels": header["levels"],
                "pages": header["pages"],
                "count": header["count"],
            }
        )

    return {
        "source": "index.html",
        "generated_by": "tools/find_special_case_words.py",
        "summary": {
            "headers": len(headers),
            "total_protected_terms": len(terms),
            "total_protected_term_occurrences": protected_term_occurrences(special_cases),
            "protected_terms_in_headers": len(header_terms),
            "protected_term_header_occurrences": header_term_occurrences,
        },
        "protected_terms_in_headers": [
            {"text": text, "count": count}
            for text, count in sorted(header_terms.items(), key=lambda item: (-item[1], item[0].casefold()))
        ],
        "headers": headers,
    }


def sorted_terms(stats: Iterable[TermStats]) -> list[dict]:
    return [
        item.to_json()
        for item in sorted(stats, key=lambda stat: (-stat.count, stat.canonical.lower()))
    ]


def write_special_cases(index_path: Path) -> tuple[Path, Path]:
    html = index_path.read_text(encoding="utf-8")
    data = analyze_html(html)
    data = {
        "source": index_path.name,
        "generated_by": "tools/find_special_case_words.py",
        **data,
    }
    output_path = index_path.with_name("special-case-words.json")
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    examples = build_examples(html, data)
    examples_path = index_path.with_name("special-case-examples.json")
    examples_path.write_text(json.dumps(examples, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path, examples_path


def resolve_targets(args: argparse.Namespace) -> list[Path]:
    if args.all:
        return sorted(OUT.glob("*/index.html"))
    if not args.targets:
        raise SystemExit("Pass --all, a slug, or one or more index.html paths.")

    paths = []
    for target in args.targets:
        path = Path(target)
        if path.is_file():
            paths.append(path)
            continue
        if path.is_dir() and (path / "index.html").is_file():
            paths.append(path / "index.html")
            continue
        slug_path = OUT / target / "index.html"
        if slug_path.is_file():
            paths.append(slug_path)
            continue
        raise SystemExit(f"No index.html found for {target}")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="*", help="Document slugs, directories, or index.html paths.")
    parser.add_argument("--all", action="store_true", help="Scan every output/pdfium/*/index.html.")
    args = parser.parse_args()

    written = []
    for index_path in resolve_targets(args):
        words_path, examples_path = write_special_cases(index_path)
        written.append((words_path, examples_path))
        print(f"wrote {words_path}")
        print(f"wrote {examples_path}")
    print(f"{len(written)} target(s) processed")


if __name__ == "__main__":
    main()
