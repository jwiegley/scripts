#!/usr/bin/env bash
set -euo pipefail
# Batch convert all Gemini meeting notes in a directory

# Usage: ./convert_all_gemini_notes.sh [directory]
# If no directory specified, uses current directory
# Batch mode preserves transcript text by default while inferring missing tasks
# through LiteLLM. Task headline generation still uses the configured Claude
# endpoint. Set GEMINI_TO_ORG_USE_LLM=1 to enable every local model feature.
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
infer_transcript_tasks=1
if [ "${GEMINI_TO_ORG_USE_LLM:-0}" = "1" ]; then
	converter_args=()
else
	converter_args=(
		--no-shorten-tasks
		--no-clean-transcript
	)
	if [ "${GEMINI_TO_ORG_INFER_TRANSCRIPT_TASKS:-1}" = "0" ]; then
		converter_args+=(--no-infer-transcript-tasks)
		infer_transcript_tasks=0
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

converter_command=("$CONVERTER")
if [ "$infer_transcript_tasks" = "1" ]; then
	if [ -z "${GEMINI_TO_ORG_INFER_CA_BUNDLE:-}" ] && \
		[ -n "${SSL_CERT_FILE:-}" ]; then
		export GEMINI_TO_ORG_INFER_CA_BUNDLE="$SSL_CERT_FILE"
	fi
	if [ -z "${LITELLM_API_KEY:-}" ]; then
		litellm_wrapper="${GEMINI_TO_ORG_LITELLM_WRAPPER:-$HOME/.local/bin/agent-deck-litellm-env}"
		if [ ! -x "$litellm_wrapper" ]; then
			echo "Error: LiteLLM credential wrapper is unavailable: $litellm_wrapper" >&2
			exit 1
		fi
		converter_command=("$litellm_wrapper" "$CONVERTER")
	fi
fi

exec "${converter_command[@]}" --batch "${converter_args[@]}" "${files[@]}"
