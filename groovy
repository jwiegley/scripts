#!/bin/bash

script="$1"
shift 1

if [[ ! ${script[0]} =~ "^/" ]]; then
    script="$PWD/$script"
fi

ng groovy.ui.GroovyMain "$script" "$@"
