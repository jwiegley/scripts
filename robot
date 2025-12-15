#!/usr/bin/env bash

export ANTHROPIC_API_KEY=$(pass positron/api.anthropic.com | head -1)
export GEMINI_API_KEY=$(pass positron/api.gemini.com | head -1)

exec droid "$@"
