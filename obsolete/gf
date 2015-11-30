#!/bin/bash

args=""
while [[ $1 != '-e' && $1 != '-i' && $1 =~ ^- ]]; do
    args="$args $1 $2"
    shift 2
done

exec find . $args                               \
    -name '.hsenv_*' -type d -prune -o          \
    -name .git -type d -prune -o                \
    -name .shelly -type d -prune -o             \
    -name .svn -type d -prune -o                \
    -name CVS -type d -prune -o                 \
    -name _darcs -type d -prune -o              \
    -name cabal-dev -type d -prune -o           \
    -name dist -type d -prune -o                \
    \! -name '*.bz2'                            \
    \! -name '*.gif'                            \
    \! -name '*.gz'                             \
    \! -name '*.hi'                             \
    \! -name '*.jpg'                            \
    \! -name '*.o'                              \
    \! -name '*.p_o'                            \
    \! -name '*.pdf'                            \
    \! -name '*.png'                            \
    \! -name '*.xz'                             \
    -type f -print0 | xargs -P4 -0 egrep "$*"
