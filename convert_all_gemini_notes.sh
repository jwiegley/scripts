#!/bin/bash
# Batch convert all Gemini meeting notes in a directory

# Usage: ./convert_all_gemini_notes.sh [directory]
# If no directory specified, uses current directory
# Batch mode preserves transcript text by default while still using the local
# model to infer missing tasks. Set GEMINI_TO_ORG_USE_LLM=1 to enable every
# local model feature, or GEMINI_TO_ORG_INFER_TRANSCRIPT_TASKS=0 to disable
# task inference too. Configure access with CLAUDE_BASE_URL and CLAUDE_API_KEY.

DIR="${1:-.}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
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

base_url="${CLAUDE_BASE_URL:-http://localhost:8317}"
if [ -z "${CLAUDE_API_KEY:-}" ]; then
    case "$base_url" in
        http://localhost|http://localhost:*|http://127.0.0.1|http://127.0.0.1:*|http://[::1]|http://[::1]:*)
            export CLAUDE_API_KEY="${GEMINI_TO_ORG_LOCAL_AUTH:-local-endpoint}"
            ;;
    esac
fi

echo "Converting Gemini notes in: $DIR"
echo "======================================"
echo ""

converted=0
skipped=0
errors=0

for file in "$DIR"/*"Notes by Gemini.md"; do
    # Skip if no files match the pattern
    if [ ! -f "$file" ]; then
        continue
    fi

    basename=$(basename "$file")

    # Run conversion
    if output=$("$CONVERTER" "${converter_args[@]}" "$file" 2>&1); then
        if [ -n "$output" ]; then
            echo "✓ $basename -> $output"
            ((converted++))
        else
            echo "○ $basename (skipped)"
            ((skipped++))
        fi
    else
        echo "✗ $basename (error)"
        if [ -n "$output" ]; then
            printf '%s\n' "$output" | sed 's/^/  /'
        fi
        ((errors++))
    fi
done

echo ""
echo "======================================"
echo "Summary:"
echo "  Converted: $converted"
echo "  Skipped:   $skipped"
echo "  Errors:    $errors"

if [ "$errors" -gt 0 ]; then
    exit 1
fi
