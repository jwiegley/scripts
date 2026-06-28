#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3Packages.anthropic
"""
Gemini Meeting Notes to Org-mode Converter

Converts Google Meet Gemini-generated meeting notes (Markdown format)
to Emacs Org-mode format with proper metadata, TODO items, and structure.

Usage:
    python gemini_to_org.py input_file.md [output_file.org]

    If output_file is not specified, it will be generated based on the input filename.
"""

import re
import os
import sys
import json
import uuid
import textwrap
import html
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import argparse
from urllib.parse import urlparse
from dataclasses import dataclass, field

# The Anthropic SDK is used against a local Claude-compatible endpoint for
# task shortening, transcript cleanup, and transcript task inference.
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# Configuration
PARTICIPANT_DB_FILE = os.path.expanduser('~/.gemini_to_org_participants.json')
DEFAULT_LOCATION = os.getenv('GEMINI_TO_ORG_LOCATION', '')
DEFAULT_FILETAGS = os.getenv('GEMINI_TO_ORG_FILETAGS', ':todo:meeting:')
DEFAULT_VOCABULARY_FILE = os.getenv(
    'GEMINI_TO_ORG_VOCABULARY',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gemini_to_org_vocabulary.tsv')
)
SHORTEN_PROMPT_FILE = os.path.expanduser('~/.emacs.d/prompts/shorten.txt')
INFER_TASKS_PROMPT_FILE = os.path.expanduser('~/.emacs.d/prompts/infer-tasks.md')
MAX_TASK_TITLE_LENGTH = 67
DEFAULT_CLAUDE_BASE_URL = os.getenv('CLAUDE_BASE_URL', 'http://localhost:8317')
DEFAULT_CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
TRANSCRIPT_TIMESTAMP_HEADING_RE = re.compile(
    r'^[ \t]*#{1,6}[ \t]+(?:\*\*)?(\d{1,2}:\d{2}:\d{2})(?:\*\*)?'
    r'[ \t]*(?:\{#\d{1,2}:\d{2}:\d{2}\})?[ \t]*$'
)
TRANSCRIPT_SPEAKER_LINE_RE = re.compile(
    r'^(\s*\*\*([^*\n:]+?)(?::\*\*|\*\*:)\s*)(.*)$'
)


def transcript_timestamp_heading_match(line: str) -> Optional[re.Match]:
    """Return a match for a Markdown transcript timestamp heading."""
    return TRANSCRIPT_TIMESTAMP_HEADING_RE.match(line.strip())


def transcript_speaker_line_match(line: str) -> Optional[re.Match]:
    """Return a match for common Markdown transcript speaker lines."""
    return TRANSCRIPT_SPEAKER_LINE_RE.match(line)


def default_current_user_name() -> str:
    """Return the current user's full name without embedding it in the script."""
    configured_name = os.getenv('GEMINI_TO_ORG_USER_NAME') or os.getenv('USER_FULL_NAME')
    if configured_name:
        return configured_name.strip()

    try:
        import pwd
        gecos = pwd.getpwuid(os.getuid()).pw_gecos.split(',', 1)[0].strip()
        return gecos
    except Exception:
        return ''


CURRENT_USER_NAME = default_current_user_name()


def is_current_user_name(name: str) -> bool:
    """Compare a participant name to the configured current user."""
    if not CURRENT_USER_NAME:
        return False

    normalize = lambda value: re.sub(r'\s+', ' ', value).strip().casefold()
    if normalize(name) == normalize(CURRENT_USER_NAME):
        return True

    name_parts = name.split()
    current_first, current_last = current_user_name_parts()
    return (
        len(name_parts) == 1 and
        current_first is not None and
        current_last is not None and
        normalize(name_parts[0]) == normalize(current_first)
    )


def current_user_name_parts() -> Tuple[Optional[str], Optional[str]]:
    """Return current user's first and last names when known."""
    parts = CURRENT_USER_NAME.split()
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[-1]


def validate_claude_base_url(base_url: Optional[str]) -> str:
    """Require a non-hosted Claude-compatible endpoint."""
    if not base_url:
        raise ValueError(
            "A local Claude-compatible --base-url is required; refusing to use "
            "Anthropic's hosted API directly."
        )

    parsed = urlparse(base_url)
    hostname = (parsed.hostname or '').lower()
    if hostname == 'anthropic.com' or hostname.endswith('.anthropic.com'):
        raise ValueError(
            f"Refusing to use Anthropic hosted API directly: {base_url}. "
            "Use the local Claude endpoint instead."
        )

    return base_url


def deterministic_short_task_title(title: str, max_length: int = MAX_TASK_TITLE_LENGTH) -> str:
    """Create a short task title without character truncation or ellipses."""
    cleaned = re.sub(r'\s+', ' ', title).strip().rstrip('.')
    cleaned = re.sub(r'\s*\([^)]*\)\s*', ' ', cleaned)
    cleaned = re.sub(r'[:,;]\s*', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    filler = {
        'a', 'an', 'the', 'that', 'this', 'these', 'those', 'of', 'for',
        'to', 'in', 'on', 'at', 'by', 'from', 'through', 'via', 'with',
        'and', 'or', 'as', 'be', 'been', 'being', 'is', 'are', 'was',
        'were', 'will', 'should', 'could', 'would', 'further', 'specific',
        'analyzed', 'provided',
    }

    words = cleaned.split()
    compact_words = []
    for i, word in enumerate(words):
        bare = re.sub(r'^[^\w]+|[^\w]+$', '', word).lower()
        if i > 0 and bare in filler:
            continue
        compact_words.append(word)

    if compact_words:
        cleaned = ' '.join(compact_words)

    if len(cleaned) <= max_length:
        return cleaned

    chosen = []
    for word in cleaned.split():
        candidate = ' '.join(chosen + [word])
        if len(candidate) <= max_length:
            chosen.append(word)

    if chosen:
        return ' '.join(chosen)

    # Degenerate single-token task descriptions need a synthesized headline
    # rather than a silent character slice.
    return "Review generated task description"


def load_prompt_file(prompt_file: str) -> str:
    """Load a prompt file."""
    try:
        with open(os.path.expanduser(prompt_file), 'r', encoding='utf-8') as f:
            return f.read().strip()
    except OSError as e:
        raise ValueError(f"Could not read prompt {prompt_file}: {e}") from e


@dataclass
class VocabularyReplacement:
    """One vocabulary replacement rule."""

    misspelling: str
    replacement: str


class Vocabulary:
    """Applies common transcript spelling corrections."""

    def __init__(self, path: Optional[str] = DEFAULT_VOCABULARY_FILE):
        self.path = os.path.expanduser(path) if path else ''
        self.replacements: List[VocabularyReplacement] = []
        if self.path:
            self.replacements = self._load(self.path)

    def _load(self, path: str) -> List[VocabularyReplacement]:
        """Load a tab-separated vocabulary file."""
        if not os.path.exists(path):
            raise ValueError(f"Vocabulary file not found: {path}")

        replacements: List[VocabularyReplacement] = []
        with open(path, 'r', encoding='utf-8') as f:
            for line_number, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line or line.startswith('#'):
                    continue

                if '\t' in line:
                    misspelling, replacement = line.split('\t', 1)
                else:
                    parts = re.split(r'\s*=>\s*', line, maxsplit=1)
                    if len(parts) != 2:
                        raise ValueError(
                            f"Invalid vocabulary entry in {path}:{line_number}; "
                            "use 'misspelling<TAB>replacement' or 'misspelling => replacement'."
                        )
                    misspelling, replacement = parts

                misspelling = misspelling.strip()
                replacement = replacement.strip()
                if not misspelling or not replacement:
                    raise ValueError(
                        f"Invalid blank vocabulary field in {path}:{line_number}"
                    )

                replacements.append(VocabularyReplacement(misspelling, replacement))

        return replacements

    def apply(self, text: str) -> str:
        """Apply whole-word vocabulary replacements to text."""
        for entry in self.replacements:
            pattern = re.compile(
                rf'(?<![\w-]){re.escape(entry.misspelling)}(?![\w-])',
                re.IGNORECASE
            )
            text = pattern.sub(lambda match: self._match_case(entry.replacement, match.group(0)), text)
        return text

    @staticmethod
    def _match_case(replacement: str, source: str) -> str:
        """Preserve simple capitalization patterns from the misspelling."""
        if source.isupper():
            return replacement.upper()
        if source.islower():
            return replacement.lower()
        if source[:1].isupper() and source[1:].islower():
            return replacement[:1].upper() + replacement[1:]
        return replacement


@dataclass
class OrgTaskEntry:
    """Parsed Org task entry returned by an LLM."""

    keyword: str
    title: str
    priority: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)
    extra_lines: List[str] = field(default_factory=list)


@dataclass
class ParsedNextStep:
    """One Gemini next-step item plus supporting detail lines."""

    text: str
    checked: bool = False
    detail_indent: int = 2
    details: List[str] = field(default_factory=list)

    def source_text(self) -> str:
        """Return the full source text represented by this next-step item."""
        if not self.details:
            return self.text
        return ' '.join([self.text] + self.details)


@dataclass
class ExtraSection:
    """A Gemini note section that is not one of the built-in section names."""

    title: str
    content: List[str] = field(default_factory=list)


def parse_org_task_entries(text: str) -> List[OrgTaskEntry]:
    """Parse flat Org task entries from model output."""
    entries: List[OrgTaskEntry] = []
    current_headline: Optional[str] = None
    current_body: List[str] = []

    def flush():
        nonlocal current_headline, current_body
        if not current_headline:
            return

        match = re.match(
            r'^\*+\s+(TODO|TASK|DONE|WAITING)\s+'
            r'(?:(\[#(?:A|B|C)\])\s+)?(.+?)\s*$',
            current_headline.strip()
        )
        if not match:
            current_headline = None
            current_body = []
            return

        keyword, priority, title_part = match.groups()
        tags: List[str] = []
        tag_match = re.search(r'\s+((?::[A-Za-z0-9_@#%.-]+:)+)\s*$', title_part)
        if tag_match:
            tag_text = tag_match.group(1)
            tags = [tag for tag in tag_text.strip(':').split(':') if tag]
            title_part = title_part[:tag_match.start()].strip()

        properties: Dict[str, str] = {}
        extra_lines: List[str] = []
        in_properties = False
        for body_line in current_body:
            stripped = body_line.strip()
            if stripped == ':PROPERTIES:':
                in_properties = True
                continue
            if in_properties and stripped == ':END:':
                in_properties = False
                continue
            if in_properties:
                prop_match = re.match(r'^:([^:]+):\s*(.*)$', stripped)
                if prop_match:
                    properties[prop_match.group(1)] = prop_match.group(2)
                continue
            if stripped:
                extra_lines.append(body_line.rstrip())

        entries.append(OrgTaskEntry(
            keyword=keyword,
            priority=priority,
            title=title_part.strip(),
            tags=tags,
            properties=properties,
            extra_lines=extra_lines,
        ))
        current_headline = None
        current_body = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if re.match(r'^\*+\s+(?:TODO|TASK|DONE|WAITING)\s+', line.strip()):
            flush()
            current_headline = line
            current_body = []
        elif current_headline:
            current_body.append(line)

    flush()
    return entries


class ParticipantDatabase:
    """Manages persistent participant ID mappings."""

    def __init__(self, db_file: str = PARTICIPANT_DB_FILE):
        self.db_file = db_file
        self.participants: Dict[str, str] = {}
        self.load()

    def load(self):
        """Load participant IDs from JSON file."""
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.participants = json.load(f)

    def save(self):
        """Save participant IDs to JSON file."""
        with open(self.db_file, 'w') as f:
            json.dump(self.participants, f, indent=2, sort_keys=True)

    def get_id(self, name: str) -> str:
        """Get or create a UUID for a participant."""
        if name not in self.participants:
            self.participants[name] = str(uuid.uuid4()).upper()
        return self.participants[name]


class TodoShortener:
    """Shortens TODO titles using the local Claude-compatible endpoint."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 prompt_file: str = SHORTEN_PROMPT_FILE):
        """Initialize with API key and optional base URL."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")

        self.api_key = api_key or DEFAULT_CLAUDE_API_KEY
        if not self.api_key:
            raise ValueError("Claude API key not provided")

        base_url = validate_claude_base_url(base_url)

        # Create client with optional base_url
        client_kwargs = {'api_key': self.api_key, 'base_url': base_url}

        self.client = Anthropic(**client_kwargs)
        self.max_title_length = MAX_TASK_TITLE_LENGTH
        self.prompt_file = prompt_file
        self.prompt_template = self._load_prompt(prompt_file)

    def _load_prompt(self, prompt_file: str) -> str:
        """Load the task shortening prompt used by Emacs."""
        try:
            with open(os.path.expanduser(prompt_file), 'r', encoding='utf-8') as f:
                return f.read().strip()
        except OSError as e:
            raise ValueError(f"Could not read task shortening prompt {prompt_file}: {e}") from e

    def _build_task_prompt(self, title: str, keyword: str, tag: Optional[str]) -> str:
        """Build a minimal Org task for the shortening prompt."""
        tag_suffix = f"  :{tag}:" if tag else ""
        task = (
            f"*** {keyword} {title}{tag_suffix}\n"
            ":PROPERTIES:\n"
            ":ID:       00000000-0000-0000-0000-000000000000\n"
            ":END:"
        )
        return (
            f"{self.prompt_template}\n\n"
            "Shorten this task title according to the prompt above. "
            "Return only the updated Org task, with no commentary.\n\n"
            f"{task}"
        )

    def _extract_shortened_title(self, response: str) -> Optional[str]:
        """Extract the task title from a model response."""
        for line in response.splitlines():
            line = line.strip()
            if not line.startswith('*** '):
                continue

            match = re.match(r'^\*\*\*\s+(?:TODO|TASK|DONE|WAITING)\s+(.+?)\s*$', line)
            if not match:
                continue

            title = match.group(1).strip()
            title = re.sub(r'\s+(:[^:\s]+:)+\s*$', '', title).strip()
            return title

        # Be tolerant of older model behavior that returns only a
        # bare title despite being asked for an Org task.
        for line in response.splitlines():
            title = line.strip().strip('"')
            if title and not title.startswith(':') and not title.startswith('*'):
                return title

        return None

    def _call_shortening_model(self, prompt: str) -> str:
        """Request one shortened task from the local model."""
        message = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text.strip()

    def shorten_title(self, title: str, keyword: str = "TODO",
                      tag: Optional[str] = None,
                      verbose: bool = False) -> Tuple[str, Optional[str]]:
        """
        Shorten a TODO title using Claude.

        Returns:
            (shortened_title, body_text) - body_text is None if title didn't need shortening
        """
        # If title is already short enough, return as-is
        if len(title) <= self.max_title_length:
            return title, None

        prompt = self._build_task_prompt(title, keyword, tag)

        shortened = None
        last_error = "Claude did not return a usable TODO headline"
        current_prompt = prompt
        for _ in range(2):
            shortened = self._extract_shortened_title(self._call_shortening_model(current_prompt))
            if shortened and len(shortened) <= self.max_title_length:
                break

            if shortened:
                last_error = (
                    f"Claude returned an overlong TODO title "
                    f"({len(shortened)} > {self.max_title_length} chars): {shortened}"
                )
            current_prompt = (
                f"{prompt}\n\n"
                f"The previous response was invalid: {last_error}\n"
                f"Return the same Org task again, but the headline title must be "
                f"{self.max_title_length} characters or fewer. Return only the Org task."
            )
        else:
            raise ValueError(last_error)

        if verbose:
            print(f"Shortened TODO: {title}", file=sys.stderr)
            print(f"          To: {shortened}", file=sys.stderr)

        return shortened, title


class TranscriptCleaner:
    """Cleans transcript turn text while preserving timestamps and speakers."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: str = "claude-sonnet-4-5-20250929"):
        """Initialize with API key, optional base URL, and model."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")

        self.api_key = api_key or DEFAULT_CLAUDE_API_KEY
        if not self.api_key:
            raise ValueError("Claude API key not provided")

        base_url = validate_claude_base_url(base_url)

        # Create client with optional base_url
        client_kwargs = {'api_key': self.api_key, 'base_url': base_url}

        self.client = Anthropic(**client_kwargs)
        self.model = model
        self.max_chunk_size = 12000
        self.chunk_target_size = 6000
        self.max_cleanup_tokens = 8192

    def clean(self, transcript_text: str, verbose: bool = False) -> str:
        """
        Clean up a meeting transcript using Claude.

        Args:
            transcript_text: Raw markdown transcript text
            verbose: Enable verbose logging

        Returns:
            Cleaned markdown transcript text

        Raises:
            Exceptions from the local Claude-compatible endpoint or structural
            validation errors. Cleanup is fail-closed so the caller cannot
            mistake a raw or partially cleaned transcript for a successful
            cleanup.
        """
        if verbose:
            print(f"Cleaning transcript ({len(transcript_text)} chars)...", file=sys.stderr)

        # Check if we need to chunk the transcript
        if len(transcript_text) > self.max_chunk_size:
            if verbose:
                print(f"Transcript is large, processing in chunks...", file=sys.stderr)
            return self._clean_chunked(transcript_text, verbose)
        else:
            return self._clean_single(transcript_text, verbose)

    def _clean_single(self, transcript_text: str, verbose: bool = False) -> str:
        """Clean a single transcript (not chunked)."""
        turns = self._extract_speaker_turns(transcript_text)
        if not turns:
            raise ValueError("Could not find speaker turns for transcript cleanup")

        prompt = """Clean up the text for these meeting transcript speaker turns.

Each turn has an immutable ID and speaker. You are NOT rewriting the transcript
Markdown. You are only cleaning the text inside each speaker turn.

Rules:
1. Return every input ID exactly once, in the same order.
2. Do NOT add, remove, split, combine, or rename IDs.
3. Do NOT move words, phrases, clauses, or sentences between IDs.
4. Do NOT combine fragments across turns, even if that would improve grammar.
5. If a turn is a standalone acknowledgment or filler-only turn, return a
   minimal cleaned version for that same ID; do not omit the ID.
6. Clean only within the same turn: remove obvious filler words, fix grammar,
   and correct obvious transcription errors without changing meaning.
7. Preserve technical terms, proper nouns, and domain jargon.
8. If a turn cannot be safely cleaned, return its original text for that ID.

Output ONLY lines in this exact format, with no preamble or commentary:
<turn id="T0001">cleaned text</turn>"""

        full_prompt = f"{prompt}\n\n<turns>\n{self._format_turns_for_prompt(turns)}\n</turns>"
        last_error = None
        for _ in range(2):
            try:
                cleaned = self._stream_cleanup_response(full_prompt)
                if not cleaned:
                    raise ValueError("Claude returned an empty transcript cleanup response")
                replacements = self._parse_cleaned_turns(cleaned, turns)
                cleaned = self._rebuild_transcript_with_cleaned_turns(transcript_text, turns, replacements)
                self._validate_cleaned_transcript(transcript_text, cleaned)

                if verbose:
                    print(f"Transcript cleaned successfully", file=sys.stderr)

                return cleaned
            except ValueError as e:
                last_error = e
                full_prompt = (
                    f"{prompt}\n\n"
                    f"The previous response was invalid: {e}\n"
                    "Try again. Preserve every turn ID exactly once and in order. "
                    "Do not move text between IDs. Do not expand short turns; "
                    "leave acknowledgments and fragments unchanged when needed.\n\n"
                    f"<turns>\n{self._format_turns_for_prompt(turns)}\n</turns>"
                )

        raise last_error

    def _stream_cleanup_response(self, prompt: str) -> str:
        """Stream one cleanup response from the local model."""
        text_parts = []
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_cleanup_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        ) as stream:
            for text in stream.text_stream:
                text_parts.append(text)
        return ''.join(text_parts).strip()

    def _extract_speaker_turns(self, transcript_text: str) -> List[Dict[str, str]]:
        """Extract speaker turns that can be cleaned independently."""
        turns = []
        for line_index, line in enumerate(transcript_text.splitlines()):
            match = transcript_speaker_line_match(line)
            if not match:
                continue

            turn_id = f"T{len(turns) + 1:04d}"
            turns.append({
                'id': turn_id,
                'line_index': str(line_index),
                'prefix': match.group(1),
                'speaker': match.group(2).strip(),
                'text': match.group(3).strip(),
            })
        return turns

    def _format_turns_for_prompt(self, turns: List[Dict[str, str]]) -> str:
        """Format speaker turns as immutable XML-like records."""
        formatted = []
        for turn in turns:
            formatted.append(
                f'<turn id="{turn["id"]}" speaker="{html.escape(turn["speaker"])}">'
                f'{html.escape(turn["text"])}</turn>'
            )
        return '\n'.join(formatted)

    def _parse_cleaned_turns(self, response: str,
                             turns: List[Dict[str, str]]) -> Dict[str, str]:
        """Parse cleaned turn text and validate ID preservation."""
        matches = re.findall(
            r'<turn\s+id="(T\d{4})"(?:\s+[^>]*)?>(.*?)</turn>',
            response,
            flags=re.DOTALL
        )
        if not matches:
            raise ValueError("Claude returned no cleaned transcript turns")

        expected_ids = [turn['id'] for turn in turns]
        actual_ids = [turn_id for turn_id, _ in matches]
        if actual_ids != expected_ids:
            raise ValueError("Claude changed transcript turn IDs during cleanup")

        replacements = {
            turn_id: html.unescape(text).strip()
            for turn_id, text in matches
        }

        for turn in turns:
            original = turn['text']
            cleaned = replacements[turn['id']]
            original_words = len(re.findall(r'\w+', original))
            cleaned_words = len(re.findall(r'\w+', cleaned))

            if original_words <= 3 and cleaned_words > max(5, original_words + 4):
                raise ValueError(
                    f"Claude expanded short transcript turn {turn['id']} "
                    f"from {original_words} to {cleaned_words} words during cleanup"
                )
            if len(cleaned) > max(200, len(original) * 3 + 80):
                raise ValueError(
                    f"Claude expanded transcript turn {turn['id']} too much during cleanup "
                    f"({len(original)} to {len(cleaned)} chars)"
                )

        return replacements

    def _rebuild_transcript_with_cleaned_turns(
            self,
            transcript_text: str,
            turns: List[Dict[str, str]],
            replacements: Dict[str, str]) -> str:
        """Rebuild transcript Markdown with original attribution structure."""
        lines = transcript_text.splitlines()
        for turn in turns:
            line_index = int(turn['line_index'])
            cleaned_text = replacements[turn['id']]
            if cleaned_text:
                lines[line_index] = f"{turn['prefix']}{cleaned_text}"
            else:
                lines[line_index] = turn['prefix'].rstrip()
        return '\n'.join(lines)

    def _timestamp_headers(self, transcript_text: str) -> List[str]:
        """Return timestamp headings in transcript order."""
        headers = []
        for line in transcript_text.splitlines():
            stripped = line.strip()
            if transcript_timestamp_heading_match(stripped):
                headers.append(stripped)
        return headers

    def _speaker_attributions(self, transcript_text: str) -> List[str]:
        """Return speaker attributions in transcript order."""
        speakers = []
        for line in transcript_text.splitlines():
            match = transcript_speaker_line_match(line)
            if match:
                speakers.append(match.group(2).strip())
        return speakers

    def _validate_cleaned_transcript(self, original: str, cleaned: str):
        """Ensure cleanup did not change transcript structure or attribution."""
        original_timestamps = self._timestamp_headers(original)
        cleaned_timestamps = self._timestamp_headers(cleaned)
        if original_timestamps != cleaned_timestamps:
            raise ValueError(
                "Claude changed timestamp headings during transcript cleanup"
            )

        original_speakers = self._speaker_attributions(original)
        cleaned_speakers = self._speaker_attributions(cleaned)
        if original_speakers != cleaned_speakers:
            raise ValueError(
                "Claude changed speaker attribution order during transcript cleanup"
            )

    def _clean_chunked(self, transcript_text: str, verbose: bool = False) -> str:
        """Clean a large transcript by processing it in chunks."""
        # Split by timestamp boundaries while accepting Google export
        # variations in heading depth and bold wrapping.
        timestamp_pattern = (
            r'(^[ \t]*#{1,6}[ \t]+(?:\*\*)?\d{1,2}:\d{2}:\d{2}(?:\*\*)?'
            r'[ \t]*(?:\{#\d{1,2}:\d{2}:\d{2}\})?[ \t]*$)'
        )
        parts = re.split(
            timestamp_pattern,
            transcript_text,
            flags=re.MULTILINE,
        )

        # Reconstruct sections: each section is (timestamp_header, content)
        sections = []
        for i in range(1, len(parts), 2):
            if i < len(parts):
                timestamp_header = parts[i]
                content = parts[i + 1] if i + 1 < len(parts) else ""
                sections.append((timestamp_header, content))

        if verbose:
            print(f"Split transcript into {len(sections)} timestamp sections", file=sys.stderr)

        if not sections:
            raise ValueError("Could not find timestamp sections for transcript cleanup")

        # Group timestamp sections by character budget so cleanup requests
        # stay small enough to complete promptly on the local endpoint.
        section_chunks = []
        current_chunk = []
        current_length = 0
        for section in sections:
            section_text = f"{section[0]}\n{section[1]}\n"
            section_length = len(section_text)
            if current_chunk and current_length + section_length > self.chunk_target_size:
                section_chunks.append(current_chunk)
                current_chunk = []
                current_length = 0

            current_chunk.append(section)
            current_length += section_length

        if current_chunk:
            section_chunks.append(current_chunk)

        chunks = []
        previous_section_count = 0
        for chunk_sections in section_chunks:
            first_real_timestamp = chunk_sections[0][0] if chunk_sections else None

            # For chunks after the first, include last 2 sections from previous chunk as context
            if previous_section_count > 0:
                context_sections = sections[max(0, previous_section_count - 2):previous_section_count]
                context_text = "[CONTEXT - DO NOT INCLUDE IN OUTPUT]\n"
                for ts, content in context_sections:
                    context_text += f"{ts}\n{content}\n"
                context_text += "\n"
            else:
                context_text = ""

            # Build chunk text
            chunk_text = context_text
            for ts, content in chunk_sections:
                chunk_text += f"{ts}\n{content}\n"

            chunks.append((chunk_text, len(context_text) > 0, first_real_timestamp))
            previous_section_count += len(chunk_sections)

        if verbose:
            print(f"Processing {len(chunks)} chunks...", file=sys.stderr)

        # Process each chunk
        cleaned_chunks = []
        for idx, (chunk_text, has_context, first_real_timestamp) in enumerate(chunks):
            if verbose:
                print(f"Processing chunk {idx + 1}/{len(chunks)}...", file=sys.stderr)

            cleaned_chunk = self._clean_single(chunk_text, verbose=False)

            # If this chunk had context, remove any returned context before
            # the first timestamp that belongs to this chunk. The model may
            # keep or drop the explicit context marker.
            if has_context and first_real_timestamp:
                real_start = cleaned_chunk.find(first_real_timestamp)
                if real_start == -1:
                    timestamp_match = re.search(r'\d{1,2}:\d{2}:\d{2}', first_real_timestamp)
                    if timestamp_match:
                        timestamp = re.escape(timestamp_match.group(0))
                        real_match = re.search(
                            rf'#{{1,6}}\s+(?:\*\*)?{timestamp}(?:\*\*)?'
                            rf'(?:\s*\{{#{timestamp}\}})?',
                            cleaned_chunk
                        )
                        if real_match:
                            real_start = real_match.start()

                if real_start != -1:
                    cleaned_chunk = cleaned_chunk[real_start:]
                else:
                    lines = cleaned_chunk.split('\n')
                    cleaned_chunk = '\n'.join(
                        line for line in lines
                        if '[CONTEXT - DO NOT INCLUDE IN OUTPUT]' not in line
                    )

            cleaned_chunks.append(cleaned_chunk)

        # Concatenate all cleaned chunks
        result = '\n\n'.join(cleaned_chunks)

        if verbose:
            print(f"Transcript cleaning complete ({len(result)} chars)", file=sys.stderr)

        return result


class TranscriptTaskInferer:
    """Infers missing action items from transcript text via local Claude."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 prompt_file: str = INFER_TASKS_PROMPT_FILE,
                 model: str = "claude-sonnet-4-5-20250929"):
        """Initialize with local Claude-compatible endpoint settings."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")

        self.api_key = api_key or DEFAULT_CLAUDE_API_KEY
        if not self.api_key:
            raise ValueError("Claude API key not provided")

        base_url = validate_claude_base_url(base_url)
        self.client = Anthropic(api_key=self.api_key, base_url=base_url)
        self.model = model
        self.prompt_file = prompt_file
        self.prompt_template = load_prompt_file(prompt_file)

    def _prompt_with_source(self, source_text: str) -> str:
        """Apply the configured infer-tasks prompt to source text."""
        if '{{SOURCE_TEXT}}' in self.prompt_template:
            return self.prompt_template.replace('{{SOURCE_TEXT}}', source_text)

        return f"{self.prompt_template}\n\n<input>\n{source_text}\n</input>"

    def _call_model(self, prompt: str, max_tokens: int = 12000) -> str:
        """Call the local Claude-compatible endpoint."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()

    def infer_transcript_tasks(self, transcript_text: str, verbose: bool = False) -> str:
        """Infer candidate tasks from the full transcript text."""
        if verbose:
            print(
                f"Inferring tasks from transcript using {self.prompt_file} "
                f"({len(transcript_text)} chars)...",
                file=sys.stderr
            )

        return self._call_model(self._prompt_with_source(transcript_text))

    def select_additional_tasks(self, transcript_text: str, gemini_tasks: List[str],
                                inferred_tasks_text: str,
                                verbose: bool = False) -> List[OrgTaskEntry]:
        """Select inferred tasks that should be added beyond Gemini tasks."""
        inferred_entries = parse_org_task_entries(inferred_tasks_text)
        if verbose:
            print(f"Inferred {len(inferred_entries)} transcript task candidates", file=sys.stderr)

        if not inferred_entries:
            return []

        gemini_task_text = '\n'.join(f"- {task}" for task in gemini_tasks) or "(none)"
        comparison_prompt = f"""You are augmenting Gemini meeting action items.

You will receive:
1. The full transcript text.
2. Gemini's action-item list.
3. A second AI-produced list of tasks inferred from the transcript.

Use careful judgment to decide which inferred tasks really should be added to
the final action-item list.

Rules:
- Default to omission. Add a task only when the transcript contains a clear
  unresolved commitment, request, or follow-up that should survive as an action
  item.
- Return ONLY inferred tasks that are grounded in explicit transcript language.
- Omit tasks already covered by Gemini's action items, even if wording differs.
- Omit weaker, broader, narrower, or procedural versions of an existing Gemini task.
- Omit speculative discussion, completed past work, and vague aspirations.
- Omit status updates or ongoing work descriptions unless someone makes a new
  future-oriented commitment during this meeting.
- Omit tasks supported only by phrases like "has been working on", "was able to",
  "not merged", "running into conflicts", or "making progress".
- Keep only independently committed outcomes that should become action items.
- Preserve assignee tags from inferred tasks when they are correct.
- Output a flat list of Org-mode task entries using one star, TODO/TASK/WAITING,
  optional priority, title, and optional tags.
- Keep every title text at or below {MAX_TASK_TITLE_LENGTH} characters.
- Do not include rationale, explanations, markdown, or prose after the task list.
- If no inferred task should be added, output exactly:
No additional tasks identified.

<gemini_action_items>
{gemini_task_text}
</gemini_action_items>

<inferred_task_candidates>
{inferred_tasks_text}
</inferred_task_candidates>

<transcript>
{transcript_text}
</transcript>"""

        selected_text = self._call_model(comparison_prompt, max_tokens=8000)
        selected_entries = parse_org_task_entries(selected_text)
        if not selected_entries:
            selected_entries = self._select_additional_tasks_locally(
                transcript_text,
                gemini_tasks,
                inferred_entries,
            )

        if verbose:
            print(f"Selected {len(selected_entries)} additional transcript tasks", file=sys.stderr)

        return selected_entries

    def _task_tokens(self, text: str, *, include_actions: bool = True) -> List[str]:
        """Return normalized tokens for task comparison."""
        text = html.unescape(text).casefold()
        text = re.sub(r'\[[^\]]+\]', ' ', text)
        text = text.replace('follow-up', 'followup')
        synonyms = {
            'contracting': 'contract',
            'contractor': 'contract',
            'contracts': 'contract',
            'discussion': 'discuss',
            'discussions': 'discuss',
            'followup': 'meeting',
            'meetup': 'meeting',
            'meetups': 'meeting',
            'session': 'meeting',
            'sessions': 'meeting',
            'terms': 'term',
            'whiteboard': 'meeting',
        }
        stopwords = {
            'and', 'or', 'but', 'with', 'without', 'from', 'into', 'onto',
            'for', 'to', 'of', 'in', 'on', 'at', 'by', 'as', 'is', 'are',
            'be', 'being', 'been', 'the', 'a', 'an', 'this', 'that', 'these',
            'those', 'it', 'its', 'their', 'our', 'your', 'his', 'her', 'task',
            'tasks', 'todo', 'will',
        }
        action_words = {
            'complete', 'consider', 'discuss', 'evaluate', 'file',
            'investigate', 'negotiate', 'plan', 'prepare', 'provide', 'pull',
            'push', 'review', 'schedule', 'test',
        }
        tokens = []
        for token in re.findall(r'[a-z0-9]+(?:\.[0-9]+)?', text):
            if token in stopwords:
                continue
            token = synonyms.get(token, token)
            if len(token) > 3 and token.endswith('s') and not token.endswith('ss'):
                token = token[:-1]
            if not include_actions and token in action_words:
                continue
            tokens.append(token)
        return tokens

    def _task_token_set(self, text: str, *, include_actions: bool = True) -> set:
        """Return normalized token set for task comparison."""
        return set(self._task_tokens(text, include_actions=include_actions))

    def _is_grounded_task_title(self, title: str, transcript_tokens: set) -> bool:
        """Return whether a candidate title is sufficiently supported by source."""
        title_tokens = self._task_token_set(title, include_actions=False)
        if not title_tokens:
            return True
        covered = sum(1 for token in title_tokens if token in transcript_tokens)
        return covered / len(title_tokens) >= 0.70

    def _is_meeting_task(self, tokens: set) -> bool:
        """Return whether tokens describe scheduling or planning a meeting."""
        return (
            'meeting' in tokens and
            bool(tokens & {'schedule', 'plan', 'discuss'})
        )

    def _is_duplicate_task_title(self, title: str, existing_titles: List[str]) -> bool:
        """Return whether a candidate title is covered by existing task titles."""
        candidate = self._task_token_set(title)
        if not candidate:
            return False
        for existing_title in existing_titles:
            existing = self._task_token_set(existing_title)
            if not existing:
                continue
            overlap = len(candidate & existing)
            if overlap / len(candidate) >= 0.50:
                return True
            if overlap / len(candidate | existing) >= 0.45:
                return True
            if self._is_meeting_task(candidate) and self._is_meeting_task(existing):
                topic_overlap = (candidate - {'meeting', 'schedule', 'plan', 'discuss'}) & (
                    existing - {'meeting', 'schedule', 'plan', 'discuss'}
                )
                if topic_overlap or overlap >= 2:
                    return True
        return False

    def _select_additional_tasks_locally(
            self,
            transcript_text: str,
            gemini_tasks: List[str],
            inferred_entries: List[OrgTaskEntry]) -> List[OrgTaskEntry]:
        """Choose grounded, non-duplicate candidates without another model pass."""
        transcript_tokens = self._task_token_set(transcript_text, include_actions=True)
        existing_titles = list(gemini_tasks)
        selected_entries: List[OrgTaskEntry] = []

        for entry in inferred_entries:
            if not self._is_grounded_task_title(entry.title, transcript_tokens):
                continue
            if self._is_duplicate_task_title(entry.title, existing_titles):
                continue
            selected_entries.append(entry)
            existing_titles.append(entry.title)

        return selected_entries

    def infer_additional_tasks(self, transcript_text: str, gemini_tasks: List[str],
                               verbose: bool = False) -> List[OrgTaskEntry]:
        """Infer transcript tasks and select the missing additions."""
        if not transcript_text.strip():
            return []

        inferred = self.infer_transcript_tasks(transcript_text, verbose=verbose)
        return self.select_additional_tasks(
            transcript_text,
            gemini_tasks,
            inferred,
            verbose=verbose
        )


class GeminiToOrgConverter:
    """Converts Gemini meeting notes to Org-mode format."""

    def __init__(self, input_file: str, participant_db: ParticipantDatabase,
                 todo_shortener: Optional['TodoShortener'] = None,
                 transcript_cleaner: Optional['TranscriptCleaner'] = None,
                 task_inferer: Optional['TranscriptTaskInferer'] = None,
                 vocabulary: Optional[Vocabulary] = None,
                 verbose: bool = False):
        self.input_file = input_file
        self.participant_db = participant_db
        self.todo_shortener = todo_shortener
        self.transcript_cleaner = transcript_cleaner
        self.task_inferer = task_inferer
        self.vocabulary = vocabulary
        self.verbose = verbose
        self.metadata = {}
        self.content = ""
        self.sections = {
            'summary': [],
            'decisions': [],
            'details': [],
            'next_steps': [],
            'transcript': []
        }
        self.extra_sections: List[ExtraSection] = []
        self.note_section_order: List[Tuple[str, Optional[int]]] = []

    def convert(self) -> str:
        """Main conversion method."""
        self._parse_filename()
        self._read_content()
        self._parse_content()
        return self._build_org_output()

    def _parse_filename(self):
        """Parse filename to extract metadata.

        Handles multiple Gemini note formats:
        - "Name - Title - YYYY_MM_DD HH_MM TZ - Notes by Gemini.md"
        - "Title - YYYY_MM_DD HH_MM TZ - Notes by Gemini.md"
        - "Meeting started YYYY_MM_DD HH_MM TZ - Notes by Gemini.md"
        """
        basename = os.path.basename(self.input_file)

        # Check if this is a Gemini notes file
        if not basename.endswith('Notes by Gemini.md'):
            raise ValueError(f"Not a Gemini notes file (must end with 'Notes by Gemini.md'): {basename}")

        # Remove the suffix
        name_part = basename[:-len(' - Notes by Gemini.md')].strip()
        if name_part.endswith(' -'):
            name_part = name_part[:-2].strip()

        # Extract date/time pattern: YYYY_MM_DD HH_MM TZ
        datetime_pattern = r'(\d{4})_(\d{2})_(\d{2})\s+(\d{2})_(\d{2})\s+(\w+)(?:\s+-)?$'
        datetime_match = re.search(datetime_pattern, name_part)

        if not datetime_match:
            raise ValueError(f"Could not find date/time in filename: {basename}")

        year, month, day, hour, minute, tz = datetime_match.groups()

        # Extract the part before the date/time
        prefix = name_part[:datetime_match.start()].strip()

        # Remove trailing dash if present
        if prefix.endswith(' -'):
            prefix = prefix[:-2].strip()

        # Try to split into participant and title
        if ' - ' in prefix:
            parts = prefix.split(' - ', 1)
            participant1 = parts[0].strip()
            title = parts[1].strip()
        else:
            # No clear separation - use the whole prefix as title
            participant1 = ''
            title = prefix if prefix else 'Meeting'

        # Create datetime object
        dt = datetime(int(year), int(month), int(day), int(hour), int(minute))

        self.metadata.update({
            'participant1': participant1,
            'title': title,
            'date': dt,
            'timezone': tz,
            'year': year,
            'month': month,
            'day': day,
            'hour': hour,
            'minute': minute,
        })

    def _read_content(self):
        """Read the markdown file."""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            self.content = f.read()
        if self.vocabulary:
            self.content = self.vocabulary.apply(self.content)

    def _parse_markdown_heading(self, line: str) -> Optional[Tuple[int, str]]:
        """Return (heading_level, normalized_title) for a Markdown heading."""
        match = re.match(r'^(#{1,6})\s+(.*?)\s*(?:\{#[^}]+\})?\s*$', line.strip())
        if not match:
            return None

        title = match.group(2).strip()
        title = re.sub(r'\\([\\`*_{}\[\]()#+\-.!])', r'\1', title)

        # Google currently wraps many headings in bold markers and may prefix
        # them with an emoji. Normalize those decorations away for matching.
        changed = True
        while changed:
            changed = False
            for marker in ('**', '__', '*', '_', '`'):
                if title.startswith(marker) and title.endswith(marker):
                    title = title[len(marker):-len(marker)].strip()
                    changed = True

        title = re.sub(r'^[^\w\d:]+', '', title).strip()
        title = re.sub(r'\s+', ' ', title)
        return len(match.group(1)), title

    def _section_for_heading(self, level: int, title: str) -> Optional[str]:
        """Map a normalized heading title to an internal section name."""
        normalized = title.casefold().strip()

        if normalized in ('summary', 'overview'):
            return 'summary'
        if normalized in ('decisions', 'decision log'):
            return 'decisions'
        if normalized in ('details', 'detailed notes', 'discussion details'):
            return 'details'
        if normalized in ('next steps', 'suggested next steps', 'action items', 'tasks'):
            return 'next_steps'
        if normalized in ('transcript', 'full transcript'):
            return 'transcript'

        # Some older exports did not include a separate top-level transcript
        # marker and instead used the meeting title suffixed with "Transcript".
        if level <= 2 and normalized.endswith(' - transcript'):
            return 'transcript'

        return None

    def _is_boilerplate_line(self, line: str) -> bool:
        """Identify Google feedback and export boilerplate outside transcript."""
        stripped = line.strip()
        normalized = re.sub(r'\\([\\`*_{}\[\]()#+\-.!])', r'\1', stripped)
        normalized = normalized.replace('**', '').strip()

        boilerplate_prefixes = (
            'Meeting records [Transcript]',
            "We've updated the Decisions section",
            'Let us know what you think:',
            "*You should review Gemini's notes",
            '*How is the quality of these specific notes?',
            '*Did the screenshots in this section make your notes',
            '[image',
        )
        return any(normalized.startswith(prefix) for prefix in boilerplate_prefixes)

    def _is_image_line(self, line: str) -> bool:
        """Identify inline image placeholders and image reference definitions."""
        stripped = line.strip()
        return (
            stripped.startswith('![') or
            stripped.startswith('![][') or
            re.match(r'^\[image\d+\]:\s*<data:image/', stripped) is not None
        )

    def _parse_content(self):
        """Parse the markdown content into sections."""
        lines = self.content.split('\n')
        current_section = None
        current_content = []
        current_section_level = None
        current_section_title = None

        def flush_current_section():
            nonlocal current_section, current_content, current_section_title
            if not current_section:
                return
            if current_section == 'extra':
                self._store_extra_section(current_section_title, current_content)
            else:
                self._store_section(current_section, current_content)

        for line in lines:
            heading = self._parse_markdown_heading(line)
            if heading:
                level, title = heading
                section = self._section_for_heading(level, title)
            else:
                level, title, section = None, None, None

            # Check for main section headers. Newer Google exports decorate
            # headings as "### **Summary**" or "# **📖 Transcript**"; older
            # exports used plain headings. The normalized section names above
            # keep both formats on the same path.
            if section == 'summary':
                flush_current_section()
                current_section = 'summary'
                current_content = []
                current_section_level = level
                current_section_title = None
            elif section == 'details':
                flush_current_section()
                current_section = 'details'
                current_content = []
                current_section_level = level
                current_section_title = None
            elif section == 'decisions':
                flush_current_section()
                current_section = 'decisions'
                current_content = []
                current_section_level = level
                current_section_title = None
            elif section == 'next_steps':
                flush_current_section()
                current_section = 'next_steps'
                current_content = []
                current_section_level = level
                current_section_title = None
            elif section == 'transcript':
                flush_current_section()
                current_section = 'transcript'
                current_content = []
                current_section_level = level
                current_section_title = None
            elif heading and current_section and current_section != 'transcript':
                if current_section == 'decisions':
                    current_content.append(line)
                    continue

                # Unknown headings at the same or higher document level become
                # preserved extra note sections. Deeper headings stay inside
                # the current section.
                if current_section_level is None or level <= current_section_level:
                    flush_current_section()
                    current_section = 'extra'
                    current_content = []
                    current_section_level = level
                    current_section_title = title
                else:
                    current_content.append(line)
            elif current_section and current_section != 'transcript' and \
                    (self._is_boilerplate_line(line) or self._is_image_line(line)):
                continue
            elif current_section:
                current_content.append(line)

        # Store the last section
        flush_current_section()

    def _store_section(self, section: str, content: List[str]):
        """Store parsed section content."""
        if section in self.sections:
            nonblank = [line for line in content if line.strip()]
            if not nonblank:
                return

            existing_nonblank = [line for line in self.sections[section] if line.strip()]
            if not existing_nonblank or len(nonblank) >= len(existing_nonblank):
                self.sections[section] = content
                if section not in {'summary', 'transcript'}:
                    key = (section, None)
                    if key not in self.note_section_order:
                        self.note_section_order.append(key)

    def _store_extra_section(self, title: Optional[str], content: List[str]):
        """Store an unrecognized Gemini note section without dropping it."""
        if not title:
            return

        nonblank = [
            line for line in content
            if line.strip() and not self._is_boilerplate_line(line) and not self._is_image_line(line)
        ]
        if not nonblank:
            return

        self.extra_sections.append(ExtraSection(title=title, content=content))
        self.note_section_order.append(('extra', len(self.extra_sections) - 1))

    def _build_org_output(self) -> str:
        """Build the complete Org-mode output."""
        output = []

        # Add PROPERTIES drawer
        output.append(":PROPERTIES:")
        output.append(f":ID:       {str(uuid.uuid4()).upper()}")

        # Format creation time
        dt = self.metadata['date']
        created_str = dt.strftime('[%Y-%m-%d %a %H:%M]')
        output.append(f":CREATED:  {created_str}")
        if DEFAULT_LOCATION:
            output.append(f":LOCATION: {DEFAULT_LOCATION}")
        output.append(":END:")

        # Extract a participant name from the title when the filename format permits it.
        participant_name = self._extract_participant_name()

        # Add metadata
        output.append(f"#+category: {participant_name.split()[0] if participant_name else 'Meeting'}")
        output.append(f"#+date: {dt.strftime('[%Y-%m-%d %a %H:%M]')}")
        output.append(f"#+filetags: {DEFAULT_FILETAGS}")
        output.append(f"#+title: {self.metadata['title']}")
        output.append("")

        # Add participant link if we can identify them
        if participant_name:
            participant_id = self.participant_db.get_id(participant_name)
            output.append(f"- [[id:{participant_id}][{participant_name}]]")
            output.append("")

        # Add Summary section
        output.append("* Summary")
        output.append("")
        output.extend(self._convert_summary())
        output.append("")

        for section_name, section_index in self.note_section_order:
            self._append_note_section(output, section_name, section_index)

        # Add Transcript section (single newline before it)
        output.append("* Transcript")
        output.append("")
        output.extend(self._convert_transcript())

        # Join all lines and ensure no more than 2 consecutive newlines
        result = '\n'.join(output)
        # Replace 3 or more newlines with exactly 2 newlines
        result = re.sub(r'\n{3,}', '\n\n', result)
        if self.vocabulary:
            result = self.vocabulary.apply(result)

        return result

    def _append_note_section(
            self,
            output: List[str],
            section_name: str,
            section_index: Optional[int]):
        """Append one parsed non-summary note section in source order."""
        if section_name == 'decisions' and self.sections['decisions']:
            output.append("** Decisions")
            output.append("")
            output.extend(self._convert_decisions())
            output.append("")
        elif section_name == 'details' and self.sections['details']:
            output.append("** Details")
            output.append("")
            output.extend(self._convert_details())
            output.append("")
        elif section_name == 'next_steps' and self.sections['next_steps']:
            output.append("** Suggested next steps")
            output.extend(self._convert_next_steps())
        elif section_name == 'extra' and section_index is not None:
            extra_section = self.extra_sections[section_index]
            output.append(f"** {self._convert_inline_markdown(extra_section.title)}")
            output.append("")
            output.extend(self._convert_structured_section_lines(extra_section.content))
            output.append("")

    def _apply_text_conversions(self, text: str) -> str:
        """Apply common escapes, Markdown links, and entities to Org text."""
        # Remove backslash escaping from backticks, periods, and brackets
        text = text.replace('\\`', '`')
        text = text.replace(r'\.', '.')
        text = text.replace('\\[', '[')
        text = text.replace('\\]', ']')

        text = self._convert_markdown_links(text)
        text = html.unescape(text)

        return text

    def _convert_markdown_links(self, text: str) -> str:
        """Convert Markdown links to Org links, preserving balanced URL parens."""
        output = []
        index = 0
        while index < len(text):
            if text[index] != '[':
                output.append(text[index])
                index += 1
                continue

            label_end = text.find(']', index + 1)
            if label_end == -1 or label_end + 1 >= len(text) or text[label_end + 1] != '(':
                output.append(text[index])
                index += 1
                continue

            url_start = label_end + 2
            url_index = url_start
            depth = 0
            while url_index < len(text):
                char = text[url_index]
                if char == '(':
                    depth += 1
                elif char == ')':
                    if depth == 0:
                        break
                    depth -= 1
                url_index += 1

            if url_index >= len(text):
                output.append(text[index])
                index += 1
                continue

            label = text[index + 1:label_end]
            url = text[url_start:url_index]
            output.append(f"[[{url}][{label}]]")
            index = url_index + 1

        return ''.join(output)

    def _format_org_code_span(self, code: str) -> str:
        """Format one Markdown inline-code span using a safe Org delimiter."""
        if '=' in code and '~' not in code:
            return f"~{code}~"
        return f"={code}="

    def _wrap_paragraph(self, text: str, width: int = 78, initial_indent: str = '', subsequent_indent: str = '  ') -> str:
        """Wrap text to specified width with proper indentation."""
        # Use textwrap to wrap the text
        wrapped = textwrap.fill(
            text,
            width=width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
            break_long_words=False,
            break_on_hyphens=False
        )
        return wrapped

    def _org_list_indent(self, indent: str) -> str:
        """Return source indentation suitable for nested Org list items."""
        return indent.replace('\t', '  ')

    def _relative_org_list_indent(self, indent: str, base_columns: int) -> str:
        """Return list indentation relative to a parent Markdown list item."""
        expanded_indent = self._org_list_indent(indent)
        if len(expanded_indent) <= base_columns:
            return ''
        return expanded_indent[base_columns:]

    def _ordered_list_match(self, line: str) -> Optional[Tuple[str, str, str]]:
        """Return (marker, text, indent) for a Markdown ordered-list line."""
        match = re.match(r'^(\s*)(\d+[.)])\s+(.*)$', line)
        if not match:
            return None
        indent, marker, text = match.groups()
        return marker, text.strip(), self._org_list_indent(indent)

    def _format_ordered_list_item(self, marker: str, text: str, indent: str) -> str:
        """Format one ordered-list item as Org text."""
        text = self._convert_inline_markdown(text)
        initial_indent = f"{indent}{marker} "
        subsequent_indent = ' ' * len(initial_indent)
        return self._wrap_paragraph(
            text,
            width=78,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
        )

    def _extract_participant_name(self) -> Optional[str]:
        """Extract participant name from the content or title."""
        # Try to find in the "Invited" line
        for line in self.content.split('\n'):
            if line.startswith('Invited'):
                # Extract email addresses and names
                match = re.search(r'\[([^\]]+)\]', line)
                if match:
                    # Get the second name (usually the other participant)
                    names = re.findall(r'\[([^\]]+)\]', line)
                    if len(names) >= 2:
                        # Extract name from email format "Name" or from email
                        name_match = re.match(r'([^<]+)', names[1])
                        if name_match:
                            return name_match.group(1).strip()

        # Filename formats vary enough that ambiguous names are left unset.
        return None

    def _convert_summary(self) -> List[str]:
        """Convert summary section to org-mode format."""
        output = []
        content = '\n'.join(self.sections['summary']).strip()

        # Remove other markdown artifacts
        content = re.sub(r'\\-', '-', content)

        # Split into paragraphs and clean up
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        for para in paragraphs:
            # Check for bold topic followed by description (Gemini sub-topic format)
            # Pattern: **Bold Title**<optional trailing spaces>\n<description>
            bold_desc_match = re.match(
                r'(?:\*\*([^*]+)\*\*|__([^_\n]+)__)\s*\n(.*)',
                para,
                re.DOTALL,
            )
            if bold_desc_match:
                title = (bold_desc_match.group(1) or bold_desc_match.group(2)).strip()
                description = bold_desc_match.group(3).strip()
                # Format as Org-mode description list
                wrapped = self._wrap_paragraph(
                    f"{self._convert_inline_markdown(title)} :: "
                    f"{self._convert_inline_markdown(description)}",
                    width=78, initial_indent='- ', subsequent_indent='  ')
                output.append(wrapped)
            else:
                summary_list = self._convert_summary_list_paragraph(para)
                if summary_list is not None:
                    output.extend(summary_list)
                else:
                    para = self._convert_inline_markdown(para)
                    wrapped = self._wrap_paragraph(para, width=78, initial_indent='', subsequent_indent='')
                    output.append(wrapped)
            output.append("")

        return output

    def _convert_summary_list_paragraph(self, paragraph: str) -> Optional[List[str]]:
        """Convert a summary paragraph containing Markdown list items."""
        lines = [line.rstrip() for line in paragraph.split('\n') if line.strip()]
        if not lines:
            return None

        has_list_item = any(
            re.match(r'^\s*[*+-]\s+', line) or self._ordered_list_match(line)
            for line in lines
        )
        if not has_list_item:
            return None

        output = []
        for line in lines:
            stripped = line.strip()
            bullet = re.match(r'^(\s*)[*+-]\s+(.*)$', line)
            ordered_item = self._ordered_list_match(line)

            if bullet:
                indent, bullet_text = bullet.groups()
                list_indent = self._org_list_indent(indent if len(indent) >= 2 else '')
                initial_indent = f"{list_indent}- "
                text = self._convert_inline_markdown(bullet_text.strip())
                output.append(
                    self._wrap_paragraph(
                        text,
                        width=78,
                        initial_indent=initial_indent,
                        subsequent_indent=' ' * len(initial_indent),
                    )
                )
            elif ordered_item:
                marker, text, indent = ordered_item
                output.append(self._format_ordered_list_item(marker, text, indent))
            else:
                text = self._convert_inline_markdown(stripped)
                output.append(
                    self._wrap_paragraph(
                        text,
                        width=78,
                        initial_indent='',
                        subsequent_indent='',
                    )
                )

        return output

    def _convert_inline_markdown(self, text: str) -> str:
        """Convert common inline Markdown markup to Org syntax."""
        text = text.replace('\\`', '`')
        code_spans = []

        def protect_code_span(match):
            code_spans.append(match.group(1))
            return f"@@GEMINICODE{len(code_spans) - 1}@@"

        text = re.sub(r'`([^`\n]+)`', protect_code_span, text)
        text = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'/\1/', text)
        text = re.sub(r'(?<!\w)__([^_\n]+)__(?!\w)', r'*\1*', text)
        text = re.sub(r'(?<!\w)_([^_\n]+)_(?!\w)', r'/\1/', text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', text)
        text = self._apply_text_conversions(text)

        for index, code in enumerate(code_spans):
            text = text.replace(
                f"@@GEMINICODE{index}@@",
                self._format_org_code_span(code),
            )

        return text

    def _convert_structured_section_lines(self, lines: List[str]) -> List[str]:
        """Convert general Gemini note section content to Org."""
        output = []
        previous_was_content = False

        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                continue

            if self._is_boilerplate_line(stripped) or self._is_image_line(stripped):
                continue

            heading = self._parse_markdown_heading(stripped)
            if heading:
                _, title = heading
                if previous_was_content:
                    output.append("")
                output.append(f"*** {self._convert_inline_markdown(title)}")
                output.append("")
                previous_was_content = False
                continue

            bullet = re.match(r'^(\s*)[*+-]\s+(.*)$', line)
            ordered_item = self._ordered_list_match(line)

            if bullet:
                indent, bullet_text = bullet.groups()
                list_indent = self._org_list_indent(indent if len(indent) >= 2 else '')
                initial_indent = f"{list_indent}- "
                text = self._convert_inline_markdown(bullet_text.strip())
                output.append(
                    self._wrap_paragraph(
                        text,
                        width=78,
                        initial_indent=initial_indent,
                        subsequent_indent=' ' * len(initial_indent)
                    )
                )
            elif ordered_item:
                marker, text, indent = ordered_item
                output.append(self._format_ordered_list_item(marker, text, indent))
            else:
                text = self._convert_inline_markdown(stripped)
                output.append(
                    self._wrap_paragraph(
                        text,
                        width=78,
                        initial_indent='',
                        subsequent_indent=''
                    )
                )
            previous_was_content = True

        return output

    def _convert_decisions(self) -> List[str]:
        """Convert Gemini decisions to org-mode while preserving subsections."""
        return self._convert_structured_section_lines(self.sections['decisions'])

    def _convert_details(self) -> List[str]:
        """Convert details section to org-mode format."""
        output = []
        in_main_bullet = False

        for raw_line in self.sections['details']:
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                continue

            # Skip Google boilerplate and unsupported embedded screenshot refs.
            if (stripped.startswith('*Notes Length:') or
                'Notes Length:' in stripped or
                self._is_boilerplate_line(stripped) or
                self._is_image_line(stripped)):
                continue

            heading = self._parse_markdown_heading(stripped)
            if heading:
                _, title = heading
                if in_main_bullet:
                    output.append("")
                output.append(f"*** {self._convert_inline_markdown(title)}")
                output.append("")
                in_main_bullet = False
                continue

            # Convert markdown list items to org-mode list items.
            bullet = re.match(r'^(\s*)[*+-]\s+(.*)$', line)
            ordered_item = self._ordered_list_match(line)

            if bullet:
                indent, bullet_text = bullet.groups()
                top_level = len(indent) < 2
                if top_level and in_main_bullet:
                    output.append("")

                list_indent = self._org_list_indent(indent if not top_level else '')
                initial_indent = f"{list_indent}- "
                line = self._convert_inline_markdown(bullet_text.strip())
                wrapped = self._wrap_paragraph(
                    line,
                    width=78,
                    initial_indent=initial_indent,
                    subsequent_indent=' ' * len(initial_indent)
                )
                output.append(wrapped)
                if top_level:
                    in_main_bullet = True
            elif ordered_item:
                marker, text, indent = ordered_item
                if not indent and in_main_bullet:
                    output.append("")
                output.append(self._format_ordered_list_item(marker, text, indent))
                if not indent:
                    in_main_bullet = True
            else:
                # Regular line, preserve it
                line = self._convert_inline_markdown(stripped)
                output.append(f"  {line}")

        return output

    def _infer_todo_title(self, text: str) -> Tuple[str, str, Optional[str]]:
        """
        Infer TODO title, keyword, and tag from task text.

        Returns:
            (title, keyword, tag) where:
            - title: The task title text
            - keyword: "TODO" or "TASK"
            - tag: Tag name (e.g., "LastName", "Alice", "Ben") or None
        """
        if CURRENT_USER_NAME:
            user_match = re.match(
                rf'^{re.escape(CURRENT_USER_NAME)}\s+will\s+(.+)',
                text,
                re.IGNORECASE
            )
            if user_match:
                return user_match.group(1).strip(), "TODO", None

        # Check for "[FirstName] [LastName] will XXX" pattern (case-insensitive)
        person_match = re.match(r'^([A-Za-z]+)\s+([A-Za-z]+)\s+will\s+(.+)', text, re.IGNORECASE)
        if person_match:
            first_name = person_match.group(1).capitalize()
            last_name = person_match.group(2).capitalize()
            task_text = person_match.group(3).strip()
            current_first, current_last = current_user_name_parts()

            # Avoid ambiguous tags when another person shares the user's first name.
            if (current_first and current_last and
                    first_name.casefold() == current_first.casefold() and
                    last_name.casefold() != current_last.casefold()):
                return task_text, "TASK", last_name

            # For everyone else, use first name
            return task_text, "TASK", first_name

        # No pattern matched, return as-is
        return text, "TODO", None

    def _parse_will_assignee_task(self, text: str) -> Optional[Tuple[List[str], str, str]]:
        """Parse 'Assignee will do task' next-step text with full ownership."""
        if CURRENT_USER_NAME:
            user_match = re.match(
                rf'^{re.escape(CURRENT_USER_NAME)}\s+will\s+(.+)',
                text,
                re.IGNORECASE
            )
            if user_match:
                return [CURRENT_USER_NAME], user_match.group(1).strip(), "TODO"

        person_match = re.match(
            r'^([A-Za-z][A-Za-z\'-]*)\s+([A-Za-z][A-Za-z\'-]*)\s+will\s+(.+)',
            text,
        )
        if person_match:
            first_name, last_name, task_text = person_match.groups()
            assignee = f"{first_name} {last_name}"
            current_first, current_last = current_user_name_parts()
            keyword = "TASK"
            if is_current_user_name(assignee):
                keyword = "TODO"
            elif (current_first and current_last and
                    first_name.casefold() == current_first.casefold() and
                    last_name.casefold() != current_last.casefold()):
                keyword = "TASK"

            return [assignee], task_text.strip(), keyword

        single_name_match = re.match(
            r'^([A-Z][A-Za-z\'-]*)\s+will\s+(.+)',
            text,
        )
        if single_name_match:
            assignee, task_text = single_name_match.groups()
            keyword = "TODO" if is_current_user_name(assignee) else "TASK"
            return [assignee], task_text.strip(), keyword

        return None

    def _is_likely_assignee_prefix(self, prefix: str) -> bool:
        """Return whether a short colon prefix is likely an assignee name."""
        prefix = re.sub(r'\s+', ' ', prefix).strip()
        if not prefix:
            return False
        if is_current_user_name(prefix):
            return True

        tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", prefix)
        if not 1 <= len(tokens) <= 2:
            return False

        common_task_words = {
            'add', 'archive', 'build', 'capture', 'confirm', 'coordinate',
            'create', 'decide', 'define', 'design', 'discuss', 'document',
            'draft', 'fix', 'follow', 'investigate', 'launch', 'negotiate',
            'prepare', 'provide', 'release', 'review', 'schedule', 'send',
            'share', 'test', 'update', 'write',
        }
        common_label_words = {
            'api', 'design', 'documentation', 'followup', 'follow-up',
            'launch', 'meeting', 'note', 'notes', 'plan', 'proposal',
            'release', 'review', 'rollout', 'task', 'tasks',
        }
        lowered = [token.casefold() for token in tokens]
        if lowered[0] in common_task_words:
            return False
        if len(lowered) == 2 and lowered[1] in common_label_words:
            return False
        if any(token.endswith(('ing', 'tion', 'ment')) for token in lowered):
            return False

        return all(token[0].isupper() for token in tokens)

    def _parse_colon_assignee_task(self, text: str) -> Optional[Tuple[List[str], str, str]]:
        """Parse 'Assignee: task' next-step text with full ownership."""
        colon_match = re.match(r'^([^:\n]{1,80}):\s+(.+)$', text, re.DOTALL)
        if not colon_match:
            return None

        prefix, task_text = (part.strip() for part in colon_match.groups())
        if not self._is_likely_assignee_prefix(prefix):
            return None

        assignees = self._split_assignees(prefix)
        if not assignees:
            return None

        keyword = "TODO" if any(is_current_user_name(assignee) for assignee in assignees) else "TASK"
        return assignees, task_text, keyword

    def _parse_short_label_task(self, text: str) -> Optional[Tuple[str, str]]:
        """Parse 'Short label: description' next-step text."""
        colon_match = re.match(r'^([^:\n]{1,80}):\s+(.+)$', text, re.DOTALL)
        if not colon_match:
            return None
        short_label, description = (part.strip() for part in colon_match.groups())
        if not short_label or not description:
            return None
        return short_label, description

    def _remove_filler_words(self, text: str) -> str:
        """Remove only a leading article from a task title."""
        return re.sub(r'^\s*(the|a|an)\s+', '', text, flags=re.IGNORECASE).strip()

    def _reformat_name_colon_title(self, text: str) -> str:
        """Convert 'Name: Title' format to '(Name) Title' only for actual names."""
        # Match "Name: Title" pattern at the beginning
        match = re.match(r'^([A-Z][a-zA-Z\s]+):\s+(.+)$', text)
        if match:
            prefix = match.group(1).strip()
            title = match.group(2).strip()

            # Only reformat if it's a name (not a gerund or common action word)
            # Exclude words ending in -ing or -tion or other verb-like patterns
            if not (prefix.endswith('ing') or
                    prefix.endswith('tion') or
                    prefix.endswith('ment') or
                    prefix.lower() in ['testing', 'running', 'building', 'updating', 'fixing']):
                return f"({prefix}) {title}"

        return text

    def _split_assignees(self, assignee_text: str) -> List[str]:
        """Split a Gemini assignee field into individual names."""
        assignees = []
        for part in re.split(r'\s*(?:,|&|\band\b)\s*', assignee_text):
            part = re.sub(r'\s+', ' ', part).strip()
            if part:
                assignees.append(part)
        return assignees

    def _task_tags_for_assignees(self, assignees: List[str], keyword: str) -> List[str]:
        """Return stable Org tags for non-current assignees."""
        tags = []
        for assignee in assignees:
            if keyword in {"TODO", "DONE", "WAITING"} and is_current_user_name(assignee):
                continue
            tag = self._org_tag_from_assignee(assignee)
            if tag and tag not in tags:
                tags.append(tag)
        return tags

    def _org_tag_from_assignee(self, assignee: str) -> str:
        """Build a safe Org tag from an assignee name."""
        tokens = re.findall(r'[A-Za-z0-9_@#%]+', assignee)
        if not tokens:
            return ''

        # Skip common honorifics when a real name follows them.
        if len(tokens) > 1 and tokens[0].rstrip('.').casefold() in {
            'dr', 'mr', 'mrs', 'ms', 'mx', 'prof'
        }:
            tokens = tokens[1:]

        return tokens[0]

    def _sanitize_org_tags(self, tags: List[str]) -> List[str]:
        """Return valid, unique Org tags."""
        sanitized_tags = []
        for tag in tags:
            sanitized = '_'.join(re.findall(r'[A-Za-z0-9_@#%]+', tag))
            sanitized = sanitized.strip('_')
            if sanitized and sanitized not in sanitized_tags:
                sanitized_tags.append(sanitized)
        return sanitized_tags

    def _format_task_headline_title(self, title: str) -> str:
        """Format task title text so Org cannot mistake content for metadata."""
        title = self._convert_inline_markdown(title)
        title = re.sub(r'\s+', ' ', title).strip()
        title = re.sub(r'^\*+\s+', '', title)

        # A title ending in " :foo:" is interpreted by Org as a tag list. Keep
        # that text as title content by terminating it before real tags are
        # appended by _append_task_entry.
        if re.search(r'\s+(?::[A-Za-z0-9_@#%.-]+:)+$', title):
            title += '.'

        return title

    def _assignee_properties(self, assignees: List[str]) -> Dict[str, str]:
        """Preserve full task ownership in Org properties."""
        if not assignees:
            return {}
        return {'ASSIGNEES': ', '.join(assignees)}

    def _append_task_entry(self, output: List[str], keyword: str, title: str,
                           tags: Optional[List[str]], body_text: Optional[str],
                           today: str, priority: Optional[str] = None,
                           properties: Optional[Dict[str, str]] = None,
                           extra_lines: Optional[List[str]] = None):
        """Append one Org task entry with standard review metadata."""
        tags = tags or []
        properties = properties or {}
        extra_lines = extra_lines or []
        tags = self._sanitize_org_tags(tags)
        title = self._format_task_headline_title(title)

        if len(title) > MAX_TASK_TITLE_LENGTH:
            original_title = title
            title = deterministic_short_task_title(title)
            title = self._format_task_headline_title(title)
            body_text = body_text or original_title

        priority_text = f" {priority}" if priority else ""
        tag_suffix = f"  :{':'.join(tags)}:" if tags else ""
        output.append(f"*** {keyword}{priority_text} {title}{tag_suffix}")

        schedule_lines = [
            line for line in extra_lines
            if line.startswith('SCHEDULED:') or line.startswith('DEADLINE:')
        ]
        body_lines = [
            line for line in extra_lines
            if not (line.startswith('SCHEDULED:') or line.startswith('DEADLINE:'))
        ]
        output.extend(schedule_lines)

        output.append(":PROPERTIES:")
        output.append(f":LAST_REVIEW: {today}")
        output.append(f":NEXT_REVIEW: {today}")
        output.append(":REVIEWS:  1")
        output.append(f":ID:       {str(uuid.uuid4()).upper()}")

        created_time = self.metadata['date'].strftime('[%Y-%m-%d %a %H:%M]')
        output.append(f":CREATED:  {created_time}")

        for key, value in properties.items():
            if key in {'LAST_REVIEW', 'NEXT_REVIEW', 'REVIEWS', 'ID', 'CREATED'}:
                continue
            output.append(f":{key}: {value}")

        output.append(":END:")

        if body_text:
            body_text = self._convert_inline_markdown(body_text)
            wrapped_body = self._wrap_paragraph(
                body_text,
                width=78,
                initial_indent='',
                subsequent_indent=''
            )
            output.append(wrapped_body)

        output.extend(body_lines)

    def _raw_transcript_text(self) -> str:
        """Return the raw parsed transcript text for AI task inference."""
        return '\n'.join(self.sections['transcript']).strip()

    def _normalize_inferred_task_entry(self, entry: OrgTaskEntry) -> OrgTaskEntry:
        """Normalize inferred task ownership into Org keyword/tag conventions."""
        owner_match = re.match(r'^\[([^\]]+)\]\s*(.*)$', entry.title)
        if not owner_match:
            if 'ASSIGNEES' in entry.properties:
                assignees = self._split_assignees(entry.properties['ASSIGNEES'])
                if assignees:
                    if entry.keyword not in {"DONE", "WAITING"}:
                        if any(is_current_user_name(assignee) for assignee in assignees):
                            entry.keyword = "TODO"
                        else:
                            entry.keyword = "TASK"
                    if not entry.tags:
                        entry.tags = self._task_tags_for_assignees(assignees, entry.keyword)
            return entry

        assignees = self._split_assignees(owner_match.group(1).strip())
        title = owner_match.group(2).strip()
        if not title:
            return entry

        if entry.keyword not in {"DONE", "WAITING"}:
            if any(is_current_user_name(assignee) for assignee in assignees):
                entry.keyword = "TODO"
            else:
                entry.keyword = "TASK"
        if not entry.tags:
            entry.tags = self._task_tags_for_assignees(assignees, entry.keyword)
        entry.properties.update(self._assignee_properties(assignees))

        entry.title = title
        return entry

    def _parse_next_step_items(self) -> List[ParsedNextStep]:
        """Parse Gemini next-step checkboxes and preserve supporting details."""
        items: List[ParsedNextStep] = []

        for line in self.sections['next_steps']:
            raw_line = line.rstrip()
            line_stripped = raw_line.strip()
            if not line_stripped or self._is_boilerplate_line(line_stripped):
                continue

            task_match = re.match(
                r'^(\s*)([-*+]|\d+[.)])(\s*)\[([ xX])\]\s+(.*)$',
                raw_line,
            )
            if task_match:
                leading_indent, marker, marker_space, checked, text = task_match.groups()
                marker_gap = max(len(self._org_list_indent(marker_space)), 1)
                detail_indent = len(self._org_list_indent(leading_indent)) + len(marker) + marker_gap
                items.append(ParsedNextStep(
                    text.strip(),
                    checked=checked.strip().casefold() == 'x',
                    detail_indent=detail_indent,
                ))
                continue

            plain_task_match = re.match(
                r'^(\s*)([-*+]|\d+[.)])(\s+)(?!\[[ xX]\]\s+)(.+)$',
                raw_line,
            )
            if plain_task_match:
                leading_indent, marker, marker_space, text = plain_task_match.groups()
                if len(self._org_list_indent(leading_indent)) < 2:
                    marker_gap = max(len(self._org_list_indent(marker_space)), 1)
                    detail_indent = len(marker) + marker_gap
                    items.append(ParsedNextStep(
                        text.strip(),
                        checked=False,
                        detail_indent=detail_indent,
                    ))
                    continue

            if not items:
                continue

            detail_bullet = re.match(r'^(\s{2,})[-*+]\s+(.*)$', raw_line)
            ordered_detail = re.match(r'^(\s{2,})(\d+[.)])\s+(.*)$', raw_line)
            if detail_bullet:
                indent, text = detail_bullet.groups()
                relative_indent = self._relative_org_list_indent(indent, items[-1].detail_indent)
                items[-1].details.append(f"{relative_indent}- {text.strip()}")
            elif ordered_detail:
                indent, marker, text = ordered_detail.groups()
                relative_indent = self._relative_org_list_indent(indent, items[-1].detail_indent)
                items[-1].details.append(f"{relative_indent}{marker} {text.strip()}")
            elif re.match(r'^\s*[-*+]\s+', raw_line):
                detail = re.sub(r'^\s*[-*+]\s+', '- ', raw_line).strip()
                items[-1].details.append(detail)
            elif items[-1].details:
                items[-1].details[-1] += ' ' + line_stripped
            else:
                items[-1].text += ' ' + line_stripped

        return items

    def _format_task_detail_lines(self, details: List[str]) -> List[str]:
        """Format preserved next-step detail lines for an Org task body."""
        output = []
        for detail in details:
            ordered_item = self._ordered_list_match(detail)
            bullet = re.match(r'^(\s*)-\s+(.*)$', detail)
            if ordered_item:
                marker, text, nested = ordered_item
                output.append(self._format_ordered_list_item(marker, text, nested))
            elif bullet:
                indent, bullet_text = bullet.groups()
                text = self._convert_inline_markdown(bullet_text.strip())
                initial_indent = f"{indent}- "
                output.append(
                    self._wrap_paragraph(
                        text,
                        width=78,
                        initial_indent=initial_indent,
                        subsequent_indent=' ' * len(initial_indent),
                    )
                )
            else:
                detail = self._convert_inline_markdown(detail)
                output.append(
                    self._wrap_paragraph(
                        detail,
                        width=78,
                        initial_indent='',
                        subsequent_indent='',
                    )
                )
        return output

    def _format_inferred_task_extra_lines(self, lines: List[str]) -> List[str]:
        """Preserve model-provided inferred task body lines."""
        output = []
        for line in lines:
            raw_line = line.rstrip()
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.startswith('SCHEDULED:') or stripped.startswith('DEADLINE:'):
                output.append(stripped)
            else:
                output.extend(self._format_task_detail_lines([raw_line]))
        return output

    def _convert_next_steps(self) -> List[str]:
        """Convert suggested next steps to TODO items with PROPERTIES."""
        output = []

        today = datetime.now().strftime('[%Y-%m-%d %a]')
        parsed_steps = self._parse_next_step_items()

        for step in parsed_steps:
            line = step.text
            # Extract the TODO text
            todo_text = line.strip()

            # Handle escaped brackets from Gemini markdown
            todo_text = todo_text.replace('\\[', '[')
            todo_text = todo_text.replace('\\]', ']')

            # Store original text for body (before any processing)
            original_text_for_body = todo_text
            todo_properties: Dict[str, str] = {}
            body_text = None
            should_shorten_title_from_body = True

            # Try to parse [Name] prefix (Gemini format)
            name_bracket_match = re.match(r'^\[([^\]]+)\]\s*(.*)', todo_text)
            if name_bracket_match:
                assignees = self._split_assignees(name_bracket_match.group(1).strip())
                remaining_text = name_bracket_match.group(2).strip()

                # Determine task ownership from all assignees.
                if step.checked:
                    todo_keyword = "DONE"
                elif any(is_current_user_name(assignee) for assignee in assignees):
                    todo_keyword = "TODO"
                else:
                    todo_keyword = "TASK"
                todo_tags = self._task_tags_for_assignees(assignees, todo_keyword)
                todo_properties.update(self._assignee_properties(assignees))

                # Check for "Short Title: Description" format
                colon_match = re.match(r'^([^:]+):\s+(.*)', remaining_text, re.DOTALL)
                if colon_match:
                    short_label = colon_match.group(1).strip()
                    description = colon_match.group(2).strip()
                    original_text_for_body = description
                    todo_title = short_label
                    body_text = description
                    should_shorten_title_from_body = False
                else:
                    original_text_for_body = remaining_text
                    todo_title = remaining_text
            else:
                will_task = self._parse_will_assignee_task(todo_text)
                if will_task:
                    assignees, todo_title, todo_keyword = will_task
                    if step.checked:
                        todo_keyword = "DONE"
                    todo_tags = self._task_tags_for_assignees(assignees, todo_keyword)
                    todo_properties.update(self._assignee_properties(assignees))
                else:
                    colon_task = self._parse_colon_assignee_task(todo_text)
                    if colon_task:
                        assignees, todo_title, todo_keyword = colon_task
                        if step.checked:
                            todo_keyword = "DONE"
                        todo_tags = self._task_tags_for_assignees(assignees, todo_keyword)
                        todo_properties.update(self._assignee_properties(assignees))
                    else:
                        short_label_task = self._parse_short_label_task(todo_text)
                        if short_label_task:
                            todo_title, description = short_label_task
                            original_text_for_body = description
                            body_text = description
                            todo_keyword = "DONE" if step.checked else "TODO"
                            todo_tags = []
                            should_shorten_title_from_body = False
                        else:
                            # Fall back to existing pattern matching
                            todo_title, todo_keyword, todo_tag = self._infer_todo_title(todo_text)
                            if step.checked:
                                todo_keyword = "DONE"
                            todo_tags = [todo_tag] if todo_tag else []

            # Remove filler words
            todo_title = self._remove_filler_words(todo_title)

            # Reformat "Name: Title" to "(Name) Title"
            todo_title = self._reformat_name_colon_title(todo_title)

            # Capitalize first letter, remove trailing period and colons
            if todo_title:
                todo_title = todo_title.replace(':', '')
                todo_title = todo_title[0].upper() + todo_title[1:] if len(todo_title) > 1 else todo_title.upper()
                todo_title = todo_title.rstrip('.')

            # Shorten TODO title if shortener is available
            if (should_shorten_title_from_body and self.todo_shortener and
                    len(original_text_for_body) > MAX_TASK_TITLE_LENGTH):
                todo_title, body_text = self.todo_shortener.shorten_title(
                    original_text_for_body,
                    keyword=todo_keyword,
                    tag=todo_tags[0] if len(todo_tags) == 1 else None,
                    verbose=self.verbose
                )
                # If shortened, body should be the description text
                if body_text:
                    body_text = original_text_for_body
            elif len(todo_title) > MAX_TASK_TITLE_LENGTH:
                todo_title = deterministic_short_task_title(todo_title)
                body_text = original_text_for_body

            detail_lines = self._format_task_detail_lines(step.details)
            self._append_task_entry(
                output,
                todo_keyword,
                todo_title,
                todo_tags,
                body_text,
                today,
                properties=todo_properties,
                extra_lines=detail_lines
            )

        if self.task_inferer and self.sections['transcript']:
            gemini_task_texts = [step.source_text() for step in parsed_steps]
            inferred_entries = self.task_inferer.infer_additional_tasks(
                self._raw_transcript_text(),
                gemini_task_texts,
                verbose=self.verbose
            )

            for entry in inferred_entries:
                entry = self._normalize_inferred_task_entry(entry)
                body_text = None
                if len(entry.title) > MAX_TASK_TITLE_LENGTH:
                    body_text = entry.title
                preserved_extra_lines = self._format_inferred_task_extra_lines(entry.extra_lines)

                self._append_task_entry(
                    output,
                    entry.keyword,
                    entry.title,
                    entry.tags,
                    body_text,
                    today,
                    priority=entry.priority,
                    properties=entry.properties,
                    extra_lines=preserved_extra_lines
                )

        return output

    def _convert_transcript(self) -> List[str]:
        """Convert transcript section to org-mode format."""
        output = []

        # If transcript cleaner is available, clean the raw transcript first
        if self.transcript_cleaner and self.sections['transcript']:
            if self.verbose:
                print("Running transcript cleanup...", file=sys.stderr)

            # Join transcript lines into single text
            raw_transcript = '\n'.join(self.sections['transcript'])

            # Clean the transcript
            cleaned_transcript = self.transcript_cleaner.clean(raw_transcript, verbose=self.verbose)

            # Split back into lines and replace the original transcript
            self.sections['transcript'] = cleaned_transcript.split('\n')

        current_timestamp = None
        current_content = []
        transcription_end_heading = None

        # Join the transcript lines back together for easier parsing
        transcript_text = '\n'.join(self.sections['transcript'])

        # Split by lines again for processing
        lines = transcript_text.split('\n')

        for line in lines:
            line_stripped = line.strip()

            normalized_line = re.sub(r'\\([\\`*_{}\[\]()#+\-.!])', r'\1', line_stripped)
            normalized_line = normalized_line.replace('**', '')

            # Stop processing at "Transcription ended after" line.
            heading = self._parse_markdown_heading(line_stripped)
            end_candidate = (
                heading[1] if heading
                else re.sub(r'^#{1,6}\s+', '', normalized_line).strip()
            )
            if re.match(r'^Transcription ended after\s+.+$', end_candidate):
                transcription_end_heading = end_candidate
                break

            # Skip empty lines and headers
            if not line_stripped:
                continue

            # Check for timestamp headings with an optional anchor.
            timestamp_match = transcript_timestamp_heading_match(line_stripped)
            if timestamp_match:
                # Save previous timestamp section
                if current_timestamp is not None:
                    output.append(f"** {current_timestamp}")
                    output.append(":PROPERTIES:")
                    output.append(f":CUSTOM_ID: {current_timestamp}")
                    output.append(":END:")
                    output.append("")
                    output.extend(current_content)
                    output.append("")

                # Start new timestamp section
                current_timestamp = timestamp_match.group(1)
                current_content = []
                continue

            # Skip metadata headers after preserving timestamp headings.
            if (line_stripped.startswith('Dec ') or
                line_stripped.startswith('##') or
                line_stripped.startswith('---') or
                ('Transcript' in line_stripped and line_stripped.startswith('#'))):
                continue

            # Convert common speaker formats to Org emphasis.
            speaker_match = transcript_speaker_line_match(line_stripped)
            if speaker_match:
                speaker = speaker_match.group(2).strip()
                text = speaker_match.group(3).strip()
                text = self._convert_inline_markdown(text)

                # Combine speaker and text, then wrap at 78 columns
                speaker_line = f"*{speaker}:* {text}"
                wrapped = self._wrap_paragraph(speaker_line, width=78,
                                              initial_indent='',
                                              subsequent_indent='')
                current_content.append(wrapped)
                current_content.append("")  # Blank line after speaker
                continue

            # Regular content line
            if line_stripped and current_timestamp:
                line_stripped = self._convert_inline_markdown(line_stripped)
                current_content.append(line_stripped)

        # Save last timestamp section
        if current_timestamp is not None:
            output.append(f"** {current_timestamp}")
            output.append(":PROPERTIES:")
            output.append(f":CUSTOM_ID: {current_timestamp}")
            output.append(":END:")
            output.append("")
            output.extend(current_content)

        if transcription_end_heading:
            if output and output[-1]:
                output.append("")
            output.append(f"** {self._convert_inline_markdown(transcription_end_heading)}")

        return output


def generate_output_filename(input_file: str, metadata: dict) -> str:
    """Generate output filename based on input metadata.

    Format: YYYYMMDDHHMM-title.org or YYYYMMDDHHMM-meeting.org
    """
    dt = metadata['date']
    title = metadata['title'].lower().replace(' ', '-')

    # Sanitize title for filename
    title = re.sub(r'[^\w\-]', '', title)

    # Ensure we have a valid filename component
    if not title:
        title = 'meeting'

    filename = f"{dt.strftime('%Y%m%d%H%M')}-{title}.org"

    # Place in same directory as input by default
    output_dir = os.path.dirname(input_file) or '.'
    return os.path.join(output_dir, filename)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Convert Gemini meeting notes to Org-mode format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s meeting.md
  %(prog)s meeting.md output.org
  %(prog)s -v meeting.md
  %(prog)s --base-url http://localhost:8317 meeting.md
  %(prog)s --no-shorten-tasks --no-clean-transcript --no-infer-transcript-tasks meeting.md
  %(prog)s --no-clean-transcript meeting.md
  %(prog)s --no-infer-transcript-tasks meeting.md
  %(prog)s --vocabulary ./gemini_to_org_vocabulary.tsv meeting.md
        """
    )
    parser.add_argument('input_file', help='Input Gemini markdown file')
    parser.add_argument('output_file', nargs='?', help='Output org-mode file (optional)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--db', default=PARTICIPANT_DB_FILE,
                       help='Participant database file (default: %(default)s)')
    parser.add_argument('--api-key', default=DEFAULT_CLAUDE_API_KEY,
                       help='Claude-compatible local endpoint API key (default: CLAUDE_API_KEY env var)')
    parser.add_argument('--base-url', default=DEFAULT_CLAUDE_BASE_URL,
                       help='Claude-compatible local endpoint URL (default: %(default)s)')
    parser.add_argument('--shorten-prompt', default=SHORTEN_PROMPT_FILE,
                       help='Prompt file for shortening task titles (default: %(default)s)')
    parser.add_argument('--infer-tasks-prompt', default=INFER_TASKS_PROMPT_FILE,
                       help='Prompt file for inferring tasks from transcript text (default: %(default)s)')
    parser.add_argument('--vocabulary', default=DEFAULT_VOCABULARY_FILE,
                       help='TSV vocabulary replacement file (default: %(default)s)')
    parser.add_argument('--no-shorten-tasks', action='store_true',
                       help='Disable LLM-powered task title shortening')
    parser.add_argument('--no-clean-transcript', action='store_true',
                       help='Disable LLM-powered transcript cleanup')
    parser.add_argument('--no-infer-transcript-tasks', action='store_true',
                       help='Disable LLM-powered transcript task inference')

    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    try:
        # Fail fast if someone explicitly points the converter at Anthropic's
        # hosted API. Local Claude-compatible endpoints are required.
        args.base_url = validate_claude_base_url(args.base_url)

        # Initialize participant database
        participant_db = ParticipantDatabase(args.db)
        vocabulary = Vocabulary(args.vocabulary)
        if args.verbose:
            print(
                f"Vocabulary enabled ({len(vocabulary.replacements)} replacements: "
                f"{args.vocabulary})",
                file=sys.stderr
            )

        # Initialize TODO shortener and transcript cleaner against the local
        # Claude-compatible endpoint. Hosted Anthropic URLs are rejected by the
        # client constructors.
        todo_shortener = None
        transcript_cleaner = None
        task_inferer = None
        api_key = args.api_key.strip() if args.api_key else None
        llm_required = (
            not args.no_shorten_tasks or
            not args.no_clean_transcript or
            not args.no_infer_transcript_tasks
        )
        if llm_required:
            if not api_key:
                raise ValueError(
                    "LLM features are enabled but no API key was provided. "
                    "Set CLAUDE_API_KEY or pass --api-key; for a local endpoint "
                    "that ignores auth, provide any non-empty placeholder."
                )
            if not ANTHROPIC_AVAILABLE:
                raise ImportError(
                    "anthropic package not installed. Run this script through "
                    "its nix-shell shebang or install the package."
                )

            if not args.no_shorten_tasks:
                todo_shortener = TodoShortener(
                    api_key=api_key,
                    base_url=args.base_url,
                    prompt_file=args.shorten_prompt
                )
                if args.verbose:
                    print(
                        f"TODO shortening enabled (max length: {MAX_TASK_TITLE_LENGTH} chars, "
                        f"prompt: {args.shorten_prompt})",
                        file=sys.stderr
                    )
            elif args.verbose:
                print("TODO shortening disabled (--no-shorten-tasks)", file=sys.stderr)

            if not args.no_clean_transcript:
                transcript_cleaner = TranscriptCleaner(api_key=api_key, base_url=args.base_url)
                if args.verbose:
                    print("Transcript cleaning enabled", file=sys.stderr)
            elif args.verbose:
                print("Transcript cleaning disabled (--no-clean-transcript)", file=sys.stderr)

            if not args.no_infer_transcript_tasks:
                task_inferer = TranscriptTaskInferer(
                    api_key=api_key,
                    base_url=args.base_url,
                    prompt_file=args.infer_tasks_prompt
                )
                if args.verbose:
                    print(
                        f"Transcript task inference enabled "
                        f"(prompt: {args.infer_tasks_prompt})",
                        file=sys.stderr
                    )
            elif args.verbose:
                print("Transcript task inference disabled (--no-infer-transcript-tasks)", file=sys.stderr)
        elif args.verbose:
            print("All LLM features disabled", file=sys.stderr)

        # Create converter
        converter = GeminiToOrgConverter(args.input_file, participant_db,
                                        todo_shortener=todo_shortener,
                                        transcript_cleaner=transcript_cleaner,
                                        task_inferer=task_inferer,
                                        vocabulary=vocabulary,
                                        verbose=args.verbose)

        # Validate filename first (this will raise ValueError if not a Gemini file)
        converter._parse_filename()

        if args.verbose:
            print(f"Converting: {args.input_file}", file=sys.stderr)

        # Now do the full conversion
        converter._read_content()
        converter._parse_content()
        org_content = converter._build_org_output()

        # Determine output filename
        if args.output_file:
            output_file = args.output_file
        else:
            output_file = generate_output_filename(args.input_file, converter.metadata)

        # Write output
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(org_content)

        # Save participant database
        participant_db.save()

        if args.verbose:
            print(f"Output written to: {output_file}", file=sys.stderr)
            print(f"Participant database updated: {args.db}", file=sys.stderr)
        else:
            print(output_file)

    except ValueError as e:
        # ValueError is usually a file format issue - not a crash
        if 'Not a Gemini notes file' in str(e):
            if args.verbose:
                print(f"Skipping: {args.input_file} (not a Gemini notes file)", file=sys.stderr)
            # Exit silently for non-Gemini files
            sys.exit(0)
        else:
            print(f"Error: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
