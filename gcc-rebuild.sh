#!/bin/bash

major=4.7
minor=0

set -e

make distclean

./configure                                     \
    --with-mpc=/opt/local                       \
    --with-gmp=/opt/local                       \
    --with-mpfr=/opt/local                      \
    --enable-languages=c,c++                    \
    --enable-stage1-checking                    \
    --disable-nls                               \
    --prefix=/usr/local/stow/gcc-${major}       \
    --with-system-zlib                          \
    --program-suffix=-mp-${major}               \
    --disable-multilib                          \
    --enable-fully-dynamic-string

make "$@"

make install

exit 0