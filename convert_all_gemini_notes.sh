#!/usr/bin/env bash
set -euo pipefail
# Batch convert all Gemini meeting notes in a directory

# Usage: ./convert_all_gemini_notes.sh [directory]
# If no directory specified, uses current directory
# Batch mode preserves transcript text by default while inferring missing tasks
# through the direct local oMLX endpoint. Task headline generation uses the same
# route. Set GEMINI_TO_ORG_USE_LLM=1 to enable every local model feature.
# GEMINI_TO_ORG_INFER_TRANSCRIPT_TASKS=0 disables task inference (only when
# GEMINI_TO_ORG_USE_LLM is unset); GEMINI_TO_ORG_RETITLE_TASKS=0 disables
# headline generation in either mode.

DIR="${1:-.}"
SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
CONVERTER="$SCRIPT_DIR/gemini_to_org.py"

if [ ! -f "$CONVERTER" ]; then
	echo "Error: expected converter at $CONVERTER"
	exit 1
fi

converter_args=()
if [ "${GEMINI_TO_ORG_USE_LLM:-0}" = "1" ]; then
	converter_args=()
else
	converter_args=(
		--no-shorten-tasks
		--no-clean-transcript
	)
	if [ "${GEMINI_TO_ORG_INFER_TRANSCRIPT_TASKS:-1}" = "0" ]; then
		converter_args+=(--no-infer-transcript-tasks)
	fi
fi

if [ "${GEMINI_TO_ORG_RETITLE_TASKS:-1}" = "0" ]; then
	converter_args+=(--no-retitle-tasks)
fi

if [ "${GEMINI_TO_ORG_ALLOW_REMOTE_ENDPOINT:-0}" = "1" ]; then
	converter_args+=(--allow-remote-endpoint)
fi

if [ "${GEMINI_TO_ORG_FORCE:-0}" = "1" ]; then
	converter_args+=(--force)
fi

base_url="${CLAUDE_BASE_URL:-http://localhost:8317}"
if [ -z "${CLAUDE_API_KEY:-}" ]; then
	case "$base_url" in
	http://localhost | http://localhost:* | http://127.0.0.1 | http://127.0.0.1:* | http://\[::1\] | http://\[::1\]:*)
		export CLAUDE_API_KEY="${GEMINI_TO_ORG_LOCAL_AUTH:-local-endpoint}"
		;;
	esac
fi

echo "Converting Gemini notes in: $DIR"
echo "======================================"
echo ""

shopt -s nullglob
files=("$DIR"/*"Notes by Gemini.md")
if [ "${#files[@]}" -eq 0 ]; then
	echo "======================================"
	echo "Summary:"
	echo "  Converted: 0"
	echo "  Skipped:   0"
	echo "  Errors:    0"
	exit 0
fi

exec "$CONVERTER" --batch "${converter_args[@]}" "${files[@]}"
