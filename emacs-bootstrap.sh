#!/bin/bash

set -e

#make uninstall
test -f Makefile && make distclean
#rm -fr /Application/Misc/Emacs.app
#rm -fr /usr/local/stow/emacs-release

./configure --with-${1:-ns} CFLAGS=-O3 \
    --prefix=/usr/local/stow/$(basename "$(pwd)") \
    CPPFLAGS=-I/opt/local/include LDFLAGS=-L/opt/local/lib

nice -n 20 make -j12 bootstrap
#make install
