#!/bin/bash
echo -ne "\033]0;" "$@" "\007"
exec ssh -t "$@" exec screen -UDR
#exec autossh -M 0 -t "$@" exec screen -UDR
