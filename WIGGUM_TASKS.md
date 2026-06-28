# Wiggum Task State

## Objective

Continue improving the maintained Gemini-to-Org transcript conversion scripts in
`~/src/scripts`, with the original fess-reported cleanup set, follow-on
preservation audit, and batch-wrapper failure addressed.

## Done

- Made AI-backed features fail closed instead of silently falling back.
- Removed hardcoded local endpoint and placeholder API key from the batch wrapper.
- Required an explicit API key when AI-backed conversion features are enabled.
- Kept hosted Anthropic API URLs rejected.
- Required configured vocabulary files to exist and added a default vocabulary TSV.
- Preserved transcript timestamp and speaker structure during cleanup with
  validation and a strict retry.
- Propagated transcript task inference failures instead of dropping inferred work.
- Propagated participant database load/save failures.
- Removed the stale handoff document that contained obsolete context.
- Prevented CLI help from displaying an environment-derived API key.
- Made transcript cleanup fail if there are no speaker turns to preserve.
- Preserved internal articles in task titles so action wording remains natural
  and faithful.
- Preserved nested supporting bullets under Gemini next-step checkboxes by
  carrying them into the generated Org task body.
- Preserved nested bullets in the Details section as real nested Org bullets
  instead of indented plain text.
- Preserved Gemini Decisions sections as first-class Org sections, including
  subsection headings such as "Aligned", while still removing Google feedback
  boilerplate.
- Preserved future or otherwise unrecognized Gemini note sections as Org
  sections once structured meeting content has begun, without treating document
  title headings as content.
- Preserved nested Markdown headings inside Details as Org headings instead of
  emitting raw Markdown heading syntax.
- Preserved source order for non-summary note sections, so Gemini sections such
  as Decisions, Suggested next steps, Details, and future extra sections are
  emitted in the order they appeared before the transcript.
- Preserved all Gemini next-step assignees in an `ASSIGNEES` property. Shared
  tasks that include the configured current user now become actionable `TODO`
  entries while retaining the other assignees as tags.
- Used Gemini's short `Title: Description` next-step labels as Org task
  headlines while preserving the full description in the task body, producing
  clearer actionable task lists without losing detail.
- Applied the same multi-assignee ownership preservation to AI-inferred
  transcript tasks, so inferred `[A, Current User]` tasks become actionable
  `TODO` entries with complete `ASSIGNEES` metadata.
- Preserved checked Gemini next-step checkboxes (`[x]`/`[X]`) as `DONE` Org
  tasks instead of dropping them, including assignee metadata.
- Sanitized assignee-derived Org tags and any model-provided tags before adding
  them to headlines, while keeping full assignee names intact in properties.
- Formatted task headline titles at the final render point so inline Markdown is
  converted and title text that looks like trailing Org tags cannot be
  misinterpreted as metadata.
- Converted inline italic Markdown (`*text*` and `_text_`) to Org emphasis and
  routed summary conversion through the shared inline converter, preserving bold
  summary topic labels plus links/code/emphasis consistently.
- Preserved underscore-delimited technical identifiers during inline Markdown
  conversion while still converting intended `_italic_` prose to Org emphasis.
- Preserved Markdown ordered lists in Details, Decisions/extra sections, and
  next-step task detail bodies as Org ordered lists.
- Preserved the Gemini transcript terminal marker, such as `Transcription ended
  after HH:MM:SS`, as a final transcript subheading instead of dropping it.
- Routed preserved next-step detail body lines through the shared inline
  Markdown converter so emphasis, code, and links are rendered consistently.
- Protected inline code spans before emphasis conversion so code-like text such
  as `` `foo*bar*` `` is not accidentally interpreted as Markdown emphasis.
- Routed task body descriptions through the shared inline Markdown converter so
  `Short label: Description` next-step bodies render emphasis, code, and links
  consistently.
- Routed transcript speaker turns and continuation lines through the shared
  inline Markdown converter so transcript emphasis, code, and links render
  consistently with notes and tasks.
- Preserved non-scheduling body lines returned with AI-inferred transcript tasks
  instead of keeping only `SCHEDULED`/`DEADLINE` metadata, formatting those
  lines with the same task-detail Markdown handling.
- Used Org's alternate inline-code delimiter for Markdown code spans containing
  `=`, so command flags and assignments such as `` `--limit=4` `` render as
  valid Org markup.
- Kept Gemini next-step text in raw Markdown form until final task rendering, so
  code spans in task descriptions are not damaged before the shared inline
  converter can choose the correct Org delimiter.
- Treated a single-token assignee matching the configured current user's first
  name as the current user, so first-name Gemini assignments become actionable
  `TODO` entries instead of external `TASK` entries.
- Preserved `WAITING` on AI-inferred transcript tasks during assignee
  normalization, while still retaining full assignee metadata and non-current
  assignee tags.
- Accepted shortened `DONE` and `WAITING` headlines from the local title
  shortener, so long checked Gemini items can be shortened without losing their
  completed state or failing model-response validation.
- Converted underscore-bold Markdown (`__text__`) in shared inline prose without
  corrupting underscore-delimited identifiers, and recognized `__topic__`
  summary headings as description-list topics.
- Preserved unmatched backticks as literal text instead of converting them into
  unmatched Org code delimiters, while still converting paired Markdown code
  spans through the shared inline-code formatter.
- Converted Markdown links with balanced parentheses in the URL without
  truncating the target at the first `)`, preserving links such as
  `[notes](https://example.com/a_(b))`.
- Parsed and preserved `DONE` in AI-inferred Org task entries, including
  priorities, tags, properties, and body lines, and kept `DONE` from being
  downgraded during assignee normalization.
- Preserved indentation for nested body bullets on AI-inferred transcript tasks
  instead of flattening all preserved model-provided body lines.
- Preserved relative indentation for nested Gemini next-step detail bullets and
  ordered items instead of flattening deeper supporting structure.
- Preserved deeper nested list indentation in Details and future/unknown note
  sections for both unordered and ordered lists.
- Accepted transcript timestamp headings and transcript end markers across
  Markdown heading levels, including the chunked cleanup path, so variant
  exports do not drop timestamped turns.
- Preserved ordered Markdown checkbox items in Suggested next steps as Org
  tasks, including checked-state handling, assignee metadata, and supporting
  detail indentation relative to the ordered-list marker.
- Preserved full assignee metadata for unbracketed "Name will ..." suggested
  next steps instead of reducing ownership to only a tag.
- Preserved first-name shorthand ownership for unbracketed "Name will ..."
  suggested next steps, including current-user and external-owner cases.
- Preserved full assignee metadata for unbracketed "Name: task" suggested next
  steps when the prefix is clearly an assignee, while treating non-owner
  "Short label: description" next steps as readable headlines with preserved
  body text.
- Preserved plain top-level unordered and ordered list items in Suggested next
  steps as open Org tasks, while still keeping nested list items as supporting
  task body details.
- Accepted the common `**Speaker**: text` transcript attribution variant in
  cleanup extraction, cleanup validation, and no-LLM transcript rendering.
- Normalized AI-inferred tasks using an existing `ASSIGNEES` property even when
  the task title has no bracketed owner prefix, so current-user tasks become
  actionable and external-owner tags are retained.
- Decoded HTML entities through the shared inline text conversion, so
  summaries, tasks, and transcript text do not keep exported entity artifacts.
- Preserved timestamp headings and anchors even when a transcript timestamp
  chunk has no speaker text.
- Preserved Markdown bullet and ordered-list structure inside Summary content
  instead of wrapping list markers into plain paragraphs.
- Made the batch wrapper default to preserving raw transcript text while still
  using the local model to infer missing transcript tasks.
- Let the batch wrapper opt into every local model feature with
  `GEMINI_TO_ORG_USE_LLM=1`, or disable task inference with
  `GEMINI_TO_ORG_INFER_TRANSCRIPT_TASKS=0`.
- Let the batch wrapper supply a non-secret local auth value for loopback model
  endpoints when no auth value is already configured.
- Made the batch wrapper print converter error details and exit nonzero when a
  file conversion fails.
- Added local duplicate and source-grounding checks for inferred transcript
  task candidates when the model selector returns no additions.
- Added regression tests for the above behaviors.

## Current Verification

- Unit tests passed: `python3 -m unittest /Users/johnw/src/scripts/test_gemini_to_org.py`
  (88 tests)
- Syntax checks passed:
  - `python3 -m py_compile /Users/johnw/src/scripts/gemini_to_org.py /Users/johnw/src/scripts/test_gemini_to_org.py`
  - `bash -n /Users/johnw/src/scripts/convert_all_gemini_notes.sh`
- Sensitive-term sweep passed across the maintained script, wrapper, tests,
  vocabulary file, and handoff document.
- A tiny wrapper end-to-end conversion passed with an explicit local test API
  key supplied through the environment.
- A strict conversion of the sample transcript completed with transcript task
  inference disabled:
  - 71 timestamps preserved, all unique.
  - 828 speaker turns preserved in the same order.
  - No warning or error output.
  - No context marker leaked into the generated Org.
  - Vocabulary replacements applied to the generated Org.
- Structural comparison against the existing best conversion showed the same
  timestamp count, speaker-turn count, task count, and speaker sequence.
- The previously risky transcript excerpt now preserves the long statement
  under the original speaker attribution, matching the baseline speaker
  sequence.
- A no-LLM sample conversion of the same export also completed successfully:
  71 timestamps, 828 speaker turns, 3 tasks, Decisions/Aligned preserved, and
  vocabulary replacements applied. The sample contains 47 timestamp links and
  71 timestamp `CUSTOM_ID` targets. Document title headings were not emitted as
  extra note sections. Section order matched the Gemini export before the
  transcript. With `GEMINI_TO_ORG_USER_NAME` configured, the shared sample task
  is emitted as a `TODO`, tagged with the other assignee, and preserves both
  assignees in properties. Gemini's short next-step labels are used as
  readable task headlines, with full descriptions preserved below them. The
  sample has no checked next-step items, so the new checked-item path does not
  change its open task counts. Existing sample tags remain stable after tag
  sanitization, headline-title formatting, inline Markdown conversion, and
  ordered-list preservation. The latest inline Markdown regression also
  confirms underscore identifiers are not converted into accidental emphasis.
  The source transcript end marker is now preserved as a final transcript
  subheading without changing timestamp or speaker-turn counts. The latest
  inline-code, task-body Markdown, and transcript-text Markdown regressions do
  not change the sample's structural counts. The inferred-task body preservation
  fix is covered by unit tests and does not affect the no-LLM sample path. Code
  spans containing `=` now use the alternate Org code delimiter without changing
  the sample's structural counts. First-name current-user assignee matching is
  covered by unit tests; the sample uses full names and remains structurally
  stable. AI-inferred `WAITING` task preservation is covered by unit tests and
  does not affect the no-LLM sample path. DONE-title shortening is covered by
  unit tests and does not affect the no-LLM sample path. Underscore-bold
  conversion is covered by unit tests and does not change the sample's
  structural counts. Unmatched-backtick preservation and parenthesized-link URL
  preservation are covered by unit tests and do not change the sample's
  structural counts. AI-inferred `DONE` task parsing and normalization are
  covered by unit tests and do not affect the no-LLM sample path. Nested
  inferred-task body bullet preservation is covered by unit tests and does not
  affect the no-LLM sample path. Nested next-step detail indentation
  preservation is covered by unit tests and does not change the sample's
  structural counts. Deeper nested list indentation in Details and
  future/unknown note sections is covered by unit tests and does not change the
  sample's structural counts. Variant transcript timestamp heading levels and
  transcript end-marker heading levels are covered by unit tests and do not
  change the sample's structural counts. Ordered checkbox items in Suggested
  next steps are covered by unit tests and do not change the sample's
  structural counts. Full owner preservation for unbracketed "Name will ..."
  suggested next steps is covered by unit tests and does not change the sample's
  structural counts. First-name shorthand owner preservation for unbracketed
  "Name will ..." suggested next steps is covered by unit tests and does not
  change the sample's structural counts. Unbracketed "Name: task" owner
  preservation and non-owner short-label body preservation are covered by unit
  tests and do not change the sample's structural counts. Plain unordered and
  ordered list items in Suggested next steps are covered by unit tests and do
  not change the sample's structural counts. Alternate transcript speaker
  attribution formatting is covered by unit tests and does not change the
  sample's structural counts. Property-based ownership normalization for
  AI-inferred tasks is covered by unit tests and does not affect the no-LLM
  sample path. HTML entity decoding is covered by unit tests and does not
  change the sample's structural counts. Empty transcript timestamp chunk
  preservation is covered by unit tests and does not change the sample's
  structural counts. Summary list preservation is covered by unit tests and
  does not change the sample's structural counts. The batch wrapper now
  succeeds from the download directory with no extra environment setup,
  producing one Org file from the sample export. The produced Org keeps 71
  timestamps, 71 timestamp targets, 828 speaker turns, the source speaker
  sequence, 47 timestamp links, additional inferred tasks beyond the original
  action items, Decisions/Aligned, Details, and the transcript end marker. The
  latest verified run produced 7 total tasks.

## Remaining

- No known remaining issues from the original fess cleanup set, the follow-on
  preservation audit, or the batch-wrapper failure reported from the download
  directory.
- Future work should be driven by new real exports or newly observed
  model-output failures rather than any currently known defect.

## Recovery Commands

```sh
cd /Users/johnw/src/scripts
python3 -m unittest /Users/johnw/src/scripts/test_gemini_to_org.py
python3 -m py_compile /Users/johnw/src/scripts/gemini_to_org.py /Users/johnw/src/scripts/test_gemini_to_org.py
bash -n /Users/johnw/src/scripts/convert_all_gemini_notes.sh
# Also run a stale-behavior search over the script, wrapper, vocabulary, and tests.
```
