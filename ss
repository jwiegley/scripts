#!/bin/bash
#exec ssh -t "$@" exec screen -UDR
echo -ne "\033]0;" "$@" "\007"
exec autossh -M 0 -t "$@" exec screen -UDR
