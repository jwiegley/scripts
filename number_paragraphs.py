#!/usr/bin/env python3
"""
Convert a plain text file into numbered paragraph format.

This script reads a text file and numbers each paragraph sequentially,
with proper indentation for continuation lines and special handling for
separator lines.

Usage:
    python number_paragraphs.py input.txt > output.txt
    python number_paragraphs.py -i input.txt
    python number_paragraphs.py -b 5 -e 3 input.txt
    python number_paragraphs.py -s input.txt  # Split paragraphs into sentences
    python number_paragraphs.py -o input.txt  # Use Org-mode section headers
    python number_paragraphs.py -o -s input.txt  # Org-mode with sentence splitting
    python number_paragraphs.py -y input.txt  # Use AI to itemize list-structured paragraphs
    python number_paragraphs.py -y --api-key YOUR_KEY input.txt
"""

import argparse
import json
import os
import re
import sys
import textwrap
from typing import Dict, List, Optional, Tuple, Union

try:
    import anthropic
except ImportError:
    anthropic = None


def is_separator_line(line: str) -> bool:
    """
    Check if a line is a separator (e.g., '-----').

    A line is considered a separator if it consists only of dashes
    and/or whitespace.

    Args:
        line: The line to check

    Returns:
        True if the line is a separator, False otherwise
    """
    stripped = line.strip()
    return bool(stripped) and all(c == '-' for c in stripped)


def should_number_paragraph(paragraph_lines: List[str]) -> bool:
    """
    Determine if a paragraph should be numbered.

    A paragraph should NOT be numbered if:
    1. It has up to 5 lines in the original input
    2. AND the last line does NOT end with a period

    Args:
        paragraph_lines: List of lines in the paragraph (original, unwrapped)

    Returns:
        True if the paragraph should be numbered, False otherwise
    """
    if not paragraph_lines:
        return True

    # Check if paragraph has up to 5 lines
    if len(paragraph_lines) > 5:
        return True

    # Check if last line ends with a period
    last_line = paragraph_lines[-1].rstrip()
    if last_line.endswith('.'):
        return True

    # Short paragraph without ending period - don't number
    return False


def parse_paragraphs(lines: List[str]) -> List[Tuple[Union[str, None], bool, bool]]:
    """
    Parse input lines into paragraphs and separators.

    Args:
        lines: List of input lines

    Returns:
        List of tuples (content, is_separator, should_number) where:
        - content is the paragraph text (joined) or separator line
        - is_separator indicates if this is a separator line
        - should_number indicates if this paragraph should be numbered
    """
    paragraphs: List[Tuple[Union[str, None], bool, bool]] = []
    current_paragraph: List[str] = []

    for line in lines:
        stripped = line.rstrip()

        # Check if this is a separator line
        if is_separator_line(stripped):
            # Save any accumulated paragraph first
            if current_paragraph:
                paragraph_text = ' '.join(current_paragraph)
                # Check if paragraph should be numbered
                should_number = should_number_paragraph(current_paragraph)
                paragraphs.append((paragraph_text, False, should_number))
                current_paragraph = []

            # Add the separator (separators are never numbered)
            paragraphs.append((stripped, True, False))

        # Blank line - end of paragraph
        elif not stripped:
            if current_paragraph:
                paragraph_text = ' '.join(current_paragraph)
                # Check if paragraph should be numbered
                should_number = should_number_paragraph(current_paragraph)
                paragraphs.append((paragraph_text, False, should_number))
                current_paragraph = []

        # Regular text line - accumulate into current paragraph
        else:
            current_paragraph.append(stripped)

    # Don't forget the last paragraph if there is one
    if current_paragraph:
        paragraph_text = ' '.join(current_paragraph)
        # Check if paragraph should be numbered
        should_number = should_number_paragraph(current_paragraph)
        paragraphs.append((paragraph_text, False, should_number))

    return paragraphs


def split_sentences(text: str) -> List[str]:
    """
    Split text into individual sentences.

    Uses regex to split on sentence-ending punctuation (., ?, !) followed
    by a space and an uppercase letter. Handles quotes and common edge cases.

    Args:
        text: The text to split into sentences

    Returns:
        List of sentences (stripped of leading/trailing whitespace)
    """
    # Pattern explanation:
    # (?<=[.!?]) - positive lookbehind for sentence-ending punctuation
    # ["\'\u201d]? - optional closing quote (straight or curly right quote)
    # \s+ - one or more whitespace characters
    # (?=[A-Z"\'\u201c]) - positive lookahead for uppercase letter or opening quote
    #
    # Split into two patterns to avoid variable-width lookbehind:
    # 1. Sentence ending with punctuation + optional quote
    # 2. Split on whitespace before uppercase/quote

    # First, handle the case where there's a quote after punctuation
    # Replace '. "' or '." ' patterns with a unique marker
    pattern = r'([.!?]["\'\u201d]?)\s+(?=[A-Z"\'\u201c])'

    sentences = re.split(pattern, text)

    # The split includes the captured groups, so we need to recombine them
    result = []
    i = 0
    while i < len(sentences):
        if i + 1 < len(sentences) and sentences[i + 1].strip():
            # Combine the sentence with its ending punctuation
            combined = (sentences[i] + sentences[i + 1]).strip()
            if combined:
                result.append(combined)
            i += 2
        else:
            # Just a sentence without captured ending
            if sentences[i].strip():
                result.append(sentences[i].strip())
            i += 1

    return result


def wrap_paragraph(text: str, paragraph_num: int, max_width: int = 78) -> str:
    """
    Wrap a paragraph with numbering and proper indentation.

    Args:
        text: The paragraph text to wrap
        paragraph_num: The paragraph number (1-indexed)
        max_width: Maximum width for wrapped text

    Returns:
        Formatted paragraph with number prefix and indented continuation lines
    """
    # Determine indentation width based on paragraph number
    indent_width = 3 if paragraph_num < 10 else 4

    prefix = f"{paragraph_num}. "
    subsequent_indent = " " * indent_width

    wrapped = textwrap.fill(
        text,
        width=max_width,
        initial_indent=prefix,
        subsequent_indent=subsequent_indent,
        break_long_words=False,
        break_on_hyphens=True
    )

    return wrapped


def wrap_paragraph_with_sentences(text: str, paragraph_num: int, max_width: int = 78) -> str:
    """
    Wrap a paragraph with sentence splitting.

    Each sentence is on its own wrapped block, separated by blank lines.
    The first sentence has the paragraph number, subsequent sentences are
    indented to match.

    Args:
        text: The paragraph text to wrap
        paragraph_num: The paragraph number (1-indexed)
        max_width: Maximum width for wrapped text

    Returns:
        Formatted paragraph with sentences separated by blank lines
    """
    # Determine indentation width based on paragraph number
    indent_width = 3 if paragraph_num < 10 else 4
    subsequent_indent = " " * indent_width

    # Split the text into sentences
    sentences = split_sentences(text)

    if not sentences:
        return ""

    result = []

    # First sentence gets the paragraph number
    first_sentence = sentences[0]
    prefix = f"{paragraph_num}. "
    wrapped_first = textwrap.fill(
        first_sentence,
        width=max_width,
        initial_indent=prefix,
        subsequent_indent=subsequent_indent,
        break_long_words=False,
        break_on_hyphens=True
    )
    result.append(wrapped_first)

    # Subsequent sentences are indented to match
    for sentence in sentences[1:]:
        wrapped = textwrap.fill(
            sentence,
            width=max_width,
            initial_indent=subsequent_indent,
            subsequent_indent=subsequent_indent,
            break_long_words=False,
            break_on_hyphens=True
        )
        result.append(wrapped)

    # Join sentences with blank lines
    return '\n\n'.join(result)


def wrap_paragraph_org_mode(text: str, paragraph_num: int, max_width: int = 78) -> str:
    """
    Wrap a paragraph in Org-mode format.

    Creates a section header with the paragraph number, followed by a blank line,
    then the wrapped paragraph text without numbering or indentation.

    Args:
        text: The paragraph text to wrap
        paragraph_num: The paragraph number (1-indexed)
        max_width: Maximum width for wrapped text

    Returns:
        Formatted paragraph with Org-mode section header
    """
    header = f"* paragraph {paragraph_num}"

    # Wrap the text without any number prefix or indentation
    wrapped = textwrap.fill(
        text,
        width=max_width,
        break_long_words=False,
        break_on_hyphens=True
    )

    return f"{header}\n\n{wrapped}"


def wrap_paragraph_with_sentences_org_mode(text: str, paragraph_num: int, max_width: int = 78) -> str:
    """
    Wrap a paragraph in Org-mode format with sentence splitting.

    Creates a section header with the paragraph number, followed by a blank line,
    then sentences separated by blank lines, without numbering or indentation.

    Args:
        text: The paragraph text to wrap
        paragraph_num: The paragraph number (1-indexed)
        max_width: Maximum width for wrapped text

    Returns:
        Formatted paragraph with Org-mode section header and separated sentences
    """
    header = f"* paragraph {paragraph_num}"

    # Split the text into sentences
    sentences = split_sentences(text)

    if not sentences:
        return header

    result = []

    # Each sentence is wrapped without any indentation
    for sentence in sentences:
        wrapped = textwrap.fill(
            sentence,
            width=max_width,
            break_long_words=False,
            break_on_hyphens=True
        )
        result.append(wrapped)

    # Join sentences with blank lines
    sentences_text = '\n\n'.join(result)

    return f"{header}\n\n{sentences_text}"


MODEL_IDS = {
    'sonnet': 'claude-sonnet-4-20250514',
    'opus': 'claude-opus-4-20250514',
}


def analyze_paragraph_structure(text: str, api_key: str, model: str = 'sonnet', base_url: Optional[str] = None) -> Dict:
    """
    Use Anthropic API to analyze if a paragraph has a list structure.

    Args:
        text: The paragraph text to analyze
        api_key: Anthropic API key
        model: Model to use ('sonnet' or 'opus')
        base_url: Optional base URL for API (for proxies like LiteLLM)

    Returns:
        Dictionary with:
        - has_list_structure: bool
        - intro_text: str (the introductory sentences)
        - items: list of dicts with 'text' and 'emphasis' keys

    Raises:
        Exception: If API call fails
    """
    if anthropic is None:
        raise ImportError("anthropic library not installed. Install with: pip install anthropic")

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = anthropic.Anthropic(**client_kwargs)

    system_prompt = """You are a JSON-only response bot. You MUST respond with valid JSON only, no other text.

Analyze if the given paragraph has a structure where introductory sentences present a main idea, followed by multiple sentences that each describe related concepts or features that could be listed as bullet points.

Return ONLY a JSON object (no markdown, no explanation, no preamble) with this exact structure:
{"has_list_structure": boolean, "intro_text": "string", "items": [{"text": "string", "emphasis": "string"}]}

Rules:
- has_list_structure: true if paragraph has intro + listable concepts, false otherwise
- intro_text: the first 1-3 sentences that set up the main idea (verbatim, unchanged)
- items: array of subsequent sentences, each with:
  - text: the sentence exactly as it appears (verbatim, unchanged)
  - emphasis: a key phrase (2-5 words) capturing the core concept
- If has_list_structure is false, intro_text should be empty string and items should be empty array
- NEVER modify the original text. Return sentences EXACTLY as they appear."""

    message = client.messages.create(
        model=MODEL_IDS.get(model, MODEL_IDS['sonnet']),
        max_tokens=2000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Analyze this paragraph and return JSON only:\n\n{text}"
            },
            {
                "role": "assistant",
                "content": "{"
            }
        ]
    )

    # Extract the response content and prepend the '{' we used as prefill
    response_text = "{" + message.content[0].text

    # Parse the JSON response
    try:
        result = json.loads(response_text)
        return result
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
            return result
        else:
            # Try to find any JSON object in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                return result
            raise ValueError(f"Failed to parse JSON response: {response_text[:200]}")


def format_paragraph_with_items(
    intro: str,
    items: List[Dict],
    paragraph_num: int,
    max_width: int = 78
) -> str:
    """
    Format a paragraph with intro and bullet items.

    Args:
        intro: The introductory text
        items: List of dicts with 'text' and 'emphasis' keys
        paragraph_num: The paragraph number (1-indexed)
        max_width: Maximum width for wrapped text

    Returns:
        Formatted paragraph with intro and bullet items
    """
    # Determine indentation width based on paragraph number
    indent_width = 3 if paragraph_num < 10 else 4
    subsequent_indent = " " * indent_width

    result = []

    # Format the intro with paragraph number
    prefix = f"{paragraph_num}. "
    wrapped_intro = textwrap.fill(
        intro,
        width=max_width,
        initial_indent=prefix,
        subsequent_indent=subsequent_indent,
        break_long_words=False,
        break_on_hyphens=True
    )
    result.append(wrapped_intro)

    # Add blank line after intro
    result.append("")

    # Format each bullet item
    for item in items:
        item_text = item['text']
        emphasis = item.get('emphasis', '')

        # Add emphasis markers around the key phrase if present
        if emphasis and emphasis in item_text:
            item_text = item_text.replace(emphasis, f'*{emphasis}*', 1)

        # Bullet items should be indented to align with paragraph text
        bullet_indent = subsequent_indent + "- "
        bullet_subsequent = subsequent_indent + "  "

        wrapped_item = textwrap.fill(
            item_text,
            width=max_width,
            initial_indent=bullet_indent,
            subsequent_indent=bullet_subsequent,
            break_long_words=False,
            break_on_hyphens=True
        )
        result.append(wrapped_item)

    return '\n'.join(result)


def format_paragraph_with_items_org_mode(
    intro: str,
    items: List[Dict],
    paragraph_num: int,
    max_width: int = 78
) -> str:
    """
    Format a paragraph with intro and bullet items in Org-mode format.

    Args:
        intro: The introductory text
        items: List of dicts with 'text' and 'emphasis' keys
        paragraph_num: The paragraph number (1-indexed)
        max_width: Maximum width for wrapped text

    Returns:
        Formatted paragraph with Org-mode header, intro and bullet items
    """
    result = []

    # Add Org-mode header
    header = f"* paragraph {paragraph_num}"
    result.append(header)
    result.append("")

    # Format the intro without paragraph number
    wrapped_intro = textwrap.fill(
        intro,
        width=max_width,
        break_long_words=False,
        break_on_hyphens=True
    )
    result.append(wrapped_intro)

    # Add blank line after intro
    result.append("")

    # Format each bullet item (no indentation in org-mode)
    for item in items:
        item_text = item['text']
        emphasis = item.get('emphasis', '')

        # Add emphasis markers around the key phrase if present
        if emphasis and emphasis in item_text:
            item_text = item_text.replace(emphasis, f'*{emphasis}*', 1)

        # Bullet items in org-mode start with "- "
        wrapped_item = textwrap.fill(
            item_text,
            width=max_width,
            initial_indent="- ",
            subsequent_indent="  ",
            break_long_words=False,
            break_on_hyphens=True
        )
        result.append(wrapped_item)

    return '\n'.join(result)


def format_document(content: str, max_width: int = 78, split_sentences: bool = False, itemize: bool = False, api_key: Optional[str] = None, model: str = 'sonnet', base_url: Optional[str] = None, org_mode: bool = False) -> str:
    """
    Format an entire document with numbered paragraphs.

    Args:
        content: The input text content
        max_width: Maximum width for wrapped text
        split_sentences: If True, split numbered paragraphs into individual sentences
        itemize: If True, use AI to analyze and format paragraphs with list structure
        api_key: Anthropic API key (required if itemize is True)
        model: Model to use for itemization ('sonnet' or 'opus')
        base_url: Optional base URL for API (for proxies like LiteLLM)
        org_mode: If True, use Org-mode section headers instead of numbered lists

    Returns:
        Formatted document with numbered paragraphs
    """
    lines = content.splitlines()
    paragraphs = parse_paragraphs(lines)

    result: List[str] = []
    paragraph_num = 0
    needs_resume_marker = False

    for i, (content, is_separator, should_number) in enumerate(paragraphs):
        if is_separator:
            # Add blank line before separator if there's content before it
            if result:
                result.append("")
            result.append(content)
            # Next numbered paragraph needs [@N] marker (only in non-org mode)
            if not org_mode:
                needs_resume_marker = True
        elif should_number:
            # This is a regular paragraph that should be numbered
            paragraph_num += 1

            # Add blank line before paragraph (unless it's the first one)
            if result:
                result.append("")

            # Add [@N] marker if resuming after non-numbered content (but not for paragraph 1)
            # Not needed in org-mode since headers contain paragraph numbers
            resume_marker = ""
            if not org_mode and needs_resume_marker and paragraph_num > 1:
                resume_marker = f"[@{paragraph_num}] "
            needs_resume_marker = False

            # Try itemize mode if enabled
            used_itemize = False
            if itemize and api_key:
                try:
                    # Analyze paragraph structure
                    analysis = analyze_paragraph_structure(content, api_key, model, base_url)

                    if analysis.get('has_list_structure', False):
                        # Format with items
                        intro_text = analysis['intro_text']
                        items = analysis.get('items', [])

                        # Add resume marker to intro if needed (not in org-mode)
                        if resume_marker:
                            intro_text = resume_marker + intro_text

                        if org_mode:
                            wrapped = format_paragraph_with_items_org_mode(
                                intro_text,
                                items,
                                paragraph_num,
                                max_width
                            )
                        else:
                            wrapped = format_paragraph_with_items(
                                intro_text,
                                items,
                                paragraph_num,
                                max_width
                            )
                        result.append(wrapped)
                        used_itemize = True
                except Exception as e:
                    # Gracefully fall back to normal formatting on API error
                    print(f"Warning: API call failed for paragraph {paragraph_num}: {e}", file=sys.stderr)
                    print(f"Falling back to normal formatting.", file=sys.stderr)

            # If itemize wasn't used, use normal formatting
            if not used_itemize:
                # Add resume marker if needed (not in org-mode)
                paragraph_content = content
                if resume_marker:
                    paragraph_content = resume_marker + content

                # Wrap the paragraph (with or without sentence splitting)
                # Note: itemize takes precedence over split_sentences when list structure is detected
                if org_mode:
                    if split_sentences:
                        wrapped = wrap_paragraph_with_sentences_org_mode(paragraph_content, paragraph_num, max_width)
                    else:
                        wrapped = wrap_paragraph_org_mode(paragraph_content, paragraph_num, max_width)
                else:
                    if split_sentences:
                        wrapped = wrap_paragraph_with_sentences(paragraph_content, paragraph_num, max_width)
                    else:
                        wrapped = wrap_paragraph(paragraph_content, paragraph_num, max_width)
                result.append(wrapped)
        else:
            # This is a non-numbered paragraph (short, no ending period)
            # Add blank line before paragraph (unless it's the first one)
            if result:
                result.append("")

            # Next numbered paragraph needs [@N] marker (only in non-org mode)
            if not org_mode:
                needs_resume_marker = True

            # Output the paragraph without numbering, but rewrap it
            wrapped = textwrap.fill(
                content,
                width=max_width,
                break_long_words=False,
                break_on_hyphens=True
            )
            result.append(wrapped)

    return '\n'.join(result)


def format_with_boundaries(content: str, begin_line: int, end_skip: int, max_width: int = 78, split_sentences: bool = False, itemize: bool = False, api_key: Optional[str] = None, model: str = 'sonnet', base_url: Optional[str] = None, org_mode: bool = False) -> str:
    """
    Format a document, only processing lines within specified boundaries.

    Args:
        content: The input text content
        begin_line: Line number to start processing (1-indexed, lines before are kept as-is)
        end_skip: Number of lines to skip at end (kept as-is)
        max_width: Maximum width for wrapped text
        split_sentences: If True, split numbered paragraphs into individual sentences
        itemize: If True, use AI to analyze and format paragraphs with list structure
        api_key: Anthropic API key (required if itemize is True)
        model: Model to use for itemization ('sonnet' or 'opus')
        base_url: Optional base URL for API (for proxies like LiteLLM)
        org_mode: If True, use Org-mode section headers instead of numbered lists

    Returns:
        Formatted document with numbered paragraphs in the specified region
    """
    lines = content.splitlines()
    total_lines = len(lines)

    # Calculate boundaries (convert to 0-indexed)
    start_idx = max(0, begin_line - 1)
    end_idx = max(start_idx, total_lines - end_skip)

    # Split into prefix, middle (to process), and suffix
    prefix_lines = lines[:start_idx]
    middle_lines = lines[start_idx:end_idx]
    suffix_lines = lines[end_idx:]

    # Format the middle section
    middle_content = '\n'.join(middle_lines)
    formatted_middle = format_document(middle_content, max_width, split_sentences, itemize, api_key, model, base_url, org_mode)

    # Reassemble
    result_parts = []
    if prefix_lines:
        result_parts.append('\n'.join(prefix_lines))
    if formatted_middle:
        result_parts.append(formatted_middle)
    if suffix_lines:
        result_parts.append('\n'.join(suffix_lines))

    return '\n'.join(result_parts)


def main() -> None:
    """
    Main entry point for the script.

    Parses command-line arguments and processes the file accordingly.
    """
    parser = argparse.ArgumentParser(
        description='Convert a plain text file into numbered paragraph format.'
    )
    parser.add_argument('input_file', help='Input file to process')
    parser.add_argument('-i', '--in-place', action='store_true',
                        help='Modify file in place')
    parser.add_argument('-b', '--begin', type=int, default=1,
                        help='Start paragraph numbering at line N (1-indexed)')
    parser.add_argument('-e', '--end-skip', type=int, default=0,
                        help='Stop numbering N lines before end of file')
    parser.add_argument('-s', '--split-sentences', action='store_true',
                        help='Split numbered paragraphs into individual sentences')
    parser.add_argument('-o', '--org-mode', action='store_true',
                        help='Use Org-mode section headers instead of numbered lists')
    parser.add_argument('-y', '--itemize', action='store_true',
                        help='Use AI to analyze and format paragraphs with list structure')
    parser.add_argument('--api-key', type=str, default=None,
                        help='Anthropic API key (defaults to ANTHROPIC_API_KEY environment variable)')
    parser.add_argument('--model', type=str, choices=['sonnet', 'opus'], default='sonnet',
                        help='AI model to use for itemization (default: sonnet)')
    parser.add_argument('--base-url', type=str, default=None,
                        help='Base URL for API (for proxies like LiteLLM)')

    args = parser.parse_args()

    # Validate itemize mode requirements
    if args.itemize:
        # Get API key from argument or environment
        api_key = args.api_key or os.environ.get('ANTHROPIC_API_KEY')

        if not api_key:
            print("Error: --itemize requires an API key. Provide --api-key or set ANTHROPIC_API_KEY environment variable.", file=sys.stderr)
            sys.exit(1)

        if anthropic is None:
            print("Error: --itemize requires the anthropic library. Install with: pip install anthropic", file=sys.stderr)
            sys.exit(1)
    else:
        api_key = None

    try:
        # Read the input file with UTF-8 encoding
        with open(args.input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Format the document with boundaries
        if args.begin > 1 or args.end_skip > 0:
            formatted = format_with_boundaries(
                content,
                args.begin,
                args.end_skip,
                split_sentences=args.split_sentences,
                itemize=args.itemize,
                api_key=api_key,
                model=args.model,
                base_url=args.base_url,
                org_mode=args.org_mode
            )
        else:
            formatted = format_document(
                content,
                split_sentences=args.split_sentences,
                itemize=args.itemize,
                api_key=api_key,
                model=args.model,
                base_url=args.base_url,
                org_mode=args.org_mode
            )

        # Write output
        if args.in_place:
            with open(args.input_file, 'w', encoding='utf-8') as f:
                f.write(formatted)
                f.write('\n')
        else:
            print(formatted)

    except FileNotFoundError:
        print(f"Error: File '{args.input_file}' not found", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError:
        print(f"Error: File '{args.input_file}' is not valid UTF-8", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
