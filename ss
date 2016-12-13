#!/bin/bash

if [[ "$1" == "jw" ]]; then
    for i in 2143 5622 8307 ; do
        socat file:/dev/null tcp:208.82.103.192:$i,connect-timeout=1
    done > /dev/null 2>&1
elif [[ "$1" == "jw3" ]]; then
    for i in 2143 5622 8307 ; do
        socat file:/dev/null tcp:208.82.102.85:$i,connect-timeout=1
    done > /dev/null 2>&1
fi

ssh -t "$@" exec screen -UDR || ssh -t "$@"

if [[ "$1" == "jw" ]]; then
    for i in 1995 2034 6327 ; do
        socat file:/dev/null tcp:208.82.103.192:$i,connect-timeout=1
    done > /dev/null 2>&1
elif [[ "$1" == "jw3" ]]; then
    for i in 1995 2034 6327 ; do
        socat file:/dev/null tcp:208.82.102.85:$i,connect-timeout=1
    done > /dev/null 2>&1
fi
