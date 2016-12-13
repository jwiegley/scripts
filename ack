#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

exec rg --color=always -j4 -nH -e "$@"
