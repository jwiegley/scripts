#!/bin/bash

set -e

#make uninstall
test -f Makefile && make distclean
#rm -fr /Application/Misc/Emacs.app
#rm -fr /usr/local/stow/emacs-release

./configure --with-${1:-mac} CFLAGS=-O3 \
    --prefix=/usr/local/stow/emacs-release \
    --enable-mac-app=/Applications/Misc \
    CPPFLAGS=-I/opt/local/include LDFLAGS=-L/opt/local/lib

nice -n 20 make -j12
#make install
