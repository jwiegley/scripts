#!/usr/bin/env bash
export PATH=/etc/profiles/per-user/johnw/bin:$PATH
exec uvx --python 3.12 --no-config --from 'aider-chat[browser]' aider -- "$@"
