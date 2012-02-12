#!/bin/bash

set -e

test -f Makefile && make uninstall
test -f Makefile && make distclean
rm -fr /Application/Misc/Emacs.app

(cd /usr/local/stow; sudo stow -D emacs-release)
rm -fr /usr/local/stow/emacs-release

./configure --with-mac CFLAGS=-O3 \
    --prefix=/usr/local/stow/emacs-release \
    --enable-mac-app=/Applications/Misc \
    CPPFLAGS=-I/opt/local/include LDFLAGS=-L/opt/local/lib

nice -n 20 make $@
make install

(cd /usr/local/stow; sudo stow emacs-release)
