#!/usr/bin/env bash

if [[ -f .makefile ]]; then
    exec make -f .makefile "$@"
elif [[ -f ../.makefile ]]; then
    exec make -C .. -f .makefile "$@"
elif [[ -f ../../.makefile ]]; then
    exec make -C ../.. -f .makefile "$@"
elif [[ -f ../../../.makefile ]]; then
    exec make -C ../../.. -f .makefile "$@"
elif [[ -f ../../../../.makefile ]]; then
    exec make -C ../../../.. -f .makefile "$@"
else
    exec make "$@"
fi
