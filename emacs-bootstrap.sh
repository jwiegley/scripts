#!/bin/bash

set -e

DEVEL=$HOME/.emacs.d/devel

cd $DEVEL/build

make clean

../configure \
    --with-${1:-ns} \
    --prefix=$DEVEL/installed \
    --enable-asserts \
    CFLAGS='-g2 -ggdb' \
    CPPFLAGS=-I/opt/local/include \
    LDFLAGS=-L/opt/local/lib

nice -n 20 make bootstrap
#nice -n 20 make install
