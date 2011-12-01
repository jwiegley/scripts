#!/bin/bash

echo -ne "\033]0;" "$@" "\007"

if [[ "$1" == -a ]]; then
    shift 1
    exec autossh -M 0 -t "$@" exec screen -UDR
else
    exec ssh -t "$@" exec screen -UDR
fi
