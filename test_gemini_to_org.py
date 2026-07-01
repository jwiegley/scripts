import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).with_name("gemini_to_org.py")
WRAPPER = Path(__file__).with_name("convert_all_gemini_notes.sh")


def load_module():
    spec = importlib.util.spec_from_file_location("gemini_to_org", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeStream:
    def __init__(self, text):
        self.text_stream = iter([text])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeMessages:
    def __init__(self, text):
        self.values = list(text) if isinstance(text, list) else [text]

    def stream(self, **kwargs):
        return FakeStream(self.values.pop(0))


class FakeClient:
    def __init__(self, text):
        self.messages = FakeMessages(text)


class GeminiToOrgTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()

    def make_cleaner(self, response):
        cleaner = self.mod.TranscriptCleaner.__new__(self.mod.TranscriptCleaner)
        cleaner.client = FakeClient(response)
        cleaner.model = "fake-model"
        cleaner.max_cleanup_tokens = 8192
        return cleaner

    def make_shortener(self, responses):
        class FakeMessagesCreate:
            def __init__(self, values):
                self.values = list(values)

            def create(self, **kwargs):
                value = self.values.pop(0)
                return SimpleNamespace(content=[SimpleNamespace(text=value)])

        class FakeShortenerClient:
            def __init__(self, values):
                self.messages = FakeMessagesCreate(values)

        shortener = self.mod.TodoShortener.__new__(self.mod.TodoShortener)
        shortener.client = FakeShortenerClient(responses)
        shortener.max_title_length = self.mod.MAX_TASK_TITLE_LENGTH
        shortener.prompt_template = "Shorten task titles."
        return shortener

    def test_vocabulary_is_required_and_applied(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "missing.tsv"
            with self.assertRaisesRegex(ValueError, "Vocabulary file not found"):
                self.mod.Vocabulary(str(missing))

            vocab_file = Path(td) / "vocab.tsv"
            vocab_file.write_text("Aries\tAres\nAzimoff\tAsimov\n", encoding="utf-8")
            vocab = self.mod.Vocabulary(str(vocab_file))
            self.assertEqual(vocab.apply("Aries targets Azimoff"), "Ares targets Asimov")

    def test_hosted_anthropic_url_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Refusing to use Anthropic hosted API"):
            self.mod.validate_claude_base_url("https://api.anthropic.com")

    def test_parse_org_task_entries_preserves_done_state(self):
        entries = self.mod.parse_org_task_entries(
            "* DONE [#A] Archive launch notes  :Owner:\n"
            ":PROPERTIES:\n"
            ":ASSIGNEES: Current User\n"
            ":END:\n"
            "Include final context.\n"
        )

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].keyword, "DONE")
        self.assertEqual(entries[0].priority, "[#A]")
        self.assertEqual(entries[0].title, "Archive launch notes")
        self.assertEqual(entries[0].tags, ["Owner"])
        self.assertEqual(entries[0].properties, {"ASSIGNEES": "Current User"})
        self.assertEqual(entries[0].extra_lines, ["Include final context."])

    def test_corrupt_participant_database_fails_loudly(self):
        with tempfile.TemporaryDirectory() as td:
            db_file = Path(td) / "participants.json"
            db_file.write_text("{not json", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                self.mod.ParticipantDatabase(str(db_file))

    def test_task_shortener_retries_overlong_model_response(self):
        shortener = self.make_shortener([
            "*** TODO This model response is intentionally far too long to be accepted as a valid task title",
            "*** TODO Review Ares task title",
        ])
        title, body = shortener.shorten_title(
            "Review the detailed Ares task title with enough words to require shortening."
        )
        self.assertEqual(title, "Review Ares task title")
        self.assertEqual(
            body,
            "Review the detailed Ares task title with enough words to require shortening."
        )

    def test_cli_requires_api_key_when_llm_features_are_enabled(self):
        with tempfile.TemporaryDirectory() as td:
            input_file = Path(td) / "Meeting started 2026_06_25 12_57 PDT - Notes by Gemini.md"
            input_file.write_text(
                "# Notes by Gemini\n\n### **Summary**\n\nTest.\n",
                encoding="utf-8",
            )
            output_file = Path(td) / "out.org"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--db",
                    str(Path(td) / "participants.json"),
                    str(input_file),
                    str(output_file),
                ],
                env={**os.environ, "GEMINI_TO_ORG_USER_NAME": "Current User"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("LLM features are enabled but no API key was provided", result.stderr)
            self.assertFalse(output_file.exists())

    def test_cli_allows_explicit_non_llm_conversion_without_api_key(self):
        with tempfile.TemporaryDirectory() as td:
            input_file = Path(td) / "Meeting started 2026_06_25 12_57 PDT - Notes by Gemini.md"
            input_file.write_text(
                "# Notes by Gemini\n\n"
                "### **Summary**\n\nAries targets Azimoff.\n\n"
                "### **Suggested next steps**\n\n"
                "- [ ] [Current User] Review Aries for Azimoff.\n\n"
                "# **Transcript**\n\n"
                "### **00:00:01**\n\n"
                "**Current User:** Aries and Azimoff.\n",
                encoding="utf-8",
            )
            output_file = Path(td) / "out.org"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--no-shorten-tasks",
                    "--no-clean-transcript",
                    "--no-infer-transcript-tasks",
                    "--db",
                    str(Path(td) / "participants.json"),
                    str(input_file),
                    str(output_file),
                ],
                env={**os.environ, "GEMINI_TO_ORG_USER_NAME": "Current User"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            text = output_file.read_text(encoding="utf-8")
            self.assertIn("Ares targets Asimov", text)
            self.assertNotIn("Aries", text)
            self.assertNotIn("Azimoff", text)

    def test_cli_help_does_not_print_env_api_key(self):
        sentinel = "local-value-for-help-test"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            env={**os.environ, "CLAUDE_API_KEY": sentinel},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertNotIn(sentinel, combined)
        self.assertIn("CLAUDE_API_KEY env var", combined)

    def test_batch_wrapper_supplies_local_auth_for_loopback_endpoint(self):
        with tempfile.TemporaryDirectory() as td:
            tempdir = Path(td)
            wrapper = tempdir / "convert_all_gemini_notes.sh"
            wrapper.write_text(WRAPPER.read_text(encoding="utf-8"), encoding="utf-8")
            wrapper.chmod(0o755)
            converter = tempdir / "gemini_to_org.py"
            converter.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$CLAUDE_API_KEY\" > auth.txt\n"
                "printf '%s\\n' \"$1.org\"\n",
                encoding="utf-8",
            )
            converter.chmod(0o755)
            notes = tempdir / "Meeting - Notes by Gemini.md"
            notes.write_text("# Notes by Gemini\n", encoding="utf-8")

            env = {
                key: value for key, value in os.environ.items()
                if key not in {"CLAUDE_API_KEY", "CLAUDE_BASE_URL", "GEMINI_TO_ORG_LOCAL_AUTH"}
            }
            result = subprocess.run(
                [str(wrapper)],
                cwd=tempdir,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((tempdir / "auth.txt").read_text(encoding="utf-8").strip(), "local-endpoint")
            self.assertIn("Converted: 1", result.stdout)

    def test_batch_wrapper_does_not_supply_local_auth_for_nonloopback_endpoint(self):
        with tempfile.TemporaryDirectory() as td:
            tempdir = Path(td)
            wrapper = tempdir / "convert_all_gemini_notes.sh"
            wrapper.write_text(WRAPPER.read_text(encoding="utf-8"), encoding="utf-8")
            wrapper.chmod(0o755)
            converter = tempdir / "gemini_to_org.py"
            converter.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"${CLAUDE_API_KEY:-unset}\" > auth.txt\n"
                "printf '%s\\n' \"$1.org\"\n",
                encoding="utf-8",
            )
            converter.chmod(0o755)
            notes = tempdir / "Meeting - Notes by Gemini.md"
            notes.write_text("# Notes by Gemini\n", encoding="utf-8")

            env = {
                key: value for key, value in os.environ.items()
                if key not in {"CLAUDE_API_KEY", "GEMINI_TO_ORG_LOCAL_AUTH"}
            }
            env["CLAUDE_BASE_URL"] = "http://example.test:8317"
            result = subprocess.run(
                [str(wrapper)],
                cwd=tempdir,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((tempdir / "auth.txt").read_text(encoding="utf-8").strip(), "unset")
            self.assertIn("Converted: 1", result.stdout)

    def test_batch_wrapper_preserves_transcript_and_infers_tasks_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            tempdir = Path(td)
            wrapper = tempdir / "convert_all_gemini_notes.sh"
            wrapper.write_text(WRAPPER.read_text(encoding="utf-8"), encoding="utf-8")
            wrapper.chmod(0o755)
            converter = tempdir / "gemini_to_org.py"
            converter.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$*\" > args.txt\n"
                "printf '%s\\n' \"$1.org\"\n",
                encoding="utf-8",
            )
            converter.chmod(0o755)
            notes = tempdir / "Meeting - Notes by Gemini.md"
            notes.write_text("# Notes by Gemini\n", encoding="utf-8")

            env = {
                key: value for key, value in os.environ.items()
                if key not in {"GEMINI_TO_ORG_USE_LLM", "CLAUDE_API_KEY"}
            }
            result = subprocess.run(
                [str(wrapper)],
                cwd=tempdir,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            args = (tempdir / "args.txt").read_text(encoding="utf-8")
            self.assertIn("--no-shorten-tasks", args)
            self.assertIn("--no-clean-transcript", args)
            self.assertNotIn("--no-infer-transcript-tasks", args)

    def test_batch_wrapper_can_disable_inferred_tasks(self):
        with tempfile.TemporaryDirectory() as td:
            tempdir = Path(td)
            wrapper = tempdir / "convert_all_gemini_notes.sh"
            wrapper.write_text(WRAPPER.read_text(encoding="utf-8"), encoding="utf-8")
            wrapper.chmod(0o755)
            converter = tempdir / "gemini_to_org.py"
            converter.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$*\" > args.txt\n"
                "printf '%s\\n' \"$1.org\"\n",
                encoding="utf-8",
            )
            converter.chmod(0o755)
            notes = tempdir / "Meeting - Notes by Gemini.md"
            notes.write_text("# Notes by Gemini\n", encoding="utf-8")

            env = {
                key: value for key, value in os.environ.items()
                if key not in {"GEMINI_TO_ORG_USE_LLM", "CLAUDE_API_KEY"}
            }
            env["GEMINI_TO_ORG_INFER_TRANSCRIPT_TASKS"] = "0"
            result = subprocess.run(
                [str(wrapper)],
                cwd=tempdir,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            args = (tempdir / "args.txt").read_text(encoding="utf-8")
            self.assertIn("--no-shorten-tasks", args)
            self.assertIn("--no-clean-transcript", args)
            self.assertIn("--no-infer-transcript-tasks", args)

    def test_batch_wrapper_can_enable_local_model_features(self):
        with tempfile.TemporaryDirectory() as td:
            tempdir = Path(td)
            wrapper = tempdir / "convert_all_gemini_notes.sh"
            wrapper.write_text(WRAPPER.read_text(encoding="utf-8"), encoding="utf-8")
            wrapper.chmod(0o755)
            converter = tempdir / "gemini_to_org.py"
            converter.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$*\" > args.txt\n"
                "printf '%s\\n' \"$1.org\"\n",
                encoding="utf-8",
            )
            converter.chmod(0o755)
            notes = tempdir / "Meeting - Notes by Gemini.md"
            notes.write_text("# Notes by Gemini\n", encoding="utf-8")

            env = {**os.environ, "GEMINI_TO_ORG_USE_LLM": "1", "CLAUDE_API_KEY": "local-endpoint"}
            result = subprocess.run(
                [str(wrapper)],
                cwd=tempdir,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            args = (tempdir / "args.txt").read_text(encoding="utf-8")
            self.assertNotIn("--no-shorten-tasks", args)
            self.assertNotIn("--no-clean-transcript", args)
            self.assertNotIn("--no-infer-transcript-tasks", args)

    def test_batch_wrapper_prints_converter_error_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            tempdir = Path(td)
            wrapper = tempdir / "convert_all_gemini_notes.sh"
            wrapper.write_text(WRAPPER.read_text(encoding="utf-8"), encoding="utf-8")
            wrapper.chmod(0o755)
            converter = tempdir / "gemini_to_org.py"
            converter.write_text(
                "#!/bin/sh\n"
                "echo 'converter failed' >&2\n"
                "exit 42\n",
                encoding="utf-8",
            )
            converter.chmod(0o755)
            notes = tempdir / "Meeting - Notes by Gemini.md"
            notes.write_text("# Notes by Gemini\n", encoding="utf-8")

            result = subprocess.run(
                [str(wrapper)],
                cwd=tempdir,
                env={**os.environ, "CLAUDE_API_KEY": "local-endpoint"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("converter failed", result.stdout)
            self.assertIn("Errors:    1", result.stdout)

    def test_task_title_cleanup_preserves_internal_articles(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        self.assertEqual(
            converter._remove_filler_words("Write a design for the API"),
            "Write a design for the API",
        )
        self.assertEqual(
            converter._remove_filler_words("The rollout plan"),
            "rollout plan",
        )

    def test_summary_bold_topic_and_inline_markdown_are_preserved(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "summary": [
                "**Launch review**",
                "Discussed `flags`, *risk*, and [notes](https://example.com).",
            ]
        }

        summary = "\n".join(converter._convert_summary())
        self.assertIn("- Launch review :: Discussed =flags=, /risk/, and", summary)
        self.assertIn("[[https://example.com][notes]].", summary)

    def test_summary_underscore_bold_topic_is_preserved(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "summary": [
                "__Launch review__",
                "Discussed _timing_ and `flags`.",
            ]
        }

        summary = "\n".join(converter._convert_summary())
        self.assertIn("- Launch review :: Discussed /timing/ and =flags=.", summary)

    def test_summary_decodes_html_entities(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "summary": [
                "**Launch review**",
                "Discussed A&amp;B and &quot;risk&quot;.",
            ]
        }

        summary = "\n".join(converter._convert_summary())
        self.assertIn('- Launch review :: Discussed A&B and "risk".', summary)

    def test_summary_list_items_are_preserved(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "summary": [
                "- Review *risk*",
                "  - Check `parser` output",
                "1. Confirm _timing_",
            ]
        }

        summary = "\n".join(converter._convert_summary())
        self.assertIn("- Review /risk/", summary)
        self.assertIn("  - Check =parser= output", summary)
        self.assertIn("1. Confirm /timing/", summary)

    def test_inline_markdown_converts_italic(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        self.assertEqual(
            converter._convert_inline_markdown("Review *risk* and _timing_."),
            "Review /risk/ and /timing/.",
        )

    def test_inline_markdown_converts_underscore_bold(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        self.assertEqual(
            converter._convert_inline_markdown("Review __risk__ and _timing_."),
            "Review *risk* and /timing/.",
        )

    def test_inline_markdown_preserves_underscore_identifiers(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        self.assertEqual(
            converter._convert_inline_markdown("Use cycle_accurate_simulator for timing."),
            "Use cycle_accurate_simulator for timing.",
        )

    def test_inline_markdown_preserves_markup_inside_code_spans(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        self.assertEqual(
            converter._convert_inline_markdown("Use `foo*bar*` before *risk*."),
            "Use =foo*bar*= before /risk/.",
        )

    def test_inline_markdown_uses_safe_code_delimiter_for_equals(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        self.assertEqual(
            converter._convert_inline_markdown("Run `--limit=4` before *testing*."),
            "Run ~--limit=4~ before /testing/.",
        )

    def test_inline_markdown_preserves_unmatched_backtick(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        self.assertEqual(
            converter._convert_inline_markdown("Keep `partial marker and *risk*."),
            "Keep `partial marker and /risk/.",
        )

    def test_inline_markdown_preserves_parenthesized_link_urls(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        self.assertEqual(
            converter._convert_inline_markdown("See [notes](https://example.com/a_(b))."),
            "See [[https://example.com/a_(b)][notes]].",
        )

    def test_inline_markdown_decodes_html_entities(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        self.assertEqual(
            converter._convert_inline_markdown(
                "Review A&amp;B, &quot;risk&quot;, and &#39;timing&#39;."
            ),
            'Review A&B, "risk", and \'timing\'.',
        )

    def test_next_step_details_are_preserved_in_task_body(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "- [ ] Draft a plan for the API",
                "  - Include the parser contract",
                "    and the rollback case.",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("*** TODO Draft a plan for the API", org)
        self.assertIn("- Include the parser contract and the rollback case.", org)

    def test_next_step_ordered_details_are_preserved(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "- [ ] Draft a plan for the API",
                "  1. Confirm `parser` ownership",
                "     and release timing.",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("1. Confirm =parser= ownership and release timing.", org)

    def test_next_step_nested_detail_bullets_keep_relative_indent(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "- [ ] Draft a plan for the API",
                "  - Include the parser contract",
                "    - Cover rollback behavior",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("- Include the parser contract", org)
        self.assertIn("  - Cover rollback behavior", org)

    def test_next_step_nested_ordered_details_keep_relative_indent(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "- [ ] Draft a plan for the API",
                "  1. Confirm parser ownership",
                "    2. Confirm release timing",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("1. Confirm parser ownership", org)
        self.assertIn("  2. Confirm release timing", org)

    def test_ordered_next_step_checkbox_becomes_task(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [
                    "1. [ ] [Current User] Write the launch note.",
                    "2. [x] [External Owner] Archive the release notes.",
                ],
                "transcript": [],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = None
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** TODO Write the launch note", org)
        self.assertIn(":ASSIGNEES: Current User", org)
        self.assertIn("*** DONE Archive the release notes  :External:", org)
        self.assertIn(":ASSIGNEES: External Owner", org)

    def test_ordered_next_step_details_keep_relative_indent(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "1. [ ] Draft a plan for the API",
                "   - Include the parser contract",
                "     - Cover rollback behavior",
                "   1. Confirm parser ownership",
                "     2. Confirm release timing",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("*** TODO Draft a plan for the API", org)
        self.assertIn("- Include the parser contract", org)
        self.assertIn("  - Cover rollback behavior", org)
        self.assertIn("1. Confirm parser ownership", org)
        self.assertIn("  2. Confirm release timing", org)

    def test_plain_next_step_bullets_become_tasks(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "- Draft a plan for the API",
                "- Confirm the release timing",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("*** TODO Draft a plan for the API", org)
        self.assertIn("*** TODO Confirm the release timing", org)
        self.assertNotIn("- Confirm the release timing", org)

    def test_plain_ordered_next_step_items_become_tasks(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "1. Draft a plan for the API",
                "2. Confirm the release timing",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("*** TODO Draft a plan for the API", org)
        self.assertIn("*** TODO Confirm the release timing", org)

    def test_plain_next_step_nested_bullets_remain_task_details(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "- Draft a plan for the API",
                "  - Include the parser contract",
                "    - Cover rollback behavior",
                "- Confirm the release timing",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("*** TODO Draft a plan for the API", org)
        self.assertIn("- Include the parser contract", org)
        self.assertIn("  - Cover rollback behavior", org)
        self.assertIn("*** TODO Confirm the release timing", org)

    def test_next_step_detail_inline_markdown_is_converted(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "- [ ] Draft a plan for the API",
                "  - Include *risk*, _timing_, `parser`, and [notes](https://example.com).",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn(
            "- Include /risk/, /timing/, =parser=, and [[https://example.com][notes]].",
            org,
        )

    def test_next_step_short_label_becomes_headline(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "- [ ] [External Owner] Write Launch Note: Write a detailed launch note for the API reviewers.",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("*** TASK Write Launch Note  :External:", org)
        self.assertIn("Write a detailed launch note for the API reviewers.", org)

    def test_next_step_short_label_body_inline_markdown_is_converted(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "- [ ] [External Owner] Write Launch Note: Include *risk*, _timing_, `parser`, and `--limit=4` notes.",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("*** TASK Write Launch Note  :External:", org)
        self.assertIn("Include /risk/, /timing/, =parser=, and ~--limit=4~ notes.", org)

    def test_next_step_decodes_html_entities(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "- [ ] Review A&amp;B: Confirm &quot;risk&quot; timing.",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("*** TODO Review A&B", org)
        self.assertIn('Confirm "risk" timing.', org)

    def test_checked_next_step_becomes_done_task(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [
                    "- [x] [Current User, External Owner] Archive launch notes.",
                ],
                "transcript": [],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = None
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** DONE Archive launch notes  :External:", org)
        self.assertIn(":ASSIGNEES: Current User, External Owner", org)

    def test_checked_next_step_can_be_shortened_as_done(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [
                    "- [x] [Current User] Archive the launch notes with supporting context that is too long for a good Org headline.",
                ],
                "transcript": [],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = self.make_shortener([
                "*** DONE Archive launch notes",
            ])
            converter.task_inferer = None
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** DONE Archive launch notes", org)
        self.assertIn(
            "Archive the launch notes with supporting context that is too long for a good",
            org,
        )
        self.assertIn("Org headline.", org)

    def test_multi_assignee_next_step_preserves_all_owners(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [
                    "- [ ] [Teammate One, Current User] Write a launch note.",
                ],
                "transcript": [],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = None
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** TODO Write a launch note  :Teammate:", org)
        self.assertIn(":ASSIGNEES: Teammate One, Current User", org)

    def test_first_name_current_assignee_becomes_todo(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [
                    "- [ ] [Current] Write a launch note.",
                ],
                "transcript": [],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = None
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** TODO Write a launch note", org)
        self.assertNotIn(":Current:", org)
        self.assertIn(":ASSIGNEES: Current", org)

    def test_will_style_current_assignee_preserves_owner_property(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [
                    "- [ ] Current User will write a launch note.",
                ],
                "transcript": [],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = None
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** TODO Write a launch note", org)
        self.assertIn(":ASSIGNEES: Current User", org)

    def test_will_style_current_first_name_preserves_owner_property(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [
                    "- [ ] Current will write a launch note.",
                ],
                "transcript": [],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = None
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** TODO Write a launch note", org)
        self.assertNotIn(":Current:", org)
        self.assertIn(":ASSIGNEES: Current", org)

    def test_will_style_external_assignee_preserves_owner_property(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [
                    "- [ ] Teammate Owner will write a launch note.",
                ],
                "transcript": [],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = None
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** TASK Write a launch note  :Teammate:", org)
        self.assertIn(":ASSIGNEES: Teammate Owner", org)

    def test_will_style_external_first_name_preserves_owner_property(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [
                    "- [ ] Teammate will write a launch note.",
                ],
                "transcript": [],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = None
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** TASK Write a launch note  :Teammate:", org)
        self.assertIn(":ASSIGNEES: Teammate", org)

    def test_checked_will_style_assignee_preserves_done_and_owner(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [
                    "- [x] Teammate Owner will archive launch notes.",
                ],
                "transcript": [],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = None
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** DONE Archive launch notes  :Teammate:", org)
        self.assertIn(":ASSIGNEES: Teammate Owner", org)

    def test_colon_style_current_assignee_preserves_owner_property(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [
                    "- [ ] Current User: Write a launch note.",
                ],
                "transcript": [],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = None
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** TODO Write a launch note", org)
        self.assertIn(":ASSIGNEES: Current User", org)

    def test_colon_style_external_assignee_preserves_owner_property(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [
                    "- [ ] Teammate Owner: Write a launch note.",
                ],
                "transcript": [],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = None
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** TASK Write a launch note  :Teammate:", org)
        self.assertIn(":ASSIGNEES: Teammate Owner", org)

    def test_unassigned_short_label_next_step_preserves_body(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "- [ ] Write Launch Note: Include risk, timing, and review context.",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("*** TODO Write Launch Note", org)
        self.assertIn("Include risk, timing, and review context.", org)
        self.assertNotIn("(Write Launch Note)", org)

    def test_non_current_multi_assignee_next_step_keeps_all_tags(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [
                    "- [ ] [Alice Owner and Bob Reviewer] Write a launch note.",
                ],
                "transcript": [],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = None
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** TASK Write a launch note  :Alice:Bob:", org)
        self.assertIn(":ASSIGNEES: Alice Owner, Bob Reviewer", org)

    def test_assignee_tags_are_sanitized_but_names_are_preserved(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [
                "- [ ] [Dr. Ada-Lovelace, O'Neil Reviewer] Review the launch note.",
            ],
            "transcript": [],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = None
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("*** TASK Review the launch note  :Ada:O:", org)
        self.assertIn(":ASSIGNEES: Dr. Ada-Lovelace, O'Neil Reviewer", org)

    def test_append_task_entry_sanitizes_existing_tags(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        output = []

        converter._append_task_entry(
            output,
            "TASK",
            "Review launch note",
            ["bad tag", "bad:tag", "bad tag"],
            None,
            "[2026-06-28 Sun]",
        )

        self.assertIn("*** TASK Review launch note  :bad_tag:", "\n".join(output))

    def test_task_headline_title_cannot_become_accidental_tags(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        output = []

        converter._append_task_entry(
            output,
            "TASK",
            "Review `launch` note :urgent:",
            ["owner"],
            None,
            "[2026-06-28 Sun]",
        )

        self.assertIn("*** TASK Review =launch= note :urgent:.  :owner:", "\n".join(output))

    def test_details_nested_bullets_remain_org_bullets(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "details": [
                "- **Architecture:** Review the interface.",
                "  - Preserve the nested point with `code` and [link](https://example.com).",
            ]
        }

        details = converter._convert_details()
        org = "\n".join(details)
        self.assertIn("- *Architecture:* Review the interface.", org)
        self.assertIn(
            "  - Preserve the nested point with =code= and [[https://example.com][link]].",
            org,
        )

    def test_details_nested_headings_remain_org_headings(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "details": [
                "#### **Open questions**",
                "Confirm `rollout` timing.",
            ]
        }

        details = converter._convert_details()
        org = "\n".join(details)
        self.assertIn("*** Open questions", org)
        self.assertIn("  Confirm =rollout= timing.", org)
        self.assertNotIn("####", org)

    def test_details_ordered_lists_remain_ordered(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "details": [
                "1. Confirm `parser` ownership.",
                "  2. Confirm release timing.",
            ]
        }

        org = "\n".join(converter._convert_details())
        self.assertIn("1. Confirm =parser= ownership.", org)
        self.assertIn("  2. Confirm release timing.", org)

    def test_details_deeply_nested_list_indentation_is_preserved(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "details": [
                "- Review the launch path.",
                "  - Confirm parser ownership.",
                "    - Capture rollback behavior.",
                "1. Document the release plan.",
                "  2. Confirm review timing.",
                "    3. Capture follow-up owner.",
            ]
        }

        org = "\n".join(converter._convert_details())
        self.assertIn("- Review the launch path.", org)
        self.assertIn("  - Confirm parser ownership.", org)
        self.assertIn("    - Capture rollback behavior.", org)
        self.assertIn("1. Document the release plan.", org)
        self.assertIn("  2. Confirm review timing.", org)
        self.assertIn("    3. Capture follow-up owner.", org)

    def test_decisions_section_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            input_file = Path(td) / "Meeting started 2026_06_25 12_57 PDT - Notes by Gemini.md"
            input_file.write_text(
                "# **Notes**\n\n"
                "### **Summary**\n\n"
                "The team reviewed the plan.\n\n"
                "### **Decisions**\n\n"
                "## Aligned\n\n"
                "* **Backend choice** Use one backend.\n\n"
                "We've **updated the Decisions section** using your feedback.\n\n"
                "Let us know what you think: [Helpful](https://example.com)\n\n"
                "### **Next steps**\n\n"
                "- [ ] [Current User] Write a rollout note.\n\n"
                "### **Details**\n\n"
                "- Additional context.\n\n"
                "# **Transcript**\n\n"
                "### **00:00:01**\n\n"
                "**Current User:** We aligned on the backend.\n",
                encoding="utf-8",
            )
            converter = self.mod.GeminiToOrgConverter(
                str(input_file),
                self.mod.ParticipantDatabase(str(Path(td) / "participants.json")),
            )
            converter._parse_filename()
            converter._read_content()
            converter._parse_content()

            org = converter._build_org_output()
            self.assertIn("** Decisions", org)
            self.assertIn("*** Aligned", org)
            self.assertIn("- *Backend choice* Use one backend.", org)
            self.assertNotIn("updated the Decisions section", org)
            self.assertNotIn("Let us know what you think", org)

    def test_unknown_note_section_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            input_file = Path(td) / "Meeting started 2026_06_25 12_57 PDT - Notes by Gemini.md"
            input_file.write_text(
                "# **Notes**\n\n"
                "## Team sync\n\n"
                "### **Summary**\n\n"
                "The team reviewed the plan.\n\n"
                "### **Risks**\n\n"
                "- **Schedule:** The API review may slip.\n"
                "  - Confirm the backup date with [Ops](https://example.com).\n\n"
                "#### Mitigation\n\n"
                "Use `feature flags` for the staged rollout.\n\n"
                "### **Next steps**\n\n"
                "- [ ] [Current User] Confirm the backup date.\n\n"
                "# **Transcript**\n\n"
                "### **00:00:01**\n\n"
                "**Current User:** We discussed schedule risk.\n",
                encoding="utf-8",
            )
            converter = self.mod.GeminiToOrgConverter(
                str(input_file),
                self.mod.ParticipantDatabase(str(Path(td) / "participants.json")),
            )
            converter._parse_filename()
            converter._read_content()
            converter._parse_content()

            org = converter._build_org_output()
            self.assertIn("** Risks", org)
            self.assertIn("- *Schedule:* The API review may slip.", org)
            self.assertIn(
                "  - Confirm the backup date with [[https://example.com][Ops]].",
                org,
            )
            self.assertIn("*** Mitigation", org)
            self.assertIn("Use =feature flags= for the staged rollout.", org)
            self.assertNotIn("** Team sync", org)

    def test_unknown_section_ordered_lists_remain_ordered(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        lines = [
            "1. Review *risk*.",
            "  2. Capture [notes](https://example.com).",
        ]

        org = "\n".join(converter._convert_structured_section_lines(lines))
        self.assertIn("1. Review /risk/.", org)
        self.assertIn("  2. Capture [[https://example.com][notes]].", org)

    def test_unknown_section_deeply_nested_lists_keep_indentation(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        lines = [
            "- Review the launch path.",
            "  - Confirm parser ownership.",
            "    - Capture rollback behavior.",
            "1. Document the release plan.",
            "  2. Confirm review timing.",
            "    3. Capture follow-up owner.",
        ]

        org = "\n".join(converter._convert_structured_section_lines(lines))
        self.assertIn("- Review the launch path.", org)
        self.assertIn("  - Confirm parser ownership.", org)
        self.assertIn("    - Capture rollback behavior.", org)
        self.assertIn("1. Document the release plan.", org)
        self.assertIn("  2. Confirm review timing.", org)
        self.assertIn("    3. Capture follow-up owner.", org)

    def test_note_sections_keep_source_order(self):
        with tempfile.TemporaryDirectory() as td:
            input_file = Path(td) / "Meeting started 2026_06_25 12_57 PDT - Notes by Gemini.md"
            input_file.write_text(
                "# **Notes**\n\n"
                "### **Summary**\n\n"
                "The team reviewed the plan.\n\n"
                "### **Next steps**\n\n"
                "- [ ] [Current User] Write the launch note.\n\n"
                "### **Details**\n\n"
                "- The launch note needs owner review.\n\n"
                "### **Open questions**\n\n"
                "- Who reviews the final note?\n\n"
                "# **Transcript**\n\n"
                "### **00:00:01**\n\n"
                "**Current User:** We discussed the launch note.\n",
                encoding="utf-8",
            )
            converter = self.mod.GeminiToOrgConverter(
                str(input_file),
                self.mod.ParticipantDatabase(str(Path(td) / "participants.json")),
            )
            converter._parse_filename()
            converter._read_content()
            converter._parse_content()

            org = converter._build_org_output()
            next_steps_pos = org.index("** Suggested next steps")
            details_pos = org.index("** Details")
            open_questions_pos = org.index("** Open questions")
            transcript_pos = org.index("* Transcript")
            self.assertLess(next_steps_pos, details_pos)
            self.assertLess(details_pos, open_questions_pos)
            self.assertLess(open_questions_pos, transcript_pos)

    def test_transcript_cleanup_requires_speaker_turns(self):
        cleaner = self.make_cleaner("")
        with self.assertRaisesRegex(ValueError, "Could not find speaker turns"):
            cleaner._clean_single("### **00:00:01**\n\nNo attributed speaker line.")

    def test_transcript_cleanup_preserves_speaker_turns(self):
        original = (
            "### **00:38:52**\n\n"
            "**Speaker One:** Exactly.\n\n"
            "**Speaker Two:** approved.\n\n"
            "**Speaker One:** This is speaker one's long statement.\n\n"
            "**Speaker Two:** Yeah.\n"
        )
        response = (
            '<turn id="T0001">Exactly.</turn>\n'
            '<turn id="T0002">Approved.</turn>\n'
            '<turn id="T0003">This is speaker one\'s long statement.</turn>\n'
            '<turn id="T0004">Yeah.</turn>'
        )
        cleaned = self.make_cleaner(response)._clean_single(original)
        self.assertIn("**Speaker Two:** Approved.", cleaned)
        self.assertIn("**Speaker One:** This is speaker one's long statement.", cleaned)
        self.assertEqual(
            self.mod.TranscriptCleaner.__new__(self.mod.TranscriptCleaner)
            ._speaker_attributions(cleaned),
            ["Speaker One", "Speaker Two", "Speaker One", "Speaker Two"],
        )

    def test_transcript_cleanup_accepts_speaker_bold_name_variant(self):
        original = (
            "### **00:38:52**\n\n"
            "**Speaker One**: exactly.\n\n"
            "**Speaker Two**: approved.\n"
        )
        response = (
            '<turn id="T0001">Exactly.</turn>\n'
            '<turn id="T0002">Approved.</turn>'
        )
        cleaned = self.make_cleaner(response)._clean_single(original)
        self.assertIn("**Speaker One**: Exactly.", cleaned)
        self.assertIn("**Speaker Two**: Approved.", cleaned)
        self.assertEqual(
            self.mod.TranscriptCleaner.__new__(self.mod.TranscriptCleaner)
            ._speaker_attributions(cleaned),
            ["Speaker One", "Speaker Two"],
        )

    def test_transcript_cleanup_rejects_moved_text(self):
        original = (
            "### **00:38:52**\n\n"
            "**Speaker One:** Exactly.\n\n"
            "**Speaker Two:** approved.\n\n"
            "**Speaker One:** This is speaker one's long statement.\n\n"
            "**Speaker Two:** Yeah.\n"
        )
        response = (
            '<turn id="T0001">Exactly.</turn>\n'
            '<turn id="T0002">This is speaker one\'s long statement that moved under speaker two.</turn>\n'
            '<turn id="T0003">This is speaker one\'s long statement.</turn>\n'
            '<turn id="T0004">Yeah.</turn>'
        )
        with self.assertRaisesRegex(ValueError, "expanded short transcript turn"):
            self.make_cleaner([response, response])._clean_single(original)

    def test_transcript_cleanup_retries_invalid_turn_response(self):
        original = (
            "### **00:38:52**\n\n"
            "**Speaker One:** Exactly.\n\n"
            "**Speaker Two:** approved.\n"
        )
        bad_response = (
            '<turn id="T0001">Exactly.</turn>\n'
            '<turn id="T0002">This incorrectly expanded a short turn into a full sentence.</turn>'
        )
        good_response = (
            '<turn id="T0001">Exactly.</turn>\n'
            '<turn id="T0002">Approved.</turn>'
        )
        cleaned = self.make_cleaner([bad_response, good_response])._clean_single(original)
        self.assertIn("**Speaker Two:** Approved.", cleaned)

    def test_transcript_end_marker_is_preserved(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.transcript_cleaner = None
        converter.sections = {
            "transcript": [
                "### **00:00:01** {#00:00:01}",
                "**Current User:** Review the launch note.",
                "### **Transcription ended after 00:00:09**",
            ]
        }

        org = "\n".join(converter._convert_transcript())
        self.assertIn("** 00:00:01", org)
        self.assertIn(":CUSTOM_ID: 00:00:01", org)
        self.assertIn("*Current User:* Review the launch note.", org)
        self.assertIn("** Transcription ended after 00:00:09", org)

    def test_transcript_timestamp_heading_variants_are_preserved(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.transcript_cleaner = None
        converter.sections = {
            "transcript": [
                "## **00:00:01** {#00:00:01}",
                "**Current User:** Review the launch note.",
                "#### 00:00:02",
                "**Second Speaker:** Confirm the release plan.",
                "## **Transcription ended after 00:00:09**",
            ]
        }

        org = "\n".join(converter._convert_transcript())
        self.assertIn("** 00:00:01", org)
        self.assertIn(":CUSTOM_ID: 00:00:01", org)
        self.assertIn("*Current User:* Review the launch note.", org)
        self.assertIn("** 00:00:02", org)
        self.assertIn(":CUSTOM_ID: 00:00:02", org)
        self.assertIn("*Second Speaker:* Confirm the release plan.", org)
        self.assertIn("** Transcription ended after 00:00:09", org)

    def test_transcript_empty_timestamp_chunk_is_preserved(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.transcript_cleaner = None
        converter.sections = {
            "transcript": [
                "### **00:00:01** {#00:00:01}",
                "### **00:00:02** {#00:00:02}",
                "**Current User:** Review the launch note.",
            ]
        }

        org = "\n".join(converter._convert_transcript())
        self.assertIn("** 00:00:01", org)
        self.assertIn(":CUSTOM_ID: 00:00:01", org)
        self.assertIn("** 00:00:02", org)
        self.assertIn(":CUSTOM_ID: 00:00:02", org)
        self.assertIn("*Current User:* Review the launch note.", org)

    def test_transcript_speaker_bold_name_variant_is_converted(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.transcript_cleaner = None
        converter.sections = {
            "transcript": [
                "### **00:00:01** {#00:00:01}",
                "**Current User**: Review the launch note.",
                "**Second Speaker**: Confirm the release plan.",
            ]
        }

        org = "\n".join(converter._convert_transcript())
        self.assertIn("*Current User:* Review the launch note.", org)
        self.assertIn("*Second Speaker:* Confirm the release plan.", org)

    def test_transcript_text_inline_markdown_is_converted(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.transcript_cleaner = None
        converter.sections = {
            "transcript": [
                "### **00:00:01** {#00:00:01}",
                "**Current User:** Review *risk*, _timing_, `parser`, and [notes](https://example.com).",
                "Then preserve *details* and `foo_bar` in continuation text.",
            ]
        }

        org = "\n".join(converter._convert_transcript())
        self.assertIn("*Current User:* Review /risk/, /timing/, =parser=, and", org)
        self.assertIn("[[https://example.com][notes]].", org)
        self.assertIn(
            "Then preserve /details/ and =foo_bar= in continuation text.",
            org,
        )

    def test_transcript_decodes_html_entities(self):
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.transcript_cleaner = None
        converter.sections = {
            "transcript": [
                "### **00:00:01** {#00:00:01}",
                "**Current User:** Review A&amp;B and &quot;risk&quot;.",
            ]
        }

        org = "\n".join(converter._convert_transcript())
        self.assertIn('*Current User:* Review A&B and "risk".', org)

    def test_chunked_cleanup_fails_closed(self):
        class FailingCleaner(self.mod.TranscriptCleaner):
            def __init__(self):
                self.max_chunk_size = 1
                self.chunk_target_size = 120

            def _clean_single(self, text, verbose=False):
                if "section 2" in text:
                    raise ValueError("bad cleanup")
                return text

        transcript = "\n".join(
            f"### **00:00:0{i}** {{#00:00:0{i}}}\n**A:** section {i}."
            for i in range(4)
        )
        with self.assertRaisesRegex(ValueError, "bad cleanup"):
            FailingCleaner()._clean_chunked(transcript)

    def test_chunked_cleanup_requires_timestamp_sections(self):
        cleaner = self.mod.TranscriptCleaner.__new__(self.mod.TranscriptCleaner)
        with self.assertRaisesRegex(ValueError, "Could not find timestamp sections"):
            cleaner._clean_chunked("No timestamp headings here.")

    def test_chunked_cleanup_accepts_timestamp_heading_variants(self):
        class EchoCleaner(self.mod.TranscriptCleaner):
            def __init__(self):
                self.chunk_target_size = 10000

            def _clean_single(self, text, verbose=False):
                return text

        transcript = (
            "## **00:00:01** {#00:00:01}\n\n"
            "**Current User:** Review the launch note.\n\n"
            "#### 00:00:02\n\n"
            "**Second Speaker:** Confirm the release plan.\n"
        )

        cleaned = EchoCleaner()._clean_chunked(transcript)
        self.assertIn("## **00:00:01** {#00:00:01}", cleaned)
        self.assertIn("#### 00:00:02", cleaned)

    def test_task_inference_errors_propagate(self):
        class FailingInferer:
            def infer_additional_tasks(self, transcript_text, gemini_tasks, verbose=False):
                raise ValueError("task inference failed")

        with tempfile.TemporaryDirectory() as td:
            input_file = Path(td) / "Meeting started 2026_06_25 12_57 PDT - Notes by Gemini.md"
            input_file.write_text("", encoding="utf-8")
            converter = self.mod.GeminiToOrgConverter(
                str(input_file),
                self.mod.ParticipantDatabase(str(Path(td) / "participants.json")),
                task_inferer=FailingInferer(),
            )
            converter._parse_filename()
            converter.sections["next_steps"] = ["- [ ] [Current User] Review task inference."]
            converter.sections["transcript"] = [
                "### **00:00:01**",
                "**Current User:** Please review task inference.",
            ]
            with self.assertRaisesRegex(ValueError, "task inference failed"):
                converter._convert_next_steps()

    def test_task_inference_chunks_large_transcript(self):
        inferer = self.mod.TranscriptTaskInferer.__new__(self.mod.TranscriptTaskInferer)
        inferer.prompt_template = "Infer tasks:\n{{SOURCE_TEXT}}"
        inferer.infer_chunk_target_chars = 4000
        calls = []

        def record_call(prompt, max_tokens=12000):
            calls.append(prompt)
            return f"* TODO Review chunk {len(calls)}"

        inferer._call_model = record_call
        transcript = "\n\n".join(
            f"### **00:{index // 60:02d}:{index % 60:02d}**\n"
            f"**A:** Review parser item {index}. " + ("Details. " * 10)
            for index in range(1, 90)
        )

        inferred = inferer.infer_transcript_tasks(transcript)

        self.assertGreater(len(calls), 1)
        self.assertTrue(all(len(call) <= 4100 for call in calls))
        self.assertIn("* TODO Review chunk 1", inferred)
        self.assertIn(f"* TODO Review chunk {len(calls)}", inferred)

    def test_task_selection_uses_compact_transcript_evidence(self):
        inferer = self.mod.TranscriptTaskInferer.__new__(self.mod.TranscriptTaskInferer)
        inferer.selection_evidence_max_chars = 4000
        inferer.selection_evidence_snippet_chars = 500
        prompts = []

        def no_model_selection(prompt, max_tokens=8000):
            prompts.append(prompt)
            return "No additional tasks identified."

        inferer._call_model = no_model_selection
        transcript = (
            ("irrelevant filler\n\n" * 500)
            + "### **00:04:00**\n"
            + "**A:** We need to review the parser rollback checklist.\n"
        )
        inferred_text = "* TODO Review parser rollback checklist"

        selected = inferer.select_additional_tasks(transcript, [], inferred_text)

        self.assertEqual([entry.title for entry in selected], ["Review parser rollback checklist"])
        self.assertEqual(len(prompts), 1)
        self.assertLess(len(prompts[0]), 6000)
        self.assertIn("review the parser rollback checklist", prompts[0])
        self.assertNotIn("irrelevant filler\n\nirrelevant filler\n\nirrelevant filler", prompts[0])

    def test_task_inference_selector_keeps_grounded_missing_candidate(self):
        inferer = self.mod.TranscriptTaskInferer.__new__(self.mod.TranscriptTaskInferer)

        def no_model_selection(prompt, max_tokens=8000):
            return "No additional tasks identified."

        inferer._call_model = no_model_selection
        inferred_text = (
            "* TODO Schedule follow-up meeting with team\n"
            "* TODO Review parser rollback checklist\n"
            "* TODO Investigate imaginary cache daemon\n"
        )

        selected = inferer.select_additional_tasks(
            "We need to review the parser rollback checklist.",
            ["[Current User] Schedule follow-up meeting: Discuss parser timing."],
            inferred_text,
        )

        self.assertEqual([entry.title for entry in selected], ["Review parser rollback checklist"])

    def test_inferred_task_extra_body_lines_are_preserved(self):
        class FakeInferer:
            def infer_additional_tasks(self, transcript_text, gemini_tasks, verbose=False):
                return [
                    self_mod.OrgTaskEntry(
                        keyword="TASK",
                        title="Review inferred follow-up",
                        extra_lines=[
                            "SCHEDULED: <2026-06-30 Tue>",
                            "- Include *risk* and `parser` notes.",
                            "  - Preserve nested *context* and `flags`.",
                        ],
                    )
                ]

        self_mod = self.mod
        converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
        converter.sections = {
            "next_steps": [],
            "transcript": [
                "### **00:00:01**",
                "**Current User:** Please review the inferred follow-up.",
            ],
        }
        converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
        converter.todo_shortener = None
        converter.task_inferer = FakeInferer()
        converter.verbose = False

        org = "\n".join(converter._convert_next_steps())
        self.assertIn("*** TASK Review inferred follow-up", org)
        self.assertIn("SCHEDULED: <2026-06-30 Tue>", org)
        self.assertIn("- Include /risk/ and =parser= notes.", org)
        self.assertIn("  - Preserve nested /context/ and =flags=.", org)
        self.assertLess(org.index("SCHEDULED:"), org.index(":PROPERTIES:"))

    def test_inferred_waiting_task_preserves_waiting_state(self):
        class FakeInferer:
            def infer_additional_tasks(self, transcript_text, gemini_tasks, verbose=False):
                return [
                    self_mod.OrgTaskEntry(
                        keyword="WAITING",
                        title="[External Owner, Current User] Wait for review",
                    )
                ]

        self_mod = self.mod
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [],
                "transcript": [
                    "### **00:00:01**",
                    "**Current User:** We need to wait for review.",
                ],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = FakeInferer()
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** WAITING Wait for review  :External:", org)
        self.assertIn(":ASSIGNEES: External Owner, Current User", org)
        self.assertNotIn(":Current:", org)

    def test_inferred_done_task_preserves_done_state(self):
        class FakeInferer:
            def infer_additional_tasks(self, transcript_text, gemini_tasks, verbose=False):
                return [
                    self_mod.OrgTaskEntry(
                        keyword="DONE",
                        title="[Current User] Archive completed notes",
                    )
                ]

        self_mod = self.mod
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            converter.sections = {
                "next_steps": [],
                "transcript": [
                    "### **00:00:01**",
                    "**Current User:** The notes are archived.",
                ],
            }
            converter.metadata = {"date": datetime(2026, 6, 25, 12, 57)}
            converter.todo_shortener = None
            converter.task_inferer = FakeInferer()
            converter.verbose = False

            org = "\n".join(converter._convert_next_steps())
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertIn("*** DONE Archive completed notes", org)
        self.assertIn(":ASSIGNEES: Current User", org)
        self.assertNotIn(":Current:", org)

    def test_inferred_multi_assignee_task_preserves_all_owners(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            entry = self.mod.OrgTaskEntry(
                keyword="TASK",
                title="[Alice Owner, Current User] Confirm rollout plan",
            )
            normalized = converter._normalize_inferred_task_entry(entry)
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertEqual(normalized.keyword, "TODO")
        self.assertEqual(normalized.title, "Confirm rollout plan")
        self.assertEqual(normalized.tags, ["Alice"])
        self.assertEqual(
            normalized.properties,
            {"ASSIGNEES": "Alice Owner, Current User"},
        )

    def test_inferred_assignees_property_current_user_becomes_todo(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            entry = self.mod.OrgTaskEntry(
                keyword="TASK",
                title="Confirm rollout plan",
                properties={"ASSIGNEES": "Alice Owner, Current User"},
            )
            normalized = converter._normalize_inferred_task_entry(entry)
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertEqual(normalized.keyword, "TODO")
        self.assertEqual(normalized.title, "Confirm rollout plan")
        self.assertEqual(normalized.tags, ["Alice"])
        self.assertEqual(
            normalized.properties,
            {"ASSIGNEES": "Alice Owner, Current User"},
        )

    def test_inferred_assignees_property_external_owner_stays_task(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            entry = self.mod.OrgTaskEntry(
                keyword="TODO",
                title="Confirm rollout plan",
                properties={"ASSIGNEES": "External Owner"},
            )
            normalized = converter._normalize_inferred_task_entry(entry)
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertEqual(normalized.keyword, "TASK")
        self.assertEqual(normalized.tags, ["External"])
        self.assertEqual(normalized.properties, {"ASSIGNEES": "External Owner"})

    def test_inferred_assignees_property_preserves_waiting_state(self):
        old_name = self.mod.CURRENT_USER_NAME
        self.mod.CURRENT_USER_NAME = "Current User"
        try:
            converter = self.mod.GeminiToOrgConverter.__new__(self.mod.GeminiToOrgConverter)
            entry = self.mod.OrgTaskEntry(
                keyword="WAITING",
                title="Wait for review",
                properties={"ASSIGNEES": "External Owner, Current User"},
            )
            normalized = converter._normalize_inferred_task_entry(entry)
        finally:
            self.mod.CURRENT_USER_NAME = old_name

        self.assertEqual(normalized.keyword, "WAITING")
        self.assertEqual(normalized.tags, ["External"])
        self.assertEqual(
            normalized.properties,
            {"ASSIGNEES": "External Owner, Current User"},
        )


if __name__ == "__main__":
    unittest.main()
