#!/bin/bash

if [[ "$1" == -t ]]; then
    shift 1
    exec git branch -v "$@"
else
    exec git branch --color -va "$@" | egrep -v '\<(t|dwallin)\/'
fi
