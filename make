#!/bin/sh

if [ "$(uname -p)" = "powerpc" ]; then
    exec /usr/bin/make "$@"
else
    exec /usr/bin/make -j3 "$@"
fi
