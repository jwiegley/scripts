#!/bin/bash

#if [[ "$1" == -a ]]; then
#    shift 1
#    exec autossh -M 0 -t "$@" exec screen -UDR
#else
    #exec ssh -t "$@" exec screen -UDR

if [[ "$1" == "jw" ]]; then
    for i in 2143 5622 8307 ; do
        telnet newartisans.com $i
    done > /dev/null 2>&1
fi

mosh "$@" -- screen -UDR

if [[ "$1" == "jw" ]]; then
    for i in 1995 2034 6327 ; do
        telnet newartisans.com $i
    done > /dev/null 2>&1
fi

#fi
