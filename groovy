#!/bin/bash

script="$1"
shift 1

#if [[ $script =~ '^/' ]]; then
#    script="$script"
#else
#    script="$PWD/$script"
#fi

ng groovy.ui.GroovyMain "$script" "$@"
