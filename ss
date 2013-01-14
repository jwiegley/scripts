#!/bin/bash

#if [[ "$1" == -a ]]; then
#    shift 1
#    exec autossh -M 0 -t "$@" exec screen -UDR
#else
    #exec ssh -t "$@" exec screen -UDR
    exec mosh "$@" -- screen -UDR
#fi
