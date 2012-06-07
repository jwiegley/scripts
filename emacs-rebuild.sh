#!/bin/bash

set -e

test -f Makefile && make uninstall
test -f Makefile && make distclean

rm -fr /Application/Misc/Emacs.app

(cd /usr/local/stow; sudo stow -D emacs-release)
rm -fr /usr/local/stow/emacs-release

./configure --prefix=/usr/local/stow/emacs-release \
    --with-mac --enable-mac-app=/Applications/Misc \
    CC=/usr/local/bin/clang CFLAGS=-O3 \
    CPPFLAGS=-I/opt/local/include LDFLAGS="-O3 -L/opt/local/lib"

nice -n 20 make $@
make install

rm -f /usr/local/stow/emacs-release/share/info/dir
(cd /usr/local/stow; sudo stow emacs-release)

exit 0
