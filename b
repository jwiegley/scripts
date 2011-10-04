#!/bin/bash

if [[ "$1" == -t ]]; then
    shift 1
    exec git branch -v "$@" | cut -c 1-108
else
    exec git branch --color -v "$@" | egrep -v '\<(t|dwallin|eniebler|dabrahams|ssomani)\/' | cut -c 1-108 | grep -v remotes/cvs
fi
