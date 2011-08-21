#!/bin/bash

major=4.7
minor=0

set -e

make distclean

./configure                                                     \
    --with-mpc=/opt/local                                       \
    --with-gmp=/opt/local                                       \
    --with-mpfr=/opt/local                                      \
    --enable-languages=c,c++                                    \
    --enable-stage1-checking                                    \
    --disable-nls                                               \
    --disable-multilib                                          \
    --prefix=/usr/local/stow/gcc-${major}-$(date +%Y%m%d)       \
    --with-system-zlib                                          \
    --program-suffix=-mp-${major}

make -j4

make install

exit 0